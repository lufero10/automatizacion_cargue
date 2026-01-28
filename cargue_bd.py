import arcpy
import json
import os
from datetime import datetime
import pandas as pd
import numpy as np
from utils.espacializaciontematica import espacializacion
#from utils.reglas.dcvg_reglas import REGLAS_TEMATICA
from utils.reglas.reglas_tematicas import REGLAS_TEMATICA

# -------------------------------------------------------------------
# 🗂️ Geodatabase temporal de trabajo
# -------------------------------------------------------------------
GDB_DESTINO = arcpy.env.scratchGDB
print(f"⚙️  Geodatabase temporal establecida: {GDB_DESTINO}")

def detectar_tipo_dato_arcgis(tipo_pandas):
    """
    Convierte tipos de pandas a tipos de campo ArcGIS.
    """
    if pd.api.types.is_integer_dtype(tipo_pandas):
        return "LONG"
    elif pd.api.types.is_float_dtype(tipo_pandas):
        return "DOUBLE"
    elif pd.api.types.is_bool_dtype(tipo_pandas):
        return "SHORT"
    elif pd.api.types.is_datetime64_any_dtype(tipo_pandas):
        return "DATE"
    elif pd.api.types.is_object_dtype(tipo_pandas):
        return "TEXT"
    else:
        # Fallback: por seguridad, usar texto
        return "TEXT"


def cargar_df_a_tabla(df, gdb_destino, nombre_tabla):
    """
    Crea una tabla en la geodatabase y carga los datos del DataFrame.
    Maneja correctamente valores nulos (pd.NA, np.nan) y tipos compatibles con ArcGIS.
    """
    import arcpy
    import numpy as np
    import pandas as pd
    import os

    tabla_destino = os.path.join(gdb_destino, nombre_tabla)

    # ---------------------------------------------------------
    # 🧹 Si existe la tabla, eliminarla (para sobreescritura)
    # ---------------------------------------------------------
    if arcpy.Exists(tabla_destino):
        print(f"Sobreescribiendo la tabla existente: {tabla_destino}")
        arcpy.Delete_management(tabla_destino)

    # ---------------------------------------------------------
    # 🏗️ Crear tabla vacía
    # ---------------------------------------------------------
    print(f"Creando la tabla '{nombre_tabla}' en {gdb_destino}...")
    arcpy.CreateTable_management(gdb_destino, nombre_tabla)

    # ---------------------------------------------------------
    # 🧩 Crear campos según tipos detectados
    # ---------------------------------------------------------
    print("Agregando campos a la tabla...")
    print("📊 Tipos de datos detectados en df:")
    print(df.dtypes)

    for col, tipo in df.dtypes.items():
        # 🔒 Saltar campos reservados de ArcGIS
        if col.upper() in ["OBJECTID", "SHAPE", "SHAPE_LENGTH", "SHAPE_AREA"]:
            continue

        tipo_dato = detectar_tipo_dato_arcgis(tipo)
        try:
            arcpy.AddField_management(tabla_destino, col, tipo_dato)
        except Exception as e:
            print(f"⚠️ Error al agregar el campo {col}: {e}")

    # ---------------------------------------------------------
    # 🧹 Limpieza de valores incompatibles con ArcGIS
    # ---------------------------------------------------------
    # Convertir pd.NA, np.nan, y NaT en None (ArcGIS acepta None como valor nulo)
    df = df.replace({pd.NA: None, np.nan: None})
    df = df.where(pd.notnull(df), None)

    # Convertir columnas datetime a tipo string si ArcGIS no las acepta como date
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str).replace("NaT", None)

    # ---------------------------------------------------------
    # 💾 Insertar filas del DataFrame en la tabla
    # ---------------------------------------------------------
    campos_reservados = ["OBJECTID", "SHAPE", "SHAPE_LENGTH", "SHAPE_AREA"]
    # 1. Definir la lista de campos a insertar (solo campos válidos)
    campos_insertar = [c for c in df.columns if c.upper() not in campos_reservados]
    print(f"📥 Insertando {len(df)} registros en {nombre_tabla}...")

    # 2. Slice the DataFrame to match the insertion fields EXACTLY
    df_a_insertar = df[campos_insertar]  # <--- Esto asegura que el orden es correcto

    with arcpy.da.InsertCursor(tabla_destino, campos_insertar) as cursor:
        # Iterar sobre las filas del DataFrame ya filtrado
        for i, row in enumerate(df_a_insertar.itertuples(index=False), start=1):
            try:
                # Convertir el NamedTuple de itertuples a una lista de Python simple
                cursor.insertRow(list(row))
            except Exception as e:
                # Si el error es el de tamaño, imprimir la lista de campos y la longitud de la fila
                if "fields size must match size of the row" in str(e):
                    print(f"⚠️ ERROR DE TAMAÑO EN FILA {i}:")
                    print(f"   Campos esperados por ArcPy: {len(campos_insertar)}")
                    print(f"   Campos de la fila de Pandas: {len(row)}")
                print(f"⚠️ Error al insertar fila {i}: {e}")

    print(f"✅ Tabla '{nombre_tabla}' creada y cargada correctamente.")


def asignar_globalid(df_secundario, cobdestino, inspection_type_json, fecha_cargue=None):
    """
    Asigna el GLOBALID desde el feature class principal a la tabla secundaria
    usando ENGROUTEID, CONTRACTNUMBER y la fecha de cargue.
    """
    if fecha_cargue is None:
        fecha_cargue = datetime.now().strftime("%Y-%m-%d")

    fields = ["GLOBALID", "ENGROUTEID", "CONTRACTNUMBER", "CREATIONDATE", "INSPECTIONTYPE"]

    print(f"📄 Asignando INSPECTIONRANGE_GlobalID desde {os.path.basename(cobdestino)}...")

    try:
        data_fc = [row for row in arcpy.da.SearchCursor(cobdestino, fields)]
        df_fc = pd.DataFrame(data_fc, columns=fields)

        df_fc = df_fc[
            (df_fc["INSPECTIONTYPE"].str.upper() == inspection_type_json.strip().upper()) &
            (df_fc["CREATIONDATE"].dt.strftime("%Y-%m-%d") == fecha_cargue)
        ][["GLOBALID", "ENGROUTEID", "CONTRACTNUMBER"]]

        df_fc = df_fc.rename(columns={"GLOBALID": "INSPECTIONRANGE_GlobalID"})

        for col in ["ENGROUTEID", "CONTRACTNUMBER"]:
            df_fc[col] = df_fc[col].astype(str)
            df_secundario[col] = df_secundario[col].astype(str)

        df_secundario = df_secundario.merge(df_fc, on=["ENGROUTEID", "CONTRACTNUMBER"], how="left")

        missing = df_secundario["INSPECTIONRANGE_GlobalID"].isna().sum()
        print(f"✅ INSPECTIONRANGE_GlobalID asignado. Registros sin asignar: {missing}")

    except Exception as e:
        print(f"❌ Error al asignar GLOBALID: {e}")

    return df_secundario


def cargue_bd(fc, tematica, mapeo_tematica, gdb_destino):
    """
    Carga información desde un feature class (fc) a las tablas destino (Principal y Secundaria)
    usando la configuración de mapeo JSON proporcionada, con invocación de reglas unificada.
    """

    print("🔎 Iniciando cargue a BD...")
    print(f"📁 Feature class de origen: {fc}")
    print(f"📘 Temática seleccionada: {tematica}")

    if mapeo_tematica is None or mapeo_tematica.get("tipo") != "complejo":
        print("❌ El mapeo no es válido o no es de tipo 'complejo'.")
        return

    # --- 1. CONFIGURACIÓN ÚNICA Y EXTRACCIÓN (E) ---

    # Propiedades de la GDB Empresarial (SDE)
    GDB_UPDM = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde"
    # --- Sección de conexión en cargue_bd.py ---
    DESC = arcpy.Describe(gdb_destino)  # Usamos el destino que entra por parámetro
    TIPO_DB = DESC.workspaceType

    if TIPO_DB == "RemoteDatabase":
        # Solo las SDE tienen connectionProperties
        CP = DESC.connectionProperties
        DB_NAME = getattr(CP, 'database', '')
        NOMBRE_DB_PREFIX = f"{DB_NAME}.DBO." if DB_NAME else "DBO."
        CURRENT_USER = getattr(CP, 'user', 'Unknown')
    else:
        # Si es File GDB local (como la de tu log), no hay prefijos de servidor
        NOMBRE_DB_PREFIX = ""
        CURRENT_USER = "LocalUser"
        arcpy.AddMessage("ℹ️ Destino detectado como GDB Local. Omitiendo propiedades de conexión SDE.")

    # Cargar Feature Class ÚNICO a DataFrame
    try:
        campos_fc = [f.name for f in arcpy.ListFields(fc)]
        df_origen = pd.DataFrame([row for row in arcpy.da.SearchCursor(fc, campos_fc)], columns=campos_fc)
        print(f"📊 Total de registros en el feature class (origen): {len(df_origen)}")
    except Exception as e:
        arcpy.AddError(f"Error al cargar el feature class en DataFrame: {e}")
        return

    # --- 2. DEFINICIÓN DINÁMICA DE COMPONENTES ---

    componentes = [
        {"nombre_logico": "Tabla Principal", "config": mapeo_tematica["tabla_principal"], "es_principal": True},
        {"nombre_logico": "Tabla Secundaria", "config": mapeo_tematica["tabla_secundaria"], "es_principal": False}
    ]

    # --- 3. PROCESO ETL Y ESPACIALIZACIÓN ITERATIVO ---

    # Variables de Espacialización (Constantes)
    campo_engrid = 'ENGROUTEID'
    centerline = os.path.join(gdb_destino, "P_centerline")
    campo_routeid = 'ENGROUTEID'
    sr = 'GEOGCS["GCS_MAGNA",DATUM["D_MAGNA",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 1000;8.98315284119521E-09;0.001;0.002;IsHighPrecision'

    cobdestino_principal = None

    for comp in componentes:
        nombre_logico = comp["nombre_logico"]

        # Extracción de la configuración del JSON
        nombre_tabla_fc = comp["config"]["nombre"]
        mapeo_campos = comp["config"]["campos"]
        es_principal = comp["es_principal"]
        tipo_espacial = comp["config"].get("tipo_espacial")
        nombre_funcion_reglas = comp["config"].get("funcion_reglas")

        if not tipo_espacial or not nombre_funcion_reglas:
            print(f"❌ Error: Configuración incompleta en {nombre_logico}. Faltan 'tipo_espacial' o 'funcion_reglas'.")
            continue

        print(f"\n--- 🔄 Procesando {nombre_logico}: {nombre_tabla_fc} ---")

        # 3.1. Copia, Renombre y Transformación (T)
        df_componente = df_origen.copy()
        df_componente.rename(columns=mapeo_campos, inplace=True)

        # -------------------------------------------------------------
        # 3.2. Aplicar Reglas (Lógica UNIFICADA por JSON)
        # -------------------------------------------------------------

        # Buscar la función en el catálogo importado
        funcion_reglas = REGLAS_TEMATICA.get(nombre_funcion_reglas)

        if funcion_reglas:
            print(f"   Aplicando reglas: {nombre_funcion_reglas}...")

            # Ejecución unificada: Pasa los tres argumentos (df, CURRENT_USER, mapeo_tematica)
            df_componente = funcion_reglas(df_componente, CURRENT_USER, mapeo_tematica)

            ############################PRUEBAS############################

            # 🚀 PUNTO DE INSPECCIÓN CRÍTICO AÑADIDO AQUÍ 🚀
            print("\n--- 🔎 DIAGNÓSTICO: COLUMNAS DEL DATAFRAME DESPUÉS DE REGLAS ---")
            print("Total de columnas:", len(df_componente.columns))
            print("Nombres de columnas:", list(df_componente.columns))
            print("-------------------------------------------------------------------\n")
            # ---------------------------------------------------------------------------





            # --- Lógica de RELACIÓN (GLOBALID) ---
            # Este paso es exclusivo de la tabla Secundaria y se ejecuta DESPUÉS de sus reglas.
            if not es_principal:
                inspection_type_json = mapeo_tematica.get("inspection_type")
                if cobdestino_principal:
                    # La función asignar_globalid requiere el destino de la tabla principal.
                    df_componente = asignar_globalid(df_componente, cobdestino_principal, inspection_type_json)
                else:
                    print(
                        "⚠️ ERROR: No se encontró el destino principal para asignar GLOBALID. Imposible crear relación.")
        else:
            print(f"⚠️ No se encontró función de reglas para '{nombre_funcion_reglas}' en REGLAS_TEMATICA.")

        # 3.3. Carga (L) a Tabla
        cargar_df_a_tabla(df_componente, gdb_destino, nombre_tabla_fc)
        print(f"✅ {nombre_logico} cargada correctamente en GDB temporal.")

        # 3.4. Espacialización
        ft = os.path.join(gdb_destino, nombre_tabla_fc)
        out_fc = os.path.join(gdb_destino, f"{nombre_tabla_fc}_Espacializada")
        cobdestino = os.path.join(GDB_UPDM, f"{NOMBRE_DB_PREFIX}P_Integrity", nombre_tabla_fc)

        # Almacenar el destino de la principal para el paso 3.2.
        if es_principal:
            cobdestino_principal = cobdestino

        espacializacion(
            ft, campo_engrid, out_fc, centerline, campo_routeid,
            tipo_espacial, sr, cobdestino
        )
        print(f"✨ Espacialización de {nombre_logico} finalizada e insertada en SDE.")

    print("\n🏁 Cargue completo.")
















# def cargue_bd(fc, tematica, mapeo_tematica, gdb_destino):
#     """
#     Carga información desde un feature class a la tabla destino
#     aplicando las reglas específicas según la temática.
#     """
#
#     print("🔎 Iniciando cargue a BD...")
#     print(f"📁 Feature class recibido: {fc}")
#     print(f"📘 Temática seleccionada: {tematica}")
#
#     if mapeo_tematica is None:
#         print("❌ No se encontró un mapeo para la temática proporcionada.")
#         return
#
#     tipo_tematica = mapeo_tematica.get("tipo", "sencillo")
#
#     # ================================================================
#     # 1️⃣ PROCESO TABLA PRINCIPAL
#     # ================================================================
#     if tipo_tematica == "complejo":
#         tabla_principal = mapeo_tematica.get("tabla_principal", {})
#         nombre_tabla = tabla_principal.get("nombre", "")
#         campos = tabla_principal.get("campos", {})
#     else:
#         nombre_tabla = mapeo_tematica.get("tabla", "")
#         campos = mapeo_tematica.get("campos", {})
#
#     # Cargar Feature Class en DataFrame
#     try:
#         campos_fc = [f.name for f in arcpy.ListFields(fc)]
#         data = [row for row in arcpy.da.SearchCursor(fc, campos_fc)]
#         df = pd.DataFrame(data, columns=campos_fc)
#         print(f"📊 Total de registros en el feature class: {len(df)}")
#     except Exception as e:
#         arcpy.AddError(f"Error al cargar el feature class en DataFrame: {e}")
#         return
#
#     # Renombrar columnas según mapeo
#     df.rename(columns=campos, inplace=True)
#
#     # Aplicar reglas según temática
#     funcion_reglas = REGLAS_TEMATICA.get(tematica)
#     if funcion_reglas:
#         df = funcion_reglas(df)
#     else:
#         print(f"⚠️ No se encontró función de reglas para la temática '{tematica}'")
#
#     # Cargar DataFrame a la tabla de destino
#     cargar_df_a_tabla(df, gdb_destino, nombre_tabla)
#
#     # ================================================================
#     # 2️⃣ ESPACIALIZACIÓN DE TABLA PRINCIPAL
#     # ================================================================
#     GDB_UPDM = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde"
#     DESC = arcpy.Describe(GDB_UPDM)
#     CP = DESC.connectionProperties
#     TIPO_DB = DESC.workspaceType
#     NOMBRE_DB = CP.database + ".DBO." if TIPO_DB == "RemoteDatabase" else ""
#     CURRENT_USER = CP.user
#
#     nombre_tabla_fc = 'P_InspectionRange_1'
#     ft = os.path.join(gdb_destino, nombre_tabla_fc)
#     campo_engrid = 'ENGROUTEID'
#     out_fc = os.path.join(gdb_destino, f"{nombre_tabla_fc}_Espacializada")
#     centerline = os.path.join(gdb_destino, "P_centerline")
#     campo_routeid = 'ENGROUTEID'
#     tipo_dato = 'Linea Abscisado'
#     sr = 'GEOGCS["GCS_MAGNA",DATUM["D_MAGNA",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 1000;8.98315284119521E-09;0.001;0.002;IsHighPrecision'
#     cobdestino = os.path.join(GDB_UPDM, f"{NOMBRE_DB}P_Integrity", nombre_tabla_fc)
#
#     espacializacion(ft, campo_engrid, out_fc, centerline, campo_routeid, tipo_dato, sr, cobdestino)
#
#     # ================================================================
#     # 3️⃣ PROCESO TABLA SECUNDARIA (si existe en el JSON)
#     # ================================================================
#     if "tabla_secundaria" in mapeo_tematica:
#         print("🔄 Procesando tabla secundaria...")
#
#         tabla_secundaria = mapeo_tematica["tabla_secundaria"]
#         nombre_tabla_sec = tabla_secundaria.get("nombre", "")
#         campos_sec = tabla_secundaria.get("campos", {})
#
#         # Cargar nuevamente el feature class (puede ajustarse a otra fuente)
#         try:
#             campos_fc_sec = [f.name for f in arcpy.ListFields(fc)]
#             data_sec = [row for row in arcpy.da.SearchCursor(fc, campos_fc_sec)]
#             df_secundario = pd.DataFrame(data_sec, columns=campos_fc_sec)
#             print(f"📊 Total de registros para tabla secundaria: {len(df_secundario)}")
#         except Exception as e:
#             arcpy.AddError(f"Error al cargar el feature class secundario: {e}")
#             return
#
#         #boRRAR
#         cols_antes = df_secundario.columns.tolist()
#
#         # Renombrar columnas según mapeo
#         df_secundario.rename(columns=campos_sec, inplace=True)
#
#         ###BORRAR
#         cols_despues = df_secundario.columns.tolist()
#
#         print("🔍 Cambios en nombres de columnas:")
#         for c1, c2 in zip(cols_antes, cols_despues):
#             if c1 != c2:
#                 print(f" - {c1} → {c2}")
#
#         # 🔸 Aplicar reglas específicas de DCVG secundario
#         df_secundario = reglas_dcvg_secundario(df_secundario, CURRENT_USER, mapeo_tematica)
#
#         # Asignar GLOBALID desde tabla principal
#         inspection_type_json = mapeo_tematica.get("inspection_type", "DCVG")
#         df_secundario = asignar_globalid(df_secundario, cobdestino, inspection_type_json)
#
#         # Cargar la tabla secundaria en la GDB
#         cargar_df_a_tabla(df_secundario, gdb_destino, nombre_tabla_sec)
#
#         print(f"✅ Tabla secundaria '{nombre_tabla_sec}' cargada correctamente con referencia al GLOBALID.")
#
#     else:
#         print("ℹ️ No se definió tabla secundaria en el JSON. Proceso finalizado.")
#
#     # ================================================================
#     # ESPACIALIZACIÓN DE TABLA SECUNDARIA
#     # ================================================================
#     GDB_UPDM = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde"
#     DESC = arcpy.Describe(GDB_UPDM)
#     CP = DESC.connectionProperties
#     TIPO_DB = DESC.workspaceType
#     NOMBRE_DB = CP.database + ".DBO." if TIPO_DB == "RemoteDatabase" else ""
#     CURRENT_USER = CP.user
#
#     nombre_tabla_fc = 'P_DASurveyReadings_1'
#     ft = os.path.join(gdb_destino, nombre_tabla_fc)
#     campo_engrid = 'ENGROUTEID'
#     out_fc = os.path.join(gdb_destino, f"{nombre_tabla_fc}_Espacializada")
#     centerline = os.path.join(gdb_destino, "P_centerline")
#     campo_routeid = 'ENGROUTEID'
#     tipo_dato = 'Coordenadas XYZ'
#     sr = 'GEOGCS["GCS_MAGNA",DATUM["D_MAGNA",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 1000;8.98315284119521E-09;0.001;0.002;IsHighPrecision'
#     cobdestino = os.path.join(GDB_UPDM, f"{NOMBRE_DB}P_Integrity", nombre_tabla_fc)
#
#     espacializacion(ft, campo_engrid, out_fc, centerline, campo_routeid, tipo_dato, sr, cobdestino)
#
#
#     print("🏁 Cargue completo.")






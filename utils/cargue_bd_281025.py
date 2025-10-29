import arcpy
import json
import os
from datetime import datetime
import pandas as pd
import numpy as np
from utils.espacializaciontematica import espacializacion

# Importar reglas por temática
from utils.reglas.dcvg_reglas import aplicar_reglas_dcvg
from utils.reglas.dcvg_reglas import reglas_dcvg_secundario



# BASE_DIR = os.path.dirname(__file__)
# PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))  # sube un nivel desde utils
# GDB_DESTINO = os.path.join(PROJECT_DIR, "sde", "TGI_UPDM.sde")

GDB_DESTINO = r'D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\Centerline.gdb'

#
# print("GDB_DESTINO:", GDB_DESTINO)
# desc = arcpy.Describe(GDB_DESTINO)
# print("workspaceType:", desc.workspaceType)

def cargar_json(ruta_json):
    try:
        with open(ruta_json, 'r', encoding='utf-8') as archivo:
            mapeo = json.load(archivo)
        return mapeo
    except Exception as e:
        arcpy.AddError(f"Error al cargar el mapeo desde el archivo JSON: {e}")
        return None

def obtener_mapeo_tematica(tematica, mapeo):
    return mapeo.get(tematica.lower(), None)

def aplicar_reglas_conversion(df, reglas_conversion, campos_agrupacion=None, mapeo_tematica=None):
    if not reglas_conversion:
        return df

    # Aseguramos que agrupación solo tenga columnas válidas
    if campos_agrupacion:
        campos_agrupacion = [c for c in campos_agrupacion if c in df.columns]

    reglas_agg = {}
    duplicados = {}

    # Construcción de reglas
    for columna, operaciones in reglas_conversion.items():
        # Verificar que la columna exista en df
        if columna not in df.columns:
            print(f"⚠️ Columna '{columna}' no encontrada en DF. Se omite.")
            continue

        for operacion, nombres_salida in operaciones.items():
            if not isinstance(nombres_salida, list):
                nombres_salida = [nombres_salida]

            nombre_principal = nombres_salida[0]
            reglas_agg.setdefault(columna, {})[operacion] = nombre_principal

            if len(nombres_salida) > 1:
                duplicados[nombre_principal] = nombres_salida[1:]

    if not reglas_agg:
        print("⚠️ No se construyeron reglas de conversión válidas.")
        return df

    # Transformar en formato válido para agg()
    reglas_pandas = {col: list(ops.keys()) for col, ops in reglas_agg.items()}

    # Ejecutar la agregación
    if campos_agrupacion:
        df_agg = df.groupby(campos_agrupacion).agg(reglas_pandas).reset_index()
    else:
        df_agg = df.agg(reglas_pandas).to_frame().T  # una sola fila

    # Aplanar columnas MultiIndex
    df_agg.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in df_agg.columns]

    # Renombrar columnas según reglas
    renombres = {f"{col}_{op}": nuevo for col, ops in reglas_agg.items() for op, nuevo in ops.items()}
    df_agg = df_agg.rename(columns=renombres)

    # Duplicar columnas
    for col_origen, nuevas in duplicados.items():
        if col_origen in df_agg.columns:
            for nueva in nuevas:
                df_agg[nueva] = df_agg[col_origen]

    return df_agg

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
    else:
        # Valor por defecto para texto
        return "TEXT"



def cargar_df_a_tabla(df, gdb_destino, nombre_tabla):
    """
    Crea una tabla en la geodatabase y carga los datos del DataFrame.
    """
    import arcpy

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
    # 💾 Insertar filas del DataFrame en la tabla
    # ---------------------------------------------------------
    campos_insertar = [c for c in df.columns if c.upper() not in ["OBJECTID", "SHAPE", "SHAPE_LENGTH", "SHAPE_AREA"]]
    print(f"📥 Insertando {len(df)} registros en {nombre_tabla}...")

    with arcpy.da.InsertCursor(tabla_destino, campos_insertar) as cursor:
        for _, row in df[campos_insertar].iterrows():
            cursor.insertRow(row)

    print(f"✅ Tabla '{nombre_tabla}' creada y cargada correctamente.")

def asignar_globalid(df_secundario, cobdestino, inspection_type_json):
    """
    Asigna el GLOBALID desde el feature class principal a la tabla secundaria
    usando ENGROUTEID, CONTRACTNUMBER y la fecha de cargue.

    Parámetros:
        df_secundario (pd.DataFrame): DataFrame de la tabla secundaria.
        cobdestino (str): Ruta del feature class principal en la GDB.
        inspection_type_json (str): Tipo de inspección a filtrar (Ej. "dcvg").

    Retorna:
        pd.DataFrame: DataFrame secundario con INSPECTIONRANGE_GlobalID asignado.
    """

    # 📅 Fecha de cargue (formato YYYY-MM-DD)
    fecha_cargue = datetime.now().strftime("%Y-%m-%d")

    # 🎯 Campos a extraer
    fields = ["GLOBALID", "ENGROUTEID", "CONTRACTNUMBER", "CREATIONDATE", "INSPECTIONTYPE"]

    # 📥 Extraer datos filtrados del feature class
    data_fc = [
        row for row in arcpy.da.SearchCursor(cobdestino, fields)
        if row[4].strip().upper() == inspection_type_json.strip().upper() and row[3].strftime("%Y-%m-%d") == fecha_cargue
    ]

    print(f"🔍 Registros extraídos de {cobdestino}: {len(data_fc)}")

    # Si no hay registros, retornar el DataFrame sin modificaciones
    if not data_fc:
        print("⚠️ No se encontraron registros en la fecha de cargue.")
        return df_secundario

    # Convertir a DataFrame y renombrar GLOBALID
    df_fc = pd.DataFrame(data_fc, columns=fields)[["GLOBALID", "ENGROUTEID", "CONTRACTNUMBER"]]
    df_fc = df_fc.rename(columns={"GLOBALID": "INSPECTIONRANGE_GlobalID"})

    # 🔄 Asegurar que los tipos de datos sean iguales antes del merge
    df_secundario["ENGROUTEID"] = df_secundario["ENGROUTEID"].astype(str)
    df_secundario["CONTRACTNUMBER"] = df_secundario["CONTRACTNUMBER"].astype(str)
    df_fc["ENGROUTEID"] = df_fc["ENGROUTEID"].astype(str)
    df_fc["CONTRACTNUMBER"] = df_fc["CONTRACTNUMBER"].astype(str)

    # 🔄 Asignar `INSPECTIONRANGE_GlobalID` a la tabla secundaria
    df_secundario = df_secundario.merge(df_fc, on=["ENGROUTEID", "CONTRACTNUMBER"], how="left")

    # 🛠️ Validar si hay registros sin `INSPECTIONRANGE_GlobalID`
    missing_globalid = df_secundario["INSPECTIONRANGE_GlobalID"].isna().sum()
    if missing_globalid:
        print(f"⚠️ {missing_globalid} registros en la tabla secundaria no tienen INSPECTIONRANGE_GlobalID asignado.")
    else:
        print("✅ INSPECTIONRANGE_GlobalID asignado correctamente.")

    return df_secundario

# Diccionario para seleccionar la función de reglas según temática
REGLAS_TEMATICA = {
    "dcvg": aplicar_reglas_dcvg
    # "otra_tematica": aplicar_reglas_otra,
}


def cargue_bd(fc, tematica, mapeo_tematica, gdb_destino):
    """
    Carga información desde un feature class a la tabla destino
    aplicando las reglas específicas según la temática.
    """

    print("🔎 Iniciando cargue a BD...")
    print(f"📁 Feature class recibido: {fc}")
    print(f"📘 Temática seleccionada: {tematica}")

    if mapeo_tematica is None:
        print("❌ No se encontró un mapeo para la temática proporcionada.")
        return

    tipo_tematica = mapeo_tematica.get("tipo", "sencillo")

    # ================================================================
    # 1️⃣ PROCESO TABLA PRINCIPAL
    # ================================================================
    if tipo_tematica == "complejo":
        tabla_principal = mapeo_tematica.get("tabla_principal", {})
        nombre_tabla = tabla_principal.get("nombre", "")
        campos = tabla_principal.get("campos", {})
    else:
        nombre_tabla = mapeo_tematica.get("tabla", "")
        campos = mapeo_tematica.get("campos", {})

    # Cargar Feature Class en DataFrame
    try:
        campos_fc = [f.name for f in arcpy.ListFields(fc)]
        data = [row for row in arcpy.da.SearchCursor(fc, campos_fc)]
        df = pd.DataFrame(data, columns=campos_fc)
        print(f"📊 Total de registros en el feature class: {len(df)}")
    except Exception as e:
        arcpy.AddError(f"Error al cargar el feature class en DataFrame: {e}")
        return

    # Renombrar columnas según mapeo
    df.rename(columns=campos, inplace=True)

    # Aplicar reglas según temática
    funcion_reglas = REGLAS_TEMATICA.get(tematica)
    if funcion_reglas:
        df = funcion_reglas(df)
    else:
        print(f"⚠️ No se encontró función de reglas para la temática '{tematica}'")

    # Cargar DataFrame a la tabla de destino
    cargar_df_a_tabla(df, gdb_destino, nombre_tabla)

    # ================================================================
    # 2️⃣ ESPACIALIZACIÓN DE TABLA PRINCIPAL
    # ================================================================
    GDB_UPDM = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde"
    DESC = arcpy.Describe(GDB_UPDM)
    CP = DESC.connectionProperties
    TIPO_DB = DESC.workspaceType
    NOMBRE_DB = CP.database + ".DBO." if TIPO_DB == "RemoteDatabase" else ""
    CURRENT_USER = CP.user

    nombre_tabla_fc = 'P_InspectionRange_1'
    ft = os.path.join(gdb_destino, nombre_tabla_fc)
    campo_engrid = 'ENGROUTEID'
    out_fc = os.path.join(gdb_destino, f"{nombre_tabla_fc}_Espacializada")
    centerline = os.path.join(gdb_destino, "P_centerline")
    campo_routeid = 'ENGROUTEID'
    tipo_dato = 'Linea Abscisado'
    sr = 'GEOGCS["GCS_MAGNA",DATUM["D_MAGNA",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 1000;8.98315284119521E-09;0.001;0.002;IsHighPrecision'
    cobdestino = os.path.join(GDB_UPDM, f"{NOMBRE_DB}P_Integrity", nombre_tabla_fc)

    espacializacion(ft, campo_engrid, out_fc, centerline, campo_routeid, tipo_dato, sr, cobdestino)

    # ================================================================
    # 3️⃣ PROCESO TABLA SECUNDARIA (si existe en el JSON)
    # ================================================================
    if "tabla_secundaria" in mapeo_tematica:
        print("🔄 Procesando tabla secundaria...")

        tabla_secundaria = mapeo_tematica["tabla_secundaria"]
        nombre_tabla_sec = tabla_secundaria.get("nombre", "")
        campos_sec = tabla_secundaria.get("campos", {})

        # Cargar nuevamente el feature class (puede ajustarse a otra fuente)
        try:
            campos_fc_sec = [f.name for f in arcpy.ListFields(fc)]
            data_sec = [row for row in arcpy.da.SearchCursor(fc, campos_fc_sec)]
            df_secundario = pd.DataFrame(data_sec, columns=campos_fc_sec)
            print(f"📊 Total de registros para tabla secundaria: {len(df_secundario)}")
        except Exception as e:
            arcpy.AddError(f"Error al cargar el feature class secundario: {e}")
            return

        # Renombrar columnas según mapeo
        df_secundario.rename(columns=campos_sec, inplace=True)

        # 🔸 Aplicar reglas específicas de DCVG secundario
        df_secundario = reglas_dcvg_secundario(df_secundario, CURRENT_USER, mapeo_tematica)

        # Asignar GLOBALID desde tabla principal
        inspection_type_json = mapeo_tematica.get("inspection_type", "DCVG")
        df_secundario = asignar_globalid(df_secundario, cobdestino, inspection_type_json)

        # Cargar la tabla secundaria en la GDB
        cargar_df_a_tabla(df_secundario, gdb_destino, nombre_tabla_sec)

        print(f"✅ Tabla secundaria '{nombre_tabla_sec}' cargada correctamente con referencia al GLOBALID.")

    else:
        print("ℹ️ No se definió tabla secundaria en el JSON. Proceso finalizado.")

    # ================================================================
    # ESPACIALIZACIÓN DE TABLA SECUNDARIA
    # ================================================================
    GDB_UPDM = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde"
    DESC = arcpy.Describe(GDB_UPDM)
    CP = DESC.connectionProperties
    TIPO_DB = DESC.workspaceType
    NOMBRE_DB = CP.database + ".DBO." if TIPO_DB == "RemoteDatabase" else ""
    CURRENT_USER = CP.user

    nombre_tabla_fc = 'P_DASurveyReadings_1'
    ft = os.path.join(gdb_destino, nombre_tabla_fc)
    campo_engrid = 'ENGROUTEID'
    out_fc = os.path.join(gdb_destino, f"{nombre_tabla_fc}_Espacializada")
    centerline = os.path.join(gdb_destino, "P_centerline")
    campo_routeid = 'ENGROUTEID'
    tipo_dato = 'Coordenadas XYZ'
    sr = 'GEOGCS["GCS_MAGNA",DATUM["D_MAGNA",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 1000;8.98315284119521E-09;0.001;0.002;IsHighPrecision'
    cobdestino = os.path.join(GDB_UPDM, f"{NOMBRE_DB}P_Integrity", nombre_tabla_fc)

    espacializacion(ft, campo_engrid, out_fc, centerline, campo_routeid, tipo_dato, sr, cobdestino)


    print("🏁 Cargue completo.")






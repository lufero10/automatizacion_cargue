import arcpy
import json
import os
from datetime import datetime
import pandas as pd
import numpy as np


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


def cargar_df_a_tabla(df, gdb_scratch, nombre_tabla):
    """
    Carga un DataFrame de Pandas en una Tabla de una Geodatabase.
    Si la tabla ya existe, la elimina y la crea nuevamente.

    Parámetros:
    - df: DataFrame de Pandas con los datos a cargar.
    - gdb_scratch: Geodatabase de destino.
    - nombre_tabla: Nombre de la tabla de destino.
    """

    # Ruta completa de la Tabla destino
    scratch = gdb_scratch
    tabla_destino = os.path.join(scratch, nombre_tabla)

    # Verificar si la tabla ya existe y eliminarla
    if arcpy.Exists(tabla_destino):
        arcpy.AddMessage(f"Sobreescribiendo la tabla existente: {tabla_destino}")
        arcpy.Delete_management(tabla_destino)

    # Crear tabla en la Geodatabase
    arcpy.AddMessage(f"Creando la tabla '{nombre_tabla}' en {scratch}...")
    arcpy.CreateTable_management(scratch, nombre_tabla)

    # Mapeo de tipos de pandas/numpy a ArcGIS
    dtype_to_arcgis = {
        "object": "TEXT",
        "string": "TEXT",
        "bool": "SHORT",
        "int64": "LONG",
        "int32": "LONG",
        "float64": "DOUBLE",
        "float32": "FLOAT",
        "datetime64[ns]": "DATE"
    }

    # Agregar los campos del DataFrame a la tabla
    arcpy.AddMessage("Agregando campos a la tabla...")
    print("📊 Tipos de datos detectados en df:")
    print(df.dtypes)

    for col in df.columns:
        pandas_dtype = str(df[col].dtype)
        tipo_dato = dtype_to_arcgis.get(pandas_dtype, "TEXT")  # Default TEXT

        if tipo_dato == "TEXT":
            arcpy.AddField_management(tabla_destino, col, tipo_dato, field_length=255)
        else:
            arcpy.AddField_management(tabla_destino, col, tipo_dato)

    # Convertir DataFrame a NumPy array compatible con ArcGIS
    dtype_mapping = {
        'int64': np.int32,
        'int32': np.int32,
        'float64': np.float64,
        'float32': np.float32,
        'object': 'U255',
        'string': 'U255',
        'bool': np.int16,
        'datetime64[ns]': 'datetime64[s]'
    }

    structured_array = np.array(
        [tuple(x) for x in df.to_numpy()],
        dtype=[(col, dtype_mapping.get(str(df[col].dtype), 'U255')) for col in df.columns]
    )

    # Crear tabla temporal en memoria
    temp_table = os.path.join("in_memory", "temp_table")
    arcpy.da.NumPyArrayToTable(structured_array, temp_table)

    # Ejecutar Append para cargar los datos en la tabla destino
    try:
        arcpy.Append_management(temp_table, tabla_destino, "NO_TEST")
        arcpy.AddMessage(f"✅ Datos cargados exitosamente en {tabla_destino}")
    except Exception as e:
        arcpy.AddError(f"❌ Error al cargar los datos: {e}")
    finally:
        arcpy.Delete_management(temp_table)  # Eliminar tabla temporal



def cargue_bd(fc, mapeo_tematica, gdb_destino):
    """
    Carga información desde un feature class a las tablas destino
    definidas en el mapeo JSON.

    Parámetros:
    -----------
    fc : str
        Ruta completa del feature class de entrada (ej: scratch.gdb\COBERTURA_FC).
    mapeo_tematica : dict
        Configuración cargada desde el JSON para la temática.
    gdb_destino : str
        Ruta de la geodatabase donde se crearán o actualizarán las tablas destino.
    """

    print("🔎 Iniciando cargue a BD...")
    print(f"📁 Feature class recibido: {fc}")
    print(f"📘 Contenido del mapeo de la temática:\n{mapeo_tematica}")

    # ==========================================================
    # 🔸 Validación inicial del mapeo
    # ==========================================================
    if mapeo_tematica is None:
        print("❌ No se encontró un mapeo para la temática proporcionada.")
        return

    tipo_tematica = mapeo_tematica.get("tipo", "sencillo")

    # ==========================================================
    # 🔸 Identificación de tablas y campos según tipo de temática
    # ==========================================================
    if tipo_tematica == "complejo":
        # ✅ Tablas principales y secundarias
        nombre_tabla = mapeo_tematica.get("tabla_principal", {}).get("nombre", "")
        nombre_tabla_secundaria = mapeo_tematica.get("tabla_secundaria", {}).get("nombre", "")

        campos = mapeo_tematica.get("tabla_principal", {}).get("campos", {})
        campos_secundarios = mapeo_tematica.get("tabla_secundaria", {}).get("campos", {})

        if nombre_tabla:
            print(f"✅ Nombre de la tabla principal: {nombre_tabla}")
        else:
            print("⚠️ No se encontró el nombre de la tabla principal en el mapeo.")

        if nombre_tabla_secundaria:
            print(f"✅ Nombre de la tabla secundaria: {nombre_tabla_secundaria}")
        else:
            print("⚠️ No se encontró el nombre de la tabla secundaria en el mapeo.")

    else:  # 🔹 Caso sencillo
        nombre_tabla = mapeo_tematica.get("tabla", "")
        campos = mapeo_tematica.get("campos", {})
        campos_secundarios = {}

        print(f"✅ Nombre de la tabla sencilla: {nombre_tabla}")

    # ==========================================================
    # 🔸 Listado de campos obligatorios
    # ==========================================================
    campos_obligatorios = list(campos.values())
    print(f"📌 Campos obligatorios en tabla principal ({len(campos_obligatorios)}): {campos_obligatorios}")

    campos_obligatorios_secundarios = list(campos_secundarios.values()) if campos_secundarios else []
    if campos_obligatorios_secundarios:
        print(f"📌 Campos obligatorios en tabla secundaria ({len(campos_obligatorios_secundarios)}): {campos_obligatorios_secundarios}")

    print("🧩 Estructura del mapeo validada correctamente.\n")


    # -------------------------------------------------------------
    # 🔹 Cargar el feature class en un DataFrame de pandas
    # -------------------------------------------------------------
    try:
        # Listar todos los campos disponibles en el feature class
        campos_fc = [f.name for f in arcpy.ListFields(fc)]
        print(f"📋 Campos encontrados en el FC: {campos_fc}")

        # Leer los datos del FC con un SearchCursor
        data = [row for row in arcpy.da.SearchCursor(fc, campos_fc)]
        df = pd.DataFrame(data, columns=campos_fc)

        total_registros = len(df)
        print(f"📊 Total de registros en el feature class: {total_registros}")
        print(f"🔎 Vista previa de columnas en DF: {df.columns.tolist()}")

    except Exception as e:
        arcpy.AddError(f"Error al cargar el feature class en DataFrame: {e}")
        return


    print(df.columns.tolist())
    print("📋 Diccionario de mapeo:", campos)
    df.rename(columns=campos, inplace=True)
    df_original = df.copy()
    print("📝 Copia de seguridad creada: df_original")
    print(df.columns.tolist())

    print("📌 Columnas después del rename:", df.columns.tolist())

    for col in ["ENGFROMM", "ENGTOM"]:
        if col in df.columns:
            print(f"Preview de {col}:")
            print(df[col].head(10))
        else:
            print(f"⚠️ La columna {col} NO existe en el DataFrame")

    # Aplicar reglas específicas de la temática
    from utils.reglas.dcvg_reglas import aplicar_reglas_dcvg
    df = aplicar_reglas_dcvg(df)

    # Adición columnas para cargue
    df['FECHA_CARGUE'] = fecha_cargue
    df['CREATIONDATE'] = fecha_cargue
    df['LASTUPDATE'] = fecha_cargue
    # df['CREATOR'] = current_user
    # df['UPDATEDBY'] = current_user
    df['CREATOR'] = 'usuario_pruebas'
    df['UPDATEDBY'] = 'usuario_pruebas'

    if tipo_tematica == "complejo":
        inspection_type = mapeo_tematica.get("inspection_type", "").strip()
        datype = mapeo_tematica.get("datype", "").strip()
        df['INSPECTIONTYPE'] = inspection_type
        df['DATYPE'] = datype
        print(f"INSPECTIONTYPE asignado: {inspection_type}")
        print(f"DATYPE asignado: {datype}")

    print(10 * '#' + "DF despues de renombrar" + 10 * '#')
    print(df.columns.tolist())
    print(df.head())

    cargar_df_a_tabla(df, GDB_DESTINO, nombre_tabla)



fc = r'C:\Users\TICE21\AppData\Local\Temp\scratch.gdb\COBERTURA_FC'
RUTA_JSON = os.path.join(os.path.dirname(__file__), 'mapeo_tablas_tematicas.json')
mapeo = cargar_json(RUTA_JSON)
tematica = 'dcvg'
mapeo_tematica = obtener_mapeo_tematica(tematica, mapeo)
cargue_bd(fc,mapeo_tematica,GDB_DESTINO)
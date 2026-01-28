import pandas as pd
import numpy as np
from datetime import datetime

def reglas_cips_principal(df, CURRENT_USER, mapeo_tematica):
    """
    Aplica las reglas específicas de la temática CIPS al DataFrame (agregación min/max).
    Utiliza la misma lógica de agregación que DCVG.
    """
    if df.empty:
        return df

    # -------------------------------------------------
    # Campos de agrupación (iguales a DCVG)
    campos_agrupacion = ["ENGROUTEID", "CONTRACTNUMBER"]

    # -------------------------------------------------
    # Reglas de conversión fijas (Basado en los campos de origen)
    reglas_conversion = {
        "ENGM": {
            "min": "ENGFROMM",
            "max": "ENGTOM"
        },
        "Fecha_de_Inspección": {
            "min": "INSPECTIONSTARTDATE",
            "max": ["INSPECTIONENDDATE", "FROMDATE"]
        }
    }

    # -------------------------------------------------
    # Preparación de las reglas para pandas (MISMA LÓGICA DE DCVG)
    reglas_agg = {}
    duplicados = {}
    for columna, operaciones in reglas_conversion.items():
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

    # Formato para pandas agg()
    reglas_pandas = {col: list(ops.keys()) for col, ops in reglas_agg.items()}

    # -------------------------------------------------
    # Aplicar agregación
    if all(c in df.columns for c in campos_agrupacion):
        df_agg = df.groupby(campos_agrupacion).agg(reglas_pandas).reset_index()
    else:
        df_agg = df.agg(reglas_pandas).to_frame().T

    # Aplanar MultiIndex si existe
    df_agg.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in df_agg.columns]

    # Renombrar columnas según reglas
    renombres = {f"{col}_{op}": nuevo for col, ops in reglas_agg.items() for op, nuevo in ops.items()}
    df_agg = df_agg.rename(columns=renombres)

    # Duplicar columnas si aplica
    for col_origen, nuevas in duplicados.items():
        if col_origen in df_agg.columns:
            for nueva in nuevas:
                df_agg[nueva] = df_agg[col_origen]

    # -------------------------------------------------
    # Columnas adicionales de fecha y control (USANDO ARGUMENTOS DINÁMICOS)
    from datetime import datetime
    fecha_cargue = datetime.now().strftime("%Y-%m-%d %H:%M")
    df_agg['FECHA_CARGUE'] = fecha_cargue
    df_agg['CREATIONDATE'] = fecha_cargue
    df_agg['LASTUPDATE'] = fecha_cargue

    df_agg['CREATOR'] = CURRENT_USER
    df_agg['UPDATEDBY'] = CURRENT_USER
    df_agg['INSPECTIONTYPE'] = mapeo_tematica.get("inspection_type", "CIPS")
    df_agg['DATYPE'] = mapeo_tematica.get("datype", "Close Interval Potential Survey")

    return df_agg

def reglas_cips_secundario(df_secundario, CURRENT_USER, mapeo_tematica):
    """
    Aplica las reglas específicas para la tabla secundaria de CIPS (P_DASurveyReadings_1).

    Incluye:
      1. Asignación de campos de control (CREATIONDATE, UPDATEDBY, etc.).
      2. Conversiones específicas (Manejo de nulos en Altitud).
      3. PASO CRÍTICO: Renombramiento y filtrado estricto a las columnas UPDM.
    """

    # -------------------------------------------------
    # 🕒 1. Asignar metadatos de control (Idéntico al estándar DCVG)
    # -------------------------------------------------
    fecha_cargue = datetime.now().strftime("%Y-%m-%d %H:%M")

    df_secundario["FECHA_CARGUE"] = fecha_cargue
    df_secundario["CREATIONDATE"] = fecha_cargue
    df_secundario["LASTUPDATE"] = fecha_cargue
    df_secundario["CREATOR"] = CURRENT_USER
    df_secundario["UPDATEDBY"] = CURRENT_USER
    df_secundario["DATYPE"] = mapeo_tematica.get("datype", "Close Interval Potential Survey")
    df_secundario["DEPTHUNITS"] = 4  # Valor fijo para UPDM

    # -------------------------------------------------
    # 🔄 2. Conversiones específicas CIPS (Manejo de nulos)
    # -------------------------------------------------

    # ⚠️ MANEJO DE NULOS PARA ALTITUD (Equivalente a CASE WHEN [Altitud] IS NULL THEN 0)
    # El campo de origen que ArcPy creó es "Altitud".
    if "Altitud" in df_secundario.columns:
        # Reemplazar valores nulos (NaN) por cero (0) en la columna de Altitud.
        df_secundario["Altitud"] = df_secundario["Altitud"].fillna(0)

    # Nota: Si se requiere manejo de nulos para P_On_mV, P_Off_mV, etc., se añadiría aquí.

    # -------------------------------------------------
    # ⚠️ 3. PASO CRÍTICO: RENOMBRAR Y FILTRAR A DESTINO UPDM
    # Esto elimina columnas sobrantes (OBJECTID, Shape, Distrito) y garantiza el orden correcto.
    # -------------------------------------------------

    mapeo_campos = mapeo_tematica['tabla_secundaria']['campos']

    # 3.1 Renombrar: Convierte los nombres de origen (e.g., 'Altitud') a los de destino UPDM (e.g., 'GPSZ').
    df_secundario = df_secundario.rename(columns=mapeo_campos)

    # 3.2 Definir la lista de columnas de destino final (UPDM)
    columnas_destino = list(mapeo_campos.values())

    # Añadir los campos de auditoría generados en el paso 1
    # ESTE ORDEN DEBE SER CONSISTENTE con el InsertCursor.
    columnas_destino.extend([
        'DATYPE',
        'DEPTHUNITS',
        'CREATIONDATE',
        'LASTUPDATE',
        'CREATOR',
        'UPDATEDBY'
    ])

    # 3.3 FILTRO ESTRICTO: Seleccionar solo las columnas finales y forzar el orden.

    print("\n--- 🔎 DIAGNÓSTICO INTERNO: PRE-FILTRO ESTRICTO ---")
    print("Total de columnas (antes de filtro estricto):", len(df_secundario.columns))
    print("Nombres de columnas:", list(df_secundario.columns))
    print("---------------------------------------------------\n")

    df_secundario = df_secundario[columnas_destino]

    print("\n--- 🔎 DIAGNÓSTICO INTERNO: POST-FILTRO ESTRICTO ---")
    print("Total de columnas (después de filtro estricto):", len(df_secundario.columns))
    print("Nombres de columnas:", list(df_secundario.columns))
    print("---------------------------------------------------\n")


    # -------------------------------------------------
    # ✅ Retornar DataFrame transformado
    # -------------------------------------------------
    return df_secundario
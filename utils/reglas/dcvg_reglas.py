import pandas as pd
import numpy as np
from datetime import datetime

def aplicar_reglas_dcvg(df):
    """
    Aplica las reglas específicas de la temática DCVG al DataFrame.
    Convierte, agrega y duplica columnas según la lógica original de DCVG.
    """
    if df.empty:
        return df

    # -------------------------------------------------
    # Campos de agrupación (fijos para DCVG)
    campos_agrupacion = ["ENGROUTEID", "CONTRACTNUMBER"]

    # -------------------------------------------------
    # Reglas de conversión fijas para DCVG
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
    # Preparación de las reglas para pandas
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
    # Columnas adicionales de fecha y control
    from datetime import datetime
    fecha_cargue = datetime.now().strftime("%Y-%m-%d %H:%M")
    df_agg['FECHA_CARGUE'] = fecha_cargue
    df_agg['CREATIONDATE'] = fecha_cargue
    df_agg['LASTUPDATE'] = fecha_cargue
    df_agg['CREATOR'] = 'usuario_pruebas'
    df_agg['UPDATEDBY'] = 'usuario_pruebas'
    df_agg['INSPECTIONTYPE'] = "DCVG"
    df_agg['DATYPE'] = "Direct Current Voltage Gradient"

    return df_agg

def reglas_dcvg_secundario(df_secundario, CURRENT_USER, mapeo_tematica):
    """Aplica las reglas específicas para la tabla secundaria de DCVG."""
    fecha_cargue = datetime.now().strftime("%Y-%m-%d %H:%M")

    df_secundario['FECHA_CARGUE'] = fecha_cargue
    df_secundario['CREATIONDATE'] = fecha_cargue
    df_secundario['LASTUPDATE'] = fecha_cargue
    df_secundario['CREATOR'] = CURRENT_USER
    df_secundario['UPDATEDBY'] = CURRENT_USER
    df_secundario['DATYPE'] = mapeo_tematica.get("datype", "")

    return df_secundario
def aplicar_reglas_conversiones(df):
    """Aplica conversiones específicas para DCVG."""
    # Conversión de ENGM → ENGFROMM / ENGTOM
    if "ENGM" in df.columns:
        df["ENGFROMM"] = df["ENGM"].min()
        df["ENGTOM"] = df["ENGM"].max()

    # Conversión de Fecha_de_Inspección
    if "Fecha_de_Inspección" in df.columns:
        fecha = pd.to_datetime(df["Fecha_de_Inspección"], errors="coerce")
        df["INSPECTIONSTARTDATE"] = fecha.min()
        df["INSPECTIONENDDATE"] = fecha.max()

    # CARACTER_ON_OFF → CARON / CAROFF
    if "carácter_On_Off" in df.columns:
        df["CARON"] = df["carácter_On_Off"].str[0].map({"A": 1, "C": 2})
        df["CAROFF"] = df["carácter_On_Off"].str[1].map({"A": 1, "C": 2})

    # CLASIFICACION → SEVERITYCLA
    mapa_clasificacion = {
        "Muy Pequeño": 6,
        "Pequeño": 1,
        "Mediano": 2,
        "Mediano-Grande": 3,
        "Grande": 4
    }
    if "CLASIFICACION" in df.columns:
        df["SEVERITYCLA"] = df["CLASIFICACION"].map(mapa_clasificacion)

    return df


def validar_datos(df):
    """Valida reglas de negocio específicas para DCVG."""
    errores = []

    if "ENGROUTEID" in df.columns and df["ENGROUTEID"].isnull().any():
        errores.append("Existen registros sin ENGROUTEID")

    for campo in ["ENGFROMM", "ENGTOM"]:
        if campo in df.columns and (df[campo] < 0).any():
            errores.append(f"El campo {campo} contiene valores negativos")

    if errores:
        print("⚠️ Errores encontrados:")
        for e in errores:
            print(" -", e)
    else:
        print("✅ Validaciones DCVG superadas correctamente.")

    return df

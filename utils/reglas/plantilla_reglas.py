"""
===========================================
 PLANTILLA DE REGLAS Y CONVERSIONES
 Autor: Luigi Reds
 Descripción:
     Este módulo define la estructura base para aplicar
     conversiones y validaciones a un DataFrame antes
     del cargue en una geodatabase.

 Uso:
     1️⃣ Copia este archivo y renómbralo según la temática (ej: dcvg_reglas.py).
     2️⃣ Implementa la lógica en las funciones aplicar_conversiones() y validar_datos().
     3️⃣ Importa y ejecuta estas funciones desde tu flujo principal.

===========================================
"""

import pandas as pd
import numpy as np

# =========================================================
# 🔁 CONVERSIONES ESPECÍFICAS POR TEMÁTICA
# =========================================================
def aplicar_conversiones(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica conversiones específicas de la temática.

    Ejemplo de uso:
        df = aplicar_conversiones(df)

    Parámetros:
        df (DataFrame): Datos cargados desde Excel o CSV.

    Retorna:
        DataFrame con los nuevos campos o valores convertidos.
    """

    # 🧩 Ejemplo: Calcular rango mínimo/máximo de ENGM
    if "ENGM" in df.columns:
        df["ENGFROMM"] = df["ENGM"].min()
        df["ENGTOM"] = df["ENGM"].max()

    # 🧩 Ejemplo: Convertir fecha de inspección
    if "Fecha_de_Inspección" in df.columns:
        fechas = pd.to_datetime(df["Fecha_de_Inspección"], errors="coerce")
        df["INSPECTIONSTARTDATE"] = fechas.min()
        df["INSPECTIONENDDATE"] = fechas.max()

    # ⚙️ Agrega aquí tus conversiones personalizadas...
    # --------------------------------------------------
    # if "Campo1" in df.columns:
    #     df["NuevoCampo"] = df["Campo1"].apply(lambda x: alguna_funcion(x))

    return df


# =========================================================
# ✅ VALIDACIONES DE REGLAS DE NEGOCIO
# =========================================================
def validar_datos(df: pd.DataFrame) -> list:
    """
    Realiza validaciones de negocio sobre los datos.

    Ejemplo de uso:
        errores = validar_datos(df)
        if errores:
            for e in errores: print("❌", e)

    Parámetros:
        df (DataFrame): Datos ya convertidos.

    Retorna:
        Lista de errores detectados.
    """

    errores = []

    # 🔍 Ejemplo: Campos obligatorios
    if "ENGROUTEID" in df.columns and df["ENGROUTEID"].isnull().any():
        errores.append("Existen registros sin ENGROUTEID.")

    # 🔍 Ejemplo: Campos que no deben ser negativos
    for campo in ["ENGFROMM", "ENGTOM"]:
        if campo in df.columns and (df[campo] < 0).any():
            errores.append(f"El campo {campo} contiene valores negativos.")

    # 🔍 Ejemplo: Validación personalizada
    # if "TIPO_EVENTO" in df.columns and "ESPESOR" in df.columns:
    #     mask = (df["TIPO_EVENTO"] == "Pérdida de metal") & (df["ESPESOR"].isnull())
    #     if mask.any():
    #         errores.append("Los registros con 'Pérdida de metal' deben tener ESPESOR.")

    if not errores:
        print("✅ Validaciones completadas: sin errores detectados.")
    else:
        print(f"⚠️ Se detectaron {len(errores)} error(es):")
        for e in errores:
            print("   -", e)

    return errores


# =========================================================
# 🧩 FUNCIONES AUXILIARES OPCIONALES
# =========================================================
def normalizar_texto(df: pd.DataFrame, columnas: list) -> pd.DataFrame:
    """Convierte a mayúsculas y limpia espacios en columnas de texto."""
    for col in columnas:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df


def reemplazar_valores(df: pd.DataFrame, columna: str, mapa: dict) -> pd.DataFrame:
    """Reemplaza valores en una columna según un diccionario de mapeo."""
    if columna in df.columns:
        df[columna] = df[columna].replace(mapa)
    return df

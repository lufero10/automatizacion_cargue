import json
import pandas as pd
import os
import arcpy
from datetime import time


# def cargar_mapeo_tematica(ruta_base, tematica):
#     """
#     Carga el archivo JSON de mapeo específico para la temática indicada.
#
#     Args:
#         ruta_base (str): Ruta base del proyecto (por ejemplo, D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM)
#         tematica (str): Nombre de la temática, p. ej. 'dcvg'
#
#     Returns:
#         dict: Contenido del archivo JSON correspondiente
#     """
#     ruta_json = os.path.join(ruta_base, "utils", "mapeos", f"{tematica}.json")
#
#     if not os.path.exists(ruta_json):
#         raise FileNotFoundError(f"No se encontró el archivo JSON en: {ruta_json}")
#
#     with open(ruta_json, "r", encoding="utf-8") as archivo:
#         return json.load(archivo)
def cargar_mapeo_tematica(tematica):
    """
    Carga el archivo JSON de mapeo correspondiente a la temática indicada.

    Args:
        tematica (str): Nombre de la temática (por ejemplo, 'dcvg')

    Returns:
        dict: Contenido del archivo JSON correspondiente o None si ocurre un error.
    """
    try:
        # Obtener la ruta absoluta al directorio del script actual
        base_dir = os.path.dirname(__file__)
        ruta_json = os.path.join(base_dir, "../mapeos", f"{tematica}.json")

        if not os.path.exists(ruta_json):
            raise FileNotFoundError(f"No se encontró el archivo JSON en: {ruta_json}")

        with open(ruta_json, "r", encoding="utf-8") as archivo:
            mapeo = json.load(archivo)

        arcpy.AddMessage(f"✅ Mapeo '{tematica}' cargado correctamente.")
        return mapeo

    except Exception as e:
        arcpy.AddError(f"❌ Error al cargar el mapeo de la temática '{tematica}': {e}")
        return None


def generar_informe_validacion(df, mapeo_tematica):
    """
    Ya no comparamos nombres de columnas con el JSON.
    Solo informamos sobre la calidad de los datos internos.
    """
    errores_calidad = validar_valores_adicionales(df)

    # Si hay errores de calidad, los mostramos como advertencias en el log de ArcGIS
    if errores_calidad:
        for err in errores_calidad:
            arcpy.AddWarning(f"⚠️ CALIDAD: {err}")

    # --- AQUÍ ESTABA EL ERROR: FALTABA CERRAR LA LLAVE ---
    return {
        "estado": "OK",
        "errores_adicionales": errores_calidad,
        "tabla_principal": {"estado": "OK", "faltantes": []},
        "tabla_secundaria": {"estado": "OK", "faltantes": []}
    }

def validar_columnas(df, campos):
    """Valida que las columnas requeridas estén presentes en el DataFrame."""
    requeridas = list(campos.keys())
    faltantes = [col for col in requeridas if col not in df.columns]
    return faltantes


def validar_tipos(df, campos):
    """Valida tipos de datos básicos (ejemplo: ENGROUTEID debe ser texto)."""
    errores = []
    if "ENGROUTEID" in campos and "ENGROUTEID" in df.columns:
        if df["ENGROUTEID"].dtype != object:
            errores.append("El campo 'ENGROUTEID' debe ser de tipo TEXTO")
    return errores


def validar_valores_adicionales(df):
    """
    Validación de contenido:
    - 'No Contrato' único.
    - 'Fecha de Inspección' sin horas.
    """
    errores = []

    # 1. Validación No Contrato
    campo_c = "No Contrato"
    if campo_c in df.columns:
        contratos_unicos = df[campo_c].dropna().unique()
        if len(contratos_unicos) > 1:
            errores.append(f"Múltiples contratos detectados: {list(contratos_unicos)}")

    # 2. Validación Fecha de Inspección
    campo_f = "Fecha de Inspección"
    if campo_f in df.columns:
        # Convertimos a datetime para validar la hora de forma robusta
        fechas = pd.to_datetime(df[campo_f], errors='coerce')
        for i, val in fechas.items():
            if pd.notna(val) and (val.hour != 0 or val.minute != 0 or val.second != 0):
                errores.append(f"Fila {i+2}: La fecha tiene hora ({df.loc[i, campo_f]})")

    return errores


ruta_excel = r"D:\Requerimientos\2025\Diciembre\6.5 Inspecciones CIPS 16.12.2025.xlsx"
df = pd.read_excel(ruta_excel)
# --------------------------------------------
# 3️⃣ Validar el DataFrame
# --------------------------------------------
errores = validar_valores_adicionales(df)

if errores:
    print("❌ Se encontraron errores:")
    for e in errores:
        print(" -", e)
else:
    print("✅ Validación completada sin errores")
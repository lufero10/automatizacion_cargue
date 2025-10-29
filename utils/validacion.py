import json
import pandas as pd
import os
import arcpy


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
        ruta_json = os.path.join(base_dir, "mapeos", f"{tematica}.json")

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
    Genera un informe de validación para la tabla_principal y tabla_secundaria
    usando el mapeo de una temática específica (por ejemplo dcvg.json).
    """
    informe = {}

    # --- Tabla principal ---
    if "tabla_principal" in mapeo_tematica:
        tabla_principal = mapeo_tematica["tabla_principal"]
        campos_principal = tabla_principal["campos"]

        faltantes_principal = validar_columnas(df, campos_principal)
        errores_tipo_principal = validar_tipos(df, campos_principal)
        estado_principal = "OK" if not faltantes_principal and not errores_tipo_principal else "ERROR"

        informe["tabla_principal"] = {
            "nombre": tabla_principal["nombre"],
            "estado": estado_principal,
            "faltantes": faltantes_principal,
            "errores_tipo": errores_tipo_principal,
        }

    # --- Tabla secundaria ---
    if "tabla_secundaria" in mapeo_tematica:
        tabla_secundaria = mapeo_tematica["tabla_secundaria"]
        campos_secundaria = tabla_secundaria["campos"]

        faltantes_secundaria = validar_columnas(df, campos_secundaria)
        errores_tipo_secundaria = validar_tipos(df, campos_secundaria)
        estado_secundaria = "OK" if not faltantes_secundaria and not errores_tipo_secundaria else "ERROR"

        informe["tabla_secundaria"] = {
            "nombre": tabla_secundaria["nombre"],
            "estado": estado_secundaria,
            "faltantes": faltantes_secundaria,
            "errores_tipo": errores_tipo_secundaria,
        }

    # --- Validaciones adicionales ---
    informe["errores_adicionales"] = validar_valores_adicionales(df)

    return informe


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
    Validaciones adicionales:
      - 'No Contrato' debe tener un único valor en todo el archivo.
      - 'Fecha de Inspección' debe cumplir formato dd/mm/aaaa.
    """
    errores = []

    if "No Contrato" in df.columns:
        contratos_unicos = df["No Contrato"].dropna().unique()
        if len(contratos_unicos) > 1:
            errores.append(f"Se encontraron múltiples valores en 'No Contrato': {list(contratos_unicos)}")

    if "Fecha de Inspección" in df.columns:
        for i, val in df["Fecha de Inspección"].dropna().items():
            try:
                pd.to_datetime(val, format="%d/%m/%Y", errors="raise")
            except Exception:
                errores.append(f"Formato inválido en 'Fecha de Inspección' fila {i+2}: {val} (debe ser dd/mm/aaaa)")

    return errores

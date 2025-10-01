import json
import pandas as pd

def cargar_mapeo(ruta_json):
    """Carga el mapeo de columnas desde un JSON."""
    with open(ruta_json, "r", encoding="utf-8") as f:
        return json.load(f)

def validar_columnas(df, campos):
    """Valida que las columnas requeridas estén presentes en el DataFrame."""
    requeridas = list(campos.keys())
    faltantes = [col for col in requeridas if col not in df.columns]
    return faltantes

def validar_tipos(df, campos):
    """Valida tipos de datos en columnas específicas (ej. ENGROUTEID debe ser texto)."""
    errores = []
    if "ENGROUTEID" in campos and "ENGROUTEID" in df.columns:
        if df["ENGROUTEID"].dtype != object:  # 'object' equivale a texto en pandas
            errores.append("El campo 'ENGROUTEID' debe ser de tipo TEXTO")
    return errores

def validar_valores_adicionales(df):
    """
    Validaciones adicionales:
      - 'No Contrato' debe tener un único valor en todo el archivo.
      - 'Fecha de Inspección' debe cumplir formato dd/mm/aaaa.
    """
    errores = []

    # Validar No Contrato único
    if "No Contrato" in df.columns:
        contratos_unicos = df["No Contrato"].dropna().unique()
        if len(contratos_unicos) > 1:
            errores.append(
                f"Se encontraron múltiples valores en 'No Contrato': {list(contratos_unicos)}"
            )

    # Validar formato de Fecha de Inspección
    if "Fecha de Inspección" in df.columns:
        for i, val in df["Fecha de Inspección"].dropna().items():
            try:
                pd.to_datetime(val, format="%d/%m/%Y", errors="raise")
            except Exception:
                errores.append(
                    f"Formato inválido en 'Fecha de Inspección' fila {i+2}: {val} (debe ser dd/mm/aaaa)"
                )

    return errores

def generar_informe_validacion(df, mapeo, tematica):
    """
    Genera un informe de validación para tabla_principal y tabla_secundaria,
    más validaciones adicionales.
    """
    informe = {}

    if tematica not in mapeo:
        raise ValueError(f"La temática '{tematica}' no existe en el JSON.")

    config = mapeo[tematica]

    # Tabla principal
    campos_principal = config["tabla_principal"]["campos"]
    faltantes_principal = validar_columnas(df, campos_principal)
    errores_tipo_principal = validar_tipos(df, campos_principal)
    estado_principal = "OK" if not faltantes_principal and not errores_tipo_principal else "ERROR"

    informe["tabla_principal"] = {
        "nombre": config["tabla_principal"]["nombre"],
        "estado": estado_principal,
        "faltantes": faltantes_principal,
        "errores_tipo": errores_tipo_principal,
    }

    # Tabla secundaria
    campos_secundaria = config["tabla_secundaria"]["campos"]
    faltantes_secundaria = validar_columnas(df, campos_secundaria)
    errores_tipo_secundaria = validar_tipos(df, campos_secundaria)
    estado_secundaria = "OK" if not faltantes_secundaria and not errores_tipo_secundaria else "ERROR"

    informe["tabla_secundaria"] = {
        "nombre": config["tabla_secundaria"]["nombre"],
        "estado": estado_secundaria,
        "faltantes": faltantes_secundaria,
        "errores_tipo": errores_tipo_secundaria,
    }

    # Validaciones adicionales
    informe["errores_adicionales"] = validar_valores_adicionales(df)

    return informe

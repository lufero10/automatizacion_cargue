# utils/reglas/reglas_tematicas.py

# Importar funciones de la temática DCVG
from .dcvg_reglas import reglas_dcvg_principal, reglas_dcvg_secundario

# Importar funciones de la temática CIPS
from .cips_reglas import reglas_cips_principal, reglas_cips_secundario

# 📚 CATÁLOGO CENTRAL DE REGLAS
# Este diccionario mapea el nombre de la función (usado en el JSON) a la función real.
REGLAS_TEMATICA = {
    # ------------------
    # DCVG (Direct Current Voltage Gradient)
    # ------------------
    "reglas_dcvg_principal": reglas_dcvg_principal,
    "reglas_dcvg_secundario": reglas_dcvg_secundario,

    # ------------------
    # CIPS (Current Interruption Potential Survey)
    # ------------------
    "reglas_cips_principal": reglas_cips_principal,
    "reglas_cips_secundario": reglas_cips_secundario,
}
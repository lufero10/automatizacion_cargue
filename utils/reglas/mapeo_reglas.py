from . import dcvg_reglas

# Mapear cada temática a su función de reglas
REGLAS_POR_TEMATICA = {
    "dcvg": dcvg_reglas.aplicar_reglas_dcvg,
    # "otra_temática": otra_regla.aplicar_reglas_otra
}

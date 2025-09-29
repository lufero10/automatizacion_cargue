import os
import pandas as pd
import arcpy
from utils.validacion import cargar_mapeo, generar_informe_validacion
from utils.cargue_excel import cargar_excel_a_gdb
from utils.alineacion import alineacion


def main():
    # Configuración general
    ruta_proyecto = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM"
    ruta_excel = os.path.join(ruta_proyecto, "DCVG_PPM_T_LBBR_10_24_1300010947_551003090_TEL_Rev0.xlsx")
    ruta_json = os.path.join(ruta_proyecto, "mapeo_tablas_tematicas.json")

    tematica = "dcvg"
    nombre_hoja = "DCVG"
    inputGeom = "Punto"   # opciones válidas: "Punto" | "Linea"
    route = r'D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\Centerline.gdb\P_centerline'
    tolerancia = 50

    # Configuración de entorno
    arcpy.env.overwriteOutput = True
    outLocation = arcpy.env.scratchGDB
    cobertura_name = "COBERTURA_FC"

    # 1. Validación contra JSON
    mapeo = cargar_mapeo(ruta_json)
    df = pd.read_excel(ruta_excel, sheet_name=nombre_hoja)
    informe = generar_informe_validacion(df, mapeo, tematica)

    errores = []
    for campo, resultado in informe.items():
        if resultado["estado"] != "OK":
            errores.extend(resultado["faltantes"])
            print(f"❌ Error en campo {campo}: faltan {resultado['faltantes']}")

    if errores:
        print("❌ Validación fallida. Revise los campos faltantes.")
        return
    else:
        print("✅ Validación exitosa. Continuando con el cargue...")

    # 2. Cargar Excel como tabla y generar cobertura
    cobertura_fc = cargar_excel_a_gdb(
        ruta_excel, nombre_hoja, outLocation, cobertura_name, inputGeom
    )
    print(f"✅ Cobertura creada en: {cobertura_fc}")

    # 3. Ejecutar alineación
    alineacion(cobertura_fc, route, tolerancia)

    print("🚀 Flujo completado correctamente.")


if __name__ == "__main__":
    main()

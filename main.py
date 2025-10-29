import os
import pandas as pd
import arcpy
import pprint
from utils.validacion import cargar_mapeo_tematica, generar_informe_validacion
from utils.cargue_excel import cargar_excel_a_gdb
from utils.alineacion import alineacion
from utils.cargue_bd import cargue_bd
from utils.reglas.dcvg_reglas import aplicar_reglas_dcvg


def main():
    # --- 🧭 CONFIGURACIÓN GENERAL ---
    print("\n🧭 INICIANDO PROCESO AUTOMATIZADO DE CARGUE UPDM...\n")

    ruta_proyecto = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM"
    ruta_excel = os.path.join(ruta_proyecto, "DCVG_PPM_T_LBBR_10_24_1300010947_551003090_TEL_Rev0.xlsx")
    tematica = "dcvg"
    nombre_hoja = "DCVG"
    inputGeom = "Punto"  # "Punto" | "Linea"
    route = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\Centerline.gdb\P_centerline"
    tolerancia = 50
    gdb_destino = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\Centerline.gdb"

    arcpy.env.overwriteOutput = True
    outLocation = arcpy.env.scratchGDB
    cobertura_name = "COBERTURA_FC"

    # # --- 1️⃣ CARGAR MAPEO ---
    print("📘 [1/6] Cargando mapeo de temática...")
    mapeo_tematica = cargar_mapeo_tematica(tematica)
    print("✅ Mapeo cargado correctamente.\n")

    # --- 2️⃣ VALIDACIÓN DEL EXCEL ---
    print("📊 [2/6] Validando estructura del archivo Excel...")
    df = pd.read_excel(ruta_excel, sheet_name=nombre_hoja)
    informe = generar_informe_validacion(df, mapeo_tematica)
    print("✅ Validación completada.\n")

    print("📘 MAPEO DETECTADO:")
    pprint.pprint(mapeo_tematica)
    print("\n📋 INFORME DE VALIDACIÓN:")
    pprint.pprint(informe)
    print()

    # --- 3️⃣ CARGA DEL EXCEL COMO FEATURE CLASS ---
    print("📥 [3/6] Cargando archivo Excel a GDB y generando feature class...")
    cobertura_fc = cargar_excel_a_gdb(ruta_excel, nombre_hoja, outLocation, cobertura_name, inputGeom)
    print(f"cobertura_fc: {cobertura_fc}")

    if not arcpy.Exists(cobertura_fc):
        raise RuntimeError("❌ No se generó la cobertura. Verifica el cargue del Excel.")
    print(f"✅ Feature class creada correctamente: {cobertura_fc}\n")

    # --- 4️⃣ ALINEACIÓN CON CENTERLINE ---
    print("📐 [4/6] Ejecutando alineación con el Centerline...")
    if not arcpy.Exists(route):
        raise FileNotFoundError(f"❌ No se encontró la ruta del Centerline: {route}")

    alineacion(cobertura_fc, route, tolerancia)
    print("✅ Alineación completada correctamente.\n")

    # --- 5️⃣ CARGUE A BASE DE DATOS ---
    print("💾 [5/6] Iniciando cargue a base de datos destino...")
    cobertura_fc = r"C:\Users\TICE21\AppData\Local\Temp\scratch.gdb\COBERTURA_FC"#Borrar

    cargue_bd(cobertura_fc, tematica, mapeo_tematica, gdb_destino)
    print("✅ Cargue a base de datos completado.\n")

    # --- 6️⃣ FINALIZACIÓN ---
    print("🎯 [6/6] Flujo completo ejecutado exitosamente.")
    print("🚀 Proceso finalizado sin errores.")


if __name__ == "__main__":
    main()

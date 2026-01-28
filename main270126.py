import pandas as pd
import arcpy
import pprint
from utils.validacion import cargar_mapeo_tematica, generar_informe_validacion
from utils.cargue_excel import cargar_excel_a_gdb
from utils.alineacion import alineacion
from cargue_bd import cargue_bd
from datetime import datetime
import sys
import os

# Carpeta del main.py
script_dir = os.path.dirname(__file__)
if script_dir not in sys.path:
    sys.path.append(script_dir)


def main():
    # # --- 🧭 CONFIGURACIÓN GENERAL ---
    # print(f"\n🧭 INICIANDO PROCESO AUTOMATIZADO DE CARGUE UPDM... ({datetime.now():%Y-%m-%d %H:%M:%S})\n")
    #
    # ruta_proyecto = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM"
    # ruta_excel = r"D:\Requerimientos\2025\Noviembre\6.1 DCVG 11.11.2025.xlsx"
    # tematica = "dcvg"
    # nombre_hoja = "DCVG"
    # # ruta_excel = r"D:\Requerimientos\2025\Diciembre\6.5 Inspecciones CIPS 16.12.2025.xlsx"
    # # tematica = "cips"
    # # nombre_hoja = "CIPS - PAP"
    # inputGeom = "Punto"  # "Punto" | "Linea"
    # route = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\Centerline.gdb\P_centerline"
    # tolerancia = 50
    # gdb_destino = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\Centerline.gdb"
    #
    # arcpy.env.overwriteOutput = True
    # #outLocation = arcpy.env.scratchGDB
    # outLocation = r"C:\Users\TICE21\OneDrive\Documentos\ArcGIS\Projects\TGI\TGI.gdb"
    # cobertura_name = "COBERTURA_FC"
    arcpy.AddMessage(f"🧭 INICIANDO PROCESO AUTOMATIZADO... ({datetime.now():%Y-%m-%d %H:%M:%S})")

    # --- 📥 CAPTURA DE PARÁMETROS DESDE LA HERRAMIENTA ---
    ruta_excel = arcpy.GetParameterAsText(0)
    tematica = arcpy.GetParameterAsText(1).lower()
    nombre_hoja = arcpy.GetParameterAsText(2)
    inputGeom = arcpy.GetParameterAsText(3)
    route = arcpy.GetParameterAsText(4)
    tolerancia = int(arcpy.GetParameterAsText(5))
    gdb_destino = arcpy.GetParameterAsText(6)

    # Configuraciones fijas o derivadas
    arcpy.env.overwriteOutput = True
    # Usamos el scratchGDB para procesos intermedios pesados
    outLocation = arcpy.env.scratchGDB
    cobertura_name = "COBERTURA_FC"


    # # --- 1️⃣ CARGAR MAPEO ---
    print("📘 [1/6] Cargando mapeo de temática...")
    arcpy.AddMessage("📘 [1/6] Cargando mapeo de temática...")
    mapeo_tematica = cargar_mapeo_tematica(tematica)
    print("✅ Mapeo cargado correctamente.\n")

    # --- 2️⃣ VALIDACIÓN DEL EXCEL ---
    print("📊 [2/6] Validando estructura del archivo Excel...")
    arcpy.AddMessage("📊 [2/6] Validando estructura del archivo Excel...")
    df = pd.read_excel(ruta_excel, sheet_name=nombre_hoja)
    #df = pd.read_excel(ruta_excel)
    informe = generar_informe_validacion(df, mapeo_tematica)
    print("✅ Validación completada.\n")

    print("📘 MAPEO DETECTADO:")
    pprint.pprint(mapeo_tematica)
    print("\n📋 INFORME DE VALIDACIÓN:")
    pprint.pprint(informe)
    print()

    # --- 3️⃣ CARGA DEL EXCEL COMO FEATURE CLASS ---
    print("📥 [3/6] Cargando archivo Excel a GDB y generando feature class...")
    arcpy.AddMessage("📥 [3/6] Cargando archivo Excel a GDB y generando feature class...")
    cobertura_fc = cargar_excel_a_gdb(ruta_excel, nombre_hoja, outLocation, cobertura_name, inputGeom)
    print(f"cobertura_fc: {cobertura_fc}")

    if not arcpy.Exists(cobertura_fc):
        raise RuntimeError("❌ No se generó la cobertura. Verifica el cargue del Excel.")
    print(f"✅ Feature class creada correctamente: {cobertura_fc}\n")

    # --- 4️⃣ ALINEACIÓN CON CENTERLINE ---
    print("📐 [4/6] Ejecutando alineación con el Centerline...")
    arcpy.AddMessage("📐 [4/6] Ejecutando alineación con el Centerline...")
    if not arcpy.Exists(route):
        raise FileNotFoundError(f"❌ No se encontró la ruta del Centerline: {route}")
    print("🪪 Campos del FC cargado:", [f.name for f in arcpy.ListFields(cobertura_fc)])
    alineacion(cobertura_fc, route, tolerancia)
    print("✅ Alineación completada correctamente.\n")

    # --- 5️⃣ CARGUE A BASE DE DATOS ---
    print("💾 [5/6] Iniciando cargue a base de datos destino...")
    #cobertura_fc = r"C:\Users\TICE21\AppData\Local\Temp\scratch.gdb\COBERTURA_FC"#Borrar

    cargue_bd(cobertura_fc, tematica, mapeo_tematica, gdb_destino)
    print("✅ Cargue a base de datos completado.\n")

    # --- 6️⃣ FINALIZACIÓN ---
    print(f"🎯 [6/6] Flujo completo ejecutado exitosamente. Finalizado en: {datetime.now():%Y-%m-%d %H:%M:%S}")
    arcpy.AddMessage(f"🎯 [6/6] Flujo completo ejecutado exitosamente. Finalizado en: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("🚀 Proceso finalizado sin errores.")
    arcpy.AddMessage("🚀 Proceso finalizado sin errores.")


if __name__ == "__main__":
    main()

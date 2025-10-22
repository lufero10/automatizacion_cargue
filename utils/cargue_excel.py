import arcpy
import os

def cargar_excel_a_gdb(ruta_excel, nombre_hoja, outLocation, cobertura_fc, inputGeom):
    """
    Carga un Excel como tabla en la GDB y lo convierte en feature class (puntos o líneas).
    Devuelve la ruta final de la cobertura.
    """
    # Validar existencia del archivo
    if not os.path.exists(ruta_excel):
        raise FileNotFoundError(f"❌ No se encontró el archivo Excel en: {ruta_excel}")

    # Construir la ruta a la hoja (IMPORTANTE: usar comillas simples internas y $ final)
    inTable = f"{ruta_excel}\\{nombre_hoja}$"
    outTable = os.path.join(outLocation, "Geo_tabla")
    cobertura_fc = os.path.join(outLocation, cobertura_fc)

    print(f"🔎 Intentando leer hoja desde: {inTable}")
    print(f"📄 Archivo Excel encontrado: {os.path.exists(ruta_excel)}")

    # 1. Limpiar previos
    if arcpy.Exists(outTable):
        arcpy.Delete_management(outTable)
        print(f"🧹 Tabla previa borrada: {outTable}")
    if arcpy.Exists(cobertura_fc):
        arcpy.Delete_management(cobertura_fc)
        print(f"🧹 Cobertura previa borrada: {cobertura_fc}")

    # 2. Excel → Tabla GDB
    print("📥 Convirtiendo Excel a tabla GDB...")
    arcpy.ExcelToTable_conversion(ruta_excel, os.path.join(outLocation, "Geo_tabla"), nombre_hoja)
    print("✅ Tabla creada correctamente.")

    # 3. Campo ID_ALINEAR (si no existe, crear; siempre recalcular)
    if "ID_ALINEAR" not in [f.name for f in arcpy.ListFields(outTable)]:
        arcpy.AddField_management(outTable, "ID_ALINEAR", "LONG")
        print("🆕 Campo ID_ALINEAR creado.")
    arcpy.CalculateField_management(outTable, "ID_ALINEAR", "!OBJECTID!", "PYTHON3")
    print("🔢 Campo ID_ALINEAR calculado.")

    # 4. Crear geometría según tipo
    print(f"📍 Creando geometría tipo {inputGeom}...")
    if inputGeom == "Punto":
        arcpy.management.XYTableToPoint(
            outTable, cobertura_fc, "Longitud", "Latitud", "Altitud",
            arcpy.SpatialReference(4686)  # MAGNA-SIRGAS
        )
    elif inputGeom == "Linea":
        arcpy.management.XYToLine(
            outTable, cobertura_fc,
            "Longitud_Inicio", "Latitud_Inicio",
            "Longitud_Fin", "Latitud_Fin",
            "GEODESIC", "ID_ALINEAR",
            arcpy.SpatialReference(4686)
        )
        arcpy.AddIndex_management(cobertura_fc, "ID_ALINEAR", "NGIndex", "UNIQUE", "ASCENDING")
        arcpy.JoinField_management(cobertura_fc, "ID_ALINEAR", outTable, "ID_ALINEAR")
    else:
        raise ValueError("❌ inputGeom debe ser 'Punto' o 'Linea'.")

    print(f"✅ Cobertura creada correctamente: {cobertura_fc}")
    return cobertura_fc

import arcpy
import os

def cargar_excel_a_gdb(ruta_excel, nombre_hoja, outLocation, cobertura_fc, inputGeom):
    """
    Carga un Excel como tabla en la GDB y lo convierte en featureclass (puntos o líneas).
    Devuelve la ruta final de la cobertura.
    """
    import os, arcpy

    inTable = f"{ruta_excel}\\{nombre_hoja}$"  # Excel-> hoja
    outTable = os.path.join(outLocation, "Geo_tabla")
    cobertura_fc = os.path.join(outLocation, cobertura_fc)  # ruta final

    # 1. Limpiar previos
    if arcpy.Exists(outTable):
        arcpy.Delete_management(outTable)
        arcpy.AddMessage(outTable + " borrada")
    if arcpy.Exists(cobertura_fc):
        arcpy.Delete_management(cobertura_fc)
        arcpy.AddMessage(cobertura_fc + " borrada")

    # 2. Excel → Tabla GDB
    arcpy.TableToTable_conversion(inTable, outLocation, "Geo_tabla")

    # 3. Campo ID_ALINEAR (si no existe, crear; siempre recalcular)
    if "ID_ALINEAR" not in [f.name for f in arcpy.ListFields(outTable)]:
        arcpy.AddField_management(outTable, "ID_ALINEAR", "LONG")
    arcpy.CalculateField_management(outTable, "ID_ALINEAR", "!OBJECTID!", "PYTHON3")

    # 4. Geometría
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

    return cobertura_fc

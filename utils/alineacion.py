# utils/alineacion.py
import arcpy
import os
import datetime


def alineacion(cobertura, route, tolerancia):
    """
    Alinea coberturas contra rutas y calcula medidas (ENGFROMM, ENGTOM, ENGM).

    Parámetros:
        cobertura (str): Ruta al feature class de cobertura.
        route (str): Ruta al feature class de rutas.
        tolerancia (str): Tolerancia espacial para la alineación (ejemplo: "1 Meters").
    """
    arcpy.env.overwriteOutput = True
    desc = arcpy.Describe(cobertura)
    nombre = desc.name
    tipo = desc.shapeType

    # Obtener el OID de la cobertura
    oid_field = arcpy.Describe(cobertura).OIDFieldName

    # Paths temporales en scratch GDB
    GDB = arcpy.env.scratchGDB
    coberturasel = os.path.join(GDB, "COBERTURA")
    coberturavertices = os.path.join(GDB, "VERTICES")
    routesel = os.path.join(GDB, "ROUTE_SEL")
    tablelocatemeasure = os.path.join(GDB, "TABLE_LOCATE_MEASURE")

    # Campos de alineación
    campos_por_tipo = {
        "Polyline": [("ENGFROMM", "DOUBLE"), ("ENGTOM", "DOUBLE")],
        "Point": [("ENGM", "DOUBLE")],
        "Multipoint": [("ENGM", "DOUBLE")]
    }

    # Crear campos si no existen
    for campo, tipo_campo in campos_por_tipo.get(tipo, []):
        if campo not in [f.name for f in arcpy.ListFields(cobertura)]:
            arcpy.AddField_management(cobertura, campo, tipo_campo)
            arcpy.CalculateField_management(cobertura, campo, "None", "PYTHON3")

    # Copia inicial de cobertura
    arcpy.Select_analysis(cobertura, coberturasel)

    # Procesar por ENGROUTEID
    with arcpy.da.SearchCursor(cobertura, ["ENGROUTEID"], sql_clause=(None, "GROUP BY ENGROUTEID")) as cursor:
        for (rguid,) in cursor:
            ahora = datetime.datetime.now()
            arcpy.AddMessage(f"🔄 Alineando {rguid} ({ahora})")

            where_clause = f"ENGROUTEID = '{rguid}'"

            arcpy.Select_analysis(route, routesel, where_clause)
            arcpy.Select_analysis(cobertura, coberturasel, where_clause)

            arcpy.MakeFeatureLayer_management(cobertura, "COBERTURA_LAYER")

            if tipo == "Polyline":
                # Inicio
                arcpy.FeatureVerticesToPoints_management(coberturasel, coberturavertices, "START")
                arcpy.LocateFeaturesAlongRoutes_lr(
                    coberturavertices, routesel, "ENGROUTEID", tolerancia,
                    tablelocatemeasure, "ENGROUTEID POINT BEGIN_M"
                )
                arcpy.AddJoin_management("COBERTURA_LAYER", oid_field, tablelocatemeasure, "ID_ALINEAR", "KEEP_COMMON")
                arcpy.CalculateField_management("COBERTURA_LAYER", f"{nombre}.ENGFROMM", "round(!TABLE_LOCATE_MEASURE.BEGIN_M!,3)", "PYTHON3")
                arcpy.RemoveJoin_management("COBERTURA_LAYER", "TABLE_LOCATE_MEASURE")

                # Fin
                arcpy.FeatureVerticesToPoints_management(coberturasel, coberturavertices, "END")
                arcpy.LocateFeaturesAlongRoutes_lr(
                    coberturavertices, routesel, "ENGROUTEID", tolerancia,
                    tablelocatemeasure, "ENGROUTEID POINT BEGIN_M"
                )
                arcpy.AddJoin_management("COBERTURA_LAYER", oid_field, tablelocatemeasure, "ID_ALINEAR", "KEEP_COMMON")
                arcpy.CalculateField_management("COBERTURA_LAYER", f"{nombre}.ENGTOM", "round(!TABLE_LOCATE_MEASURE.BEGIN_M!,3)", "PYTHON3")
                arcpy.RemoveJoin_management("COBERTURA_LAYER", "TABLE_LOCATE_MEASURE")

            elif tipo in ("Point", "Multipoint"):
                arcpy.LocateFeaturesAlongRoutes_lr(
                    coberturasel, routesel, "ENGROUTEID", tolerancia,
                    tablelocatemeasure, "ENGROUTEID POINT BEGIN_M"
                )
                arcpy.AddJoin_management("COBERTURA_LAYER", oid_field, tablelocatemeasure, "ID_ALINEAR", "KEEP_COMMON")
                arcpy.CalculateField_management("COBERTURA_LAYER", f"{nombre}.ENGM", "round(!TABLE_LOCATE_MEASURE.BEGIN_M!,3)", "PYTHON3")
                arcpy.RemoveJoin_management("COBERTURA_LAYER", "TABLE_LOCATE_MEASURE")

    arcpy.AddMessage("✅ Alineación finalizada.")



# def alineacion(cobertura, route, tolerancia):
#     desc = arcpy.Describe(cobertura)
#     arcpy.env.overwriteOutput = True
#     nombre = desc.name
#     tipo = desc.shapeType
#
#     fields = arcpy.ListFields (cobertura, field_type = 'OID')
#     for field in fields:
#         objid = (field.name)
#
#     #arcpy.AddField_management(cobertura, 'ID_ALINEAR', 'LONG')
#     #expresion = '!' + objid + '!'
#     #arcpy.CalculateField_management (cobertura, 'ID_ALINEAR', expresion, 'PYTHON_9.3')
#
#     GDB = arcpy.env.scratchGDB
#     coberturasel = os.path.join(GDB, 'COBERTURA')
#     coberturavertices = os.path.join(GDB, 'VERTICES')
#     routesel = os.path.join(GDB, 'route')
#     tablelocatemeasure = os.path.join(GDB, 'TABLE_LOCATE_MEASURE')
#
#     if tipo == 'Polyline':
#         try:
#             arcpy.AddField_management(cobertura, 'ENGFROMM', 'DOUBLE')
#         except Exception as e:
#             arcpy.AddWarning(e)
#         try:
#             arcpy.AddField_management(cobertura, 'ENGTOM', 'DOUBLE')
#         except Exception as e:
#             arcpy.AddWarning(e)
#         try:
#             arcpy.CalculateField_management(cobertura, 'ENGFROMM', 'None', 'PYTHON_9.3')
#         except Exception as e:
#             arcpy.AddWarning(e)
#         try:
#             arcpy.CalculateField_management(cobertura, 'ENGTOM', 'None', 'PYTHON_9.3')
#         except Exception as e:
#             arcpy.AddWarning(e)
#     elif tipo == 'Point' or tipo == 'Multipoint':
#         try:
#             arcpy.AddField_management(cobertura, 'ENGM', 'DOUBLE')
#         except Exception as e:
#             arcpy.AddWarning(e)
#         try:
#             arcpy.CalculateField_management(cobertura, 'ENGM', 'None', 'PYTHON_9.3')
#         except Exception as e:
#             arcpy.AddWarning(e)
#
#
#
#     arcpy.Select_analysis (cobertura, coberturasel)
#
#     fields = ['ENGROUTEID']
#     cursor1 = arcpy.da.SearchCursor(cobertura, fields, sql_clause=(None, 'GROUP BY ENGROUTEID'))
#     for row1 in cursor1:
#         rguid = row1[0]
#         ahora = datetime.datetime.now()
#         arcpy.AddMessage('Alineando ' + rguid + ' ' + str(ahora))
#         expresion = "ENGROUTEID = '" + rguid + "'"
#         arcpy.Select_analysis(route, routesel, expresion)
#         arcpy.Select_analysis(cobertura, coberturasel, expresion)
#         arcpy.MakeFeatureLayer_management (cobertura, 'COBERTURA_LAYER')
#         if tipo == 'Polyline':
#             arcpy.FeatureVerticesToPoints_management (coberturasel, coberturavertices, 'START')
#             arcpy.LocateFeaturesAlongRoutes_lr (coberturavertices, routesel, 'ENGROUTEID', tolerancia, tablelocatemeasure, 'ENGROUTEID POINT BEGIN_M')
#             arcpy.AddJoin_management ('COBERTURA_LAYER', 'ID_ALINEAR', tablelocatemeasure, 'ID_ALINEAR', 'KEEP_COMMON')
#             arcpy.CalculateField_management ('COBERTURA_LAYER', nombre + '.ENGFROMM', 'round(!TABLE_LOCATE_MEASURE.BEGIN_M!,3)', 'PYTHON_9.3')
#             arcpy.RemoveJoin_management('COBERTURA_LAYER', 'TABLE_LOCATE_MEASURE')
#
#             arcpy.FeatureVerticesToPoints_management (coberturasel, coberturavertices, 'END')
#             arcpy.LocateFeaturesAlongRoutes_lr (coberturavertices, routesel, 'ENGROUTEID', tolerancia, tablelocatemeasure, 'ENGROUTEID POINT BEGIN_M')
#             arcpy.AddJoin_management ('COBERTURA_LAYER', 'ID_ALINEAR', tablelocatemeasure, 'ID_ALINEAR', 'KEEP_COMMON')
#             arcpy.CalculateField_management ('COBERTURA_LAYER', nombre + '.ENGTOM', 'round(!TABLE_LOCATE_MEASURE.BEGIN_M!,3)', 'PYTHON_9.3')
#             arcpy.RemoveJoin_management('COBERTURA_LAYER', 'TABLE_LOCATE_MEASURE')
#
#         elif tipo == 'Point':
#             arcpy.LocateFeaturesAlongRoutes_lr (coberturasel, routesel, 'ENGROUTEID', tolerancia, tablelocatemeasure, 'ENGROUTEID POINT BEGIN_M')
#             arcpy.AddJoin_management ('COBERTURA_LAYER', 'ID_ALINEAR', tablelocatemeasure, 'ID_ALINEAR', 'KEEP_COMMON')
#             arcpy.CalculateField_management ('COBERTURA_LAYER', nombre + '.ENGM', 'round(!TABLE_LOCATE_MEASURE.BEGIN_M!,3)', 'PYTHON_9.3')
#             arcpy.RemoveJoin_management('COBERTURA_LAYER', 'TABLE_LOCATE_MEASURE')
#
#     arcpy.AddMessage("✅ Alineación finalizada.")

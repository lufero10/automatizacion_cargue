import arcpy, sys, os, datetime



def alineacion(cobertura, route, tolerancia):
    desc = arcpy.Describe(cobertura)
    arcpy.env.overwriteOutput = True
    nombre = desc.name
    tipo = desc.shapeType

    fields = arcpy.ListFields (cobertura, field_type = 'OID')
    for field in fields:
        objid = (field.name)

    #arcpy.AddField_management(cobertura, 'ID_ALINEAR', 'LONG')
    #expresion = '!' + objid + '!'
    #arcpy.CalculateField_management (cobertura, 'ID_ALINEAR', expresion, 'PYTHON_9.3')

    GDB = arcpy.env.scratchGDB
    coberturasel = os.path.join(GDB, 'COBERTURA')
    coberturavertices = os.path.join(GDB, 'VERTICES')
    routesel = os.path.join(GDB, 'route')
    tablelocatemeasure = os.path.join(GDB, 'TABLE_LOCATE_MEASURE')

    if tipo == 'Polyline':
        try:
            arcpy.AddField_management(cobertura, 'ENGFROMM', 'DOUBLE')
        except Exception as e:
            arcpy.AddWarning(e)
        try:
            arcpy.AddField_management(cobertura, 'ENGTOM', 'DOUBLE')
        except Exception as e:
            arcpy.AddWarning(e)
        try:
            arcpy.CalculateField_management(cobertura, 'ENGFROMM', 'None', 'PYTHON_9.3')
        except Exception as e:
            arcpy.AddWarning(e)
        try:
            arcpy.CalculateField_management(cobertura, 'ENGTOM', 'None', 'PYTHON_9.3')
        except Exception as e:
            arcpy.AddWarning(e)
    elif tipo == 'Point' or tipo == 'Multipoint':
        try:
            arcpy.AddField_management(cobertura, 'ENGM', 'DOUBLE')
        except Exception as e:
            arcpy.AddWarning(e)
        try:
            arcpy.CalculateField_management(cobertura, 'ENGM', 'None', 'PYTHON_9.3')
        except Exception as e:
            arcpy.AddWarning(e)



    arcpy.Select_analysis (cobertura, coberturasel)

    fields = ['ENGROUTEID']
    cursor1 = arcpy.da.SearchCursor(cobertura, fields, sql_clause=(None, 'GROUP BY ENGROUTEID'))
    for row1 in cursor1:
        rguid = row1[0]
        ahora = datetime.datetime.now()
        arcpy.AddMessage('Alineando ' + rguid + ' ' + str(ahora))
        expresion = "ENGROUTEID = '" + rguid + "'"
        arcpy.Select_analysis(route, routesel, expresion)
        arcpy.Select_analysis(cobertura, coberturasel, expresion)
        arcpy.MakeFeatureLayer_management (cobertura, 'COBERTURA_LAYER')
        if tipo == 'Polyline':
            arcpy.FeatureVerticesToPoints_management (coberturasel, coberturavertices, 'START')
            arcpy.LocateFeaturesAlongRoutes_lr (coberturavertices, routesel, 'ENGROUTEID', tolerancia, tablelocatemeasure, 'ENGROUTEID POINT BEGIN_M')
            arcpy.AddJoin_management ('COBERTURA_LAYER', 'ID_ALINEAR', tablelocatemeasure, 'ID_ALINEAR', 'KEEP_COMMON')
            arcpy.CalculateField_management ('COBERTURA_LAYER', nombre + '.ENGFROMM', 'round(!TABLE_LOCATE_MEASURE.BEGIN_M!,3)', 'PYTHON_9.3')
            arcpy.RemoveJoin_management('COBERTURA_LAYER', 'TABLE_LOCATE_MEASURE')

            arcpy.FeatureVerticesToPoints_management (coberturasel, coberturavertices, 'END')
            arcpy.LocateFeaturesAlongRoutes_lr (coberturavertices, routesel, 'ENGROUTEID', tolerancia, tablelocatemeasure, 'ENGROUTEID POINT BEGIN_M')
            arcpy.AddJoin_management ('COBERTURA_LAYER', 'ID_ALINEAR', tablelocatemeasure, 'ID_ALINEAR', 'KEEP_COMMON')
            arcpy.CalculateField_management ('COBERTURA_LAYER', nombre + '.ENGTOM', 'round(!TABLE_LOCATE_MEASURE.BEGIN_M!,3)', 'PYTHON_9.3')
            arcpy.RemoveJoin_management('COBERTURA_LAYER', 'TABLE_LOCATE_MEASURE')

        elif tipo == 'Point':
            arcpy.LocateFeaturesAlongRoutes_lr (coberturasel, routesel, 'ENGROUTEID', tolerancia, tablelocatemeasure, 'ENGROUTEID POINT BEGIN_M')
            arcpy.AddJoin_management ('COBERTURA_LAYER', 'ID_ALINEAR', tablelocatemeasure, 'ID_ALINEAR', 'KEEP_COMMON')
            arcpy.CalculateField_management ('COBERTURA_LAYER', nombre + '.ENGM', 'round(!TABLE_LOCATE_MEASURE.BEGIN_M!,3)', 'PYTHON_9.3')
            arcpy.RemoveJoin_management('COBERTURA_LAYER', 'TABLE_LOCATE_MEASURE')


cobertura = r'C:\Users\TICE21\AppData\Local\Temp\scratch.gdb\COBERTURA_1'
route = r'D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\Centerline.gdb\P_centerline'
tolerancia = 50

alineacion(cobertura, route, tolerancia)









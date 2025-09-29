# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Tabla_to_Alineacion.py
# Created on: 2020-05-06 14:43:42.00000
#   Luis Fernando Rojas
# Description:
# ---------------------------------------------------------------------------

# Importar modulos
import arcpy
import os
from alineacion import alineacion


# Espacio de trabajo

arcpy.env.scratchWorkspace = "C:\\Geoprocesos\\CARGUES\\Cargues\\scratch.gdb"
arcpy.env.overwriteOutput = True
#arcpy.env.scratchGDB
arcpy.AddMessage('Espacio de trabajo: ' + arcpy.env.scratchGDB)


# Variables locales

#inTable = "C:\\Requerimientos\\TGI\\Cargue\\Pruebas\\7.12. Cobertura Vegetal Prueba.xls\\'Cobertura Vegetal$'"
inTable = arcpy.GetParameterAsText(0)
#route = r'C:\Requerimientos\Procesos.gdb\P_Centerline'
route = arcpy.GetParameterAsText(1)
tolerancia = arcpy.GetParameterAsText(2)
inputGeom = arcpy.GetParameterAsText(3)
#outPath = r'C:\Requerimientos\TGI\Cargue\Pruebas\REPORTE_ALINEACION.xls'
outPath = arcpy.GetParameterAsText(4)
outFile = os.path.split(inTable)
outFile = os.path.splitext(os.path.basename(outFile[0]))[0]
outPath = os.path.join(outPath,outFile)
outLocation = arcpy.env.scratchGDB
outTable = 'Geo_tabla'
cobertura = os.path.join(outLocation, outTable+"_layer")


# Crear tabla arcgis

if arcpy.Exists(outTable):
    arcpy.Delete_management(outTable)
    arcpy.AddMessage(outTable + ' Borrada')
elif arcpy.Exists(cobertura):
    arcpy.Delete_management(cobertura)
    arcpy.AddMessage(cobertura + ' Borrada')
else:
    pass
arcpy.TableToTable_conversion(inTable, outLocation, outTable)
inTableFeature = os.path.join(outLocation, outTable)


# Asignación ID para Join espacialización

arcpy.AddField_management(inTableFeature, 'ID_ALINEAR', 'LONG')
arcpy.CalculateField_management(inTableFeature, "ID_ALINEAR", "!OBJECTID!", "PYTHON_9.3", "")


# Proceso Make XY Event Layer

if inputGeom == 'Punto':
    #arcpy.MakeXYEventLayer_management(inTableFeature, "Longitud", "Latitud", cobertura, "GEOGCS['GCS_MAGNA',DATUM['D_MAGNA',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],VERTCS['NAD_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PARAMETER['Vertical_Shift',0.0],PARAMETER['Direction',1.0],UNIT['Meter',1.0]];-400 -400 1000000000;-100000 10000;-100000 10000;8,98315284119521E-09;0,001;0,001;IsHighPrecision", "Altitud")
    arcpy.management.MakeXYEventLayer(inTableFeature, "Longitud", "Latitud", cobertura, "GEOGCS['GCS_MAGNA',DATUM['D_MAGNA',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 1000;8.98315284119521E-09;0.001;0.001;IsHighPrecision", "Altitud")
elif inputGeom == 'Linea':
    # Para Arcgis Pro
    #arcpy.XYToLine_management(inTableFeature, cobertura, "Longitud Inicio", "Latitud Inicio", "Longitud Fin", "Latitud Fin", "0", "ID_ALINEAR", "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8,98315284119522E-09;0,001;0,001;IsHighPrecision")
    arcpy.management.XYToLine(inTableFeature, cobertura, "Longitud_Inicio", "Latitud_Inicio", "Longitud_Fin", "Latitud_Fin", "GEODESIC", "ID_ALINEAR", "GEOGCS['GCS_MAGNA',DATUM['D_MAGNA',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119521E-09;0.001;0.001;IsHighPrecision")
    arcpy.AddIndex_management(cobertura, 'ID_ALINEAR', 'NGIndex', 'UNIQUE', 'ASCENDING')
    arcpy.JoinField_management(cobertura, "ID_ALINEAR", inTableFeature, "ID_ALINEAR", "")


# Proceso Alineacion

alineacion(cobertura, route, tolerancia)


# Exportar reporte

arcpy.AddMessage('Ruta salida ' + outPath)
arcpy.TableToExcel_conversion(cobertura, outPath + ' Alineado.xls', "NAME", "CODE")
arcpy.AddMessage('Reporte de alineación generado correctamente')

arcpy.ClearWorkspaceCache_management()




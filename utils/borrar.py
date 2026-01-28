# import arcpy
# import os
# import uuid
#
# # Tablas versionadas con su LASTUPDATE correspondiente
# tablas = {
#     r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde\TGI_UPDM.DBO.P_Integrity\P_InspectionRange":
#         "2025-12-10 16:34:00",
#
#     r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde\TGI_UPDM.DBO.P_Integrity\P_DASurveyReadings":
#         "2025-12-10 16:36:00"
# }
#
# def obtener_workspace_sde(ruta):
#     partes = ruta.split(".sde")
#     return partes[0] + ".sde"
#
# for tabla, fecha_lastupdate in tablas.items():
#     if not arcpy.Exists(tabla):
#         print(f"⚠️ No existe: {tabla}")
#         continue
#
#     try:
#         workspace = obtener_workspace_sde(tabla)
#         arcpy.env.workspace = workspace
#
#         capa_temp = f"temp_{uuid.uuid4().hex[:6]}"
#
#         # Iniciar edición versionada
#         editor = arcpy.da.Editor(workspace)
#         editor.startEditing(False, True)
#         editor.startOperation()
#
#         # Vista temporal
#         arcpy.management.MakeTableView(tabla, capa_temp)
#
#         # Intento 1: formato simple
#         where = f"LASTUPDATE = '{fecha_lastupdate}'"
#
#         try:
#             arcpy.management.SelectLayerByAttribute(capa_temp, "NEW_SELECTION", where)
#         except:
#             # Intento 2: formato con date
#             where = f"LASTUPDATE = date '{fecha_lastupdate}'"
#             arcpy.management.SelectLayerByAttribute(capa_temp, "NEW_SELECTION", where)
#
#         # Eliminar registros seleccionados
#         arcpy.management.DeleteRows(capa_temp)
#
#         print(f"🗑️ Eliminados registros donde LASTUPDATE = {fecha_lastupdate} en: {tabla}")
#
#         editor.stopOperation()
#         editor.stopEditing(True)
#
#     except Exception as e:
#         print(f"❌ Error eliminando registros en {tabla}: {e}")












import arcpy
import os

# Tablas versionadas
tablas = [
    r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde\TGI_UPDM.DBO.P_Integrity\P_InspectionRange_1",
    r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde\TGI_UPDM.DBO.P_Integrity\P_DASurveyReadings_1"
]

def obtener_workspace_sde(ruta):
    """Devuelve siempre la ruta .sde, sin importar cuántos subniveles tenga."""
    partes = ruta.split(".sde")
    return partes[0] + ".sde"

for tabla in tablas:
    if not arcpy.Exists(tabla):
        print(f"⚠️ No existe: {tabla}")
        continue

    try:
        workspace = obtener_workspace_sde(tabla)
        arcpy.env.workspace = workspace

        editor = arcpy.da.Editor(workspace)
        editor.startEditing(False, True)
        editor.startOperation()

        arcpy.management.DeleteRows(tabla)
        print(f"✅ Registros eliminados correctamente en: {tabla}")

        editor.stopOperation()
        editor.stopEditing(True)

    except Exception as e:
        print(f"❌ Error al eliminar registros en {tabla}: {e}")

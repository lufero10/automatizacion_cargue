import arcpy
import os

# Tablas versionadas
tablas = [
    r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde\TGI_UPDM.DBO.P_Integrity\P_InspectionRange_1",
    r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde\TGI_UPDM.DBO.P_Integrity\P_DASurveyReadings_1"
]

for tabla in tablas:
    if not arcpy.Exists(tabla):
        print(f"⚠️ No existe: {tabla}")
        continue

    try:
        # Extraer el workspace desde la ruta
        workspace = os.path.dirname(os.path.dirname(tabla))  # sube dos niveles: del feature dataset a la conexión .sde
        arcpy.env.workspace = workspace

        # Crear editor para versionadas
        editor = arcpy.da.Editor(workspace)
        editor.startEditing(False, True)
        editor.startOperation()

        arcpy.management.DeleteRows(tabla)
        print(f"✅ Registros eliminados correctamente en: {tabla}")

        editor.stopOperation()
        editor.stopEditing(True)

    except Exception as e:
        print(f"❌ Error al eliminar registros en {tabla}: {e}")

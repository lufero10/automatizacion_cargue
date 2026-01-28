import arcpy
import os
import sys
import importlib

class Toolbox(object):
    def __init__(self):
        self.label = "Toolbox Cargue UPDM"
        self.alias = "ToolboxUPDM"
        self.tools = [CargueUPDM]

class CargueUPDM(object):
    def __init__(self):
        self.label = "1. Proceso Automatizado de Cargue"
        self.description = "Flujo completo de cargue: Excel -> Alineación -> GDB."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # 0. Archivo Excel
        p0 = arcpy.Parameter(displayName="Archivo Excel de Inspecciones", name="ruta_excel", datatype="DEFile", parameterType="Required", direction="Input")
        p0.filter.list = ['xlsx']

        # 1. Nombre de la Hoja (CAMBIADO A POSICIÓN 1)
        p1 = arcpy.Parameter(displayName="Nombre de la Hoja", name="nombre_hoja", datatype="GPString", parameterType="Required", direction="Input")

        # 2. Temática
        p2 = arcpy.Parameter(displayName="Temática", name="tematica", datatype="GPString", parameterType="Required", direction="Input")

        try:
            folder = os.path.dirname(__file__)
            ruta_mapeos = os.path.join(folder, "mapeos")
            if os.path.exists(ruta_mapeos):
                archivos_json = [f.replace('.json', '') for f in os.listdir(ruta_mapeos) if f.endswith('.json')]
                p2.filter.list = sorted(archivos_json)
        except:
            p2.filter.list = ["DCVG", "CIPS", "PCM"]

        # 3. Geometría
        p3 = arcpy.Parameter(displayName="Tipo de Geometría", name="inputGeom", datatype="GPString", parameterType="Required", direction="Input")
        p3.filter.list = ["Punto", "Linea"]
        p3.value = "Punto"

        # 4. Centerline
        p4 = arcpy.Parameter(displayName="Capa Centerline (P_centerline)", name="route", datatype="GPFeatureLayer", parameterType="Required", direction="Input")

        # 5. Tolerancia
        p5 = arcpy.Parameter(displayName="Tolerancia (metros)", name="tolerancia", datatype="GPLong", parameterType="Required", direction="Input")
        p5.value = 50

        # 6. GDB Destino
        p6 = arcpy.Parameter(displayName="GDB Destino (SDE o FileGDB)", name="gdb_destino", datatype="DEWorkspace", parameterType="Required", direction="Input")

        return [p0, p1, p2, p3, p4, p5, p6]

    def updateParameters(self, parameters):
        # Si el usuario selecciona un archivo Excel (índice 0)
        if parameters[0].value:
            if not parameters[0].hasBeenValidated:
                try:
                    import pandas as pd
                    ruta = parameters[0].valueAsText
                    xl = pd.ExcelFile(ruta)
                    hojas = xl.sheet_names

                    # AHORA ACTUALIZAMOS EL PARÁMETRO 1 (LA HOJA)
                    parameters[1].filter.type = "ValueList"
                    parameters[1].filter.list = hojas

                    if parameters[1].valueAsText not in hojas:
                        parameters[1].value = hojas[0]
                except:
                    parameters[1].filter.list = []
        return

    def execute(self, parameters, messages):
        folder = os.path.dirname(__file__)
        if folder not in sys.path:
            sys.path.append(folder)

        try:
            import main
            importlib.reload(main)

            # ENVIAMOS LOS VALORES EN EL NUEVO ORDEN
            lista_valores = [p.valueAsText for p in parameters]

            messages.addMessage("🚀 Iniciando lógica principal...")
            main.main(lista_valores)

        except Exception as e:
            messages.addErrorMessage(f"❌ Error en la ejecución: {str(e)}")
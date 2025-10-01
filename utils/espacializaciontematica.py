import arcpy
import os
import datetime


def espacializacion(ft, campo_engrid, out_fc, centerline, campo_routeid, tipo_dato, sr, cobdestino):
    """
    Procesa los datos de entrada para generar una cobertura geográfica o una tabla en ArcGIS.

    Parámetros:
    - ft: Tabla de entrada.
    - campo_engrid: Campo de identificación de la ruta en la tabla de entrada.
    - out_fc: Feature class o tabla de salida.
    - centerline: Feature class con la geometría de referencia.
    - campo_routeid: Campo de identificación de la ruta en la geometría de referencia.
    - tipo_dato: Tipo de procesamiento ('Coordenadas XYZ', 'Punto Abscisado', 'Linea Abscisado' o tabla).
    - sr: Sistema de referencia espacial.
    - cobdestino: Tabla de destino para procesamiento.
    """

    # Configuración de entorno
    arcpy.env.workspace = "in_memory"
    arcpy.env.overwriteOutput = True

    # Selección de plantilla en blanco
    out_tb = os.path.join("in_memory", "tabla_procesada")
    #out_tb = r"C:\Users\TICE21\AppData\Local\Temp\scratch.gdb\tabla_procesada"
    arcpy.AddMessage(f"Seleccionando plantilla en blanco... {datetime.datetime.now()}")

    arcpy.TableSelect_analysis(cobdestino, out_tb, "OBJECTID = 0")
    arcpy.DeleteField_management(out_tb, ["ENGROUTENAME"])
    arcpy.Append_management(ft, out_tb, "NO_TEST")

    # Agregar campo EVENTID si no existe
    try:
        arcpy.AddField_management(out_tb, "EVENTID", "TEXT", field_length=38)
    except Exception as e:
        arcpy.AddWarning(f"Error al agregar EVENTID: {e}")

    arcpy.AddMessage(f"Calculando EventID... {datetime.datetime.now()}")

    arcpy.CalculateField_management(
        out_tb,
        "EVENTID",
        expression="ID()",
        expression_type="PYTHON_9.3",
        code_block="import uuid\ndef ID(): return str(uuid.uuid4())"
    )

    # Reemplazar valores vacíos con None en todas las columnas
    for field in arcpy.ListFields(out_tb):
        try:
            arcpy.CalculateField_management(
                out_tb,
                field.name,
                expression=f"NULOS(!{field.name}!)",
                expression_type="PYTHON_9.3",
                code_block="""
    def NULOS(A):
        if A is None or (isinstance(A, str) and A.strip() == ""):
            return None
        return A
                """
            )
        except:
            pass  # Si el campo no se puede actualizar, ignorarlo

    # Procesamiento basado en el tipo de dato
    if tipo_dato in ["Coordenadas XYZ", "Punto Abscisado", "Linea Abscisado"]:
        arcpy.AddMessage(f"Creando cobertura geográfica... {datetime.datetime.now()}")
        arcpy.JoinField_management(out_tb, campo_engrid, centerline, campo_routeid, ["ENGROUTENAME"])

        if tipo_dato == "Coordenadas XYZ":
            try:
                arcpy.MakeXYEventLayer_management(out_tb, "GPSX", "GPSY", "XY_LAYER", sr, "GPSZ")
                arcpy.Select_analysis("XY_LAYER", out_fc)
            except Exception as e:
                arcpy.AddWarning(f"Error en coordenadas XYZ: {e}")
        else:
            route_properties = "ENGROUTEID POINT ENGM" if tipo_dato == "Punto Abscisado" else "ENGROUTEID LINE ENGFROMM ENGTOM"
            try:
                arcpy.MakeRouteEventLayer_lr(centerline, campo_routeid, out_tb, route_properties, "ROUTE_LAYER")
                arcpy.Select_analysis("ROUTE_LAYER", out_fc)
            except Exception as e:
                arcpy.AddWarning(f"Error en eventos de ruta: {e}")

        # Validación y reparación de geometría
        outchk = f"{out_fc}_chk"
        arcpy.CheckGeometry_management(out_fc, outchk)
        count = int(arcpy.GetCount_management(outchk).getOutput(0))

        if count > 0:
            arcpy.JoinField_management(outchk, "FEATURE_ID", out_fc, "OBJECTID")
            arcpy.AddWarning(f"Se presentaron errores de geometría, revise: {outchk}")

        arcpy.RepairGeometry_management(out_fc)
        arcpy.Delete_management(out_tb)

        # Verificación de datos generados
        if int(arcpy.GetCount_management(out_fc).getOutput(0)) == 0:
            arcpy.AddWarning("Se generó cobertura vacía")
    else:
        arcpy.AddMessage(f"Creando tabla... {datetime.datetime.now()}")
        try:
            arcpy.JoinField_management(out_tb, campo_engrid, centerline, campo_routeid, ["ENGROUTENAME"])
        except Exception as e:
            arcpy.AddWarning(f"Error al unir tabla: {e}")

        arcpy.TableSelect_analysis(out_tb, out_fc)


    try:
        # Iniciar sesión de edición en la versión correcta
        #gdb_destino = os.path.join(os.path.dirname(__file__), 'sde', 'UPDM_TGI.sde')
        gdb_destino = os.path.join(os.path.dirname(__file__), 'sde', 'PRUEBAS_UPDM_TGI.sde')
        arcpy.AddMessage(f"Iniciando sesión de edición en {gdb_destino}... {datetime.datetime.now()}")

        edit = arcpy.da.Editor(gdb_destino)
        edit.startEditing(False, True)  # False = no autoguardado, True = versionado

        edit.startOperation()  # Iniciar operación de edición

        # Cargar datos con Append
        arcpy.AddMessage(f"Cargando FeatureClass {cobdestino} en base de datos... {datetime.datetime.now()}")
        arcpy.Append_management(out_fc, cobdestino, "NO_TEST")

        # Confirmar cambios
        edit.stopOperation()
        edit.stopEditing(True)  # Guardar cambios

        arcpy.AddMessage(f"Datos cargados exitosamente en {cobdestino}... {datetime.datetime.now()}")

    except Exception as e:
        edit.stopEditing(False)  # Revertir cambios en caso de error
        arcpy.AddError(f"Error al cargar los datos en {cobdestino}: {e}")
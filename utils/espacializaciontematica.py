import arcpy
import os
import datetime
import uuid


def espacializacion(ft, campo_engrid, out_fc, centerline, campo_routeid, tipo_dato, sr, cobdestino):
    """
    Procesa los datos de entrada para generar una cobertura geográfica o una tabla en ArcGIS.
    """
    arcpy.env.workspace = "in_memory"
    arcpy.env.overwriteOutput = True

    out_tb = os.path.join("in_memory", "tabla_procesada")
    arcpy.AddMessage(f"Seleccionando plantilla en blanco... {datetime.datetime.now()}")

    arcpy.TableSelect_analysis(cobdestino, out_tb, "OBJECTID = 0")

    if "ENGROUTENAME" in [f.name for f in arcpy.ListFields(out_tb)]:
        arcpy.DeleteField_management(out_tb, ["ENGROUTENAME"])

    arcpy.Append_management(ft, out_tb, "NO_TEST")

    try:
        arcpy.AddField_management(out_tb, "EVENTID", "TEXT", field_length=38)
    except:
        pass

    arcpy.AddMessage(f"Calculando EventID... {datetime.datetime.now()}")

    # --- BLOQUE EVENTID (PEGADO AL MARGEN IZQUIERDO) ---
    code_eventid = """
def ID():
    import uuid
    return str(uuid.uuid4())
"""

    arcpy.CalculateField_management(
        out_tb,
        "EVENTID",
        expression="ID()",
        expression_type="PYTHON3",
        code_block=code_eventid
    )

    # --- BLOQUE NULOS (PEGADO AL MARGEN IZQUIERDO) ---
    campos_sistema = ["OBJECTID", "FID", "SHAPE", "SHAPE_LENGTH", "SHAPE_AREA", "EVENTID"]

    code_nulos = """
def NULOS(A):
    if A is None or (isinstance(A, str) and A.strip() == ""):
        return None
    return A
"""

    for field in arcpy.ListFields(out_tb):
        if field.name.upper() not in campos_sistema and field.editable:
            try:
                arcpy.CalculateField_management(
                    out_tb,
                    field.name,
                    expression=f"NULOS(!{field.name}!)",
                    expression_type="PYTHON3",
                    code_block=code_nulos
                )
            except:
                pass

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

        arcpy.RepairGeometry_management(out_fc)

        if int(arcpy.GetCount_management(out_fc).getOutput(0)) == 0:
            arcpy.AddWarning("Se generó cobertura vacía")

    else:
        arcpy.AddMessage(f"Creando tabla... {datetime.datetime.now()}")
        try:
            arcpy.JoinField_management(out_tb, campo_engrid, centerline, campo_routeid, ["ENGROUTENAME"])
        except:
            pass
        arcpy.TableSelect_analysis(out_tb, out_fc)

    # --- CARGA A SDE ---
    gdb_destino = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde"

    try:
        arcpy.AddMessage(f"Iniciando sesión de edición en SDE... {datetime.datetime.now()}")
        edit = arcpy.da.Editor(gdb_destino)
        edit.startEditing(False, True)
        edit.startOperation()

        arcpy.AddMessage(f"Cargando datos en {os.path.basename(cobdestino)}...")
        arcpy.Append_management(out_fc, cobdestino, "NO_TEST")

        edit.stopOperation()
        edit.stopEditing(True)
        arcpy.AddMessage(f"✅ Éxito: Datos cargados en SDE ({datetime.datetime.now()})")

    except Exception as e:
        if 'edit' in locals() and edit.isEditing:
            edit.stopOperation()
            edit.stopEditing(False)
        arcpy.AddError(f"❌ Error en carga SDE: {e}")
    finally:
        arcpy.Delete_management("in_memory")
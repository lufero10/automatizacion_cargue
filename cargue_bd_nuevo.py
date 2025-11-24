import pandas as pd
import arcpy
import os


# Las funciones auxiliares y REGLAS_TEMATICA se asumen definidas
# en otro lugar del script o módulo.

def cargue_bd(fc, tematica, mapeo_tematica, gdb_destino):
    """
    Carga información desde un feature class a las tablas destino
    aplicando las reglas específicas según la temática, basándose en el mapeo JSON.
    """

    print("🔎 Iniciando cargue a BD...")
    print(f"📁 Feature class de origen: {fc}")
    print(f"📘 Temática seleccionada: {tematica}")

    if mapeo_tematica is None:
        print("❌ No se encontró un mapeo para la temática proporcionada.")
        return

    # --- 1. CONFIGURACIÓN ÚNICA (E) ---

    # 1.1. Propiedades de la GDB Empresarial (SDE) - Se asume que GDB_UPDM es constante.
    GDB_UPDM = r"D:\Requerimientos\TGI\AUTOMATIZACION_CARGUE_UPDM\sde\TGI_UPDM.sde"
    DESC = arcpy.Describe(GDB_UPDM)
    CP = DESC.connectionProperties
    TIPO_DB = DESC.workspaceType
    NOMBRE_DB_PREFIX = CP.database + ".DBO." if TIPO_DB == "RemoteDatabase" else ""
    CURRENT_USER = CP.user

    # 1.2. Cargar Feature Class ÚNICO a DataFrame
    try:
        campos_fc = [f.name for f in arcpy.ListFields(fc)]
        df_origen = pd.DataFrame([row for row in arcpy.da.SearchCursor(fc, campos_fc)], columns=campos_fc)
        print(f"📊 Total de registros en el feature class (origen): {len(df_origen)}")
    except Exception as e:
        arcpy.AddError(f"Error al cargar el feature class en DataFrame: {e}")
        return

    # --- 2. DEFINICIÓN DINÁMICA DE COMPONENTES ---

    componentes = []
    tipo_tematica = mapeo_tematica.get("tipo", "sencillo")

    # A. Tabla Principal
    if tipo_tematica == "complejo":
        principal = mapeo_tematica.get("tabla_principal", {})
    else:
        principal = {"nombre": mapeo_tematica.get("tabla", ""), "campos": mapeo_tematica.get("campos", {})}

    componentes.append({
        "nombre_logico": "Tabla Principal",
        "nombre_fc": principal.get("nombre", ""),  # <--- Nombre del FC Destino/Tabla
        "mapeo_campos": principal.get("campos", {}),
        "es_principal": True,
        "tipo_espacial": 'Linea Abscisado' if tipo_tematica == "complejo" else 'Punto Coordenadas',
        # Tipo de dato espacial
    })

    # B. Tabla Secundaria (Si existe)
    if "tabla_secundaria" in mapeo_tematica:
        secundaria = mapeo_tematica["tabla_secundaria"]
        componentes.append({
            "nombre_logico": "Tabla Secundaria",
            "nombre_fc": secundaria.get("nombre", ""),  # <--- Nombre del FC Destino/Tabla
            "mapeo_campos": secundaria.get("campos", {}),
            "es_principal": False,
            "tipo_espacial": 'Coordenadas XYZ',  # Tipo de dato espacial
        })

    # --- 3. PROCESO ETL Y ESPACIALIZACIÓN ITERATIVO ---

    # Variables de Espacialización (Se asume que estas son constantes para la temática DCVG):
    campo_engrid = 'ENGROUTEID'
    centerline = os.path.join(gdb_destino, "P_centerline")
    campo_routeid = 'ENGROUTEID'
    sr = 'GEOGCS["GCS_MAGNA",DATUM["D_MAGNA",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 1000;8.98315284119521E-09;0.001;0.002;IsHighPrecision'

    # Se guarda el cobdestino de la principal para usarlo en la secundaria (GLOBALID)
    cobdestino_principal = None

    for comp in componentes:
        nombre_logico = comp["nombre_logico"]
        nombre_tabla_fc = comp["nombre_fc"]  # <-- Valor del campo "nombre" del JSON
        mapeo_campos = comp["mapeo_campos"]
        es_principal = comp["es_principal"]
        tipo_espacial = comp["tipo_espacial"]

        print(f"\n--- 🔄 Procesando {nombre_logico}: {nombre_tabla_fc} ---")

        # 3.1. Copia, Renombre y Transformación (T)
        df_componente = df_origen.copy()
        df_componente.rename(columns=mapeo_campos, inplace=True)

        # 3.2. Aplicar Reglas (Lógica Condicional para Reglas Específicas)
        if es_principal:
            # Reglas generales según temática (DCVG)
            funcion_reglas = REGLAS_TEMATICA.get(tematica)
            if funcion_reglas:
                df_componente = funcion_reglas(df_componente)
        else:
            # Lógica Específica DCVG Secundaria: Reglas y Asignación de GLOBALID
            df_componente = reglas_dcvg_secundario(df_componente, CURRENT_USER, mapeo_tematica)

            # Asignación de GLOBALID: Requiere el cobdestino de la principal (ya cargada)
            inspection_type_json = mapeo_tematica.get("inspection_type", "DCVG")
            if cobdestino_principal:
                df_componente = asignar_globalid(df_componente, cobdestino_principal, inspection_type_json)
            else:
                print("⚠️ ERROR: No se encontró el destino de la tabla principal para asignar GLOBALID.")

        # 3.3. Carga (L) a Tabla
        cargar_df_a_tabla(df_componente, gdb_destino, nombre_tabla_fc)
        print(f"✅ {nombre_logico} cargada correctamente en GDB temporal.")

        # 3.4. Espacialización

        ft = os.path.join(gdb_destino, nombre_tabla_fc)
        out_fc = os.path.join(gdb_destino, f"{nombre_tabla_fc}_Espacializada")
        cobdestino = os.path.join(GDB_UPDM, f"{NOMBRE_DB_PREFIX}P_Integrity",
                                  nombre_tabla_fc)  # <-- Generado dinámicamente

        # Guardar el cobdestino de la principal para uso de la secundaria
        if es_principal:
            cobdestino_principal = cobdestino

        espacializacion(
            ft, campo_engrid, out_fc, centerline, campo_routeid,
            tipo_espacial, sr, cobdestino
        )
        print(f"✨ Espacialización de {nombre_logico} finalizada e insertada en SDE.")

    print("\n🏁 Cargue completo.")
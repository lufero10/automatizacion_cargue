def estandarizar_fc(fc_trabajo, mapeo):
    """
    Estandarización mínima:
    - Renombrar campos según mapeo['renombrar']
    - NO crea campos faltantes
    """
    print(f"🔧 Estandarizando FC: {fc_trabajo}")

    fields_fc = {f.name for f in arcpy.ListFields(fc_trabajo)}

    # --- Renombrar ---
    for origen, destino in mapeo.get("renombrar", {}).items():
        if origen in fields_fc:
            print(f"   ↪ Renombrando: {origen} → {destino}")
            arcpy.AlterField_management(
                in_table=fc_trabajo,
                field=origen,
                new_field_name=destino,
                new_field_alias=destino
            )
        else:
            print(f"   ⚠ No existe el campo a renombrar: {origen}")

    print("✅ Estandarización completada.")
    return fc_trabajo

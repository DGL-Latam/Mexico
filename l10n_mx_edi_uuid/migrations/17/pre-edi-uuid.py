import csv

def backup_data_pre_migration(cr, registry):
    # Nombre del archivo CSV donde se almacenarán los datos
    backup_file = '/tmp/edi_uuid.csv'

    # Ejecutar una consulta para obtener los datos necesarios
    cr.execute("""
        SELECT name, L10n_mx_edi_uuid
        FROM account_edi_document
        WHERE L10n_mx_edi_uuid IS NOT NULL
    """)
    records = cr.fetchall()

    if not records:
        print("No records found to backup.")
        return

    # Guardar los datos en un archivo CSV
    with open(backup_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['name', 'L10n_mx_edi_uuid'])  # Escribir encabezados
        writer.writerows(records)

    print(f"Backup completed. {len(records)} records saved to {backup_file}.")

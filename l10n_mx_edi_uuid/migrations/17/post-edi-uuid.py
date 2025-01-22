import csv
from odoo import api, SUPERUSER_ID


def restore_data_post_migration(cr, registry):
    # Nombre del archivo CSV con los datos respaldados
    backup_file = '/tmp/edi_uuid.csv'

    # Cargar los datos desde el archivo CSV
    try:
        with open(backup_file, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            records = list(reader)
    except FileNotFoundError:
        print(f"Backup file {backup_file} not found.")
        return

    if not records:
        print("No records found in the backup file.")
        return

    # Obtener el entorno Odoo
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Restaurar los datos en account_move
    for record in records:
        name = record['name']
        uuid = record['L10n_mx_edi_uuid']

        # Buscar la entrada correspondiente en account_move
        account_move = env['account.move'].search([('name', '=', name)], limit=1)
        if account_move:
            account_move.write({'L10n_mxedi_cfdi_uuid': uuid})
            print(f"Updated account_move name {name} with UUID {uuid}")
        else:
            print(f"No account_move found for name {name}")

    print("Data restoration completed.")

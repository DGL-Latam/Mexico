{
    'name': 'Intercompany Invoices',
    'version': '15.0.0.1',
    'author': 'DGL-Latam',
    'description': 'Facturas intercompañias',
    'license': 'LGPL-3',
    'depends': [
                'account_inter_company_rules',
                'sale_purchase_inter_company_rules',
            'intercompany_auto_picking_reception'],
    'data': ['views/res_config_settings_sale_invoice_views.xml',
             'views/inter_company_so_invoice_view.xml']
}
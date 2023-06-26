{
    'name': 'Descarga CDFI SAT-WS',
    'author': 'DGL-Latam',
    'license': 'LGPL-3',
    'category': '',
    "version": "0.0.5",
    'depends': [
        'base_automation',
        'account',
        'l10n_mx_edi', 
        'documents',
        'l10n_mx_edi_uuid',
    ],
    'data' : [
        'security/ir.model.access.csv',
        'views/facturas_sat.xml',
        'views/res_company.xml',
        'views/ir_cron.xml',
    ],
    'installable': True,
}
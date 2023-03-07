{
    'name': 'Descarga CDFI SAT-WS',
    'author': 'DGL-Latam',
    'license': 'LGPL-3',
    'category': '',
    "version": "0.0.1",
    'depends': [
        'base_automation',
        'account',
        'l10n_mx_edi', 
        'documents',
    ],
    'data' : [
        'security/ir.model.access.csv',
        'views/facturas_sat.xml',
    ],
    'installable': True,
}
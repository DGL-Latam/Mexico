{
    'name': 'Datos extras Globales cfdi 4.0',
    'summary': '''
    Datos extras para las facturas globales del cfdi 4.0
    ''',
    'author': 'DGL-Latam',
    'version': '17.0',
    'depends': [
        'l10n_mx_edi',
    ],
    'test': [
    ],
    'data': [
        'views/account_move.xml',
        # 'data/cfdi.xml',
    ],
    'installable': True, #change value to False 
    'auto_install': False,
    'application': True,
}

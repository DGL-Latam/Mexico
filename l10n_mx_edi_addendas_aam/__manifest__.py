{
    'name': 'Mexican Addendas Amazon',
    'author': 'DGL-Latam',
    'license': 'LGPL-3',
    'category': '',
    "version": "15.1",
    'depends': [
        'base_automation',
        'l10n_mx_edi_extended',
        'l10n_mx_edi_addendas_base',
        
    ],
    'test': [],
    'data': [   
        'data/cfdi.xml',
        'views/account_move.xml',
    ],
    'demo': [
    ],
    'installable': True,
}
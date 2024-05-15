{
    'name': 'Mexican Addendas Amazon',
    'author': 'DGL-Latam',
    'license': 'LGPL-3',
    'category': '',
    "version": "17.0",
    'depends': [
        'base_automation',
        'l10n_mx_edi_extended',
        'l10n_mx_edi_addendas_base',
        
    ],
    'test': [],
    'data': [ 
        'data/addenda_aam.xml',  
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False, #change value to False
}
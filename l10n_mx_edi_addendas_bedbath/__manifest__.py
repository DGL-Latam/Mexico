{
    'name': 'Mexican Addenda Bed Bath',
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
        'data/addenda_bedbath.xml',
        'data/bedbath_views.xml',
        'data/server_actions.xml',
        'security/ir.model.access.csv',
        
    ],
    'demo': [
    ],
    'installable': True,
}
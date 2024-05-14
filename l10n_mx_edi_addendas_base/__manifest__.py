{
    'name': 'Base Mexican Addendas',
    'summary':'''
    This is the base module for showing current working addendas''',
    'author': 'DGL-Latam',
    'license': 'LGPL-3',
    'category': '',
    "version": "17.0",
    'depends': [
        'base_automation',
        'l10n_mx_edi',
    ],
    'test': [],
    'data': [
        #'data/cfdi.xml',
        'views/res_config_view.xml',    
        'views/account_move.xml',    
    ],
    'demo': [
    ],
    'installable': False, #change value to False
    'auto_install': True, 
}

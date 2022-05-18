{
    'name': 'Base Mexican Addendas',
    'summary':'''
    This is the base module for showing current working addendas''',
    'author': 'DGL-Latam',
    'license': 'LGPL-3',
    'category': '',
    "version": "15.0",
    'depends': [
        'base_automation',
        'l10n_mx_edi',
        'html_text',
    ],
    'test': [],
    'data': [
        'data/cfdi.xml',
        'views/res_config_view.xml',        
    ],
    'demo': [
    ],
    'installable': True,
}

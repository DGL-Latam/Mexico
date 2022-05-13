{
    'name': 'Mexican Addendas SAMS',
    'author': 'DGL-Latam',
    'license': 'LGPL-3',
    'category': '',
    "version": "15.0",
    'depends': [
        'base_automation',
        'html_text',
        'l10n_mx_edi_extended',
        'l10n_mx_edi_addendas_base',
        
    ],
    'test': [],
    'data': [   
        'views/account_account_views.xml',
        'data/addenda_sams.xml'
    ],
    'demo': [
    ],
    'installable': True,
}

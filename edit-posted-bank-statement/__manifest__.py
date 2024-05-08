{
    'name': 'Edit posted bank statements',
    'author': 'DGL-Latam',
    'license': 'LGPL-3',
    'category': 'Accounting/Accounting',
    "version": "17.0",
    'depends': [
        'account',
        'l10n_mx_edi',
              
    ],
    'test': [],
    'data': [   
        'data/account_bank_statement_view.xml'
    ],
    'demo': [
    ],
    'installable': True, #change value True to false test
    'auto_install': False, #change value True to false test
}
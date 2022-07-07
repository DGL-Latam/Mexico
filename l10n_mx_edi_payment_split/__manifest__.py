{
    'name': 'EDI Payment Split',
    'summary': '''
    Allow split payment in multiple invoices.
    ''',
    'author': 'DGL-Latam',
    'license': 'AGPL-3',
    'category': 'Installer',
    'version': '1.3',
    'depends': [
        'l10n_mx_edi',
        'sale_management',
        'sale_purchase',
        'stock',
    ],
    'test': [
    ],
    'data': [
        'data/res_currency_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_payment.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

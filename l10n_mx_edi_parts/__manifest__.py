{
    'name': 'Invoiced Product Units',
    'summary': '''
    Show the part number (serial number) that have been invoiced from a particular product.
    ''',
    'author': 'DGL-Latam',
    'website': 'https://www.vauxoo.com',
    'license': 'AGPL-3',
    'category': 'Installer',
    'version': '15.0.1',
    'depends': [
        'l10n_mx_edi',
        'sale_management',
        'sale_purchase',
        'stock',
    ],
    'test': [
    ],
    'data': [
        'data/cfdi.xml',
        'views/report_invoice_document.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

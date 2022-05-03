# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Invoiced leased properties',
    'summary': '''
    Add the corresponding data for properties leasing for mexican invoices and SAT Requirements
    ''',
    'author': 'DGL-Latam',
    'license': 'AGPL-3',
    'category': 'Installer',
    'version': '15.0',
    'depends': [
        'l10n_mx_edi',
        'sale_renting',
    ],
    'test': [
    ],
    'data': [
        'data/cfdi.xml',
        'views/product_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
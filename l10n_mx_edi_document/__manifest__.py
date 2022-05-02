# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Manage Mexican Documents',
    'version': '12.0.1.0.0',
    'author': 'Vauxoo',
    'category': 'Accounting',
    'license': 'LGPL-3',
    'depends': [
        'documents',
        'l10n_mx_edi',
        'l10n_mx_edi_uuid',
    ],
    'data': [
        'data/data.xml',
        'views/account_payment.xml',
        'views/assets.xml',
        'views/documents_views.xml',
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/*'
    ],
    'installable': True,
}

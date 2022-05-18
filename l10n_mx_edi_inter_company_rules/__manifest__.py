# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Inter Company Module for EDI Invoices',
    'version': '15.0',
    "author": "DGL-Latam",
    "license": "LGPL-3",
    'category': 'Hidden',
    'summary': 'Complement for inter_company_rules that copy the EDI Document',
    'depends': [
        'account_inter_company_rules',
        'sale_purchase_inter_company_rules',
        'l10n_mx_edi',
    ],
    'data': [
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
}

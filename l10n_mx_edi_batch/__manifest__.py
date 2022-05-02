# Copyright 2018 Vauxoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "EDI Stamp on ZIP",
    'author': "Vauxoo",
    'website': "http://www.vauxoo.com",
    'license': 'AGPL-3',
    'category': 'Hidden',
    'version': '12.0.1.0.0',
    'depends': [
        'l10n_mx_edi',
    ],
    'data': [
    ],
    'demo': [
    ],
    'external_dependencies': {
        'python': [
            'zeep',
            'zeep.transports',
        ],
    },
    'installable': True,
    'auto_install': False,
}

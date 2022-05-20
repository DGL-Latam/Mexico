# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Tax Cash Basis Entries at Payment Date",
    "summary": """
    Properly create the Journal Entries on Tax Cash basis when using foreign
    currencies the Tax must be set at date of payment
    """,
    "version": "",
    "author": "DGL-Latam",
    "category": "Accounting",
    "depends": [
        "l10n_mx_edi",
    ],
    "demo": [],
    "data": [],
    "installable": True,
    "auto_install": True,
}

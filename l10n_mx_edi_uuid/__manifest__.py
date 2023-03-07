{
    "name": "UUID Search Invoices",
    "summary": """
        Adds the option to search by the uuid of the attachment
        of the invoice by default when searching for the name
    """,
    "version": "15.0",
    "author": "DGL-Latam",
    "category": "Localization/Mexico",
    "depends": [
        'l10n_mx_edi',
    ],
    "demo": [
    ],
    "data": [
        'views/account_invoice_views.xml',
    ],
    "installable": True,
    "auto_install": False,
}

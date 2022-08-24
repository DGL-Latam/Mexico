# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Intercompañias automatizacion mov inventarios (Recepcion/Salidas)',
    'description': """
Cuando se registra la entrada/salida de una orden de compra/venta intercompañia se vera reflejada en ambas compañias, 
reduciendo el trabajo de almacen.
""",
    "author": "DGL-Latam",
    "version": "0.0.1",
    'category': 'Hidden/Tools',
    'depends': ['sale_purchase_inter_company_rules'],
    'installable': True,
    'auto_install': False,
    'data': [
    ],
    'license': 'LGPL-3',
}
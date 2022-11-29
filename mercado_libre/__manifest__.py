# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Conexion Mercado Libre',
    'description': """
Conecta con API Mercado libre
===========================

Permite obtener los pedidos que se generen en nuestro portal de ventas de Mercado libre y genera la orden de venta 
""",
    "author": "DGL-Latam",
    "version": "1.2.0",
    'category': 'Hidden/Tools',
    'depends': ['web','sale','sale_stock','tracking_ref_so'],
    'installable': True,
    'auto_install': False,
    'data': [
        'security/mercadolibre_security',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/ir_cron.xml',   
        'views/sale_views.xml',
    ],
    'license': 'LGPL-3',
}
{
    'name': 'Conexion Mercado Libre',
    'description': """
Conecta con API Mercado libre
====================================

Permite obtener los pedidos que se generen en nuestro portal de ventas de Mercado libre y genera la orden de venta 
""",
    'category': 'Hidden/Tools',
    'depends': ['web','sale'],
    'installable': True,
    'auto_install': False,
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
}
from odoo import models,fields

class AccountMove(models.Model):
    _inherit = "account.move"

    needs_detallista = fields.Boolean(string="Activar Complemento detallista")

    pedido_date = fields.Date("Fecha del pedido")
    delivery_reference = fields.Char(string="Número de contra-recibo")
    delivery_reference_date = fields.Date(string="Fecha contra-recibo")

    department_name = fields.Char(string="Contacto de compras")
    special_service_type = fields.Selection([{
        'AJ' : 'Ajustes',
        'CAC' : 'Descuento en efectivo',
        'COD' : 'Efectivo a la entrega',
        'EAB' : 'Descuento por pronto pago',
        'FC' : 'Costes del flete',
        'FI' : 'Costes Financieros',
        'HD' : 'Manipulado',
        'QD' : 'Descuento por cantidad',
        'AA' : 'Abono por publicidad',
        'ADS' : 'Pedido de un pallet completo',
        'ADT' : 'Recogida'
    }], string="Tipo de Servicio Especial", default="AA")
    percentage_special_service = fields.float(string="Cantidad o Porcentaje")

    

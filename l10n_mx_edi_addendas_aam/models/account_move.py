from odoo import fields,models

class AccountMove(models.Model):
    _inherit = "account.move"
    
    x_amazon = fields.Char(string="Condicion de Pago", help="PO:XXXXX")
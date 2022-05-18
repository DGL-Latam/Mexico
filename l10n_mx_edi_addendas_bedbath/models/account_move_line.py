from odoo import models,fields


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    x_addenda_supplier_code = fields.Char(
        string="Supplier Code", 
        help="Product code as handled by the supplier. This value has to be set on each invoice line"
    )
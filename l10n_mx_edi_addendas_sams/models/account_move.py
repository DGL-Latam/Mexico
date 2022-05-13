from odoo import fields,models

class AccountMove(models.Model):
    _inherit = "account.move"
    x_addenda_sams = fields.Date(string="Date Purchase Order", help="The date of the purchase order for SAMS addenda")
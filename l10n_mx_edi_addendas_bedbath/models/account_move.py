from odoo import fields,models

class AccountMove(models.Model):
    _inherit = "account.move"
    x_addenda_bed_bath = fields.Char(
        string="Addenda Bed Bath", 
        help="Used to concatenate wizard fields"
    )
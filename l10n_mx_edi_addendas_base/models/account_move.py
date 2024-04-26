from odoo import models,fields

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    partner_vat = fields.Char(related="partner_id.vat")
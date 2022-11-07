from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    payslip_id = fields.One2many('hr.payslip')

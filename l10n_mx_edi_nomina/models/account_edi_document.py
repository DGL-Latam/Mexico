from odoo import models, fields

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'


    payslip_id = fields.Many2one('hr.payslip')

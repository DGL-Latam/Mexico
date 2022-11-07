from odoo import models, fields

class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    payslip_id = fields.Many2one('hr.payslip')
    def _is_compatible_with_journal(self, journal):
        # TO OVERRIDE
        self.ensure_one()
        return journal.type in  ['sale','general']

    def _check_payslip_configuration(self, payslip):
        errors = []

        return errors
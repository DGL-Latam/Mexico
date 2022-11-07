from odoo import fields, models, _

from odoo.exceptions import UserError

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        """
            Generate the accounting entries related to the selected payslips
            A move is created for each journal and for each month.
        """
        res = super(HrPayslip, self).action_payslip_done()
        self.write({
            'payslip_id' : self.id,
        })
        return res
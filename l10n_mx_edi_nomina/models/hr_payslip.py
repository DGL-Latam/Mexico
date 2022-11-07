from odoo import fields, models, _

from odoo.exceptions import UserError

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    edi_document_ids = fields.One2many(
        comodel_name='account.edi.document',
        inverse_name='payslip_id'
    )

    def action_payslip_done(self):
        super().action_payslip_done()
        edi_document_vals_list = []

        for payslip in self:
            for edi_format in payslip.journal_id.edi_format_ids:
                errors = edi_format._check_payslip_configuration(payslip)
                if errors:
                    raise UserError(_("Invalid payslip configuration:\n\n%s") % '\n'.join(errors))
                existing_edi_document = payslip.edi_document_ids.filtered(lambda x: x.edi_format_id == edi_format)
                if existing_edi_document:
                    existing_edi_document.write({
                        'state' : 'to_send',
                        'attachment_id' : False,
                    })
                else:
                    edi_document_vals_list.append({
                        'edi_format_id' : edi_format.id,
                        'payslip_id' : payslip.id,
                        'state' : 'to_send',
                        'move_id': self.move_id.id
                    })
            self.env['account.edi.document'].create(edi_document_vals_list)
            self.edi_document_ids._process_documents_web_services()
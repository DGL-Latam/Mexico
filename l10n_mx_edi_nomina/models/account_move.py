from odoo import models, fields
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    payslip_id = fields.One2many('hr.payslip', inverse_name='move_id')


    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        edi_document_vals_list = []
        for move in posted:
            if not move.invoice_date:
                certificate_date = self.env['l10n_mx_edi.certificate'].sudo().get_mx_current_datetime()
                move.invoice_date = certificate_date.date()
                move.with_context(check_move_validity=False)._onchange_invoice_date()
            for edi_format in move.journal_id.edi_format_ids:
                is_edi_payroll = move.payslip_id and move.move_type == 'entry' and edi_format.code == 'cfdi_3_3'
                if is_edi_payroll:
                    errors = edi_format._check_move_configuration(move)
                    if errors:
                        raise UserError(_("Invalid invoice configuration:\n\n%s") % '\n'.join(errors))
                    existing_edi_document = move.edi_document_ids.filtered(lambda x: x.edi_format_id == edi_format)
                    if existing_edi_document:
                        existing_edi_document.write({
                            'state': 'to_send',
                            'attachment_id': False,
                        })
                    else:
                        edi_document_vals_list.append({
                            'edi_format_id': edi_format.id,
                            'move_id': move.id,
                            'state': 'to_send',
                        })
        self.env['account.edi.document'].create(edi_document_vals_list)
        posted.edi_document_ids._process_documents_no_web_services()
        self.env.ref('account_edi.ir_cron_edi_network')._trigger()
        return posted
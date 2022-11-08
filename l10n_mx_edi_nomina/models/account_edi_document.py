from odoo import models, fields, api

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    @api.model
    def _process_job(self, documents, doc_type):

        super()._process_job(documents,doc_type)

        edi_format = documents.edi_format_id
        state = documents[0].state
        if doc_type == 'entry':
            if state == 'to_send':
                entries = documents.move_id
                with entries._send_only_when_ready():
                    edi_result = edi_format._l10n_mx_edi_post_payroll(entries)
                    super()._postprocess_post_edi_results(documents, edi_result)
            elif state == 'to_cancel':
                edi_result = edi_format._l10n_mx_edi_cancel_payroll(documents.move_id)
                super()._postprocess_cancel_edi_results(documents, edi_result)
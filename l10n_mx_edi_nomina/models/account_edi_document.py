from odoo import models, fields, api

DEFAULT_BLOCKING_LEVEL = 'error'

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    @api.model
    def _process_job(self, documents, doc_type):
        def _postprocess_post_edi_results(documents, edi_result):
            attachments_to_unlink = self.env['ir.attachment']
            for document in documents:
                move = document.move_id
                move_result = edi_result.get(move, {})
                if move_result.get('attachment'):
                    old_attachment = document.attachment_id
                    document.attachment_id = move_result['attachment']
                    if not old_attachment.res_model or not old_attachment.res_id:
                        attachments_to_unlink |= old_attachment
                if move_result.get('success') is True:
                    document.write({
                        'state': 'sent',
                        'error': False,
                        'blocking_level': False,
                    })
                else:
                    document.write({
                        'error': move_result.get('error', False),
                        'blocking_level': move_result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if 'error' in move_result else False,
                    })

            # Attachments that are not explicitly linked to a business model could be removed because they are not
            # supposed to have any traceability from the user.
            attachments_to_unlink.unlink()

        def _postprocess_cancel_edi_results(documents, edi_result):
            invoice_ids_to_cancel = set()  # Avoid duplicates
            attachments_to_unlink = self.env['ir.attachment']
            for document in documents:
                move = document.move_id
                move_result = edi_result.get(move, {})
                if move_result.get('success') is True:
                    old_attachment = document.sudo().attachment_id
                    document.write({
                        'state': 'cancelled',
                        'error': False,
                        'attachment_id': False,
                        'blocking_level': False,
                    })

                    if move.is_invoice(include_receipts=True) and move.state == 'posted':
                        # The user requested a cancellation of the EDI and it has been approved. Then, the invoice
                        # can be safely cancelled.
                        invoice_ids_to_cancel.add(move.id)

                    if not old_attachment.res_model or not old_attachment.res_id:
                        attachments_to_unlink |= old_attachment

                else:
                    document.write({
                        'error': move_result.get('error', False),
                        'blocking_level': move_result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if move_result.get('error') else False,
                    })

            if invoice_ids_to_cancel:
                invoices = self.env['account.move'].browse(list(invoice_ids_to_cancel))
                invoices.button_draft()
                invoices.button_cancel()

            # Attachments that are not explicitly linked to a business model could be removed because they are not
            # supposed to have any traceability from the user.
            attachments_to_unlink.sudo().unlink()

        super()._process_job(documents,doc_type)
        
        edi_format = documents.edi_format_id
        state = documents[0].state
        if doc_type == 'entry':
            if state == 'to_send':
                entries = documents.move_id
                with entries._send_only_when_ready():
                    edi_result = edi_format._l10n_mx_edi_post_payroll(entries)
                    _postprocess_post_edi_results(documents, edi_result)
            elif state == 'to_cancel':
                edi_result = edi_format._l10n_mx_edi_cancel_payroll(documents.move_id)
                _postprocess_cancel_edi_results(documents, edi_result)
from os.path import splitext
from odoo import models, fields


class WorkflowActionRuleAccount(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(
        selection_add=[
            ('l10n_mx_edi.mexican.document', "Mexican Document")])

    def create_record(self, attachments=None):
        rv = super(WorkflowActionRuleAccount, self).create_record(
            attachments=attachments)
        if self.create_model != 'l10n_mx_edi.mexican.document' or not attachments:  # noqa
            return rv
        document_ids = []
        body = "<p>created with DMS</p>"
        incorrect_folder = self.env.ref(
            'l10n_mx_edi_document.documents_incorrect_cfdis_folder', False)
        rule_tc = self.env.ref('documents.documents_Finance_validate_tr')
        for attachment in attachments.filtered(lambda att: not att.res_id):
            if splitext(attachment.datas_fname)[1].upper() != '.XML':
                continue
            document_type = attachment.l10n_mx_edi_document_type()
            if not document_type:
                attachment.res_model = False
                attachment.tag_ids = False
                rule_tc.apply_actions(attachment.ids)
                attachment.folder_id = incorrect_folder
                continue
            create_values = {}

            # TODO - Allow set the journal for each model
            if attachment.res_model == 'account.payment':
                journal = self.env['account.journal'].search(
                    [('type', 'in', ('bank', 'cash'))], limit=1)
                create_values.update({
                    'payment_type': 'inbound' if document_type == 'customerP' else 'outbound',  # noqa
                    'partner_type': 'customer' if document_type == 'customerP' else 'supplier',  # noqa
                    'payment_method_id': (journal.inbound_payment_method_ids[
                        0] if document_type == 'customerP' else
                        journal.outbound_payment_method_ids[0]).id,
                    'amount': 0,
                    'journal_id': journal.id,
                })
            elif attachment.res_model == 'account.invoice':
                invoice_type = {'customerI': 'out_invoice',
                                'customerE': 'out_refund',
                                'vendorI': 'in_invoice',
                                'vendorE': 'in_refund'}.get(document_type)
                journal = self.env['account.invoice'].with_context(
                    {'type': invoice_type})._default_journal()
                create_values.update({
                    'type': invoice_type,
                    'journal_id': journal.id,
                })
            document = self.env[attachment.res_model].create(create_values)
            document_ids.append(document.id)
            document.message_post(body=body, attachment_ids=[attachment.id])
            attachment.folder_id = False
            this_attachment = attachment
            if attachment.res_model or attachment.res_id:
                this_attachment = attachment.copy({'res_id': document.id})

            this_attachment.write({
                'res_model': document._name,
                'res_id': document.id,
                'folder_id': this_attachment.folder_id.id,
            })

            document_ids.append(document.id)
            document = document.xml2record()
            document.l10n_mx_edi_update_sat_status()

        if not document_ids:
            return rv
        action = {
            'type': 'ir.actions.act_window',
            'res_model': document._name,
            'name': "Mexican Documents",
            'view_id': False,
            'view_type': 'list',
            'view_mode': 'tree',
            'views': [(False, "list"), (False, "form")],
            'domain': [('id', 'in', document_ids)],
            'context': self._context,
        }
        if len(attachments) == 1 and document:
            view_id = document.get_formview_id() if document else False
            action.update({
                'view_type': 'form',
                'view_mode': 'form',
                'views': [(view_id, "form")],
                'res_id': document.id if document else False,
                'view_id': view_id,
            })
        return action

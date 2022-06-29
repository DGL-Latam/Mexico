from odoo import fields,models, _ 
from odoo.exceptions import UserError 

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_mx_edi_cancellation = fields.Char(string="Caso de cancelacion",
        help='The SAT has 4 cases in which an invoice could be cancelled, please fill this field based on your case:\n'
        'Case 1: The invoice was generated with errors and must be re-invoiced, the format must be:\n'
        '"01:UUID" where the UUID is the fiscal folio of the invoice generated to replace this record.\n'
        'Case 2: The invoice has an error on the customer, this will be cancelled and replaced by a new with the '
        'customer fixed. The format must be:\n "02", only is required the case number.\n'
        'Case 3: The invoice was generated but the operation was cancelled, this will be cancelled and not must be '
        'generated a new invoice. The format must be:\n "03", only is required the case number.\n'
        'Case 4: Global invoice. The format must be:\n "04", only is required the case number.')

    def action_cancel(self):
        ''' posted ->  cancelled '''
        if self.l10n_mx_edi_cfdi_uuid and not self.l10n_mx_edi_cancellation:
            raise UserError("Se necesita un caso de cancelacion")
            return
        #self.move_id.l10n_mx_edi_cancellation = self.l10n_mx_edi_cancellation+
        cancel_data = (self.l10n_mx_edi_cancellation or '').split('|')
        if cancel_data[0] == '01' and len(cancel_data) < 2:
            raise UserError("La cancelacion 01 necesita que se coloque el uuid que sustituye a esta factura")
            return
        self.env['account.move'].search([('id', '=', self.move_id.id)]).write({'l10n_mx_edi_cancellation': self.l10n_mx_edi_cancellation })
        self.move_id.with_context(l10n_mx_edi_cancellation= self.l10n_mx_edi_cancellation).button_cancel()
        self.move_id.edi_document_ids._process_documents_web_services()
        if self.state != 'draft':
            self.action_draft()
        super().action_cancel()

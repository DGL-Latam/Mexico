from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_mx_edi_cfdi_uuid = fields.Char(
        string='Fiscal Folio', 
        copy=False, 
        readonly=True,
        store=True,
        compute='_compute_uuid',
        compute_sudo=True
    )
    
    @api.depends('edi_document_ids')
    def _compute_uuid(self):
        for payment in self:
            payment.move_id.edi_document_ids._process_documents_web_services()
            cfdi_info = payment.move_id._l10n_mx_edi_decode_cfdi()
            payment.l10n_mx_edi_cfdi_uuid = cfdi_info.get('uuid')
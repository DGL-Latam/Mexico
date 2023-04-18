from odoo import models, fields, _, api

import logging
_logger = logging.getLogger(__name__)

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    @api.depends('state')
    def share_xml(self):
        for document in self:
            if document.edi_format_id.code != "cfdi_3_3":
                continue
            if not document.attachment_id.raw:
                continue
            if document.move_id.move_type not in ['out_invoice','out_refund']:
                continue
            if not document.move_id.related_id:
                continue
            move_related = self.env['account.move'].sudo().search([('id','=',document.move_id.related_id)])
            if not move_related:
                continue
            attach = self.env['ir.attachment'].sudo().create({
                'name' : document.attachment_id.name,
                'type' : 'binary',
                'raw' : document.attachment_id.raw,
                'res_model' : 'account.move',
                'res_id' : move_related.id,
            })
            values = {
                'move_id' : move_related.id,
                'edi_format_id' : self.env.ref('l10n_mx_edi.edi_cfdi_3_3').id,
                'attachment_id' : attach.id,
                'state' : 'sent',
            }
        return 
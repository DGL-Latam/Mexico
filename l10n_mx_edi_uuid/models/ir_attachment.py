from odoo import models, fields, _

class Attachment(models.Model):
    _inherit = 'ir.attachment'

    l10n_mx_edi_uuid = fields.Char(
        string="Folio Fiscal", 
        copy=False, 
        readonly=True, 
        store=True, 
        compute='_compute_uuids')

    def _compute_uuids(self):
        for attach in self:
            linked_edi_document = self.env['account.edi.document'].search([('attachment_id', '=', attach.id)])
            if not linked_edi_document:
                attach.l10n_mx_edi_uuid = ""
                return
            if linked_edi_document.edi_format_id.code != "cfdi_3_3":
                attach.l10n_mx_edi_uuid = ""
                return
            
            nodes = self.env['solicitud.descarga'].sudo()._getNodes(attach.datas)
            attach.l10n_mx_edi_uuid = nodes['tfd_node'].get('uuid')
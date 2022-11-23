from odoo import models, fields, exceptions, _

from lxml.objectify import fromstring
from lxml import etree
from dateutil import parser

import logging
import base64

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def load_xml_as_edi(self):
        attachments = self.env['ir.attachment'].search([('res_id','=',self.id),('res_model','=',self._name),('name','ilike','%.xml')])
        
        if not attachments:
            exceptions.ValidationError('No se encontro nigun xml adjunto')
        if self.move_type == 'out_invoice':
            self._logic_for_out_invoice(attachments)
        elif self.move_type == 'in_invoice':
            self._logic_for_in_invoice(attachments)
            
            
    def get_etree(self,attach):
        decoded = base64.b64decode(attach.datas)
        root = etree.fromstring(decoded)
        return root
    
    
    def _logic_for_in_invoice(self,attachments):
        for attach in attachments:
            root = self.get_etree(attach)
            edi_document = self.recover_edi_document(self.id)
            if not edi_document:
                values = {
                    'move_id' : self.id,
                    'edi_format_id' : self.env.ref('l10n_mx_edi.edi_cfdi_3_3').id,
                    'attachment_id' : attach.id,
                    'state' : 'sent',
                }
                self.l10n_mx_edi_post_time = parser.parse(root.get('Fecha'))
                self.env['account.edi.document'].create(values)
            else:
                edi_document.write({'attachment_id': attach.id, 'state' : 'sent'})
                self.l10n_mx_edi_post_time = parser.parse(root.get('Fecha'))

    def recover_edi_document(self,id):
        return self.env['account.edi.document'].search([('move_id','=',id),('edi_format_id','=',self.env.ref('l10n_mx_edi.edi_cfdi_3_3').id)])
        
    def _logic_for_out_invoice(self,attachments): 
        if self.state != 'posted':
            super()._post()
        for attach in attachments:
            edi_document = self.recover_edi_document(self.id)
            root = self.get_etree(attach)
            edi_document.write({'attachment_id': attach.id, 'state' : 'sent'})
            self.l10n_mx_edi_post_time = parser.parse(root.get('Fecha'))

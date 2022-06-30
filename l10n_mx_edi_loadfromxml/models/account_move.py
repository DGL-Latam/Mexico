from odoo import models, fields, exceptions, _

from lxml.objectify import fromstring
from lxml import etree

import logging
import base64
from dateutil import parser

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def load_xml_as_edi(self):
        attachments = self.env['ir.attachment'].search([('res_id','=',self.id),('res_model','=',self._name),('name','ilike','%.xml')])
        
        if not attachments:
            exceptions.ValidationError('No se encontro nigun xml adjunto')
        for attach in attachments:
            decoded = base64.b64decode(attach.datas)
            root = etree.fromstring(decoded)
            _logger.info(root.tag)
            _logger.info(root.get('Fecha'))
            _logger.info(root.find('.//{http://www.sat.gob.mx/cfd/3}Emisor').get('Rfc'))
            _logger.info(root.find('.//{http://www.sat.gob.mx/TimbreFiscalDigital}TimbreFiscalDigital').get('UUID'))
            
            values = {
                'move_id' : self.id,
                'edi_format_id' : self.env.ref('l10n_mx_edi.edi_cfdi_3_3').id,
                'attachment_id' : attach.id,
                'state' : 'sent',
            }
            self.l10n_mx_edi_post_time = parser.parse(root.get('Fecha'))
            self.env['account.edi.document'].create(values)
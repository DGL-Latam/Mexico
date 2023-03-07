from odoo import models, fields, _, api

from lxml.objectify import fromstring
from lxml import etree
import io

import logging
_logger = logging.getLogger(__name__)

class Attachment(models.Model):
    _inherit = 'ir.attachment'

    l10n_mx_edi_uuid = fields.Char(
        string="Folio Fiscal", 
        copy=False, 
        readonly=True, 
        store=True, 
        compute='_compute_uuids')
    
    @api.depends('res_id')
    def _compute_uuids(self):
        for attach in self:
            linked_edi_document = self.env['account.edi.document'].search([('attachment_id', '=', attach.id)])
            _logger.critical(linked_edi_document)
            if not linked_edi_document:
                attach.l10n_mx_edi_uuid = ""
                return
            _logger.critical(linked_edi_document.edi_format_id.code)
            if linked_edi_document.edi_format_id.code != "cfdi_3_3":
                attach.l10n_mx_edi_uuid = ""
                return
            _logger.critical(linked_edi_document.state)
            if linked_edi_document.state == "to_send":
                linked_edi_document._process_documents_web_services()
            _logger.critical(attach.raw)
            nodes = attach._getNodes(attach.raw)
            attach.l10n_mx_edi_uuid = nodes['tfd_node'].get('UUID')
            _logger.critical(nodes['tfd_node'].get('UUID'))

    def _getNodes(self, cfdi_data : str):
        def get_node(cfdi_node, attribute, namespaces):
            if hasattr(cfdi_node, 'Complemento'):
                node = cfdi_node.Complemento.xpath(attribute, namespaces=namespaces)
                return node[0] if node else None
            else:
                return None
        try:
            cfdi_node = fromstring(cfdi_data)
            emisor_node = cfdi_node.Emisor
            receptor_node = cfdi_node.Receptor

            tfd_node = get_node(
            cfdi_node,
            'tfd:TimbreFiscalDigital[1]',
            {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'},
            )
        except etree.XMLSyntaxError:
            file = io.BytesIO(cfdi_data)
            _logger.critical(file)
            for element in etree.iterparse(file):
                if '}Emisor' in element[1].tag:
                    emisor_node = element[1]
                if '}Receptor' in element[1].tag:
                    receptor_node = element[1]
                if '}Comprobante' in element[1].tag:
                    cfdi_node = element[1]
                if '}TimbreFiscalDigital' in element[1].tag:
                    tfd_node = element[1]
        except AttributeError:
            # Not a CFDI
            return {}
        return {
            'cfdi_node' : cfdi_node,
            'emisor_node' : emisor_node,
            'receptor_node' : receptor_node,
            'tfd_node' : tfd_node
        }
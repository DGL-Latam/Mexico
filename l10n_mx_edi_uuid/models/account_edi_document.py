from odoo import models, fields, _, api

from lxml.objectify import fromstring
from lxml import etree
import io

import logging
_logger = logging.getLogger(__name__)

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    l10n_mx_edi_uuid = fields.Char(
        string="Folio Fiscal", 
        copy=False, 
        readonly=True, 
        store=True, 
        compute='_compute_uuids')
    
    @api.onchange('state')
    def _compute_uuids(self):
        for document in self:
            _logger.critical(document.edi_format_id.code)
            if document.edi_format_id.code != "cfdi_3_3":
                document.l10n_mx_edi_uuid = ""
                return
            _logger.critical(document.state)
            if document.state != "sent":
                document.l10n_mx_edi_uuid = ""
                return
            nodes = document._getNodes(document.attachment_id.raw)
            document.l10n_mx_edi_uuid = nodes['tfd_node'].get('UUID')
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

            tfd_node = get_node(
            cfdi_node,
            'tfd:TimbreFiscalDigital[1]',
            {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'},
            )
        except etree.XMLSyntaxError:
            file = io.BytesIO(cfdi_data)
            _logger.critical(file)
            for element in etree.iterparse(file):
                if '}TimbreFiscalDigital' in element[1].tag:
                    tfd_node = element[1]
                    break
        except AttributeError:
            # Not a CFDI
            return {}
        return {
            'tfd_node' : tfd_node
        }
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
        readonly=True
        store=True,
        compute='_compute_uuids')
    
    @api.depends('state')
    def _compute_uuids(self):
        for document in self:
            if document.edi_format_id.code != "cfdi_3_3":
                document.l10n_mx_edi_uuid = ""
                continue
            if not document.attachment_id.raw:
                _logger.critical(document.l10n_mx_edi_uuid)
                if not document.l10n_mx_edi_uuid:
                    document.l10n_mx_edi_uuid = ""
                continue
            nodes = document._getNodes(document.attachment_id.raw)
            if 'tfd_node' not in nodes.keys():
                _logger.critical("no tfd node")
                continue

            document.l10n_mx_edi_uuid = nodes['tfd_node'].get('UUID')

    def _getNodes(self, cfdi_data : str):
        try:
            file = io.BytesIO(cfdi_data)
            tfd_node = None
            for element in etree.iterparse(file):
                if '}TimbreFiscalDigital' in element[1].tag:
                    tfd_node = element[1]
                    break
        except AttributeError:
            # Not a CFDI
            _logger.critical("Attribute errror")
            return {}
        if tfd_node is not None:
            return {
                'tfd_node' : tfd_node
            }
        return {}
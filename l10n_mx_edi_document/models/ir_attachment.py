# Copyright 2019, Vauxoo, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging
from io import BytesIO

from lxml import objectify, etree
from odoo import api, models, _
from odoo.tools.xml_utils import _check_with_xsd
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def l10n_mx_edi_is_cfdi33(self):
        self.ensure_one()
        if not self.datas:
            return False
        try:
            datas = base64.b64decode(self.datas).replace(
                b'xmlns:schemaLocation', b'xsi:schemaLocation')
            cfdi = objectify.fromstring(datas)
        except (SyntaxError, ValueError):
            return False

        attachment = self.env.ref('l10n_mx_edi.xsd_cached_cfdv33_xsd', False)
        schema = base64.b64decode(attachment.datas) if attachment else b''
        try:
            if cfdi.get('Version') != '3.3' or not hasattr(
                    cfdi, 'Complemento'):
                return False
            if hasattr(cfdi, 'Addenda'):
                cfdi.remove(cfdi.Addenda)
            if not attachment:
                return cfdi
            attribute = 'registrofiscal:CFDIRegistroFiscal'
            namespace = {
                'registrofiscal': 'http://www.sat.gob.mx/registrofiscal'}
            node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
            if node:
                cfdi.Complemento.remove(node[0])
            with BytesIO(schema) as xsd:
                _check_with_xsd(cfdi, xsd)
            return cfdi
        except ValueError:
            return False
        except IOError:
            return False
        except UserError:
            return False
        except etree.XMLSyntaxError:
            return False
        return False

    def l10n_mx_edi_document_type(self):
        self.ensure_one()
        cfdi = self.l10n_mx_edi_is_cfdi33()
        if cfdi is False:
            self.message_post(body=_('This Document is not a CFDI valid.'))
            return False
        self.res_model = {
            'P': 'account.payment',
            'I': 'account.invoice',
            'E': 'account.invoice',
        }.get(cfdi.get('TipoDeComprobante'))
        vat = self.company_id.vat
        document_type = 'customer' if cfdi.Emisor.get('Rfc') == vat else (
            'vendor' if cfdi.Receptor.get('Rfc') == vat else False)
        if not document_type:
            self.message_post(body=_(
                'Neither the emitter nor the receiver of this CFDI is this '
                'company, please review this document.'))
        return ('%s%s' % (document_type, cfdi.get(
            'TipoDeComprobante'))) if document_type else False

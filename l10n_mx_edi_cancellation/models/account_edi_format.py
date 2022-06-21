from odoo import api, models, fields, tools, _
from odoo.tools.xml_utils import _check_with_xsd
from odoo.tools.float_utils import float_round, float_is_zero

import logging
import re
import base64
import json
import requests
import random
import string

from lxml import etree
from lxml.objectify import fromstring
from math import copysign
from datetime import datetime
from io import BytesIO
from zeep import Client
from zeep.transports import Transport
from json.decoder import JSONDecodeError

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_mx_edi_finkok_cancel(self, move, credentials, cfdi):
        uuid_replace = move.l10n_mx_edi_cancel_invoice_id.l10n_mx_edi_cfdi_uuid
        return self._l10n_mx_edi_finkok_cancel_service(move.l10n_mx_edi_cfdi_uuid, move.company_id, credentials,
                                                       uuid_replace=uuid_replace,cancel_case=move.l10n_mx_edi_cancellation)

    def _l10n_mx_edi_finkok_cancel_service(self, uuid, company, credentials, uuid_replace=None,cancel_case=None
    ):
        ''' Cancel the CFDI document with PAC: finkok. Does not depend on a recordset
        '''
        cancel_data = (cancel_case or '').split('|')
        certificates = company.l10n_mx_edi_certificate_ids
        certificate = certificates.sudo().get_valid_certificate()
        cer_pem = certificate.get_pem_cer(certificate.content)
        key_pem = certificate.get_pem_key(certificate.key, certificate.password)
        try:
            transport = Transport(timeout=20)
            client = Client(credentials['cancel_url'], transport=transport)
            factory = client.type_factory('apps.services.soap.core.views')
            uuid_type = factory.UUID()
            uuid_type.UUID = uuid
            uuid_type.Motivo = cancel_data[0]
            if uuid_replace:
                uuid_type.FolioSustitucion = uuid_replace
            if cancel_data[0] == '01' and len(cancel_data) > 1:
                    uuid_type.FolioSustitucion = cancel_data[1]
            docs_list = factory.UUIDArray(uuid_type)
            response = client.service.cancel(
                docs_list,
                credentials['username'],
                credentials['password'],
                company.vat,
                cer_pem,
                key_pem,
            )
        except Exception as e:
            return {
                'errors': [_("The Finkok service failed to cancel with the following error: %s", str(e))],
            }

        if not getattr(response, 'Folios', None):
            code = getattr(response, 'CodEstatus', None)
            msg = _("Cancelling got an error") if code else _('A delay of 2 hours has to be respected before to cancel')
        else:
            code = getattr(response.Folios.Folio[0], 'EstatusUUID', None)
            cancelled = code in ('201', '202')  # cancelled or previously cancelled
            # no show code and response message if cancel was success
            code = '' if cancelled else code
            msg = '' if cancelled else _("Cancelling got an error")

        errors = []
        if code:
            errors.append(_("Code : %s") % code)
        if msg:
            errors.append(_("Message : %s") % msg)
        if errors:
            return {'errors': errors}

        return {'success': True}
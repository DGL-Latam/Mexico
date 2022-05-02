import base64
from tempfile import NamedTemporaryFile
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile, BadZipFile
from zeep import Client
from zeep.transports import Transport
from lxml import objectify
from lxml.etree import XMLSyntaxError
from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    l10n_mx_edi_stamp_code = fields.Char(
        'Stamp Code', copy=False, help='Process Id returned by finkok when you try to stamp with multistamp service')

    @api.multi
    def _l10n_mx_edi_finkok_sign(self, pac_info):
        res = super(AccountInvoice, self)._l10n_mx_edi_finkok_sign(pac_info)
        username = pac_info['username']
        password = pac_info['password']
        for inv in self.filtered(lambda i: i.l10n_mx_edi_pac_status == 'to_sign' and not i.l10n_mx_edi_stamp_code):
            test = inv.company_id.l10n_mx_edi_pac_test_env
            url = 'https://demo-transicion.finkok.com/servicios/soap/async?wsdl' if test else 'https://extra-facturacion.finkok.com/servicios/soap/async?wsdl'  # noqa
            with NamedTemporaryFile() as temp_zip:
                with ZipFile(temp_zip, 'w', compression=ZIP_DEFLATED) as stamp_zip:
                    stamp_zip.writestr(inv.l10n_mx_edi_cfdi_name, base64.b64decode(inv.l10n_mx_edi_cfdi))
                try:
                    transport = Transport(timeout=20)
                    client = Client(url, transport=transport)
                    temp_zip.seek(0)
                    response = client.service.multistamp(temp_zip.read(), username, password)
                    inv.l10n_mx_edi_stamp_code = getattr(response, 'id', None)
                except Exception as e:
                    inv.l10n_mx_edi_log_error(str(e))
                    continue
        for inv in self.filtered(lambda i: i.l10n_mx_edi_pac_status == 'to_sign' and i.l10n_mx_edi_stamp_code):
            test = inv.company_id.l10n_mx_edi_pac_test_env
            url = 'https://demo-transicion.finkok.com/servicios/soap/async?wsdl' if test else 'https://extra-facturacion.finkok.com/servicios/soap/async?wsdl'  # noqa
            try:
                transport = Transport(timeout=20)
                client = Client(url, transport=transport)
                response = client.service.get_result_multistamp(inv.l10n_mx_edi_stamp_code, username, password)
            except Exception as e:
                inv.l10n_mx_edi_log_error(str(e))
                continue
            code = 0
            msg = None
            if hasattr(response, 'Incidencias') and response.Incidencias:
                code = getattr(response.Incidencias.Incidencia[0], 'CodigoError', None)
                msg = getattr(response.Incidencias.Incidencia[0], 'MensajeIncidencia', None)
            files = inv._unzip_cfdi(response.file) if response.file else {}
            xml_signed = files.get('stamped-%s' % inv.l10n_mx_edi_cfdi_name)
            fail = files.get('fault-response-%s' % inv.l10n_mx_edi_cfdi_name)
            if fail:
                incidence = objectify.fromstring(fail)
                code = getattr(incidence.Incidencias.getchildren()[0], 'CodigoError', None)
                msg = getattr(incidence.Incidencias.getchildren()[0], 'MensajeIncidencia', None)
            if xml_signed:
                xml_signed = base64.b64encode(xml_signed)
            inv._l10n_mx_edi_post_sign_process(xml_signed, code, msg)
        return res

    @api.model
    def _unzip_cfdi(self, cfdi):
        """Return a valid xml object to be analyzed
        :param str cfdi: Base64 string of a zipped file.
        :return: an dict with files and content.
        :rtype: dict
        """
        message = ""
        content = {}
        try:
            cfdi = ZipFile(BytesIO(cfdi))
            for element in cfdi.namelist():
                content[element] = cfdi.read(element)
        except BadZipFile as error:
            message = error
        except XMLSyntaxError as error:
            message = error
        else:
            return content
        finally:
            self.message_post(body=message)

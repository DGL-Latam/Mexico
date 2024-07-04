from odoo import models, fields, exceptions, tools, _

from lxml.objectify import fromstring
from lxml import etree
from dateutil import parser

import logging
import base64
import io

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_mx_edi_decode_cfdi(self, cfdi_data=None):
        ''' Helper to extract relevant data from the CFDI to be used, for example, when printing the invoice.
        :param cfdi_data:   The optional cfdi data.
        :return:            A python dictionary.
        '''
        self.ensure_one()

        def get_node(cfdi_node, attribute, namespaces):
            if hasattr(cfdi_node, 'Complemento'):
                node = cfdi_node.Complemento.xpath(attribute, namespaces=namespaces)
                return node[0] if node else None
            else:
                return None

        def get_cadena(cfdi_node, template):
            if cfdi_node is None:
                return None
            cadena_root = etree.parse(tools.file_open(template))
            return str(etree.XSLT(cadena_root)(cfdi_node))

        def is_purchase_move(move):
            return move.move_type in move.get_purchase_types() \
                    or move.payment_id.reconciled_bill_ids

        # Find a signed cfdi.
        if not cfdi_data:
            signed_edi = self._get_l10n_mx_edi_signed_edi_document()
            if signed_edi:
                cfdi_data = base64.decodebytes(signed_edi.attachment_id.with_context(bin_size=False).datas)
            if not signed_edi and is_purchase_move(self):
                attachment = self._get_l10n_mx_edi_cfdi_attachment()
                if attachment:
                    cfdi_data = base64.decodebytes(attachment.with_context(bin_size=False).datas)

        # Nothing to decode.
        if not cfdi_data:
            return {}

        try:
            cfdi_node = fromstring(cfdi_data)
            emisor_node = cfdi_node.Emisor
            receptor_node = cfdi_node.Receptor

            tfd_node = get_node(
            cfdi_node,
            'tfd:TimbreFiscalDigital[1]',
            {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'},
            )
        except etree.XMLSyntaxError as e:
            _logger.error('XML Syntax Error: %s', e)
            file = io.BytesIO(cfdi_data)
            try:
                for element in etree.iterparse(file):
                    if '}Emisor' in element[1].tag:
                        emisor_node = element[1]
                    if '}Receptor' in element[1].tag:
                        receptor_node = element[1]
                    if '}Comprobante' in element[1].tag:
                        cfdi_node = element[1]
                    if '}TimbreFiscalDigital' in element[1].tag:
                        tfd_node = element[1]
            except Exception as e:
                _logger.error('Error decoding CFDI: %s', e)
                return {}
        except AttributeError:
            # Not a CFDI
            return {}
        except Exception as e:
            _logger.error('Error decoding CFDI: %s', e)
            return {}

        return {
            'uuid': ({} if tfd_node is None else tfd_node).get('UUID'),
            'supplier_rfc': emisor_node.get('Rfc', emisor_node.get('rfc')),
            'customer_rfc': receptor_node.get('Rfc', receptor_node.get('rfc')),
            'amount_total': cfdi_node.get('Total', cfdi_node.get('total')),
            'cfdi_node': cfdi_node,
            'usage': receptor_node.get('UsoCFDI'),
            'payment_method': cfdi_node.get('formaDePago', cfdi_node.get('MetodoPago')),
            'bank_account': cfdi_node.get('NumCtaPago'),
            'sello': cfdi_node.get('sello', cfdi_node.get('Sello', 'No identificado')),
            'sello_sat': tfd_node is not None and tfd_node.get('selloSAT', tfd_node.get('SelloSAT', 'No identificado')),
            'cadena': tfd_node is not None and get_cadena(tfd_node, self._l10n_mx_edi_get_cadena_xslts()[0]) or get_cadena(cfdi_node, self._l10n_mx_edi_get_cadena_xslts()[1]),
            'certificate_number': cfdi_node.get('noCertificado', cfdi_node.get('NoCertificado')),
            'certificate_sat_number': tfd_node is not None and tfd_node.get('NoCertificadoSAT'),
            'expedition': cfdi_node.get('LugarExpedicion'),
            'fiscal_regime': emisor_node.get('RegimenFiscal', ''),
            'emission_date_str': cfdi_node.get('fecha', cfdi_node.get('Fecha', '')).replace('T', ' '),
            'stamp_date': tfd_node is not None and tfd_node.get('FechaTimbrado', '').replace('T', ' '),
        }
    
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

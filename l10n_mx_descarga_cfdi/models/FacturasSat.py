from odoo import models, fields
import base64
import datetime
import pytz
import os
import time
import zipfile
import io


from lxml.objectify import fromstring
from lxml import etree
from dateutil import parser

from .Autentificacion import Autentificacion
from .Fiel import Fiel
from .SolicitudDescarga import SolicitudDescarga
from .Verificacion import VerificaSolicitudDescarga
from .DescargaMasiva import DescargaMasiva

import logging
_logger = logging.getLogger(__name__)


class SolicitudesDescarga(models.Model):
    _name = "solicitud.descarga"
    _descripcion = "Solicitudes Descargas SAT"
    
    id_solicitud = fields.Char(string="ID de la solicitud", copy=False, readonly=True)
    estado_solicitud = fields.Selection(selection = [
        ('0', 'Token Invalido'),
        ('1', 'Aceptada'),
        ('2', 'En proceso'),
        ('3', 'Terminada'),
        ('4', 'Error'),
        ('5', 'Rechazada'),
        ('6', 'Vencida')
    ], default='1', string='Estado de la Solicitud')

    company_id = fields.Many2one('res.company', string="Empresa", required="True")
    
    document_downloaded = fields.Many2one('documents.document', string="Documento Descargado")

    to_process_zip = fields.Boolean(default=False)
    
    def _getFiel(self, company):
        cer = company.l10n_mx_fiel_cer
        key = company.l10n_mx_fiel_key
        password = company.l10n_mx_fiel_pass
        fiel = Fiel(base64.decodebytes(cer),base64.decodebytes(key),password.encode('UTF-8'))
        return fiel

    def _getToken(self,company, fiel = None):
        if fiel is None:
            fiel = self._getFiel(company)
        autentificacion = Autentificacion(fiel)
        token = autentificacion.obtener_token()
        return token

    def _NuevaSolicitud(self,company):
        fiel = self._getFiel(company)
        token = self._getToken(company,fiel)
        solicitudDes = SolicitudDescarga(fiel)
        datetime_str = '07/12/22 00:00:00'
        datetime_str2 = '07/12/22 23:59:58'
        solicitud = solicitudDes.SolicitarDescarga(
            token,
            company.vat, 
            datetime.datetime.strptime(datetime_str, '%d/%m/%y %H:%M:%S'),
            datetime.datetime.strptime(datetime_str2, '%d/%m/%y %H:%M:%S'),
            rfc_receptor = company.vat
        )
        self.env['solicitud.descarga'].sudo().create( {
            'id_solicitud' : solicitud['id_solicitud'], 
            'estado_solicitud' : '1' if solicitud['mensaje'] == 'Solicitud Aceptada' else '0',
            'company_id' : company.id
        } )
        
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

    def _ProcessXML(self, xml : str):
        nodes = self._getNodes(xml)
        if not nodes:
            return
        reg = self.env['facturas.sat'].sudo().search([('sat_uuid','=',nodes['tfd_node'].get('UUID'))])
        if reg.id:
            return
        mexTime = pytz.timezone('America/Mexico_City')
        f_emitido = mexTime.localize(datetime.datetime.strptime( nodes['cfdi_node'].get('Fecha') , '%Y-%m-%dT%H:%M:%S'))
        f_timbrado = mexTime.localize(datetime.datetime.strptime( nodes['tfd_node'].get('FechaTimbrado') , '%Y-%m-%dT%H:%M:%S'))
        fact = self.env['facturas.sat'].sudo().create({
            'sat_uuid' : nodes['tfd_node'].get('UUID'),
            'sat_rfc_emisor' : nodes['emisor_node'].get('Rfc', nodes['emisor_node'].get('rfc')),
            'sat_monto' : float(nodes['cfdi_node'].get('Total')),
            'sat_fecha_emision' :  f_emitido.astimezone(pytz.utc).replace(tzinfo=None),
            'sat_fecha_timbrado' : f_timbrado.astimezone(pytz.utc).replace(tzinfo=None) ,
            'sat_tipo_factura' : nodes['cfdi_node'].get('TipoDeComprobante'),
            'company' : self.company_id.id
        })
        #fact.SearchOdooInvoice()
        
    def printEstado(self):
        for rec in self:
            _logger.critical(rec.estado_solicitud)
    
    def checkzip(self):
        for rec in self:
            if rec.document_downloaded.id:
                rec._ProcessZip(rec.document_downloaded.attachment_id.raw)
                rec.write({'to_process_zip' : False})
                
    def _ProcessZip(self, zipBytes):
        z = zipfile.ZipFile(io.BytesIO(zipBytes))
        for filename in z.infolist():
            file = z.read(filename)
            self._ProcessXML(file)
        z.close()
        
    def attachzip(self):
        for rec in self:
            if rec.estado_solicitud == '3':
                document = self.env['documents.document'].search([('name', 'ilike',rec.id_solicitud)], limit=1)
                rec.write({'document_downloaded' :  document.id})
    
    def _VerificarSolicitud(self):
        for rec in self:
            
            fiel = self._getFiel(self.company_id)
            token = self._getToken(self.company_id,fiel)
            verificacion = VerificaSolicitudDescarga(fiel)
            verificacionValues = verificacion.VerificarDescarga(token=token,rfc_solicitante=rec.company_id.vat, id_solicitud=rec.id_solicitud)
            estado = int( verificacionValues['estado_solicitud'] ) 
            rec.write( {'estado_solicitud' : verificacionValues['estado_solicitud']  } ) 
            
            if estado == 3:
                for paquete in verificacionValues['paquetes']:
                    descarga = DescargaMasiva(fiel)
                    zip_data = descarga.DescargarPaquete(token,rec.company_id.vat,paquete)
                    if zip_data['paquete_b64'] is not None:
                        ir_attachment = self.env['ir.attachment'].sudo().create( {
                            'name' : rec.id_solicitud,
                            'type' : 'binary',
                            'raw' : base64.b64decode(zip_data['paquete_b64']),
                        })
                        folder = self.env['documents.folder'].sudo().search([('name','ilike','SAT'),('company_id','=',rec.company_id.id)])
                        document = self.env['documents.document'].sudo().create({
                            'attachment_id' : ir_attachment.id,
                            'type' : 'binary',
                            'folder_id' : folder.id
                            })
                        rec.sudo().write({'document_downloaded' : document.id, 'to_process_zip' : True})
                
            
class FacturasSat(models.Model):
    _name = "facturas.sat"

    _description = "Facturas SAT"

    sat_uuid = fields.Char(string="Folio Fiscal", copy=False, readonly=True,  required=True)
    sat_state = fields.Char(string="Estado Factura SAT")
    sat_rfc_emisor = fields.Char(string="RFC Emisor")
    sat_monto = fields.Float(string="Monto")
    sat_fecha_emision = fields.Datetime(string="Fecha Emision")
    sat_fecha_timbrado = fields.Datetime(string="Fecha de Timbrado")
    sat_fecha_cancelacion = fields.Datetime(string="Fecha Cancelacion")
    sat_tipo_factura = fields.Selection(selection = [
        ('I', 'Ingreso'),
        ('E', 'Egreso'),
        ('P', 'Pago'),
        ('N', 'Nomina'),
        ('T', 'Traslado (Carta Porte)'),
    ], default='1', string='Tipo de Factura')

    account_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Factura Odoo")
    account_move_status = fields.Selection(string="Estado Factura Odoo", related='account_move_id.state', readonly=True)

    company = fields.Many2one(comodel_name="res.company",string="Empresa")

    _sql_constraints = [
        ('sat_uuid_unique',
        'unique(sat_uuid)', 'No se deben repetir UUID'),
    ]
    
    
    def SearchOdooInvoice(self):
        for r in self:
            fact = self.env['account.move'].search([('company_id', '=', r.company.id), ('l10n_mx_edi_cfdi_uuid','=',r.sat_uuid)])
            r.account_move_id = fact.id

    def printinfo(self):
        for r in self:
            _logger.critical(f'fecha timbrado: {r.sat_fecha_timbrado}  fecha emision: {r.sat_fecha_emision}')
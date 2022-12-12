from odoo import models, fields
import base64
import datetime
import os
import time

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
    
    def _getFiel(self, company):
        cer = company.l10n_mx_fiel_cer
        key = company.l10n_mx_fiel_key
        password = company.l10n_mx_fiel_pass
        key_pem = self.env['l10n_mx_edi.certificate'].sudo().search([],limit=1).get_pem_key(key, password)
        fiel = Fiel(base64.decodebytes(cer),key_pem,password.encode('UTF-8'))
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
        _logger.critical(token)
        solicitudDes = SolicitudDescarga(fiel)

        solicitud = solicitudDes.SolicitarDescarga(
            token,
            company.vat, 
            datetime.datetime.today() - datetime.timedelta(days=5),
            datetime.datetime.now(),
            rfc_receptor = company.vat
        )
        self.env['solicitud.descarga'].sudo().create( {
            'id_solicitud' : solicitud['id_solicitud'], 
            'estado_solicitud' : '1' if solicitud['mensaje'] == 'Solicitud Aceptada' else '0',
            'company_id' : company.id
        } )
        _logger.critical(solicitud)

        
    def _VerificarSolicitud(self):
        for rec in self:
            
            fiel = self._getFiel(self.company_id)
            token = self._getToken(self.company_id,fiel)
            _logger.critical(rec)
            _logger.critical(rec.id_solicitud)
            verificacion = VerificaSolicitudDescarga(fiel)
            verificacionValues = verificacion.VerificarDescarga(token=token,rfc_solicitante=rec.company_id.vat, id_solicitud=rec.id_solicitud)
            estado = int( verificacionValues['estado_solicitud'] ) 
            rec.write( {'estado_solicitud' : verificacionValues['estado_solicitud']  } ) 
            _logger.critical(verificacionValues)
            
            if estado == 3:
                for paquete in verificacionValues['paquetes']:
                    descarga = DescargaMasiva(fiel)
                    zip_data = descarga.DescargarPaquete(token,rec.company_id.vat,paquete)
                    _logger.critical(zip_data)
                    if zip_data['paquete_b64'] is not None:
                        ir_attachment = self.env['ir.attachment'].sudo().create( {
                            'name' : rec.id_solicitud,
                            'type' : 'binary',
                            'raw' : base64.b64decode(zip_data['paquete_b64']),
                        })
                        folder = self.env['documents.folder'].sudo().search([('name','ilike','internal'),('company_id','=',rec.company_id.id)])
                        document = self.env['documents.document'].sudo().create({
                            'attachment_id' : ir_attachment.id,
                            'type' : 'binary',
                            'folder_id' : folder.id
                        })
                        _logger.critical(zip_data)
                
            
class FacturasSat(models.Model):
    _name = "facturas.sat"

    _description = "Tabla para guardar la relacion de las facturas encontradas en el sat mediante el Web service, y las que existen en sistema"

    sat_uuid = fields.Char(string="Folio Fiscal", copy=False, readonly=True)
    sat_state = fields.Char(string="Estado Factura SAT")
    sat_rfc_emisor = fields.Char(string="RFC Emisor")
    sat_monto = fields.Float(string="Monto")
    sat_fecha_emision = fields.Date(string="Fecha Emision")
    sat_fecha_cancelacion = fields.Date(string="Fecha Cancelacion")

    account_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Factura Odoo")
    account_move_status = fields.Selection(string="Estado Factura Odoo", related='account_move_id.state', readonly=True)

    company = fields.Many2one(comodel_name="res.company",string="Empresa")

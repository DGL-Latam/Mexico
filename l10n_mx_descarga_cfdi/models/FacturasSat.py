from odoo import models, fields, api
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

    fechaInicio = fields.Datetime(string="fecha inicio busqueda")
    fechaFin = fields.Datetime(string="fecha fin busqueda")
    
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
        yesterday = datetime.datetime.today() - datetime.timedelta(days=1,hours=6)
        
        datetime_str =  yesterday.strftime('%d/%m/%y') + ' 00:00:00'
        datetime_str2 = yesterday.strftime('%d/%m/%y') + ' 23:59:59'
        fechaI = datetime.datetime.strptime(datetime_str, '%d/%m/%y %H:%M:%S')
        fechaF = datetime.datetime.strptime(datetime_str2, '%d/%m/%y %H:%M:%S')
        solicitud = solicitudDes.SolicitarDescarga(
            token,
            company.vat, 
            fechaI,
            fechaF,
            rfc_receptor = company.vat
        )
        self.env['solicitud.descarga'].sudo().create( {
            'id_solicitud' : solicitud['id_solicitud'], 
            'estado_solicitud' : '1' if solicitud['mensaje'] == 'Solicitud Aceptada' else '0',
            'company_id' : company.id,
            'fechaInicio' : fechaI,
            'fechaFin' : fechaF,
        } )

    def reintentar(self):
        fiel = self._getFiel(self.company_id)
        token = self._getToken(self.company_id,fiel)
        solicitudDes = SolicitudDescarga(fiel)
        solicitud = solicitudDes.SolicitarDescarga(
            token,
            self.company_id, 
            self.fechaInicio,
            self.fechaFin,
            rfc_receptor = self.company_id.vat
        ) 
        self.env['solicitud.descarga'].sudo().create( {
            'id_solicitud' : solicitud['id_solicitud'], 
            'estado_solicitud' : '1' if solicitud['mensaje'] == 'Solicitud Aceptada' else '0',
            'company_id' : self.company_id.id,
            'fechaInicio' : self.fechaInicio,
            'fechaFin' : self.fechaFin,
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
            conceptos_node = cfdi_node.Conceptos


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
                if '}Conceptos' in element[1].tag:
                    conceptos_node = element[1]
                if '}TimbreFiscalDigital' in element[1].tag:
                    tfd_node = element[1]
        
        except AttributeError:
            # Not a CFDI
            return {}
        return {
            'cfdi_node' : cfdi_node,
            'emisor_node' : emisor_node,
            'receptor_node' : receptor_node,
            'conceptos_node': conceptos_node,
            'tfd_node' : tfd_node,

        }

    def _ProcessXML(self, xml : str):
        nodes = self._getNodes(xml)
        registros = []
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
            'sat_name_emisor' : nodes['emisor_node'].get('Nombre', nodes['emisor_node'].get('nombre')),
            'sat_name_receptor' : nodes['receptor_node'].get('Nombre', nodes['receptor_node'].get('nombre')),
            'sat_monto' : float(nodes['cfdi_node'].get('Total')),
            'sat_fecha_emision' :  f_emitido.astimezone(pytz.utc).replace(tzinfo=None),
            'sat_fecha_timbrado' : f_timbrado.astimezone(pytz.utc).replace(tzinfo=None) ,
            'sat_tipo_factura' : nodes['cfdi_node'].get('TipoDeComprobante'),
            'company' : self.company_id.id
        })
        
        for element in nodes['conceptos_node'].Concepto:
            registros.append({
                'code_service_product':element.get('ClaveProdServ'),
                'factura_id': fact.id,
                'id_product':element.get('NoIdentificacion'),
                'name_product':element.get('Descripcion'),
                'quantity':element.get('Cantidad'),
                'unit':element.get('Unidad'),
                'valaue_unitary':element.get('ValorUnitario'),
                'amount':element.Impuestos.Traslados.Traslado.get('Importe'),
                'type_factory':element.Impuestos.Traslados.Traslado.get('TipoFactor'),
                'value_tasa':element.Impuestos.Traslados.Traslado.get('TasaOCuota'),
                'value_unitary_amount': str(float(element.get('ValorUnitario') + float(element.Impuestos.Traslados.Traslado.get('Importe')))),
                'subtotal':nodes['cfdi_node'].get('SubTotal'),
                'total': nodes['cfdi_node'].get('Total'),
                'type_moneda': nodes['cfdi_node'].get('Moneda'),
                'type_pay':nodes['cfdi_node'].get('CondicionDePago')
            })
        fact1 = self.env['details.facturasat'].sudo().create(registros) 
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
            if verificacionValues["cod_estatus"] == 404:
                rec.reintentar()
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
    sat_state = fields.Char(string="Estado Factura SAT", readonly=True)
    sat_rfc_emisor = fields.Char(string="RFC Emisor", readonly=True)
    sat_name_emisor = fields.Char(string="Nombre Emisor", readonly=True)
    sat_name_receptor = fields.Char(string="Nombre Receptor", readonly=True)
    sat_monto = fields.Float(string="Monto", readonly=True)
    sat_fecha_emision = fields.Datetime(string="Fecha Emision", readonly=True)
    sat_fecha_timbrado = fields.Datetime(string="Fecha de Timbrado", readonly=True)
    sat_fecha_cancelacion = fields.Datetime(string="Fecha Cancelacion", readonly=True)
    sat_tipo_factura = fields.Selection(selection = [
        ('I', 'Ingreso'),
        ('E', 'Egreso'),
        ('P', 'Pago'),
        ('N', 'Nomina'),
        ('T', 'Traslado (Carta Porte)'),
    ], default='1', string='Tipo de Factura', readonly=True)

    id_details_products = fields.One2many('details.facturasat','factura_id','Productos')
    account_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Factura Odoo", readonly=True)
    
    account_move_status = fields.Selection(string="Estado Factura Odoo", related='account_move_id.state', readonly=True)
    account_move_currency = fields.Many2one(comodel_name='res.currency', related="account_move_id.currency_id", readonly=True)
    account_move_total = fields.Monetary(string="Total Factura Odoo", related="account_move_id.amount_total", readonly=True, currency_field='account_move_currency')
    account_move_partner_id = fields.Many2one(string="Socio",comodel_name="res.partner", related="account_move_id.partner_id", readonly=True)
    account_move_partner_vat = fields.Char(related="account_move_partner_id.vat", readonly=True)
    account_move_date = fields.Date(string="Fecha Movimiento",related="account_move_id.date", readonly=True)

    company = fields.Many2one(comodel_name="res.company",string="Empresa")

    _sql_constraints = [
        ('sat_uuid_unique',
        'unique(sat_uuid)', 'No se deben repetir UUID'),
    ]
    
    diferentials = fields.Selection(selection= [
        ('all_good', 'No hay diferencia'),
        ('wrong_amount', 'Monto Distinto'),
        ('wrong_emiter', 'Emisor Distinto'),
        ('wrong_date', 'Fecha distinta'),
        ('wrong_status', 'Distinto Estado'),
        ('no_odoo', 'No existe en Odoo')    
    ], compute="_check_diferential", store=True)

    @api.depends('account_move_id','account_move_total','account_move_partner_vat','account_move_date','account_move_status')
    def _check_diferential(self):
        for rec in self:
            if not rec.account_move_id:
                rec.SearchOdooInvoice()
                if not rec.account_move_id:
                    rec.write({'diferentials' : 'no_odoo'})
                    continue
            if rec.account_move_total != rec.sat_monto:
                rec.write({'diferentials' : 'wrong_amount'})
                continue
            if rec.account_move_partner_vat != rec.sat_rfc_emisor:
                rec.write({'diferentials' : 'wrong_emiter'})
                continue
            if rec.account_move_date != rec.sat_fecha_emision.date():
                rec.write({'diferentials' : 'wrong_date'})
                continue
            rec.write({'diferentials' : 'all_good'})

    def SearchOdooInvoice(self):
        for r in self:
            fact = self.env['account.move'].search([('company_id', '=', r.company.id), ('l10n_mx_edi_cfdi_uuid','=',r.sat_uuid)])
            r.account_move_id = fact.id

    def printinfo(self):
        for r in self:
            _logger.critical(f'fecha timbrado: {r.sat_fecha_timbrado}  fecha emision: {r.sat_fecha_emision}')


class FacturasSatDetails(models.Model):
    _name = "details.facturasat"
    _description = "Detalles Facturas SAT"
   
    code_service_product = fields.Char(string="Clave Producto")
    id_product = fields.Char(string="Ideentificador Producto")
    name_product = fields.Char(string="Nombre Producto", readonly=True,  required=True)
    quantity = fields.Char(string="Cantidad")
    unit = fields.Char(string="UdM")
    value_unitary = fields.Char(string="Precio Unitario") 
    amount = fields.Char(string="Importe")
    value_unitary_amount = fields.Char(string="Total")
    type_factory = fields.Char(string="Tipo Factor")
    value_tasa = fields.Char(string="Impuesto")
    subtotal = fields.Char(string="SubTotal")
    total = fields.Char(string="Total")
    type_moneda = fields.Char(string="Tipo Moneda")
    type_pay = fields.Char(string="Condiciones pago")
    factura_id = fields.Many2one('facturas.sat')


from odoo import models, fields, api
from odoo.exceptions import UserError
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
    """ Modelo generado para llevar el control de las solicitadas al SAT, su estado y datos para procesamiento """
    _name = "solicitud.descarga"
    _description = "Solicitudes Descargas SAT"
    
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

    emitidas = fields.Boolean(default=False)
    
    def _getFiel(self, company):
        #Recuperamos la Fiel decodificada que tenemos guardada en la base de datos
        cer = company.l10n_mx_fiel_cer
        key = company.l10n_mx_fiel_key
        password = company.l10n_mx_fiel_pass
        fiel = Fiel(base64.decodebytes(cer),base64.decodebytes(key),password.encode('UTF-8'))
        return fiel

    def _getToken(self,company, fiel = None):
        #Se con la Fiel, se hace una peticion al sistema del SAT para que nos genere un Token para las solicitudes
        if fiel is None:
            fiel = self._getFiel(company)
        autentificacion = Autentificacion(fiel)
        token = autentificacion.obtener_token()
        return token
    
    def _GetSolicitudxma(self,company):
        # De acuerdo a la compañia obtenemos su Fiel y Token, con estos datos generamos la solicitud de Descarga
        fiel = self._getFiel(company)
        token = self._getToken(company,fiel)
        solicitudDes = SolicitudDescarga(fiel) 
        return solicitudDes, token 
    
    def _NuevaSolicitud(self,company, fechaInicio = None, fechaFin = None, emitidas = False):
        """ Metodo padre para el servicio Cron que genera las solicitudes al SAT para la recuperacion de Facturas
        company es el id de la compañia que esta haciendo la solicitud, la cual debe de tener los datos de llave Fiel, certificado y frase en su configuracion
        Fecha de inicio : Para poder indicar desde que fecha quiere que se genere, en caso de que no se especifique se tomara la fecha del dia anterior a las 0:00
        Fecga de Fin : Para poder indicar hasta que fecha se quiere recuperar facturas, en caso de no ser indicado se tomara la media noche del dia anterior
        emitidas : Booleano para indicar si se busca recuperar la facturas emitidas o recibidas"""
        solicitudDes, token = self._GetSolicitudxma(company)
        fechaI, fechaF = "" , ""
        if fechaInicio or fechaFin:
            fechaI = datetime.datetime.strptime(fechaInicio, '%d/%m/%y %H:%M:%S')
            fechaF = datetime.datetime.strptime(fechaFin, '%d/%m/%y %H:%M:%S') 
        else:
            yesterday = datetime.datetime.today() - datetime.timedelta(days=1,hours=6)
            datetime_str =  yesterday.strftime('%d/%m/%y') + ' 00:00:00'
            datetime_str2 = yesterday.strftime('%d/%m/%y') + ' 23:59:59'
            fechaI = datetime.datetime.strptime(datetime_str, '%d/%m/%y %H:%M:%S')
            fechaF = datetime.datetime.strptime(datetime_str2, '%d/%m/%y %H:%M:%S')
        if emitidas:
            #si se piden las facturas emitidas se pasa el rfc de la empresa en el valor de rfc_emisor
            solicitud = solicitudDes.SolicitarDescarga(
                token,
                company.vat, 
                fechaI,
                fechaF,
                rfc_emisor = company.vat
            )
        else:
            #si se piden las facturas emitidas se pasa el rfc de la empresa en el valor de rfc_emisor
            solicitud = solicitudDes.SolicitarDescarga(
                token,
                company.vat, 
                fechaI,
                fechaF,
                rfc_receptor = company.vat
            )
        
        #Una vez que se hizo la solicitud con los datos que nos responde creamos la entrada en nuestra tabla
        self.env['solicitud.descarga'].sudo().create( {
            'id_solicitud' : solicitud['id_solicitud'], 
            'estado_solicitud' : '1' if solicitud['mensaje'] == 'Solicitud Aceptada' else '0',
            'company_id' : company.id,
            'fechaInicio' : fechaI,
            'fechaFin' : fechaF,
            'emitidas' : emitidas,
        } )

    def reintentar(self):
        #en el caso que nos rechace la solicitud, se vuelva a intentar creando una solicitud nueva con los mismos datos
        solicitudDes,token = self._GetSolicitudxma(self.company_id)
        if self.emitidas:
            solicitud = solicitudDes.SolicitarDescarga(
                token,
                self.company_id, 
                self.fechaInicio,
                self.fechaFin,
                rfc_emisor = self.company_id.vat
            ) 
        else:
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
            'emitidas' : self.emitidas
        } )

    def _getNodes(self, cfdi_data : str):
        #Utilidad para recuperar los nodos principales del xml para despues ser procesados}
        #Tiene dos metodos de recuperacion en caso de que uno falle por desborde de memoria
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

    def _ProcessXML(self, xml : str, filename : str):
        """ Metodo para procesar el archivo xml de la factura, para colocar todos los detalles de este dentro de nuestro modelo
        xml : el contenido del archivo xml como una variable string, que sera procesado en un etree en otro metodo
        filename: Nombre que tiene el archivo, este es necesario guardarlo para que despues se pueda volver a procesar en caso de ser necesario
        
        Resulta en crear un registro en la tabla de facturas.sat al igual que todos los detalles de conceptos de esta"""
        nodes = self._getNodes(xml)
        registros = []
        if not nodes:
            return
        
        #no se debe de poder procesar una factura que ya esta registrada en nuestra BD
        reg = self.env['facturas.sat'].sudo().search([('sat_uuid','=',nodes['tfd_node'].get('UUID'))])
        if reg.id:
            return
        
        # los datos de fechas dentro de la factura ya estan en hora de mexico, entonces se indica de forma explicita en las variables
        mexTime = pytz.timezone('America/Mexico_City')
        f_emitido = mexTime.localize(datetime.datetime.strptime( nodes['cfdi_node'].get('Fecha') , '%Y-%m-%dT%H:%M:%S'))
        f_timbrado = mexTime.localize(datetime.datetime.strptime( nodes['tfd_node'].get('FechaTimbrado') , '%Y-%m-%dT%H:%M:%S'))

        #se crea el registro de la factura sin detalles, estos seran agregados posteriormente
        fact = self.env['facturas.sat'].sudo().create({
            'sat_uuid' : nodes['tfd_node'].get('UUID'),
            'sat_rfc_emisor' : nodes['emisor_node'].get('Rfc', nodes['emisor_node'].get('rfc')),
            'sat_name_emisor' : nodes['emisor_node'].get('Nombre', nodes['emisor_node'].get('nombre')),
            'sat_rfc_receptor' : nodes['receptor_node'].get('Rfc', nodes['receptor_node'].get('rfc')),
            'sat_name_receptor' : nodes['receptor_node'].get('Nombre', nodes['receptor_node'].get('nombre')),
            'sat_monto' : float(nodes['cfdi_node'].get('Total')),
            'sat_moneda' : nodes['cfdi_node'].get('Moneda'),
            'sat_fecha_emision' :  f_emitido.astimezone(pytz.utc).replace(tzinfo=None),
            'sat_fecha_timbrado' : f_timbrado.astimezone(pytz.utc).replace(tzinfo=None) ,
            'sat_tipo_factura' : nodes['cfdi_node'].get('TipoDeComprobante'),
            'sat_metodo_pago' : nodes['cfdi_node'].get('FormaPago'),
            'sat_cfdi_usage' : nodes['receptor_node'].get('UsoCFDI'),
            'company' : self.company_id.id,
            'emitida' : self.emitidas,
            'zip_downloaded' : self.document_downloaded.id,
            'document_name' : filename,
        })

        # se crean los conceptos de la factura
        fact1 = self.env['details.facturasat'].sudo().create(self.getProducts(nodes,fact.id)) 

        
    def getProducts(self, nodes, fact_id):
        """ Cada factura tiene un elemento de Conceptos, dentro de esta cada Concepto es un producto o servicio
        que se le vende/compro, a si mismo este puede tener uno o mas impuestos que pueden ser retenidos o trasladados
        segun sea el caso, se crea una linea de concepto por producto y en los impuestos cada linea es un impuesto
        distinto con su tasa o cuota para que al crear la factura se pueda buscar por codigo

        nodes : Diccionario que apunta a los etree elements de la factura,
        fact_id : Id de la factura a la cual se le anexaran los conceptos
        """
        productos = []
        tax_type = {"001" : "ISR ", "002" : "IVA ", "003" : "IEPS "} #relacionde impuesto con su codigo SAT
        for element in nodes['conceptos_node'].Concepto:
            #recorremos todos los conceptos y se obtienen sus valores
            values = {
                'factura_id' : fact_id,
                'code_service_product': element.get('ClaveProdServ'),
                'id_product' : element.get('NoIdentificacion'),
                'quantity' : element.get('Cantidad'),
                'unit' : element.get('ClaveUnidad'),
                'name_product' : element.get('Descripcion'),
                'value_unitary' : element.get('ValorUnitario'),
                'amount' : element.get('Importe'),
                'discount' : element.get('Descuento'),
                'objeto_impuesto' : element.get('ObjetoImp'),
            }
            if element.get('ObjetoImp') != "02" and nodes['cfdi_node'].get('Version') == "4.0": 
                #en el cfdi 4.0 si el Objeto de I,puesto es distinto a 02 no esta obligado a describir los impuestos o no tiene
                # por lo que se agrega el producto sin impuestos
                productos.append(values)
                continue
            try : 
                #del concepto obtenemos el elemento hijo Impuestos que en si trae las colecciones de trasladados o retenciones
                Impuestos = element.Impuestos
            except AttributeError:
                # en caso de que no tenga este elemento (como puede ocurrir con el cfdi 3.3) se agrega solo el concepto y se continua el iterador
                productos.append(values)
                continue
            impuestos_trasladados = []
            impuestos_Retenidos = []
            for el in Impuestos.getchildren():
                #se obtienen el arreglo de impuestos retenidos y trasladados en caso de que existan, caso cotrario se obtienen un arreglo vacio
                impuestos_trasladados = el if 'Traslados' in el.tag else []
                impuestos_Retenidos = el if 'Retenciones' in el.tag else []
            taxt_text = ""
            #Por cada impuesto se crea una linea de texto que describe el impuesto, en caso de las retenciones seguimos la logica de Odoo
            # que la tasa o importe se vuelve negativo para indicar que es retencion siguen el esquema "Impuesto MontoOPorcentaje"

            # TODO : en el caso de que sea importe como el IEPS en gasolina evitar la multiplicacion x 100 que solo sirve en las tasas
            if type(impuestos_trasladados) != type([]):
                for imp in impuestos_trasladados.Traslado:
                    taxt_text += tax_type[imp.get('Impuesto')] + str(float(imp.get('TasaOCuota')) * 100) + "\n"
            if type(impuestos_Retenidos) != type([]):
                for imp in impuestos_Retenidos.Retencion:
                    taxt_text += tax_type[imp.get('Impuesto')] + "-" + str(float(imp.get('TasaOCuota')) * 100) + "\n"
            values['taxes'] = taxt_text
            productos.append(values)

        return productos


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
            self._ProcessXML(file, filename.filename)
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
    _rec_name = "sat_uuid"
    _description = "Facturas SAT"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sat_uuid = fields.Char(string="Folio Fiscal", copy=False, readonly=True,  required=True)
    sat_state = fields.Char(string="Estado Factura SAT", readonly=True)
    sat_rfc_emisor = fields.Char(string="RFC Emisor", readonly=True)
    sat_name_emisor = fields.Char(string="Nombre Emisor", readonly=True)
    sat_rfc_receptor = fields.Char(string="RFC Receptor", readonly=True)
    sat_name_receptor = fields.Char(string="Nombre Receptor", readonly=True)
    sat_monto = fields.Float(string="Monto", readonly=True)
    sat_fecha_emision = fields.Datetime(string="Fecha Emision", readonly=True)
    sat_fecha_timbrado = fields.Datetime(string="Fecha de Timbrado", readonly=True)
    sat_fecha_cancelacion = fields.Datetime(string="Fecha Cancelacion", readonly=True)
    sat_moneda = fields.Char(string="Moneda", readonly=True)
    sat_tipo_factura = fields.Selection(selection = [
        ('I', 'Ingreso'),
        ('E', 'Egreso'),
        ('P', 'Pago'),
        ('N', 'Nomina'),
        ('T', 'Traslado (Carta Porte)'),
    ], default='1', string='Tipo de Factura', readonly=True)
    sat_metodo_pago = fields.Char(string="Metodo de pago", readonly=True)
    sat_cfdi_usage = fields.Char(string="Uso CFDI", readonly=True)

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

    emitida = fields.Boolean(string="La factura es nuestra", readonly=True)

    company = fields.Many2one(comodel_name="res.company",string="Empresa")

    _sql_constraints = [
        ('sat_uuid_unique',
        'unique(sat_uuid)', 'No se deben repetir UUID'),
    ]
    
    diferentials = fields.Selection(selection= [
        ('all_good', 'No hay diferencia'),
        ('wrong_amount', 'Monto Distinto'),
        ('wrong_emiter', 'Emisor Distinto'),
        ('wrong_receptor', 'Receptor Distinto'),
        ('wrong_date', 'Fecha distinta'),
        ('wrong_status', 'Distinto Estado'),
        ('no_odoo', 'No existe en Odoo'),
    ], compute="_check_diferential", store=True)
    

    zip_downloaded = fields.Many2one('documents.document', string="Zip Relacionado")
    document_name = fields.Char(string = "Nombre del archivo")

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
            if rec.emitida:
                if rec.sat_rfc_receptor != rec.account_move_partner_vat:
                    rec.write({'diferentials' : 'wrong_receptor'})
                    continue
            else:
                if rec.account_move_partner_vat != rec.sat_rfc_emisor:
                    rec.write({'diferentials' : 'wrong_emiter'})
                    continue

            if rec.account_move_date != rec.sat_fecha_emision.date():
                rec.write({'diferentials' : 'wrong_date'})
                continue
            rec.write({'diferentials' : 'all_good'})

    def SearchOdooInvoice(self):
        for r in self:
            fact = self.env['account.move'].search([('company_id', '=', r.company.id), ('l10n_mx_edi_cfdi_uuid','=',r.sat_uuid),('state','=','posted')])
            if len(fact) > 1:
                r.account_move_id = fact[0].id
                continue
            r.account_move_id = fact.id

    def printinfo(self):
        for r in self:
            _logger.critical(f'fecha timbrado: {r.sat_fecha_timbrado}  fecha emision: {r.sat_fecha_emision}')

    def createInvoice(self):
        for rec in self:
            if rec.sat_tipo_factura not in ["I","E","P"]:
                return
            move_type = rec._getMoveType()
            if "invoice" in move_type or "refund" in move_type:
                rec._CreateAccountMove(move_type)
            #else:
                #self._CreatePayment()

    def _CreateAccountMove(self, move_type : str):
        journal_id = self.env['account.journal']
        date = self.sat_fecha_emision.date()
        partner_id = self.env['res.partner']
        currency = self.env['res.currency']
        if self.emitida:
            partner_id = self.env['res.partner'].search([('vat','=',self.sat_rfc_receptor)], limit = 1)
            journal_id = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id)
        ], limit=1)
        else:
            partner_id = self.env['res.partner'].search([('vat','=',self.sat_rfc_emisor)], limit = 1)
            journal_id = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.company.id)
        ], limit=1)
        currency = self.env['res.currency'].search([('name','ilike',self.sat_moneda), ('active','=',True)])
        metodo_pago = self.env['l10n_mx_edi.payment.method'].search([('code', '=', self.sat_metodo_pago)])
        if not partner_id.id:
            raise UserError("No existe el partner para generar la factura")
        if not currency.id:
            raise UserError("La moneda esta inactiva o no existe en la base de datos")
        products = self.CreateMoveLines()
        move_id = self.env['account.move'].create({
            'move_type' : move_type,
            'partner_id' : partner_id.id,
            'journal_id' : journal_id.id,
            'invoice_date' : date,
            'date' : date,
            'currency_id' : currency.id,
            'invoice_line_ids' : products,
            'l10n_mx_edi_payment_method_id' : metodo_pago.id,
            'l10n_mx_edi_usage' : self.sat_cfdi_usage,
        })
        self.AddAttachment(move_id)
        self.write({
            'account_move_id' : move_id.id
        })

    
    def AddAttachment(self, move_id):
        zipBytes = self.zip_downloaded.attachment_id.raw
        z = zipfile.ZipFile(io.BytesIO(zipBytes))
        xml = z.read(self.document_name)
        attachment = self.env['ir.attachment'].create({
            'name': self.document_name,
            'raw': xml,
            'description': 'XML signed from Invoice %s.' % move_id.name,
            'res_model': 'account.move',
            'res_id': move_id.id,
        })
        self.env['account.edi.document'].create({
            'move_id': move_id.id,
            'edi_format_id': self.env.ref('l10n_mx_edi.edi_cfdi_3_3').id,
            'attachment_id': attachment.id,
            'state': 'sent',
        })



    def CreateMoveLines(self):
        account_id = self.env['account.account'].search([
            ('deprecated', '=', False), 
            ('user_type_id.type', 'ilike', 'income'), 
            ('company_id', '=', self.company.id), 
            ('is_off_balance', '=', False),
            ], limit=1)
        values = []
        for product in self.id_details_products:
            product_obj = self.env['product.product']
            tax_obj = self.env['account.tax']

            product_obj = product_obj.search([('default_code', '=', product.id_product)], limit=1)
            if not product_obj :
                product_obj = product_obj.search([('name', '=', product.name_product)], limit=1)
            if product_obj:
                tax_obj = product_obj.taxes_id if self.emitida else product_obj.supplier_taxes_id
            else:
                for tax in product.taxes.split("\n"):
                    if tax == "":
                        continue
                    imp = tax.split(" ")
                    tax_obj += tax_obj.search([
                        ('name', 'ilike', imp[0]),
                        ('amount', '=', float(imp[1])),
                        ('type_tax_use', '=', 'sale' if self.emitida else 'purchase')
                    ])
            values.append({
                'product_id' : product_obj.id,
                'name' : product.name_product,
                'account_id' : account_id.id,
                'quantity' : float(product.quantity),
                'price_unit' : float(product.value_unitary),
                'discount' : float(product.discount) / float(product.value_unitary),
                'tax_ids' : tax_obj.ids
            })
        return values

    def _getMoveType(self):
        if self.emitida:
            if self.sat_tipo_factura == "I":
                return "out_invoice"
            elif self.sat_tipo_factura == "E":
                return "out_refund"
            elif self.sat_tipo_factura == "P":
                return "entry"
        else:
            if self.sat_tipo_factura == "I":
                return "in_invoice"
            elif self.sat_tipo_factura == "E":
                return "in_refund"
            elif self.sat_tipo_factura == "P":
                return "entry"

class FacturasSatDetails(models.Model):
    _name = "details.facturasat"
    _description = "Detalles Facturas SAT"
   

   #Producto aka concepto
    code_service_product = fields.Char(string="Clave Producto")
    id_product = fields.Char(string="Ideentificador Producto")
    quantity = fields.Char(string="Cantidad")
    unit = fields.Char(string="UdM")
    name_product = fields.Char(string="Descripcion", readonly=True,  required=True)
    value_unitary = fields.Char(string="Precio Unitario") 
    amount = fields.Char(string="Importe")
    discount = fields.Char(string="Descuento")
    objeto_impuesto = fields.Char(string="Objeto de impuesto")
    


    #Impuestos
    taxes = fields.Char(string="Impuesto")


    #conexion a factura
    factura_id = fields.Many2one('facturas.sat')


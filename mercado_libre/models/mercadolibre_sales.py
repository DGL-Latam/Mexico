from odoo import models, fields, api

import logging
import json 
import requests
import datetime


_logger = logging.getLogger(__name__)


class MercadolibreSaleLine(models.Model):
    _name = "mercadolibre.sale.line"
    
    ml_order_id = fields.Many2one('mercadolibre.sales', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
    name = fields.Text(string='Descripcion', required=True)
    price = fields.Float('Precio Unitario', required=True, digits='Product Price', default=0.0)
    
    
    product_id = fields.Many2one(
        'product.product', string='Product', domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        change_default=True, ondelete='restrict', check_company=True)  # Unrequired company
    
    product_template_id = fields.Many2one(
        'product.template', string='Product Template',
        related="product_id.product_tmpl_id", domain=[('sale_ok', '=', True)])
    

    product_uom_qty = fields.Float(string='Cantidad', digits='Product Unit of Measure', required=True, default=1.0)

class MercadoLibreSales(models.Model):
    _name = "mercadolibre.sales"
    
    #Identificadores para hacer peticiones a mercado libre
    ml_order_id = fields.Char(string="identificador orden mercado libre", help="id de la orden de compra", required=True)
    ml_shipping_id = fields.Char(string="Identificador del envio mercado libre", help="id de la orden de envio")
    
    ml_is_order_full = fields.Boolean(default=False, help="¿Esta orden es un pedido Full?")
    
    #Datos trasladdos orden de venta Odoo
    tracking_reference = fields.Char(string="Guia de envio", help="Numero de guia del envio")
    sale_order_id = fields.Many2one('sale.order',string="Orden de venta", help="Orden de venta Generada en Odoo")
    ml_pack_id = fields.Char(string="ID del paquete", help="Este ID es el que se usa como nombre en la orden de venta", index=True)
    company_id =  fields.Many2one('res.company', string="Empresa", help="Empresa en donde se va a realizar la orden de venta", required=True)
    client_name = fields.Char(string="Nombre cliente", help="Nombre del individuo que realizo la compra en ML")

    printed = fields.Boolean(default=False, help="¿La guia de esta orden ha sido impresa anteriormente?")
    
    name = fields.Char(string="Orden", compute="_ComputeName")
    
    order_line = fields.One2many('mercadolibre.sale.line', 'ml_order_id', string='Order Lines', auto_join=True)
    productsQuantity = fields.Float(string="Cantidad de productos", compute="_ComputeQtyProducts")
    total = fields.Float(string="Total", compute="_ComputeTotalOrder")

    
    status = fields.Selection([
        ('to_create' , 'Crear OV'),
        ('ready_to_ship' , 'Listo para enviar'),
        ('shipped', 'Enviado'),
        ('delivered', 'Entregado'),
        ('not_delivered', 'No entregado')
        ('cancelled' , 'Cancelada'),
        ('fraud' , 'Cancelado por riesgo de Fraude'),
    ], default="to_create")
    
    
    _sql_constraints = [
        ('ml_order_id_unique',
        'unique(ml_order_id)', 'No se deben repetir order ID para evitar duplicidad'),
        ('ml_pack_id_unique', 
        'unique(ml_pack_id)', 'No Repetir pack id, para evitar duplicidad en vista ML'),
    ]

    def _ComputeTotalOrder(self):
        for rec in self:
            amount = 0
            for line in rec.order_line:
                amount += line.price
            rec.total = amount
    
    def _ComputeQtyProducts(self):
        for rec in self:
            qty = 0
            for line in rec.order_line:
                qty += line.product_uom_qty
            rec.productsQuantity = qty
    #TODO
    def _ProcessOrderLines(self):
        _logger.critical('')

    def _print_info(self):
       _logger.critical( '{},{},{},{}, Full: {}'.format(self.ml_order_id, self.ml_shipping_id, self.sale_order_id.id, self.tracking_reference, self.ml_is_order_full) ) 

    def _writeDataOrderDetail(self, order_details):
        if not self.ml_shipping_id:
            self.write({'ml_shipping_id' : order_details['shipping']['id']})
        if not self.client_name:
            self.write( { 'client_name' :  order_details['buyer']['first_name'] + ' ' + order_details['buyer']['last_name'] })
        if not self.ml_pack_id : 
            self.write( {'ml_pack_id' : order_details['pack_id'] if order_details['pack_id'] else self.ml_order_id } )

    def check_order(self):
        order_details = self._getOrderDetails()
        if 'error' in order_details:
            return 

        if self.env['mercadolibre.sales'].sudo().with_user(1).search([('ml_pack_id','=',order_details['pack_id']),('company_id','=', self.company_id)]):
            return

        self._writeDataOrderDetail(order_details)

        if 'fraud_risk_detected' in order_details['tags']:
            self.cancel_order(fraud=True)
            return
        if order_details['status'] in ['cancelled']:
            self.cancel_order()
            return
        
        shipping_details = self._getShippingDetails()
       
            
        if len(shipping_details['substatus_history']) == 0:
            return 

        self.write({'ml_is_order_full' : shipping_details['logistic_type'] == 'fulfillment'})    
        self._ProcessOrderLines()
        if self.ml_is_order_full:
            return
        

        #si en subestados existe ready to print entonces obtener la guia y generar el pedido :3
        #2022-08-03T22:51:33.675-04:00
        last_shipping = max(shipping_details['substatus_history'], key = lambda substatus :  datetime.datetime.strptime(substatus['date'], "%Y-%m-%dT%H:%M:%S.%f%z") )
        
        if last_shipping['substatus'] in ['ready_to_print','regenerating']:
            if not self.sale_order_id:
                client_name = order_details['buyer']['first_name'] + ' ' + order_details['buyer']['last_name']
                self.write({
                    'ml_pack_id' : order_details['pack_id'] if order_details['pack_id'] else self.ml_order_id,
                    'tracking_reference' : shipping_details['tracking_number'],
                    'client_name' : client_name
                })
                so = self.create_so()
                if not so.id:
                    return {
                        'success' : True,
                        'status' : 'orden no generada',
                        'code' : 200
                    }
                self.create_so_lines(self.sale_order_id,order_details,shipping_details)

        return {
            'success': True,
            'status': 'Datos guardados',
            'code': 200
        }


    def _GetShippingID(self):
        order_details = self._getOrderDetails()
        self.write({'ml_shipping_id' : order_details['shipping']['id']})
        
    #Peticiones API
    #=======================================================================

    def _getData(self, url):
        headers = { "Authorization" : "Bearer " + self.company_id.ml_access_token }
        res = requests.get(url,headers=headers)
        return json.loads(res.text)
   
    #Get the json of the order info whenever an event has ocurred, 
    def _getOrderDetails(self):
        url = "https://api.mercadolibre.com/orders/{order_id}".format( order_id = self.ml_order_id)
        return self._getData(url)

    #We recover the sipment details with an ID
    def _getShippingDetails(self):
        url = "https://api.mercadolibre.com/shipments/{}".format(self.shipping_id)
        return self._getData(url)

    def _getShipmentItems(self):
        url = "https://api.mercadolibre.com/shipments/{}/items".format(self.shipping_id)
        return self._getData(url)

    def _getItemDetails(self, product_id):
        url = "https://api.mercadolibre.com/items/{}/variations?include_attributes=all".format(product_id)
        return self._getData(url)

    #We recover the shipment_label as a pdf file (to attach to a sale order)
    def get_shipment_label(self):
        url = "https://api.mercadolibre.com/shipment_labels?shipment_ids={}&response_type=pdf".format(self.shipment_id)
        return self._getData(url)
    #==================================================================================
    #    

    # Creation of sale order,
    # first we create the order (so that we have an order id when we add the sale order lines), with all the data recovered from the ML notification
    # then for each item request by ML we create the sale order line,
    # if one product cannot be found via internal reference, it shall be added as a note to the sale order, if this occurs
    # the sale order will not be automatically published
    def create_so(self):
        sale_order = self.env['sale.order'].sudo().with_user(1).search([('name','=',self.ml_pack_id),('company_id','=',self.company_id.id)])
        if sale_order.id:
            self.write({'sale_order_id' : sale_order.id })
            return sale_order
        if not sale_order.id:
            prev_order = self.env['mercadolibre.sales'].search( [('ml_pack_id', '=',self.ml_pack_id ), ('ml_order_id', '!=', self.ml_order_id), ('create_date','<', self.create_date) ] )
            if prev_order.id:
                sale_order = prev_order.sale_order_id
                return sale_order
        if sale_order.id:
            self.write({'sale_order_id' : sale_order.id })
            return sale_order
        values = {
            'origin' : 'MP-ML',
            'team_id' : self.env['crm.team'].sudo().search([('name','=', 'MP-ML'),('company_id','=',self.company_id.id)]).id,
            'company_id' : self.company_id.id,
            'client_order_ref' : self.client_name,
            'partner_id' : self.env['res.partner'].sudo().search([('name','=','VENTAS PUBLICO GENERAL (ML)')]).id,
            'journal_id' : self.env['account.journal'].sudo().search([('name','=','MKP MERCADO LIBRE'), ('company_id','=',self.company_id.id)]).id,
            'name' : self.ml_pack_id,
            'user_id' : 1,
            'carrier_tracking_ref' : self.tracking_reference,
        }
        sale_order = self.env['sale.order'].sudo().with_user(1).create(values)    
        self.write({'sale_order_id' : sale_order.id })
        return sale_order
    
    # Cancelar orden de venta
    def cancel_order(self, fraud = False):
        if self.sale_order_id:
            self.sale_order_id._action_cancel()
            for delivery in self.sale_order_id.picking_ids:
                if delivery.state == 'done':
                    self.cancelation_email()
                    break
        if fraud:
            self.write({'status' : 'fraud'})
        else : 
            self.write({'status' : 'cancelled'})

    #Send the actual email
    def cancelation_email(self):
        email_to = self.company_id.ml_responsible_deliveries
        mail_values = {
            'auto_delete': True,
            'email_to': email_to,
            'body_html': "No entregar productos orden de venta " + self.sale_order_id.name + ' numero de rastreo ' + self.sale_order_id.carrier_tracking_ref ,
            'state': 'outgoing',
            'subject': "No entregar productos orden de venta " + self.sale_order_id.name + ' numero de rastreo ' + self.sale_order_id.carrier_tracking_ref ,
        }
        mail = self.env['mail.mail'].sudo().with_user(1).create(mail_values)
        mail.send([mail.id])

    #Send email product not found
    def not_found_email(self, message):
        email_to = self.company_id.ml_responsible_products
        mail_values = {
            'auto_delete': True,
            'email_to': email_to,
            'body_html': "Productos no encontrados en Odoo: \n" + message + ' revisar la orden ' + self.sale_order_id.name ,
            'state': 'outgoing',
            'subject': "Productos no encontrados en Odoo," + ' revisar la orden ' + self.sale_order_id.name,
        }
        mail = self.env['mail.mail'].sudo().with_user(1).create(mail_values)
        mail.send([mail.id])

    def create_so_lines(self,sale_order,order_details,shipping_details):
        if sale_order.amount_total == shipping_details['order_cost']:
            return sale_order
        so_lines_values = []
        error = False
        message = ''
        mail_body = ''
        for order_item in order_details['order_items']:
            mail_body = 'sku registrado '+ order_item['item']['seller_sku'] + ' ' + order_item['item']['title'] + ' precio unitario sin IVA '  + str( order_item['unit_price'] / 1.16 ) + ' cantidad ' + str(order_item['quantity']) + '\n'
            message += 'sku registrado '+ order_item['item']['seller_sku'] + ' ' + order_item['item']['title'] + ' precio unitario sin IVA '  + str( order_item['unit_price'] / 1.16 ) + ' cantidad ' + str(order_item['quantity']) + '\n'
            product_id = self.env['product.product'].sudo().search([('default_code','=',order_item['item']['seller_sku'].replace('-',''))])
            if product_id.id:
                so_lines_values.append({
                    'name' : product_id.description_sale if product_id.description_sale else '[{}] {}'.format(product_id.default_code, product_id.name),
                    'product_id' : product_id.id,
                    'product_uom' : product_id.uom_id.id,
                    'product_uom_qty' : order_item['quantity'],
                    'price_unit' : order_item['unit_price'] / 1.16,
                    'order_id' : sale_order.id,
                    'display_type' : False,
                })
            else:
                error = True
                so_lines_values.append({
                    'name' : mail_body ,
                    'order_id' : sale_order.id,
                    'display_type' : 'line_note',
                })
            
        sale_order.sudo().with_user(1).message_post(body = message)
        self.env['sale.order.line'].sudo().with_user(1).create(so_lines_values)
        
        if not error:
            sale_order.sudo().with_user(1).action_confirm()
            sale_order.picking_ids[0].sudo().with_user(1).message_post(body = message)
        
        if error:
            self.not_found_email(message)
        label_data = self.get_shipment_label(order_details['shipping']['id'],self.company_id)
        attach = self.env['ir.attachment'].sudo().search([('res_id','=',sale_order.id),('res_model','=','sale.order')])
        if attach.id:
            attach.write({'raw' : label_data})
        else:
            self.env['ir.attachment'].sudo().create({
                'name' : 'Guia ' + self.tracking_reference + '.pdf',
                'type' : 'binary',
                'raw' : label_data,
                'res_model' : 'sale.order',
            'res_id' : sale_order.id,
            })
        return sale_order


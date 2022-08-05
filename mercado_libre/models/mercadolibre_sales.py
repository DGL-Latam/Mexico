from odoo import models, fields, api

import logging
import json 
import requests
import datetime

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
    company_id =  fields.Many2one(string="Empresa", help="Empresa en donde se va a realizar la orden de venta", required=True)
    client_name = fields.Char(string="Nombre cliente", help="Nombre del individuo que realizo la compra en ML")

    status = fields.Selection([
        ('crear', 'Crear OV')
        ('venta', 'Venta'),
        ('cancelada', 'Cancelada'),
        ('reclamo', 'Reclamo'),
    ], default="crear")


    def check_order(self):
        order_details = self._getOrderDetails()
        if 'error' in order_details:
            return {
                'success': True,
                'status': 'No order found to be modified/created',
                'code': 500
            }
        if 'fraud_risk_detected' in order_details['tags'] or order_details['status'] in ['cancelled']:
            self.cancel_order()
            return {
                'success': True,
                'status': 'Order cancelled',
                'code': 200
            }
        shipping_details = self._getShippingDetails(order_details['shipping']['id'])
        if not self.ml_shipping_id:
            self.write({'ml_shipping_id' : shipping_details['id']})
        latest_ship_substatus = max(shipping_details['substatus_history'], key = lambda x : datetime.datetime.strptime(x['date'],'%Y-%m-%dT%H:%M:%S.%f%z'))

        if latest_ship_substatus['substatus'] in ['in warehouse']:
            self.write({'ml_is_order_full' : True})
            return {
                'success': True,
                'status': 'marked as full',
                'code': 200
            }
        elif latest_ship_substatus['substatus'] in ['ready_to_print']:
            if not self.sale_order_id:
                client_name = order_details['buyer']['first_name'] + ' ' + order_details['buyer']['last_name']
                self.write({
                    'ml_pack_id' : order_details['pack_id'] if order_details['pack_id'] else self.ml_order_id,
                    'tracking_reference' : shipping_details['tracking_number'],
                    'client_name' : client_name
                })
                self.create_so()
                self.create_so_lines(self.sale_order_id,order_details)

        return {
            'success': True,
            'status': 'Datos guardados',
            'code': 200
        }


    #Peticiones API
    #=======================================================================
   
    #Get the json of the order info whenever an event has ocurred, 
    def _getOrderDetails(self):
        headers = { "Authorization" : "Bearer " + self.company_id.ml_access_token }
        url = "https://api.mercadolibre.com/orders/{order_id}".format( order_id = self.ml_order_id)
        res = requests.get(url,headers=headers)
        return json.loads(res.text)

    #We recover the sipment details with an ID
    def _getShippingDetails(self, shipping_id):
        url = "https://api.mercadolibre.com/shipments/{}".format(shipping_id)
        headers = { "Authorization" : "Bearer " + self.company_id.ml_access_token }
        res = requests.get(url,headers=headers)
        return json.loads(res.text)

    #We recover the shipment_label as a pdf file (to attach to a sale order)
    def get_shipment_label(self,shipment_id, company_id):
        headers = { "Authorization" : "Bearer " + self.company_id.ml_access_token }
        url = "https://api.mercadolibre.com/shipment_labels?shipment_ids={}&response_type=pdf".format(shipment_id)
        res = requests.get(url,headers=headers)
        return res.content
    #==================================================================================
    #    

    # Creation of sale order,
    # first we create the order (so that we have an order id when we add the sale order lines), with all the data recovered from the ML notification
    # then for each item request by ML we create the sale order line,
    # if one product cannot be found via internal reference, it shall be added as a note to the sale order, if this occurs
    # the sale order will not be automatically published
    def create_so(self):
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
    
    # Cancelar orden de venta
    def cancel_order(self):
        if self.sale_order_id:
            self.sale_order_id._action_cancel()
            for delivery in self.sale_order_id.picking_ids:
                if delivery.state == 'done':
                    self.cancelation_email()
                    break
        self.write({'status' : 'cancelada'})

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

    def create_so_lines(self,sale_order,order_details):
        so_lines_values = []
        error = False
        message = ''
        for order_item in order_details['order_items']:
            message += 'sku registrado '+ order_item['item']['seller_sku'] + ' ' + order_item['item']['title'] + ' precio unitario sin IVA '  + str( order_item['unit_price'] / 1.16 ) + ' cantidad ' + str(order_item['quantity']) + '\n'
            product_id = self.env['product.product'].sudo().search([('default_code','=',order_item['item']['seller_sku'])])
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
                    'name' : message ,
                    'order_id' : sale_order.id,
                    'display_type' : 'line_note',
                })
            
        sale_order.sudo().with_user(1).message_post(body = message)
        self.env['sale.order.line'].sudo().with_user(1).create(so_lines_values)
        
        if not error:
            sale_order.sudo().with_user(1).action_confirm()
            sale_order.picking_ids[0].sudo().with_user(1).message_post(body = message)
        
        label_data = self.get_shipment_label(order_details['shipping']['id'],self.company_id)
        self.env['ir.attachment'].sudo().create({
            'name' : 'Guia ' + self.tracking_reference + '.pdf',
            'type' : 'binary',
            'raw' : label_data,
            'res_model' : 'sale.order',
            'res_id' : sale_order.id,
        })
        return sale_order


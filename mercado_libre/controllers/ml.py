from odoo.http import Controller, route, request, Response
import json 
import requests
import datetime

import logging
_logger = logging.getLogger(__name__)


class MercadoLibre(Controller):
    @route('/ML/so', type='json', auth='public', methods=['POST'], csrf=False)
    def handleOrdersNotif(self):
        
        data = request.jsonrequest
        if(data['topic'] != 'orders_v2'):
            return {
                    'success': True,
                    'status': 'No order to be modified/created',
                    'code': 200
                }

        ml_order_id = data['resource'].split('/')[2]
        company_id = self.get_company_to_use(data['user_id'])
        order_id = self.get_order(ml_order_id,company_id)
        
        
        order_details = self._getOrderDetails(ml_order_id, company_id)
        if 'error' in order_details:
            return {
                    'success': True,
                    'status': 'No order found to be modified/created',
                    'code': 200
                }
        
        order_status = order_details['status']
        order_tags = order_details['tags']
        
        if 'fraud_risk_detected' in order_tags or order_status in ['cancelled','pending_cancel']:
            self.cancel_order(order_id)
            return {
                    'success': True,
                    'status': 'Order cancelled',
                    'code': 200
                }
        if order_id:
            return {
                    'success': True,
                    'status': 'Order already created',
                    'code': 200
                }
        shipping_details = self._getShippingDetails(order_details['shipping']['id'] , company_id)
        if len(shipping_details['substatus_history']) == 0:
            return{
                'success': True,
                'status': 'OK',
                'code': 200
            }
        latest_ship_substatus = max(shipping_details['substatus_history'], key = lambda x : datetime.datetime.strptime(x['date'],'%Y-%m-%dT%H:%M:%S.%f%z'))
        created_so = None
        if (latest_ship_substatus['substatus'] in ['ready_to_print','shipment_paid'] and not order_id.id):
            sale = self.create_so(order_details,shipping_details, company_id)
            if len(sale.order_line) == 0:
                self.create_so_lines(sale,order_details)

        return {
                    'success': True,
                    'status': 'OK',
                    'code': 200
                }
    
    #check wheter a record has been created for this order (tracking purposes)
    def check_ml_table(self, ml_order_id):
        return request.env['mercadolibre.sale'].sudo().with_user(1).search([('ml_order_id','=',ml_order_id)])
    
    #check wheter an email should be sent to the warehouse responsible and seller, 
    #about not delivering the product to the mailers from SO wich already has delivery done
    def check_cancel_mail(self,order_id):
        for delivery in order_id.picking_ids:
            if delivery.state == 'done':
                self.cancelation_email( order_id.company_id )
                break
        
        
    #Send the actual email
    def cancelation_email(self, order_id):
        email_to = order_id.company_id.ml_responsible_deliveries
        mail_values = {
            'auto_delete': True,
            'email_to': email_to,
            'body_html': "No entregar productos orden de venta " + order_id.name + ' numero de rastreo ' + order_id.carrier_tracking_ref ,
            'state': 'outgoing',
            'subject': "No entregar productos orden de venta " + order_id.name + ' numero de rastreo ' + order_id.carrier_tracking_ref ,
        }
        mail = request.env['mail.mail'].sudo().with_user(1).create(mail_values)
        mail.send([mail.id])
    
    #to cancel the sale order in case ML told us is needed
    def cancel_order(self,order_id):
        if order_id:
            order_id.sudo().with_user(1)._action_cancel()
            self.check_cancel_mail(order_id)
    
    
    # Creation of sale order,
    # first we create the order (so that we have an order id when we add the sale order lines), with all the data recovered from the ML notification
    # then for each item request by ML we create the sale order line,
    # if one product cannot be found via internal reference, it shall be added as a note to the sale order, if this occurs
    # the sale order will not be automatically published
    def create_so(self, order_details, shipping_details, company_id):
        values = {
            'origin' : 'MP-ML',
            'team_id' : request.env['crm.team'].sudo().search([('name','=', 'MP-ML'),('company_id','=',company_id.id)]).id,
            'company_id' : company_id.id,
            'client_order_ref' : order_details['buyer']['first_name'] + ' ' + order_details['buyer']['last_name'],
            'carrier_tracking_ref' : shipping_details['tracking_number'],
            'partner_id' : request.env['res.partner'].sudo().search([('name','=','VENTAS PUBLICO GENERAL (ML)')]).id,
            'journal_id' : request.env['account.journal'].sudo().search([('name','=','MKP MERCADO LIBRE'), ('company_id','=',company_id.id)]).id,
            'name' : order_details['id'],
            'user_id' : 1,
        }
        sale_order = self.get_order(order_details['id'],company_id)
        if not sale_order.id:
            sale_order = request.env['sale.order'].sudo().with_user(1).create(values)    
        return sale_order
        
    def create_so_lines(self,sale_order,order_details):
        so_lines_values = []
        error = False
        message = ''
        for order_item in order_details['order_items']:
            message += 'sku registrado '+ order_item['item']['seller_sku'] + ' ' + order_item['item']['title'] + ' precio unitario sin IVA '  + str( order_item['unit_price'] / 1.16 ) + ' cantidad ' + str(order_item['quantity']) + '\n'
            _logger.critical(order_item['item']['seller_sku'])
            product_id = request.env['product.product'].sudo().search([('default_code','=',order_item['item']['seller_sku'])])
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
        request.env['sale.order.line'].sudo().with_user(1).create(so_lines_values)
        
        if not error:
            sale_order.sudo().with_user(1).action_confirm()
            sale_order.picking_ids[0].sudo().with_user(1).message_post(body = message)
        
        label_data = self.get_shipment_label(order_details['shipping']['id'],company_id)
        request.env['ir.attachment'].sudo().create({
            'name' : 'Guia ' + shipping_details['tracking_number'] + '.pdf',
            'type' : 'binary',
            'raw' : label_data,
            'res_model' : 'sale.order',
            'res_id' : sale_order.id,
        })
        return sale_order
    
    # we recover the SO if it exists on the company selected
    def get_order(self, order_id, company_id):
        return request.env['sale.order'].sudo().search([('name','=',str(order_id)),('company_id','=',company_id.id)])
    
    #We recover the sipment details with an ID
    def _getShippingDetails(self, shipping_id, company_id):
        url = "https://api.mercadolibre.com/shipments/{}".format(shipping_id)
        auth = "Bearer "
        auth += company_id.ml_access_token
        headers = {
            "Authorization" : auth,
        }
        res = requests.get(url,headers=headers)
        return json.loads(res.text)
        
    #we look for the client details, in order to get things like name
    def _getClientDetails(self,client_id, company_id):
        auth = "Bearer "
        auth += company_id.ml_access_token
        headers = {
            "Authorization" : auth,
        }
        url = "https://api.mercadolibre.com/users/{}".format(client_id)
        res = requests.get(url,headers=headers)
        return json.loads(res.text)
    
    #Get the json of the order info whenever an event has ocurred, 
    def _getOrderDetails(self, order_id, company_id):
        auth = "Bearer "
        auth += company_id.ml_access_token
        headers = {
            "Authorization" : auth,
        }
        url = "https://api.mercadolibre.com/orders/{order_id}".format( order_id = order_id)
        res = requests.get(url,headers=headers)
        return json.loads(res.text)
    
    
    # we recover the seller access tokens
    def get_company_to_use(self,seller_id):
        company_id = request.env['res.company'].sudo().search([('ml_seller_id','=',str(seller_id))])
        return company_id
    
    #We recover the shipment_label as a pdf file (to attach to a sale order)
    def get_shipment_label(self,shipment_id, company_id):
        auth = "Bearer "
        auth += company_id.ml_access_token
        headers = {
            "Authorization" : auth,
        }
        url = "https://api.mercadolibre.com/shipment_labels?shipment_ids={}&response_type=pdf".format(shipment_id)
        res = requests.get(url,headers=headers)
        return res.content
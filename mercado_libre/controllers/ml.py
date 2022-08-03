from odoo.http import Controller, route, request, Response
import json 
import requests

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
        _logger.info(data)
        ml_order_id = data['resource'].split('/')[2]
        company_id = self.get_company_to_use(data['user_id'])
        
        
        order_json = self._getOrderDetails(ml_order_id, company_id)
        
        if len(order_json['results']) == 0:
            return {
                    'success': True,
                    'status': 'No order found to be modified/created',
                    'code': 200
                }
        order_details = order_json['results'][0]
        order_status = order_details['status']
        
        _logger.info(order_status)
        
        
        
        _logger.info(request.jsonrequest)
        _logger.info(data['resource'].split('/')[2])
        return {
                    'success': True,
                    'status': 'OK',
                    'code': 200
                }
    
    def _getClientDetails(self,client_id, company_id):
        auth = "Bearer "
        auth += company_id.ml_access_token
        headers = {
            "Content-Type" : "application/json",
            "Authorization" : auth,
            "Accept" : "application/json"
        }
        url = "https://api.mercadolibre.com/users/{}".format(client_id)
    
    #Get the json of the order info whenever an event has ocurred, 
    def _getOrderDetails(self, order_id, company_id):
        auth = "Bearer "
        auth += company_id.ml_access_token
        seller_id = company_id.ml_seller_id
        headers = {
            "Content-Type" : "application/json",
            "Authorization" : auth,
            "Accept" : "application/json"
        }
        url = "https://api.mercadolibre.com/orders/search?seller={seller_id}&q={order_id}".format(seller_id = seller_id, order_id = order_id)
        res = requests.get(url,headers=headers)
        return json.loads(res.text)
    
    def get_company_to_use(self,seller_id):
        company_id = request.env['res.company'].sudo().search([('ml_seller_id','=',str(seller_id))])
        return company_id
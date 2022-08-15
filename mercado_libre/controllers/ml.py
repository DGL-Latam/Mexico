from odoo.http import Controller, route, request, Response
import json 
import requests
import datetime

class MercadoLibre(Controller):
    
    @route('/ML/Guias', auth='user', type='http', methods=['GET'])
    def getGuias(self):
        orders =  request.env['mercadolibre.sales'].sudo().search([ ('printed','=', False), ('sale_order_id','!=',False), ('sale_order_id.state', 'not in', ['cancel','draft']), ('company_id', 'in', request.env.user.company_id.ids), ('ml_shipping_id' ,'!=', False) ], limit=40 )

        ships_ids = []
        for order in orders:
            ships_ids.append(order.ml_shipping_id)

        ids_str = ''
        for id in ships_ids:
            ids_str += '{},'.format(id) 
        
        headers = { "Authorization" : "Bearer " + request.env.user.company_id.ml_access_token }

        url = "https://api.mercadolibre.com/shipment_labels?shipment_ids={}&response_type=pdf".format(ids_str)
        res = requests.get(url,headers=headers)
        
        pdf_http_headers = [('Content-Type', 'application/pdf'), ('Content-Length', len(res.content))]

        for order in orders:
            order.sudo().write({'printed' : True})

        return request.make_response(res.content, headers=pdf_http_headers)
    
    
    
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
        mls = self.check_ml_table(ml_order_id,company_id.id)
        mls.sudo().with_user(1).check_order()
        return {
            'success': True,
            'status': 'Registro creada',
            'code': 200
        }
        #could delete from here onwards
        
    #check wheter a record has been created for this order (tracking purposes) if not create it
    def check_ml_table(self, ml_order_id, company_id):
        mls = request.env['mercadolibre.sales'].sudo().with_user(1).search([('ml_order_id','=',ml_order_id),('company_id','=', company_id)])
        if not mls.id:
            mls = request.env['mercadolibre.sales'].sudo().with_user(1).create({'ml_order_id' : ml_order_id,'company_id' : company_id})
        return mls
           
    # we recover the seller access tokens
    def get_company_to_use(self,seller_id):
        company_id = request.env['res.company'].sudo().search([('ml_seller_id','=',str(seller_id))])
        return company_id
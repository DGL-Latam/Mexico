# -*- coding: utf-8 -*-

import base64
import logging
import json 
import requests

from lxml import etree, objectify
from werkzeug.urls import url_quote
from os.path import join

from odoo import api, fields, models, tools, SUPERUSER_ID, http
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    ml_seller_id = fields.Char(string="ID del vendedor", help="Valor numerico que pertenece al vendedor en la base de datos de mercado libre")
    ml_app_id = fields.Char(string="Mercado libre app id", help="App id, se puede checar en la configuracion de la app en la pagina de developers de ML")
    ml_app_secret = fields.Char(string="Mercado libre app secret", help="Secret key, se puede checar en la configuracion de la app en la pagina de developers de ML")
    ml_access_token = fields.Char(string="Access Token ML", help="Token para poder acceder a los servicios del api")
    ml_refresh_token = fields.Char(string="Token", help="Token para refrescar nuestro token de auth",)
    ml_responsible_deliveries = fields.Char(
        string="Email responsables Entrega ML", 
        help="Lista de correos electronicos al que se les notificara de no entregar la mercancia, que fue marcada como hecha en odoo, a paqueteria si el pedido fue cancelado (delivered)"
    )
    ml_responsible_products = fields.Char(string="Email responsables Productos ML", 
        help="Lista de correos electronicos al que se les notificara de no entregar la mercancia, que fue marcada como hecha en odoo, a paqueteria si el pedido fue cancelado (product)"
    )
    
    def renew_access_token(self):

        url = "https://api.mercadolibre.com/oauth/token"
        headers = {
            "Accept" : "application/json",
            "Content-Type" : "application/x-www-form-urlencoded"
        }
        data = {
            'grant_type' : 'refresh_token',
            'client_id' : self.ml_app_id,
            'client_secret' : self.ml_app_secret,
            'refresh_token' : self.ml_refresh_token,
        }
        res = requests.post(url = url, data = data, headers = headers)

        data =  json.loads(res.text)
        if 'status' in data:
            raise UserError(data['message'] + '\n' + data['error'])
        values = {
            'ml_access_token' : data['access_token'],
            'ml_refresh_token' : data['refresh_token'],
        }
        self.sudo().write(values)
        return True
            
        
        
    def get_first_access_code(self):
        self.ensure_one()

        url = "https://api.mercadolibre.com/oauth/token"
        redirect_url = http.request.env['ir.config_parameter'].get_param('web.base.url') + "/ML/so"
        data = {
            'grant_type' : 'authorization_code',
            'client_id' : self.ml_app_id,
            'client_secret' : self.ml_app_secret,
            'code' : self.ml_access_token,
            'redirect_uri' : redirect_url,
        }

        headers = {
            'Accept' : 'application/json',
            "Content-Type" : "application/x-www-form-urlencoded",
        }
        res = requests.post(url = url, data = data, headers = headers)

        data =  json.loads(res.text)
        if 'status' in data:
            raise UserError(data['message'] + '\n' + data['error'])
        values = {
            'ml_seller_id' : data['user_id'],
            'ml_access_token' : data['access_token'],
            'ml_refresh_token' : data['refresh_token'],
        }
        self.sudo().write(values)
        return True
    

    def GetReadyToPrintOrders(self):
        url = "https://api.mercadolibre.com/orders/search"
        params = {
            'seller' :  self.ml_seller_id,
            'order.status' : 'paid',
            'sort' : 'date_desc',
            'tags' : 'not_delivered',
            'shipping.substatus' : 'ready_to_print',
        }
        headers = { "Authorization" : "Bearer " + self.ml_access_token }
        res = requests.get(url,headers=headers , params=params)
        if res.status_code != 200:
            return
        data = json.loads(res.text)
        if not data['results']:
            return
        for sale in data['results']:
            self.check_ml_table(sale['id'])

    #check wheter a record has been created for this order (tracking purposes) if not create it
    def check_ml_table(self, ml_order_id):
        mls = self.env['mercadolibre.sales'].sudo().with_user(1).search([('ml_order_id','=',ml_order_id),('company_id','=', self.id)])
        if not mls.id:
            mls = self.env['mercadolibre.sales'].sudo().with_user(1).create({'ml_order_id' : ml_order_id,'company_id' : self.id})
        return mls

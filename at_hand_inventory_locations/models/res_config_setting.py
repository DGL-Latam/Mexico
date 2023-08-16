from odoo import api, models, fields, http
from odoo.exceptions import UserError



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    #este campo solo es para que se puedan colocar los datos desde la ventana de ajustes 
    at_hand_stock_locations = fields.Many2many('stock.location', related="company_id.at_hand_stock_locations", readonly=False)
    
import logging 

from odoo import api, fields, models, tools, SUPERUSER_ID, http
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    at_hand_stock_locations = fields.Many2many('stock.location')
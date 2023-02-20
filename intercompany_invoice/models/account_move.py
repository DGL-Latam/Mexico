from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

class ResCompany(models.Model):
    _inherit = "res.company"

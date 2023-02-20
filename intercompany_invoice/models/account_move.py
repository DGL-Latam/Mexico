from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

class ResCompany(models.Model):
    _inherit = "res.company"

    rule_type= fields.Selection(selection_add=[("sale_purchase_invoice_refund", "Synchronize Sales/Purchase Order and Invoices/Bills")])
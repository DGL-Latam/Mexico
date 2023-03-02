from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)
new_rule_type = [("sale_purchase_invoice_refund", "Sincronizar órdenes de venta/compra y facturas/recibos")]


class ResCompany(models.Model):
    _inherit = "res.company"


    rule_type = fields.Selection(selection_add=new_rule_type, string="Rule", default="not_synchronize")


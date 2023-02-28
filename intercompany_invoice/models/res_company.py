from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = "res.company"

    new_rule_type = [("sale_purchase_invoice_refund", "Sincronizar órdenes de venta/compra y facturas/recibos")]


    rule_type = fields.Selection(selection_add=new_rule_type, string="Rule", default="not_synchronize")

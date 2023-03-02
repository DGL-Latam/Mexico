from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)
new_rule_type = {"sale_purchase_invoice_refund", "Sincronizar órdenes de venta/compra y facturas/recibos"}


class ResCompany(models.Model):
    _inherit = "res.company"


    rule_type = fields.Selection(selection_add=list(new_rule_type.items()), string="Rule", default="not_synchronize")

    @api.onchange("rule_type")
    def onchange_rule_type(self):
        if self.rule_type not in new_rule_type.keys():
            super().onchange_rule_type()
        else:
            warehouse_id = self.warehouse_id or self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1)
            self.warehouse_id = warehouse_id

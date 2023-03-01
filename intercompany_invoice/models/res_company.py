from odoo import models, fields, api, _

class ResCompany(models.Model):
    _inherit = "res.company"

    new_rule_type = [("sale_purchase_invoice_refund", "Sincronizar órdenes de venta/compra y facturas/recibos")]

    rule_type = fields.Selection(selection_add=new_rule_type, string="Rule", default="not_synchronize")

    auto_validation = fields.Boolean()
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")

    @api.model
    def _find_company_from_partner(self, partner_id):
        company = self.sudo().search([("partner_id", "=", partner_id)], limit=1)
        return company or False

    @api.onchange('rule_type')
    def onchange_rule_type(self):
        if self.rule_type not in [("sale_purchase_invoice_refund", "Sincronizar órdenes de venta/compra y facturas/recibos")].keys():
            self.auto_validation = False
            self.warehouse_id = False
        else:
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self._origin.id)], limit=1)
            self.warehouse_id = warehouse_id
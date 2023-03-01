from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    rule_type = fields.Selection(related="company_id.rule_type", readonly=False)
    intercompany_user_id = fields.Many2one(related='company_id.intercompany_user_id', readonly=False, required=True)
    rules_company_id = fields.Many2one(related='company_id', string='Select Company', readonly=True)

    auto_validation = fields.Boolean(related="company_id.auto_validation", readonly=False)
    warehouse_id = fields.Many2one(related = "company_id.warehouse_id", readonly = False, domain = lambda self: [("company_id", "=", self.env.company.id)])

    @api.onchange('rule_type')
    def onchange_rule_type(self):
        if self.rule_type not in [("sale_purchase_invoice_refund", "Sincronizar órdenes de venta/compra y facturas/recibos")].keys():
            self.auto_validation = False
            self.warehouse_id = False
        else:
            warehouse_id = self.warehouse_id or self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1)
            self.warehouse_id = warehouse_id

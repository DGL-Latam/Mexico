from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    rule_type = fields.Selection(related="company_id.rule_type", readonly=False)
    intercompany_user_id = fields.Many2one(related='company_id.intercompany_user_id', readonly=False, required=True)
    rules_company_id = fields.Many2one(related='company_id', string='Select Company', readonly=True)

    warehouse_id = fields.Many2one(
        related='company_id.warehouse_id',
        string='Warehouse For Purchase Orders',
        readonly=False,
        domain=lambda self: [('company_id', '=', self.env.company.id)])

    auto_validation = fields.Boolean(related='company_id.auto_validation', readonly=False)
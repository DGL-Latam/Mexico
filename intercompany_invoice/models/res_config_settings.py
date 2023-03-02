from odoo import models, fields, api
from .res_company import new_rule_type

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    @api.onchange("rule_type")
    def onchange_rule_type(self):
        if self.rule_type not in new_rule_type.keys():
            super().onchange_rule_type()
        else:
            warehouse_id = self.warehouse_id or self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1)
            self.warehouse_id = warehouse_id
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    rule_type = fields.Selection(related="company_id.rule_type", readonly=False)
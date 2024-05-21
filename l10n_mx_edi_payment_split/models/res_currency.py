from odoo import fields, models
from odoo.addons import decimal_precision as dp


class CurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    rate = fields.Float(digits='Rate Precision')

# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'


    def action_post(self):
        res = super().action_post()
        for invoice in self:

            if invoice.rule_type == 'sale_purchase_invoice_refund':
                invoice.action_post()
        return res

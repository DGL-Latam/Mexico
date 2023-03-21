# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        for rec1 in self:
            invoice_from_sale = rec1.env["sale.order"].invoice_ids
            for rec2 in self:
                invoice_from_purchase = rec2.env["purchase.order"].invoice_ids

                if invoice_from_sale.name == invoice_from_purchase.ref:
                    invoice_from_purchase.action_post()
                return res
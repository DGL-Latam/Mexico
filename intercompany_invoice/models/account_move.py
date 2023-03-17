# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        count = 0
        res = super().action_post()
        bill = self.env["sale.order"].auto_purchase_order_id
        name = self.env["sale.order"].name
        if bill.partner_ref == name:
            if count > 0:
                bill.action_post_bill()
                count += 1

        return res
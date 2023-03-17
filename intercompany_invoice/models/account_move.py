# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        bill = self.env["sale.order"].auto_purchase_order_id
        if bill.move_type == "in_invoice":
            bill.action_post()

        return res
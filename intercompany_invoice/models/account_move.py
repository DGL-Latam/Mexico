# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):

        res = super().action_post()
        bill = self.env["sale.order"].auto_purchase_order_id
        bill_id = self.env["account.move"].browse(id)
        for rec in bill_id:
            if (rec == bill_id) and (rec.ref == self.env["account.move"].name):
                rec.action_post()

        return res
# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):

        res = super().action_post()
        bill = self.env["sale.order"].auto_purchase_order_id
        bill_ids = self.env["purchase.order"].invoice_ids
        invoice_ids = self.env["sale.order"].invoice_ids
        for rec1 in bill_ids:
            for rec2 in invoice_ids:
                if rec1.partner_ref == rec2.name:
                    bill_ids.id.action_post()

        return res
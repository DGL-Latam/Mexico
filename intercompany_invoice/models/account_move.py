# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        invoice = self.env["sale.order"].auto_purchase_order_id
        invoice_ids = invoice.invoice_ids
        invoice_ref = invoice.ref

        bill = self.env["purchase.order"]
        bill_ids = bill.invoice_ids
        bill_ref = bill.ref

        for rec in self:
            temp = rec.search([("ref", "=", bill_ref)])
            if temp.ref == invoice_ref:
                temp.action_post()


        return res
# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        invoice = self.env["sale.order"].auto_purchase_order_id
        invoice_ids = invoice.invoice_ids
        invoice_name = invoice.name

        bill = self.env["purchase.order"]
        bill_ids = bill.invoice_ids
        bill_ref = bill.partner_ref

        for rec in self:
            temp = rec.search([("name", "=", bill_ref)])
            if temp.ref == invoice_name:
                temp.action_post()


        return res
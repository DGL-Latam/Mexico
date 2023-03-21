# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        invoice = self.env["sale.order"]
        invoice_ids = invoice.invoice_ids
        invoice_ref = invoice.client_order_ref

        bill = self.env["sale.order"].auto_purchase_order_id
        bill_ids = bill.invoice_ids
        bill_ref = bill.name

        for rec in self:
            temp = rec.browse(bill_ids)
            for rec_1 in temp:
                if rec_1.ref == invoice_ref:
                    temp.action_post()


        return res
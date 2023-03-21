# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        invoice = self.env["sale.order"]
        invoice_ids = invoice.invoice_ids
        invoice_ref = invoice.client_order_ref
        i_ids = self.env["account.move"].browse(invoice_ids)

        bill = self.env["sale.order"].auto_purchase_order_id
        bill_ids = bill.invoice_ids
        bill_ref = bill.name

        b_ids = self.env["account.move"].browse(bill_ids)

        for rec1 in b_ids:
            for rec2 in i_ids:
                if rec1.ref == rec2.name:
                    rec1.action_post()
        return res
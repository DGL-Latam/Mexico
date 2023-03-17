# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):

        res = super().action_post()
        invoice = self.env["sale.order"]
        invoice_ids = invoice.invoice_ids

        bill = self.env["purchase.order"]
        bill_ids = bill.invoice_ids

        for rec1 in self.browse(invoice.cr, invoice.uid, invoice.ids):
            for rec1_1 in rec1.invoice_ids:
                temp_1 = rec1_1.name

            for rec2 in self.browse(bill.cr, bill.uid, bill.ids):
                for rec2_1 in rec2.bill_ids:
                    temp_2 = rec2_1.partner_ref

                if temp_1 == temp_2:
                    rec2.action_post()
        return res
# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        invoice_from_sale = self.env["sale.order"].invoice_ids
        invoice_from_purchase = self.env["purchase.order"].invoice_ids
        for rec1 in invoice_from_sale:
            number_invoice = rec1.name
            for rec2 in invoice_from_purchase:
                bill_ref = rec2.ref
                if bill_ref == number_invoice:
                    rec2.action_post()
        return res
# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        invoices = self.search([("state", "=", "draft")])
        invoice_from_sale = res.ref
        for rec1 in invoices:
            invoice_bill = self.browse(invoices.rec1)
            if invoice_bill.name == invoice_from_sale:
                rec1.action_post()


        return res
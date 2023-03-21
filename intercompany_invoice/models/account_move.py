# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        name_sale = self.env["sale.order"].name
        name_purchase = self.env["purchase.order"].name

        invoices = self.search(["state", "=", "draft"])

        for rec1 in invoices:
            invoice_id = rec1.browse(invoices.id)
            if invoice_id.ref == name_sale:
                invoice_id.action_post()

        return res
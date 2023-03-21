# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        invoice = self.env["sale.order"]
        invoice_ids = invoice.invoice_ids
        invoice_ref = invoice.client_order_ref

        return res
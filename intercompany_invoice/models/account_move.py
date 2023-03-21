# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        invoice_name = self.env["sale.order"].name
        bill = self.search([("ref", "=", "invoice_name")])
        bill.action_post()



        return res
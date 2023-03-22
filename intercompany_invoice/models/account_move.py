# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        bill = self.env["account.move"].search([("ref", "=", "invoice_name"), ("state", "=", "draft")])
        bill.action_post()



        return res
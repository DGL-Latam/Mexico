# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        invoices_bill = self.env["account.move"]

        for rec1 in invoices_bill:
            rec1.id = self.env["account.move"].search([("state", "=", "draft")])
            rec1.action_post()


        return res
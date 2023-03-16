# -*- coding: utf-8 -*-
from odoo import fields, models, _
from datetime import datetime

#date = fields.Date(default=datetime.today())

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        invoice_id = self.env["account.move"].id
        super().action_post()

        invoice_bill = self.env["account.move"].browse(invoice_id + 1)
        invoice_bill.sudo().action_post()



# -*- coding: utf-8 -*-
from odoo import fields, models, _
from datetime import datetime

#date = fields.Date(default=datetime.today())

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        invoice_id = self.env["account.move"].id
        bill_id = invoice_id + 1
        draft_id = self.env["account.move"].browse(id)
        for rec in draft_id:
            if rec == bill_id:
                rec.action_post()

        return res
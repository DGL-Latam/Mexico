# -*- coding: utf-8 -*-
from odoo import fields, models, _
from datetime import datetime

#date = fields.Date(default=datetime.today())

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        bill_id = self.env["account.move"].id + 1
        for rec in self.id:
            if rec.id == bill_id:
                rec.super.action_post()

        return res


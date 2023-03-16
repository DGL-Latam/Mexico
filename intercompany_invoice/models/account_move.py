# -*- coding: utf-8 -*-
from odoo import fields, models, _
from datetime import datetime

#date = fields.Date(default=datetime.today())

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        res_invoice_id = res.id
        res_bill_id = res_invoice_id + 1
        for rec in self:
            if rec.id == res_bill_id:
                rec.action_post()


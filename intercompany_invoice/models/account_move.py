# -*- coding: utf-8 -*-
from odoo import fields, models, _
from datetime import datetime

#date = fields.Date(default=datetime.today())

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        self.super().action_post()
        return res
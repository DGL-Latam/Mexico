# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        if self.move_type == "out_invoice":
            for rec in self:
                if rec.move_type == "in_invoice":
                    rec.super().action_post()
        return res

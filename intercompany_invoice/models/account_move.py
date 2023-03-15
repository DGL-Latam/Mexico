# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):

        posted = super()._post(soft)
        self.env["purchase.order"].action_create_invoice()
        return posted

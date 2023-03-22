# -*- coding: utf-8 -*-
from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        invoices_posted = self.env["account.move"].search([("state", "=", "posted")])
        bills_draft = self.env["account.move"].search([("state", "=", "draft"), ("ref", "=", invoices_posted.invoice_origin)])
        bills_draft.action_post()


        return res
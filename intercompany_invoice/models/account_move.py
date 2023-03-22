# -*- coding: utf-8 -*-
from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        invoices_posted = self.env["account.move"].search([("state", "=", "posted")])
        bills_draft = self.env["account.move"].search([("state", "=", "draft")])

        for rec1 in bills_draft:
            for rec2 in invoices_posted:
                if rec1.ref == rec2.invoice_origin:
                    rec1.action_post()
                    _logger.info("Mesagge from account move")


        return res
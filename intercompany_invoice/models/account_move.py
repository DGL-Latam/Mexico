# -*- coding: utf-8 -*-
from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        #invoices = self.env["account.move"]
        invoices_posted = self.env["account.move"].search([("state", "=", "posted")])
        bills_draft = self.env["account.move"].search([("state", "=", "draft")])

        for rec1 in bills_draft:
            _logger.info("from draft")
            _logger.info(rec1.id)
            _logger.info(rec1.ref)
            _logger.info(rec1.invoice_origin)
            for rec2 in invoices_posted:
                _logger.info("from_invoice")
                _logger.info(rec2.id)
                _logger.info(rec2.invoice_origin)
                if rec1.ref == rec2.invoice_origin:
                   # _logger.info(rec1.ref)
                    #_logger.info(rec2.invoice_origin)
                    rec1.action_post()



        return res
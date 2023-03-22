# -*- coding: utf-8 -*-
from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        #invoices = self.env["account.move"]
        invoices_posted = self.env["account.move"].search([("state", "=", "posted")], limit=1)
        invoice_id = invoices_posted.id

        bill_id = self.env["purchase.order"].search([("invoice_ids", ">", invoice_id)])

        for rec1 in invoices_posted:
            _logger.info("from invoice")
            _logger.info(rec1.id)
            _logger.info(rec1.invoice_origin)
            for rec2 in bill_id:
                _logger.info("from_draft")
                _logger.info(rec2.id)
                _logger.info(rec2.ref)
                if rec1.invoice_origin == rec2.ref:
                   # _logger.info(rec1.ref)
                    #_logger.info(rec2.invoice_origin)
                    rec2.action_post()



        return res
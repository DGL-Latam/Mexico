# -*- coding: utf-8 -*-
from odoo import fields, models, _
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        invoices_posted = self.env["account.move"].search([("state", "=", "posted")])
        invoice_id = invoices_posted.id

        bill_id = self.env["account.move"].search([("state", "=", "draft"), ("id", ">", invoice_id)])

        for rec1 in invoices_posted:
            _logger.info("from invoice")
            _logger.info(bill_id)
            _logger.info(rec1.id)
            _logger.info(rec1.invoice_origin)
            for rec2 in bill_id:
                _logger.info("from_bill")
                _logger.info(rec2.id)
                _logger.info(rec2.ref)
                if rec1.invoice_origin == rec2.ref:
                    rec2.invoice_date = datetime.today()
                    rec2.action_post()
        return res

    def _check_duplicate_supplier_reference(self):
        for order in self:
            if not order.company_id:
                continue
            company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
            if company and company.rule_type == 'sale_purchase_invoice_refund':
                continue
            res = super()._check_duplicate_supplier_reference()
        return res
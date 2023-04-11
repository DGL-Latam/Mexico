# -*- coding: utf-8 -*-
from odoo import fields, models, _
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        company = self.env["res.company"]._find_company_from_partner(self.partner_id.id)
        if company and company.rule_type == 'sale_purchase_invoice_refund':
            sale_orders = self.env['sale.order'].sudo().search('invoice_ids', 'in', self.id)
            purchase_orders = sale_orders.mapped('auto_purchase_order_id')
            bill = purchase_orders.sudo().with_user(1).with_company(company).action_create_invoice()
            bill.invoice_date = datetime.today()
            bill.action_post()
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
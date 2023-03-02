# -*- coding: utf-8 -*-
from odoo import fields, models, _

class sale_order(models.Model):
    _inherit = "sale.order"

    def _action_confirm(self):
        #super()._action_confirm(company)
        res = super(sale_order, self)._action_confirm()
        for order in self:
            if not order.company_id:
                continue
            company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
            if company and company.rule_type in ("sale_purchase_invoice_refund") and (not order.auto_generated):
                order.with_user(company.intercompany_user_id).with_context(default_company_id=company.id).with_company(company).inter_company_create_purchase_order(company)
        return res

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _purchase_service_create(self, quantity=False):
        line_to_purchase = set()
        for line in self:

            company = self.env['res.company']._find_company_from_partner(line.order_id.partner_id.id)
            if not company or company.rule_type not in (
            "sale_purchase_invoice_refund") and not line.order_id.auto_generated:
                line_to_purchase.add(line.id)
        line_to_purchase = self.env['sale.order.line'].browse(list(line_to_purchase))
        return super(SaleOrderLine, line_to_purchase)._purchase_service_create(quantity=quantity)

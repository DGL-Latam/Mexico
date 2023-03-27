# -*- coding: utf-8 -*-
from odoo import fields, models, _

class sale_order(models.Model):
    _inherit = "sale.order"


    def _action_confirm(self):

        res = super(sale_order, self)._action_confirm()

        for order in self:
            if not order.company_id:
                continue
            company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
            if company and company.rule_type == 'sale_purchase_invoice_refund' and (not order.auto_generated):
                order.with_user(company.intercompany_user_id).with_context(default_company_id=company.id).with_company(
                    company).inter_company_create_purchase_order(company)

        return res

    def _create_invoices(self, grouped=False, final=False, date=None):
        res = super()._create_invoices()

        for order in self:
            if not order.company_id:
                continue
            company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
            if company and company.rule_type == 'sale_purchase_invoice_refund':
                self.sudo().auto_purchase_order_id.with_company(company).action_create_invoice()
            if self.env["stock.picking"].name:
                try:
                    super()._nothing_to_invoice_error()
                except:
                    pass
        return res

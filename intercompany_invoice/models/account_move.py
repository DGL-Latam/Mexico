# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'


    def action_post(self):
        res = super().action_post()
        for invoice in self:
            if not invoice.company_id:
                continue
            company = self.env["res.company"]._find_company_from_partner(invoice.partner_id.id)
            if company and company.rule_type == 'sale_purchase_invoice_refund':
                invoice.with_user(company.intercompany_user_id).with_context(default_company_id=company.id).with_company(
                    company).action_post()
        return res

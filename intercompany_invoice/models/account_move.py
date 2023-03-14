# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'


    def action_post(self):
        res = super().action_post()

        for invoice in self:
            if not invoice.company_id:
                continue
            company = self.env["res.company"]._find_company_from_partner(invoice.partner_id.id)
            if company and company.rule_type == 'sale_purchase_invoice_refund':
                invoice.create_bill()
        return res

    def create_bill(self):
        for rec in self:
            if rec.env["sale.order"].name == rec.env["purchase.order"].partner_ref:
                rec.env["purchase.order"].create_bill()
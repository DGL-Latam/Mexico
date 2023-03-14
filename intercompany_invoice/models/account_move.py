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
            if company and company.rule_type == 'sale_purchase_invoice_refund'.format():
                invoice.env["purchase.order"].action_create_invoice()
        return res

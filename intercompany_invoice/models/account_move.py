# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'


    def action_post(self):
        res = super().action_post()
        line_ids = self.mapped('line_ids').filtered(lambda line: any(line.sale_line_ids.mapped('is_downpayment')))
        for line in line_ids:
            try:
                line.sale_line_ids.tax_id = line.tax_ids
                line.sale_line_ids.price_unit = line.price_unit
            except UserError:
                # a UserError here means the SO was locked, which prevents changing the taxes
                # just ignore the error - this is a nice to have feature and should not be blocking
                pass
        for invoice in self:
            if not invoice.company_id:
                continue
            company = self.env["res.company"]._find_company_from_partner(invoice.partner_id.id)
            if company and company.rule_type == 'sale_purchase_invoice_refund':
                invoice.create_bill()
        return res

    def create_bill(self):
        for rec in self:
            rec.env["purchase.order"].create_bill()
# -*- coding: utf-8 -*-
from odoo import fields, models, _


class purchase_order(models.Model):
    _inherit = "purchase.order"

    def _prepare_sale_order_data(self):

        res = super(purchase_order, self).button_approve(force=force)
        for order in self:
            # get the company from partner then trigger action of intercompany relation
            company_rec = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company_rec and company_rec.rule_type == 'sale_purchase_invoice_refund' and (not order.auto_generated):
                order.with_user(company_rec.intercompany_user_id).with_context(
                    default_company_id=company_rec.id).with_company(company_rec).inter_company_create_sale_order(company_rec)
        return res

    def action_create_invoice(self):
        confirm_from_sale = self.env["account.move"].action_post()

        invoices_map = {}
        res = super()._action_create_invoice()

        if confirm_from_sale:
            for invoice in res.filtered(lambda move: move.is_invoice()):
                company = self.env['res.company']._find_company_from_partner(invoice.partner_id.id)
                if company and company.rule_type == 'sale_purchase_invoice_refund' and not invoice.auto_generated:
                    invoices_map.setdefault(company, self.env['account.move'])
                    invoices_map[company] += invoice
            for company, invoices in invoices_map.items():
                context = dict(self.env.context, default_company_id=company.id)
                context.pop('default_journal_id', None)
                invoices.with_user(company.intercompany_user_id).with_context(context).with_company(
                    company)._inter_company_create_invoices()
        return res
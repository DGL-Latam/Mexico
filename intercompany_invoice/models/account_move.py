# -*- coding: utf-8 -*-
from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):

        invoices_map = {}
        posted = super()._post(soft)
        for invoice in posted.filtered(lambda move: move.is_invoice()):
            company = self.env['res.company']._find_company_from_partner(invoice.partner_id.id)
            if company and company.rule_type == 'sale_purchase_invoice_refund' and not invoice.auto_generated:
                invoices_map.setdefault(company, self.env['account.move'])
                invoices_map[company] += invoice
        for company, invoices in invoices_map.items():
            context = dict(self.env.context, default_company_id=company.id, create_bill=True)
            #context.pop('default_journal_id', None)
            invoices.with_user(company.intercompany_user_id).with_context(context).with_company(company)._inter_company_create_invoices()

        return posted

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
            context = dict(self.env.context, default_company_id=company.id)
            context.pop('default_journal_id', None)
            invoices.with_user(company.intercompany_user_id).with_context(context).with_company(company)._inter_company_create_invoices()

        return posted

    def _inter_company_create_invoices(self):
        invoices_vals_per_type = {}
        inverse_types = {
            'in_invoice': 'out_invoice',
            'in_refund': 'out_refund',
            'out_invoice': 'in_invoice',
            'out_refund': 'in_refund',
        }
        for inv in self:
            invoice_vals = inv._inter_company_prepare_invoice_data(inverse_types[inv.move_type])
            invoice_vals['invoice_line_ids'] = []
            for line in inv.invoice_line_ids:
                invoice_vals['invoice_line_ids'].append((0, 0, line._inter_company_prepare_invoice_line_data()))

            inv_new = inv.with_context(default_move_type=invoice_vals['move_type']).new(invoice_vals)
            for line in inv_new.invoice_line_ids.filtered(lambda l: not l.display_type):
                # We need to adapt the taxes following the fiscal position, but we must keep the
                # price unit.
                price_unit = line.price_unit
                line.tax_ids = line._get_computed_taxes()
                line._set_price_and_tax_after_fpos()
                line.price_unit = price_unit

            invoice_vals = inv_new._convert_to_write(inv_new._cache)
            invoice_vals.pop('line_ids', None)
            invoice_vals['origin_invoice'] = inv

            invoices_vals_per_type.setdefault(invoice_vals['move_type'], [])
            invoices_vals_per_type[invoice_vals['move_type']].append(invoice_vals)

        # Create invoices.
        moves = self.env['account.move']
        for invoice_type, invoices_vals in invoices_vals_per_type.items():
            for invoice in invoices_vals:
                origin_invoice = invoice['origin_invoice']
                invoice.pop('origin_invoice')
                msg = _("Automatically generated from %(origin)s of company %(company)s.", origin=origin_invoice.name,
                        company=origin_invoice.company_id.name)
                am = self.create(invoice)
                am.message_post(body=msg)
                moves += am
        return moves

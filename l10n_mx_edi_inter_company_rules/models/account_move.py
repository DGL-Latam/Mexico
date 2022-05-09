from odoo import api, models
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self,soft=True):
        records = self.env[self._name]
        records_so = self.env[self._name]
        for invoice in self.filtered(lambda i: i.move_type in ['out_invoice', 'out_refund']):
            company = self.env['res.company']._find_company_from_partner(invoice.partner_id.id)
            if not company or company.rule_type not in ('invoice_and_refund', 'sale', 'purchase', 'sale_purchase'):
                continue
            if not invoice.auto_generated:
                records += invoice
                _logger(invoice.name)
                continue
            records_so += invoice
        if not records + records_so:
            _logger('early return')
            return super()._post(soft=soft)
        result = super(AccountMove, self.with_context(disable_after_commit=True))._post(soft=soft)
        _logger("after super _post")
        for invoice in records:
            related = self.sudo().search([('auto_invoice_id', '=', invoice.id)])
            if not related:
                continue
            filename = ('%s-%s-MX-Invoice-%s.xml' % (
                related.journal_id.code, related.payment_reference or '', company.vat or '')).replace('/', '')
            
            invoice._get_l10n_mx_edi_signed_edi_document().sudo().copy({
                'res_id': related.id,
                'name': filename,
            })
        for invoice in records_so:
            sale = invoice.mapped('invoice_line_ids.sale_line_ids.order_id')
            if not sale:
                continue
            related = self.env['purchase.order'].sudo().search([('auto_sale_order_id', '=', sale.id)])
            if not related:
                continue
            bill = related.invoice_ids
            if bill:
                filename = ('%s-%s-MX-Invoice-%s.xml' % (
                    bill.journal_id.code, bill.payment_reference or '', bill.company_id.vat or '')).replace('/', '')
                
                invoice._get_l10n_mx_edi_signed_edi_document().sudo().copy({
                    'res_id': bill.id,
                    'name': filename,
                })
                continue
            invoice._get_l10n_mx_edi_signed_edi_document().sudo().copy({
                'res_id': related.id,
                'res_model': 'purchase.order'
            })
        return result

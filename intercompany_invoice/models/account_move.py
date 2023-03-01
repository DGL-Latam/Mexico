from odoo import api, models, fields, _
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        records = self.env[self._name]
        records_so = self.env[self._name]
        for invoice in self.filtered(lambda i: i.move_type in ['out_invoice', 'out_refund']):
            company = self.env['res.company']._find_company_from_partner(invoice.partner_id.id)
            if not company or company.rule_type not in ('invoice_and_refund', 'sale_purchase', "sale_purchase_invoice_refund"):
                continue
            if not invoice.auto_generated:
                records += invoice
                continue
            records_so += invoice

            inter_user = company.intercompany_invoice_user_id
            if inter_user:
                invoice = invoice.with_user(inter_user).sudo()
            else:
                invoice = invoice.sudo()
            invoice.with_company(company.id).width_context(skip_check_amount_difference=True)

        if not records + records_so:
            return super()._post(soft=soft)
        result = super(AccountMove, self.with_context(disable_after_commit=True))._post(soft=soft)
        result.edi_document_ids._process_documents_web_services()

        for invoice in records:
            related = self.sudo().search([('auto_invoice_id', '=', invoice.id), ('company_id', '=', invoice.company_id.id
                                                                                 )])
            if not related:
                continue
            filename = ('%s-%s-MX-Invoice-%s.xml' % (
                related.journal_id.code, related.payment_reference or '', company.vat or '')).replace('/', '')
            document = invoice._get_l10n_mx_edi_signed_edi_document()
            attachment = document.attachment_id
            copiedAttach = attachment.sudo().copy({
                'res_id': related.id,
                'company_id': related.company_id.id,
            })
            document.sudo().copy({
                'move_id': related.id,
                'attachment_id': copiedAttach.id,
                'name': filename,
            })

        for invoice in records_so:
            sale = invoice.mapped('invoice_line_ids.sale_line_ids.order_id')
            if not sale:
                continue
            related = self.env['purchase.order'].sudo().search(
                [('auto_sale_order_id', '=', sale.id), ('company_id', '=', sale.company_id.id)])
            if not related:
                continue
            bill = related.invoice_ids
            if bill:
                filename = ('%s-%s-MX-Invoice-%s.xml' % (
                    bill.journal_id.code, bill.payment_reference or '', bill.company_id.vat or '')).replace('/', '')
                document = invoice._get_l10n_mx_edi_signed_edi_document()
                attachment = document.attachment_id
                copiedAttach = attachment.sudo().copy({
                    'res_id': bill.id,
                    'company_id': bill.company_id.id,
                })
                document.sudo().copy({
                    'move_id': bill.id,
                    'attachment_id': copiedAttach.id,
                    'name': filename,
                })
                continue
            invoice._get_l10n_mx_edi_signed_edi_document().sudo().copy({
                'move_id': related.id,
            })
        
        return result

class sale_order(models.Model):
    _inherit = "sale.order"

    def _action_confirm(self):
        res = super(sale_order, self)._action_confirm()
        for order in self:
            if not order.company_id:
                continue
            company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
            if company and company.rule_type in ("sale", "sale_purchase", "sale_purchase_invoice_refund") and (not order.auto_generated):
                order.with_user(company.intercompany_user_id).with_context(default_company_id=company.id).with_company(company).inter_company_create_purchase_order(company)
        return res

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _purchase_service_create(self, quantity=False):
        line_to_purchase = set()
        for line in self:
            company = self.env['res.company']._find_company_from_partner(line.order_id.partner_id.id)
            if not company or company.rule_type not in (
            'purchase', 'sale_purchase', 'sale_purchase_invoice_refund') and not line.order_id.auto_generated:
                line_to_purchase.add(line.id)
        line_to_purchase = self.env['sale.order.line'].browse(list(line_to_purchase))
        return super(SaleOrderLine, line_to_purchase)._purchase_service_create(quantity=quantity)

class purchase_order(models.Model):
    _inherit = "purchase.order"

    def button_approve(self, force=False):

        res = super(purchase_order, self).button_approve(force=force)
        for order in self:
            company_rec = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company_rec and company_rec.rule_type in ('purchase', 'sale_purchase', 'sale_purchase_invoice_refund') and (not order.auto_generated):
                order.with_user(company_rec.intercompany_user_id).with_context(
                    default_company_id=company_rec.id).with_company(company_rec).inter_company_create_sale_order(
                    company_rec)
        return res
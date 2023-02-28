from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        records = self.env[self._name]
        records_so = self.env[self._name]
        for invoice in self.filtered(lambda i: i.move_type in ['out_invoice', 'out_refund']):
            company = self.env['res.company']._find_company_from_partner(invoice.partner_id.id)
            if not company or company.rule_type not in ('invoice_and_refund', 'sale', 'purchase', 'sale_purchase', 'sale_purchase_invoice_refund'):
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


class ResCompany(models.Model):
    _inherit = "res.company"

    rule_type = fields.Selection(selection_add=[("sale_purchase_invoice_refund", "Sincronizar órdenes de venta/compra y facturas/recibos")])

    intercompany_transaction_message = fields.Char(compute="_compute_intercompany_transaction_message")

    @api.depends("rule_type", "name")
    def _compute_intercompany_transaction_message(self):
        for record in self:
            if record.rule_type == "sale_purchase_invoice_refund":
                record.intercompany_transaction_message = _("Generación de ordenes/venta y factura/recibo para %s.", record.name)
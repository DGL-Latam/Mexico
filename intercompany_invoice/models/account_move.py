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
        if not records + records_so:
            return super()._post(soft=soft)
        result = super(AccountMove, self.with_context(disable_after_commit=True))._post(soft=soft)
        result.edi_document_ids._process_documents_web_services()

        return result

    def action_post(self):
        moves_with_payments = self.filtered('payment_id')
        other_moves = self - moves_with_payments
        if moves_with_payments:
            moves_with_payments.payment_id.action_post()
        if other_moves:
            other_moves._post(soft=True)
        return False

class ResCompany(models.Model):
    _inherit = "res.company"

    rule_type= fields.Selection(selection_add=[("sale_purchase_invoice_refund", "Sincronizar órdenes de venta/compra y facturas/recibos")])


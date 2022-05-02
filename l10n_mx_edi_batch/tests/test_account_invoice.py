import time
from odoo.addons.l10n_mx_edi.tests.common import InvoiceTransactionCase


class TestL10nMxEdiInvoiceZip(InvoiceTransactionCase):

    def test_invoice_stamp_in_zip(self):
        """Ensure that a bigger invoice is stamped in zip"""
        self.company.partner_id.write({
            'property_account_position_id': self.fiscal_position.id,
        })
        invoice = self.create_invoice()
        lines = []
        account = invoice.invoice_line_ids[0].account_id.id
        name = self.product.name * 10
        for _line in range(1000):
            lines.append((0, 0, {
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100,
                'name': name,
                'account_id': account,
                'invoice_line_tax_ids': [self.tax_positive.id],
                'uom_id': invoice.invoice_line_ids[0].uom_id.id,
            }))
        invoice.invoice_line_ids.unlink()
        for _times in range(3):
            invoice.sudo().write({'invoice_line_ids': lines})
            invoice.compute_taxes()
        invoice.action_invoice_open()
        self.assertTrue(invoice.l10n_mx_edi_stamp_code, invoice.message_ids.mapped('body'))
        time.sleep(10)
        invoice.l10n_mx_edi_update_pac_status()
        self.assertEqual(invoice.l10n_mx_edi_pac_status, "signed",
                         invoice.message_ids.mapped('body'))

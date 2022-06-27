from odoo import api,fields,models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_default_journal(self):
       return self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()

    journal_id = fields.Many2one(
        'account.journal', 
        string='Journal', 
        required=True,
        default=_get_default_journal
    )

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals['journal_id'] = self._get_default_journal()
        return invoice_vals

    
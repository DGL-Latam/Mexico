from odoo import models, fields, api
from odoo.tools.translate import _

class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        reverse_date = self.date if self.date_mode == 'custom' else move.date
        reference = ""
        if self.reason:
            reference = _('%(reason)s', reason = self.reason)
        elif move.ref:
            reference = _('%(reason)s', reason = move.ref)
        else:
            reference = _('%(reason)s', reason = move.name)
        return {
            'ref': reference,
            'date': reverse_date,
            'invoice_date': move.is_invoice(include_receipts=True) and (self.date or move.date) or False,
            'journal_id': self.journal_id.id,
            'invoice_payment_term_id': None,
            'invoice_user_id': move.invoice_user_id.id,
            'auto_post': True if reverse_date > fields.Date.context_today(self) else False,
        }
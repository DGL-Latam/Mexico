from odoo import _, api, fields, models
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_mx_edi_cancellation = fields.Char(
        string='Cancellation Case', copy=False, track_visibility='onchange',
        help='The SAT has 4 cases in which an invoice could be cancelled, please fill this field based on your case:\n'
        'Case 1: The invoice was generated with errors and must be re-invoiced, the format must be:\n'
        '"01:UUID" where the UUID is the fiscal folio of the invoice generated to replace this record.\n'
        'Case 2: The invoice has an error on the customer, this will be cancelled and replaced by a new with the '
        'customer fixed. The format must be:\n "02", only is required the case number.\n'
        'Case 3: The invoice was generated but the operation was cancelled, this will be cancelled and not must be '
        'generated a new invoice. The format must be:\n "03", only is required the case number.\n'
        'Case 4: Global invoice. The format must be:\n "04", only is required the case number.')




   


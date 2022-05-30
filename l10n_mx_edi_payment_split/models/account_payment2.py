import base64
import codecs
import json
from collections import defaultdict
from itertools import groupby
import io
import chardet

import logging
_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
from odoo.tools import float_is_zero
from odoo.tools import pycompat
BOM_MAP = {
    'utf-16le': codecs.BOM_UTF16_LE,
    'utf-16be': codecs.BOM_UTF16_BE,
    'utf-32le': codecs.BOM_UTF32_LE,
    'utf-32be': codecs.BOM_UTF32_BE,
}

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    payment_move_ids = fields.One2many('account.register.invoices', 
        'register_id', help='Invoices that were paid in mass')

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)
        payment_currency_id = self.env['res.currency'].browse(res.get('currency_id'))
        move_ids = self.env['account.move'].browse(self._context.get('active_ids')).sorted('invoice_date_due')
        res['payment_move_ids'] = [ (0, 0, {
            'move_id': move.id,
            'currency_id' : move.currency_id.id,    
            'partner_id': move.partner_id.id,
            'date': move.invoice_date,
            'date_due': move.invoice_date_due,
            'amount': move.amount_residual,
            'payment_amount': move.amount_residual,
            'payment_currency_id': payment_currency_id.id,
            'register_id' : self.id,
        }) for move in move_ids]
        self.payment_move_ids = res
        return res

    def _getMoves(self,line_ids):
        ids = []
        for line in line_ids:
            ids.append(line.move_id.id)
        return self.env['account.move'].search([('id','in', ids)])

    def _create_payment_vals_from_wizard(self):
        payment_vals = super()._create_payment_vals_from_wizard()
        return payment_vals

    @api.depends('payment_move_ids.payment_amount')
    def _compute_amount(self):
        sum = 0
        for record in self:
            for move in record.payment_move_ids:
                sum += move.payment_amount
            record.amount = sum

class AccountRegisterInvoices(models.TransientModel):
    _name = 'account.register.invoices'
    _description = 'A model to hold invoices being paid in payment register'
    _order = 'date_due ASC'
    
    move_id = fields.Many2one(
        'account.move', help='Invoice being paid')
    currency_id = fields.Many2one(
        'res.currency', help='Currency of this invoice',
        related='move_id.currency_id',)
    date = fields.Date(help="Invoice Date")
    date_due = fields.Date(string='Due Date',
                           help="Maturity Date in the invoice")
    partner_id = fields.Many2one(
        'res.partner', help='Partner involved in payment')
    amount = fields.Float(string='Due Amount', help='Amount to pay')
    payment_amount = fields.Monetary(
        store=True, 
        currency_field='currency_id',
        help='Amount being paid')
    payment_currency_id = fields.Many2one(
        'res.currency', help='Currency which this payment is being done')
    register_id = fields.Many2one(
        'account.payment.register',
        help='Technical field to connect to Bulk Invoice',
        copy=False)

    



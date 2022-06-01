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

        values = []
        for move in move_ids:
            values.append({
                'move_id': move.id,
                'currency_id' : move.currency_id.id,    
                'partner_id': move.partner_id.id,
                'date': move.invoice_date,
                'date_due': move.invoice_date_due,
                'amount': move.amount_residual,
                'payment_amount': move.amount_residual,
                'payment_currency_id': payment_currency_id.id,
                'register_id' : self.id
            })
        reginv_ids = []
        for val in values:
            _logger.info(val)
            #reginv_ids.append(self.env['account.register.invoices'].create(val))

        res['payment_move_ids'] = [ (0, 0, val) for val in values]

        
        return res

    def _getMoves(self,line_ids):
        ids = []
        for line in line_ids:
            _logger.info(line.move_id.id)
            ids.append(line.move_id.id)
        return self.env['account.move'].search([('id','in', ids)])

    def _create_payment_vals_from_wizard(self):
        payment_vals = super()._create_payment_vals_from_wizard()
        return payment_vals

    @api.depends('payment_move_ids.payment_amount','payment_move_ids')
    def _compute_amount(self):
        sum = 0
        for record in self:
            for move in record.payment_move_ids:
                if(move.currency_id == record.currency_id):
                    sum += move.payment_amount
                else:
                    sum += move.currency_id._convert(move.payment_amount,record.currency_id,record.company_id,record.payment_date)
            record.amount = sum

    def _create_payment_vals_from_batch(self, batch_result):
        values = super()._create_payment_vals_from_batch(batch_result)
        amount = 0
        _logger.info("searching for ")
        _logger.info(batch_result['lines'][0].move_id.id)
        for move in self.payment_move_ids:
            _logger.info(move)
            _logger.info(move.move_id)
            _logger.info(move.move_id.id)
            if move.move_id.id == batch_result['lines'][0].move_id.id:
                
                amount = move.payment_amount
                _logger.info("amount found")
                _logger.info(amount)
                break
        values['amount'] = amount
        return values


class AccountRegisterInvoices(models.TransientModel):
    _name = 'account.register.invoices'
    _description = 'A model to hold invoices being paid in payment register'
    _order = 'date_due ASC'
    
    move_id = fields.Many2one(
        'account.move', help='Invoice being paid' ,store=True)
    currency_id = fields.Many2one(
        'res.currency', help='Currency of this invoice',
        related='move_id.currency_id' ,store=True)
    date = fields.Date(help="Invoice Date" ,store=True)
    date_due = fields.Date(string='Due Date',
                           help="Maturity Date in the invoice" ,store=True)
    partner_id = fields.Many2one(
        'res.partner', help='Partner involved in payment' ,store=True)
    amount = fields.Float(string='Due Amount', help='Amount to pay' ,store=True)
    payment_amount = fields.Monetary(
        store=True, 
        currency_field='currency_id',
        help='Amount being paid')
    payment_currency_id = fields.Many2one(
        'res.currency', help='Currency which this payment is being done' ,store=True)
    register_id = fields.Many2one(
        'account.payment.register',
        help='Technical field to connect to Bulk Invoice',
        copy=False ,store=True)

    



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
    partner_id = fields.Many2one('res.partner',
        string="Customer/Vendor", store=True, copy=False, ondelete='restrict',
        compute='_compute_from_lines', inverse = "_inv_partner")
    csv_file = fields.Binary(copy=False, help='csv con el nombre de la factura y monto')
    csv_name = fields.Char(copy=False, help='nombre del archivo CSV')
    
    def _create_payments(self):
        payments = super()._create_payments()
        payments._generate_factoraje_journal_entry()
        return payments
    
    @api.depends('can_edit_wizard')
    def _compute_group_payment(self):
        for wizard in self:
            wizard.group_payment = True
    
    @api.depends('line_ids')
    def _compute_from_lines(self):
        super()._compute_from_lines()
        for wizard in self:
            wizard.can_edit_wizard = True
            wizard.can_group_payments = True
    
    @api.onchange('csv_file')
    def _import_csv(self):
        self.ensure_one()
        if not self.csv_file:
            return
        if self.csv_name and not self.csv_name.lower().endswith('.csv'):
            raise UserError(_("Por favor usa un archivo csv"))
        csv_data = base64.b64decode(self.csv_file)
        self.update({'payment_move_ids': False})
        try:
            encoding = chardet.detect(csv_data)['encoding'].lower()
            bom = BOM_MAP.get(encoding)
            if bom and csv_data.startswith(bom):
                encoding = encoding[:-2]
            if encoding != 'utf-8':
                csv_data = csv_data.decode(encoding).encode('utf-8')
            # Separator
            separator = ','
            csv_iterator = pycompat.csv_reader(
                io.BytesIO(csv_data), quotechar='"', delimiter=separator)
        except Exception:
            raise UserError(_("Por favor usa un archivo csv"))
        values = []
        for row in csv_iterator:
            move = self.env['account.move'].search([('name','=',row[0]),('state', '=','posted')])
            if move.amount_residual == 0:
                continue
            try:
                col_num = len(row)
                amount = float(row[1]) if col_num > 1 else 0
            except ValueError:
                continue
            if not move or amount <= 0:
                continue
                
            manual_line = self.env['account.move.line']
            for line in move.line_ids:
                if line.move_id.state != 'posted':
                    raise UserError(_("You can only register payment for posted journal entries."))

                if line.account_internal_type not in ('receivable', 'payable'):
                    continue
                if line.currency_id:
                    if line.currency_id.is_zero(line.amount_residual_currency):
                        continue
                else:
                    if line.company_currency_id.is_zero(line.amount_residual):
                        continue
                manual_line |= line
            values.append({
                'move_line_id': manual_line.id,
                'currency_id' : manual_line.currency_id.id,    
                'partner_id': manual_line.partner_id.id,
                'date': manual_line.date,
                'date_due': manual_line.move_id.invoice_date_due,
                'amount': manual_line.move_id.amount_residual,
                'payment_amount': amount,
                'register_id' : self.id
            })
        if not values:
            raise UserError(_('No se pudieron importar las facturas checar si se esta usando un csv'))
        #_logger.info(values)
        self.update({'payment_move_ids': [(0, 0, val) for val in values]})
            
    
    @api.model
    def _inv_partner(self):
        return
    
    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        #_logger.info("Actualizando payment_move_ids")
        res = super().default_get(fields_list)
        payment_currency_id = self.env['res.currency'].browse(res.get('currency_id'))
        move_ids = self.env['account.move'].browse(self._context.get('active_ids')).sorted('invoice_date_due')
        manual_line = self.env['account.move.line']
        for line in move_ids.line_ids:
            if line.move_id.state != 'posted':
                raise UserError(_("You can only register payment for posted journal entries."))

            if line.account_internal_type not in ('receivable', 'payable'):
                continue
            if line.currency_id:
                if line.currency_id.is_zero(line.amount_residual_currency):
                    continue
            else:
                if line.company_currency_id.is_zero(line.amount_residual):
                    continue
            manual_line |= line
        
        values = []
        for move in manual_line:
            values.append({
                'move_line_id': move.id,
                'currency_id' : move.currency_id.id,    
                'partner_id': move.partner_id.id,
                'date': move.date,
                'date_due': move.move_id.invoice_date_due,
                'amount': move.move_id.amount_residual,
                'payment_amount': move.move_id.amount_residual,
                'payment_currency_id': payment_currency_id.id,
                'register_id' : self.id
            })
        res['payment_move_ids'] = [ (0, 0, val) for val in values]    
        _logger.critical("fin default get")
        return res
    
    def _create_payment_vals_from_wizard(self):
        payment_vals = super()._create_payment_vals_from_wizard()
        payment_vals['partner_type'] = 'customer' if self.payment_move_ids[0].move_line_id.filtered(lambda r: r.account_internal_type in ('receivable','payable')).account_internal_type == 'receivable' else 'supplier'
        return payment_vals

    @api.depends('payment_move_ids.payment_amount','payment_move_ids')
    def _compute_amount(self):
        sum = 0
        for record in self:
            for move in record.payment_move_ids:
                    sum += move.payment_amount
            record.amount = sum

    def _create_payment_vals_from_batch(self, batch_result):
        values = super()._create_payment_vals_from_batch(batch_result)
        amount = 0
        for move in self.payment_move_ids:
            if move.move_line_id.id == batch_result['lines'][0].id:            
                amount = move.payment_amount
                break
            
        values['amount'] = amount
        values['partner_id'] = self.partner_id.id
        values['partner_type'] = 'customer' if self.payment_move_ids[0].move_line_id.filtered(lambda r: r.account_internal_type in ('receivable','payable')).account_internal_type == 'receivable' else 'supplier'
        return values
    
    
    @api.depends('amount')    
    def _compute_payment_difference(self):
        for wizard in self:
            if wizard.source_currency_id == wizard.currency_id:
                # Same currency.
                wizard.payment_difference = wizard.source_amount_currency - wizard.amount
            elif wizard.currency_id == wizard.company_id.currency_id:
                # Payment expressed on the company's currency.
                wizard.payment_difference = wizard.source_amount - wizard.amount
            else:
                # Foreign currency on payment different than the one set on the journal entries.
                amount_payment_currency = self.env.company.currency_id._convert(wizard.source_amount, wizard.currency_id, self.env.company, wizard.payment_date)
                wizard.payment_difference = amount_payment_currency - wizard.amount

    def _reconcile_payments(self, to_process, edit_mode=False):
        """ Reconcile the payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_get_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """
        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
        for vals in to_process:
            payment_lines = vals['payment'].line_ids.filtered_domain(domain)
            #_logger.info('Payment_line')
            #_logger.info(payment_lines)
            
            lines = vals['to_reconcile']
            #_logger.info('to reconcile from context')
            #_logger.info(lines)

            #_logger.info(self.payment_move_ids.move_line_id)
            #_logger.info(payment_lines + self.payment_move_ids.move_line_id)
            amounts = []
            for move in self.payment_move_ids:
                amounts.append(move.payment_amount)
            #_logger.info(amounts)     
            for account in payment_lines.account_id:
                #_logger.info( (payment_lines + self.payment_move_ids.move_line_id).filtered_domain([('reconciled', '=', False)]))
                (payment_lines + self.payment_move_ids.move_line_id)\
                    .filtered_domain([('reconciled', '=', False)])\
                    .with_context(no_exchange_difference = True).reconcile(amounts)


class AccountRegisterInvoices(models.TransientModel):
    _name = 'account.register.invoices'
    _description = 'A model to hold invoices being paid in payment register'
    _order = 'date_due ASC'
    
    move_line_id = fields.Many2one(
        'account.move.line', help='Invoice being paid' ,store=True)
    currency_id = fields.Many2one(
        'res.currency', help='Currency of this invoice',
        related='move_line_id.currency_id' ,store=True)
    date = fields.Date(help="Invoice Date" ,store=True , related='move_line_id.date')
    date_due = fields.Date(string='Due Date',
                           help="Maturity Date in the invoice" ,store=True, related='move_line_id.move_id.invoice_date_due')
    partner_id = fields.Many2one(
        'res.partner', help='Partner involved in payment' ,store=True, related='move_line_id.partner_id')
    amount = fields.Monetary(string='Due Amount',currency_field='currency_id', help='Amount to pay' ,store=True, related='move_line_id.move_id.amount_residual')
    amount_in_line_currency = fields.Monetary(string="Monto en Moneda de la factura",
        currency_field='currency_id',
        compute="_compute_amount_in_line_currency")
    payment_amount = fields.Monetary(
        store=True, 
        currency_field='payment_currency_id',
        help='Amount being paid', compute="_reset_payment_amount" , inverse = "_inv_pay_amount")
    
    
    prev_currency = fields.Many2one('res.currency',string="previous currency", help="only for calculations")
    prev_payment_date = fields.Date(string="prev date", help="only to help make calculations")
    payment_currency_id = fields.Many2one(help="Currency in wich the payment is being processed", related="register_id.currency_id")
    
    company_currency_id = fields.Many2one('res.currency',related='company_id.currency_id')
    exchange_rate = fields.Float(string="Tasa de cambio", compute="_compute_amount_in_line_currency", digits=(16, 4))
    payment_date = fields.Date(related="register_id.payment_date")
    company_id = fields.Many2one(related="register_id.company_id")
    register_id = fields.Many2one(
        'account.payment.register',
        help='Technical field to connect to Bulk Invoice',
        copy=False ,store=True)
    
    
    def _inv_pay_amount(self):
        return
    
    @api.depends('move_line_id','payment_currency_id','payment_date')
    def _reset_payment_amount(self):
        for record in self:
            #_logger.info(record.payment_amount)
            #_logger.info(record.company_id)
           
            if not record.prev_payment_date:
                record.prev_payment_date = record.payment_date
            if record.payment_currency_id == record.currency_id:
                if not record.prev_currency:
                    #_logger.info("no prevoues id")
                    record.prev_currency = record.payment_currency_id
                record.payment_amount = record.prev_currency._convert(record.payment_amount,record.payment_currency_id,record.company_id,record.payment_date)
            else:
                if not record.prev_currency:
                    record.payment_amount = record.currency_id._convert(record.amount,record.payment_currency_id,record.company_id,record.payment_date)
                else:
                    #_logger.info(record.amount_in_line_currency)
                    value_in_line_curr = record.prev_currency._convert(record.payment_amount,record.currency_id,record.company_id,record.prev_payment_date)

                    record.payment_amount =  record.currency_id._convert(value_in_line_curr,record.payment_currency_id,record.company_id,record.payment_date)

            record.prev_payment_date = record.payment_date
            record.prev_currency = record.payment_currency_id
            self._compute_amount_in_line_currency()
            
            
    @api.depends('payment_date','payment_amount','company_id','payment_currency_id')
    def _compute_amount_in_line_currency(self):
        for record in self:
            if record.company_id:
                record.amount_in_line_currency = record.payment_currency_id._convert(record.payment_amount,record.currency_id,record.company_id,record.payment_date)
                if record.payment_currency_id != record.company_currency_id:
                    record.exchange_rate  = record.payment_currency_id._convert(1,record.company_currency_id,record.company_id,record.payment_date,round=False)
                elif record.currency_id != record.company_currency_id:
                    record.exchange_rate  = record.currency_id._convert(1,record.company_currency_id,record.company_id,record.payment_date,round=False)
                else:
                    record.exchange_rate  = 1
            else:
                record.amount_in_line_currency = 0
                record.exchange_rate  = 0



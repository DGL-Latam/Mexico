from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):

    _inherit = "account.move"

    def js_assign_outstanding_line(self, line_id):
        self.ensure_one()
        if "paid_amount" in self.env.context:
            amount = self.env.context.get("paid_amount", 0.0)
            final = self.currency_id._convert(amount,self.env['account.move.line'].browse(line_id).company_currency_id,self.env['account.move.line'].browse(line_id).company_id,self.env['account.move.line'].browse(line_id).date)
            return self.with_context(move_id=self.id,line_id=line_id).js_assign_outstanding_line_amount(line_id, [final])
        return super(AccountMove, self).js_assign_outstanding_line(line_id)

    def js_assign_outstanding_line_amount(self, line_id,amount):
        ''' Called by the 'payment' widget to reconcile a suggested journal item to the present
        invoice.
        :param line_id: The id of the line to reconcile with the current invoice.
        '''
        self.ensure_one()
        lines = self.env['account.move.line'].browse(line_id)
        lines += self.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
        return lines.with_context(no_exchange_difference = True).reconcile(amount)
    

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self, amounts = None):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        results = {}

        if not self:
            return results

        # List unpaid invoices
        not_paid_invoices = self.move_id.filtered(
            lambda move: move.is_invoice(include_receipts=True) and move.payment_state not in ('paid', 'in_payment')
        )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        for line in self:
            if line.reconciled:
                raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
                raise UserError(_("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                                % line.account_id.display_name)
            if line.move_id.state != 'posted':
                if line.move_id.move_type == 'entry':
                    line.move_id._post(soft=False)
                else:
                    raise UserError(_('You can only reconcile posted entries.'))
            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                                % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id


        sorted_lines = self.sorted(key=lambda line: (line.date_maturity or line.date, line.currency_id))

        # ==== Collect all involved lines through the existing reconciliation ====

        involved_lines = sorted_lines
        involved_partials = self.env['account.partial.reconcile']
        current_lines = involved_lines
        current_partials = involved_partials
        
        while current_lines:
            current_partials = (current_lines.matched_debit_ids + current_lines.matched_credit_ids) - current_partials
            involved_partials += current_partials
            current_lines = (current_partials.debit_move_id + current_partials.credit_move_id) - current_lines
            involved_lines += current_lines

        # ==== Create partials ====
        partials = []
        if amounts:
            partials = self.env['account.partial.reconcile'].create(sorted_lines._prepare_reconciliation_partials_amount(amounts))
        else:
            partials = self.env['account.partial.reconcile'].create(sorted_lines._prepare_reconciliation_partials())

        # Track newly created partials.
        results['partials'] = partials
        involved_partials += partials

        # ==== Create entries for cash basis taxes ====
        is_cash_basis_needed = account.user_type_id.type in ('receivable', 'payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====     
        lines_to_full_reconcile = self.env['account.move.line']
        
        for line in sorted_lines.filtered(lambda line : line.move_id.move_type in ['out_invoice','in_invoice']):
            if line.currency_id.is_zero(line.amount_residual_currency):
                lines_to_full_reconcile += line
        if len(lines_to_full_reconcile) > 0:
            is_full_needed = True
            for line in sorted_lines.filtered(lambda line: line.move_id.move_type in ['entry']):
                lines_to_full_reconcile += line
        else:
            is_full_needed = False

        if is_full_needed:

            # ==== Create the exchange difference move ====
            if not self._context.get('no_exchange_difference'):
                exchange_move = None
            else:
                exchange_move = lines_to_full_reconcile.filtered(lambda line : line.move_id.move_type in ['out_invoice','in_invoice'])._create_exchange_difference_move()
                if exchange_move:
                    exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                    # Track newly created lines.
                    lines_to_full_reconcile += exchange_move_lines

                    # Track newly created partials.
                    exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                             + exchange_move_lines.matched_credit_ids
                    involved_partials += exchange_diff_partials
                    results['partials'] += exchange_diff_partials

                    exchange_move._post(soft=False)

            # ==== Create the full reconcile ====
            results['full_reconcile'] = self.env['account.full.reconcile'].create({
                'exchange_move_id': exchange_move and exchange_move.id,
                'partial_reconcile_ids': [(6, 0, lines_to_full_reconcile.ids)],
                'reconciled_line_ids': [(6, 0, lines_to_full_reconcile.ids)],
            })
        # Trigger action for paid invoices
        not_paid_invoices\
            .filtered(lambda move: move.payment_state in ('paid', 'in_payment'))\
            .action_invoice_paid()
        return results
     
    
    def _prepare_reconciliation_partials_amount(self,amounts):
        #note amounts are given on the currency of payment, not the main one (db)
        def fix_remaining_cent(currency, abs_residual, partial_amount):
            if abs_residual - currency.rounding <= partial_amount <= abs_residual + currency.rounding:
                return abs_residual
            else:
                return partial_amount
        debit_lines = iter(self.filtered(lambda line: line.balance > 0.0 or line.amount_currency > 0.0))
        credit_lines = iter(self.filtered(lambda line: line.balance < 0.0 or line.amount_currency < 0.0))
        
        debit_line = None
        credit_line = None
       
        debit_amount_residual = 0.0
        debit_amount_residual_currency = 0.0
        credit_amount_residual = 0.0
        credit_amount_residual_currency = 0.0
        debit_line_currency = None
        credit_line_currency = None

        partials_vals_list = []
        indexAmount = 0
        indexTrue = 0
        while True:
            # Move to the next available debit line.
            if not debit_line:
                debit_line = next(debit_lines, None)
                if not debit_line:
                    break
                debit_amount_residual = 0
                custom_debit_amount = debit_line.move_id.move_type in ['entry']
                
                if custom_debit_amount:
                    debit_amount_residual = debit_line.currency_id._convert(
                        amounts[indexAmount],
                        debit_line.company_currency_id,
                        debit_line.company_id,
                        debit_line.date,
                    )
                else:
                   debit_amount_residual = debit_line.amount_residual

                if debit_line.currency_id:
                    debit_amount_residual_currency = amounts[indexAmount] if custom_debit_amount else debit_line.amount_residual_currency
                    debit_line_currency = debit_line.currency_id
                else:
                    debit_amount_residual_currency = debit_amount_residual
                    debit_line_currency = debit_line.company_currency_id

            # Move to the next available credit line.
            if not credit_line:
                credit_line = next(credit_lines, None)
                if not credit_line:
                    break
                    
                custom_credit_amount = credit_line.move_id.move_type in ['entry']
                credit_amount_residual = 0
                if custom_credit_amount:
                    credit_amount_residual = - credit_line.currency_id._convert(
                        amounts[indexAmount],
                        credit_line.company_currency_id,
                        credit_line.company_id,
                        credit_line.date,
                    )
                else:
                    credit_amount_residual = credit_line.amount_residual
                if credit_line.currency_id:
                    credit_amount_residual_currency = - amounts[indexAmount] if custom_credit_amount else credit_line.amount_residual_currency
                    credit_line_currency = credit_line.currency_id

                else:
                    credit_amount_residual_currency = credit_amount_residual
                    credit_line_currency = credit_line.company_currency_id
                    
            if debit_line.currency_id != debit_line.company_currency_id and credit_line.move_id.move_type in ['entry']:
                debit_amount_residual = debit_line.currency_id._convert(
                        debit_amount_residual,
                        debit_line.company_currency_id,
                        debit_line.company_id,
                        credit_line.date,
                    )
            
            if credit_line.currency_id != credit_line.company_currency_id and debit_line.move_id.move_type in ['entry']:
                credit_amount_residual = credit_line.currency_id._convert(
                        credit_amount_residual,
                        credit_line.company_currency_id,
                        credit_line.company_id,
                        debit_line.date,
                    )
            
              
            min_amount_residual = min(abs(debit_amount_residual), abs(credit_amount_residual))
            if debit_line_currency == credit_line_currency:
                min_amount_residual_currency =  min(debit_amount_residual_currency, -credit_amount_residual_currency)# 100 #custom amount [x] in foreign currency
                min_debit_amount_residual_currency = min_amount_residual_currency
                min_credit_amount_residual_currency = min_amount_residual_currency

            else:
                min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
                    min_amount_residual,
                    debit_line.currency_id,
                    credit_line.company_id,
                    credit_line.date,
                )
                min_debit_amount_residual_currency = fix_remaining_cent(
                    debit_line.currency_id,
                    debit_amount_residual_currency,
                    min_debit_amount_residual_currency,
                )
                min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
                    min_amount_residual,
                    credit_line.currency_id,
                    debit_line.company_id,
                    debit_line.date,
                )
                min_credit_amount_residual_currency = fix_remaining_cent(
                    credit_line.currency_id,
                    -credit_amount_residual_currency,
                    min_credit_amount_residual_currency,
                )
            debit_amount_residual -= min_amount_residual
            debit_amount_residual_currency -= min_debit_amount_residual_currency
            credit_amount_residual += min_amount_residual
            credit_amount_residual_currency += min_credit_amount_residual_currency
            partials_vals_list.append({
                'amount': min_amount_residual,
                'debit_amount_currency': min_debit_amount_residual_currency,
                'credit_amount_currency': min_credit_amount_residual_currency,
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })
            indexAmount += 1
            if indexAmount < len(amounts):
                if custom_debit_amount:
                    credit_line = None
                    custom_debit_amount = debit_line.move_id.move_type in ['entry']
                if custom_debit_amount:
                    debit_amount_residual = debit_line.currency_id._convert(
                        amounts[indexAmount],
                        debit_line.company_currency_id,
                        debit_line.company_id,
                        debit_line.date,
                    )
                else:
                    debit_amount_residual = debit_line.amount_residual

                if debit_line.currency_id:
                    debit_amount_residual_currency = amounts[indexAmount] if custom_debit_amount else debit_line.amount_residual_currency
                    debit_line_currency = debit_line.currency_id
                else:
                    debit_amount_residual_currency = debit_amount_residual
                    debit_line_currency = debit_line.company_currency_id
                if custom_credit_amount:
                    debit_line = None
                    custom_credit_amount = credit_line.move_id.move_type in ['entry']
                    credit_amount_residual = 0
                    if custom_credit_amount:
                        credit_amount_residual = - credit_line.currency_id._convert(
                            amounts[indexAmount],
                            credit_line.company_currency_id,
                            credit_line.company_id,
                            credit_line.date,
                        )
                    else:
                        credit_amount_residual = credit_line.amount_residual
                    if credit_line.currency_id:
                        credit_amount_residual_currency = - amounts[indexAmount] if custom_credit_amount else credit_line.amount_residual_currency
                        credit_line_currency = credit_line.currency_id

                    else:
                        credit_amount_residual_currency = credit_amount_residual
                        credit_line_currency = credit_line.company_currency_id
                continue
            else:
                break
        
        return partials_vals_list

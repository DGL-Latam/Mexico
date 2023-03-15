from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    factoraje_move = fields.Many2one('account.move', string="Movimiento de factoraje")

    @api.onchange('state')
    def reset_factoraje(self):
        for rec in self:
            if rec.state in ['draft','cancel']:
                if rec.factoraje_move.id:
                    rec.factoraje_move.buttton_draft()

    def _generate_factoraje_journal_entry(self):
        for rec in self:
            fact_needed = False
            reconciled_values = rec.move_id._get_reconciled_invoices_partials()
            _logger.critical(reconciled_values)
            for partial in reconciled_values:
                if rec.partner_id != partial[2].partner_id:
                    fact_needed = True
                    break
            _logger.critical(fact_needed)
            _logger.critical("generar factoraje")
            if not fact_needed:
                continue
            values = {}
            for rec_value in reconciled_values:
                if rec_value[2].account_id.code not in values.keys():
                    values[rec_value[2].account_id.code] = []
                    values[rec_value[2].account_id.code].append({'partner': rec_value[2].partner_id, 'amount' : rec_value[1]})
                else:
                    found = False
                    for detail in values[rec_value[2].account_id.code]:
                        if rec_value[2].partner_id == detail['partner']:
                            detail['amount'] += rec_value[1]
                            found = True
                            break
                    if not found:
                        values[rec_value[2].account_id.code].append({'partner': rec_value[2].partner_id, 'amount' : rec_value[1]})
            _logger.critical(values)
            journal_id = rec.env['account.journal'].search([('company_id','=',rec.company_id.id),('name','ilike','Factoraje')])
            move_id = rec.env['account.move'].sudo().with_user(1).create({'date': rec.date, 'journal_id' : journal_id.id, 'move_type' : 'entry'} )
            _logger.critical(move_id)
            line_vals = []
            for key in values.keys():
                account_id = rec.env['account.account'].sudo().search([('company_id','=',rec.company_id.id),('code','=',key)])
                for pair in values[key]:
                    line_vals.append({'move_id' : move_id.id, 'partner_id' : rec.partner_id.id, 'debit' : pair['amount'], 'account_id' : account_id.id })
                    line_vals.append({'move_id' : move_id.id, 'partner_id' : pair['partner'].id, 'credit' : pair['amount'], 'account_id' : account_id.id })
            rec.env['account.move.line'].sudo().with_user(1).create(line_vals)
            move_id.with_user(1).action_post()
            rec.write({'factoraje_move': move_id.id})
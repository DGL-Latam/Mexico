from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv.expression import (NEGATIVE_TERM_OPERATORS,
                                 TERM_OPERATORS_NEGATION)
TERM_OPERATORS_POSITIVE = {v: k for k, v in TERM_OPERATORS_NEGATION.items()}

class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_mx_edi_cfdi_uuid = fields.Char(
        string='Fiscal Folio', 
        copy=False, 
        readonly=True,
        store=True,
        help='Folio in electronic invoice, is returned by SAT when send to stamp.',
        compute='_compute_uuid',
        compute_sudo=True)
    
    
    @api.depends('edi_document_ids')
    def _compute_uuid(self):
        for move in self:
            move.edi_document_ids._process_documents_web_services()
            cfdi_info = move._l10n_mx_edi_decode_cfdi()
            move.l10n_mx_edi_cfdi_uuid = cfdi_info.get('uuid')
     
    def _searchUuid(self,operator,value):
        if not value:
            return [('l10n_mx_edi_cfdi_uuid',operator,value)]
        domain_op = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
        return [('l10n_mx_edi_cfdi_uuid',operator,value)]
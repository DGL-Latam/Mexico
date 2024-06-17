from odoo import _, api, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_mx_edi_cfdi_uuid = fields.Char(
        string='Fiscal Folio', 
        copy=False, 
        readonly=True,
        help='Folio in electronic invoice, is returned by SAT when send to stamp.',
        search='search_uuid',
    )

    def search_uuid(self, operator, value):
        ids = []
        documents = self.env['account.edi.document'].search([('l10n_mx_edi_uuid', operator, value)])
        for doc in documents:
            ids.append(doc.move_id.id)
        if ids:
            return [('id', 'in', ids)]
        return [('id', 'in', [])]
    
    @api.model
    def _update_cfdi_values(self):
        documents = self.env['account.edi.document'].search([('move_id', 'in', self.ids)])
        for doc in documents:
            move = doc.move_id
            move.l10n_mx_edi_cfdi_uuid = doc.l10n_mx_edi_uuid
    
    @api.model
    def create(self, vals):
        record = super(AccountMove, self).create(vals)
        record._update_cfdi_values()
        return record

    def write(self, vals):
        result = super(AccountMove, self).write(vals)
        self._update_cfdi_values()
        return result

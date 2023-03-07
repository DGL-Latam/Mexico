from odoo import _, api, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_mx_edi_cfdi_uuid = fields.Char(
        string='Fiscal Folio', 
        copy=False, 
        readonly=True,
        help='Folio in electronic invoice, is returned by SAT when send to stamp.',
        compute='_compute_cfdi_values',
        search='search_uuid')
    
    def search_uuid(self,operator, value):
        ids = self.env['ir.attachment'].search([('l10n_mx_edi_uuid','=',value),('res_model','=', self._name)]).res_id
        return [('id', 'in', ids)]
    
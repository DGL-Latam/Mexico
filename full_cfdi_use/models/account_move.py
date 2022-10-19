from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'
    l10n_mx_edi_usage = fields.Selection(
        selection_add=[
            ('S01', 'S01 Sin efectos fiscales'),      
        ],)
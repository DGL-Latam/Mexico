from odoo import fields, models


class AccountMove(models.Model):
    """
    Se agrega un nuevo valor a la seleccion de uso de cfdi,
    Se agrega sin efectos fiscales con la clave S01
    """
    _inherit = 'account.move'
    l10n_mx_edi_usage = fields.Selection(
        selection_add=[
            ('S01', 'S01 Sin efectos fiscales'),      
        ],)
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_mx_edi_reg_pat = fields.Char(string="Registro Patronal", size=20, trim=True)
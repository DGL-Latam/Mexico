from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_mx_curp = fields.Char(string = "CURP")
    l10n_mx_seg_soc = fields.Char(string = "Seguridad Social")
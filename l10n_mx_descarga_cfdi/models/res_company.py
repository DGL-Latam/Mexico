from odoo import models, fields

class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_mx_fiel_cer = fields.Binary(string="Certificado FIEL", attachment=False)
    l10n_mx_fiel_key = fields.Binary(string="Llave FIEL", attachment=False)
    l10n_mx_fiel_pass = fields.Char(string="Contraseña Fiel")
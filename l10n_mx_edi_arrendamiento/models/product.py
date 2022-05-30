from datetime import date
from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = "product.template"
    isProperty = fields.Boolean(string="Is a real state property?", help="toggle to show data needed for real states properties")
    cuentaPredial = fields.Char("Cuenta Predial", help="Campo para introducir el valor del numero de cuenta predial del bien inmueble")
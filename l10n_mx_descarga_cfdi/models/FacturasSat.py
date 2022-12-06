from odoo import models, fields

from .Autentificacion import Autentificacion
from .Fiel import Fiel

class FacturasSat(models.Model):
    _name = "facturas.sat"

    _description = "Tabla para guardar la relacion de las facturas encontradas en el sat mediante el Web service, y las que existen en sistema"

    sat_uuid = fields.Char(string="Folio Fiscal", copy=False, readonly=True)
    sat_state = fields.Char(string="Estado Factura SAT")
    sat_rfc_emisor = fields.Char(string="RFC Emisor")
    sat_monto = fields.float(string="Monto")
    sat_fecha_emision = fields.Date(string="Fecha Emision")
    sat_fecha_cancelacion = fields.Date(string="Fecha Cancelacion")

    account_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Factura Odoo")
    account_move_status = fields.Selection(string="Estado Factura Odoo", related='account_move_id.state', readonly=True)

    company = fields.Many2one(comodel_name="res.company",string="Empresa")

    def _checkSatInvoices(self):
        certificates = self.company.l10n_mx_edi_certificate_ids
        certificate = certificates.sudo().get_valid_certificate()
        fiel = Fiel(certificate.content,certificate.key,certificate.password)
        cer_pem = certificate.get_pem_cer(certificate.content)
        key_pem = certificate.get_pem_key(certificate.key, certificate.password)
        autentificacion = Autentificacion(fiel)
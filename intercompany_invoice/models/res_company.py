from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = "res.company"

    new_rule_type = [("sale_purchase_invoice_refund", "Sincronizar órdenes de venta/compra y facturas/recibos")]

    rule_type = fields.Selection(selection_add=new_rule_type, string="Rule", default="not_synchronize")

    @api.model
    def _find_company_from_partner(self, partner_id):
        company = self.sudo().search([("partner_id", "=", partner_id)], limit=1)
        _logger.critical(company.name)
        return company or False

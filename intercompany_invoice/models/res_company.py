from odoo import api, models, fields, _

new_rule_type = {
        "sale_purchase_invoice_refund": "Sincronizar órdenes de venta/compra y facturas/recibos"
    }
class ResCompany(models.Model):
    _inherit = "res.company"

    rule_type = fields.Selection(selection_add=list(new_rule_type), string="Rule", default="not_synchronize")


    @api.model
    def _find_company_from_partner(self, partner_id):
        company =self.sudo().search(["partner_id", "=", partner_id], limit=1)
        return company or False

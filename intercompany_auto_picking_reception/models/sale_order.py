from odoo import models,fields

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    generated_order = fields.Many2one('purchase.order',string="Orden Generada" )
    def inter_company_create_purchase_order(self, company):
        super().inter_company_create_purchase_order(company)
        for rec in self:
            rec.auto_purchase_order_id = self.env['purchase.order'].sudo().search([('name', '=', rec.client_order_ref)]).id
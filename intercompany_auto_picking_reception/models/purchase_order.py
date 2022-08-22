from odoo import models,fields

class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    generated_order = fields.Many2one('sale.order',string="Orden Generada" )
    def inter_company_create_sale_order(self, company):
        super().inter_company_create_sale_order(company)
        for rec in self:
            rec.auto_sale_order_id = self.env['sale.order'].sudo().search([('name', '=', rec.partner_ref)]).id
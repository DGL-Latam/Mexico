from odoo import models,fields

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    generated_order = fields.Many2one('purchase.order',string="Orden Generada" )
    def inter_company_create_purchase_order(self, company):
        """
        Cuando se crea una orden intercompañia se coloca en el valor de auto_sale_order_id
        la orden de venta relacionda (se hace manulamente una compra se crea una venta y se relacionan por id)
        """
        super().inter_company_create_purchase_order(company)
        for rec in self:
            rec.auto_purchase_order_id = self.env['purchase.order'].sudo().search([('name', '=', rec.client_order_ref)]).id
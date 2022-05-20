from odoo import models,fields
from datetime import timedelta
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    @api.multi
    def _compute_purchased_product_qty(self):
        domain = [
            ('state', 'in', ['purchase', 'done']),
            ('product_id', 'in', self.mapped('id')),
        ]
        PurchaseOrderLines = self.env['purchase.order.line'].search(domain)
        qty = 0
        for ol in PurchaseOrderLines:
            qty += self.calculate_qty(ol.qty_received, ol.product_id,ol.product_uom)
        for product in self:
            if not product.id:
                product.purchased_product_qty = 0.0
                continue
            product.purchased_product_qty = float_round(qty, precision_rounding=product.uom_id.rounding)

        order_lines = self.env['purchase.order.line'].read_group(domain, ['product_id', 'qty_received','product_uom'], ['product_id'])
        for data in order_lines:
            data['product_uom']
        purchased_data = dict([(data['product_id'][0], data['qty_received']) for data in order_lines])
        for product in self:
            product.purchased_product_qty = float_round(purchased_data.get(product.id, 0), precision_rounding=product.uom_id.rounding)
    def calculate_qty(self,qty,product,uom):
        realqty = qty
        if product.uom_id != uom:
            realqty = uom._compute_quantity(qty, product.uom_id)
        return realqty
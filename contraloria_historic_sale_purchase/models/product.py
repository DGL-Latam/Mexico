from odoo import api,models,fields, _
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
            for move in ol.move_ids.filter:
                if move.state in ['done'] and (move.picking_type_id != 2 or move.picking_type_id.sequence_code not in ['out','OUT','DEV','dev'] ):
                    qty = move.product_uom_qty
            
        for product in self:
            if not product.id:
                product.purchased_product_qty = 0.0
                continue
            product.purchased_product_qty = float_round(qty, precision_rounding=product.uom_id.rounding)

    def calculate_qty(self,qty,product,uom):
        realqty = qty
        if product.uom_id != uom:
            realqty = uom._compute_quantity(qty, product.uom_id)
        return realqty
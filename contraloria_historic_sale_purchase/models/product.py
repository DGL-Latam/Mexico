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
            for move in ol.move_ids:
                if move.state in ['done']:
                    if not move.origin_returned_move_id:
                        qty += move.product_uom_qty
                    else:
                        qty -= move.product_uom_qty 
        for product in self:
            if not product.id:
                product.purchased_product_qty = 0.0
                continue
            product.purchased_product_qty = float_round(qty, precision_rounding=product.uom_id.rounding)

    
    @api.multi
    def _compute_sales_count(self):
        r = {}
        if not self.user_has_groups('sales_team.group_sale_salesman'):
            return r
        done_states = self.env['sale.report']._get_done_states()
        domain = [
            ('state', 'in', done_states),
            ('product_id', 'in', self.ids),
        ]
        PurchaseSaleLines = self.env['sale.order.line'].search(domain)
        qty = 0
        for sl in PurchaseSaleLines:
            for move in sl.move_ids:
                if move.state in ['done']:
                    if not move.origin_returned_move_id:
                        qty += move.product_uom_qty
                    else:
                        qty -= move.product_uom_qty
        domain = [
            ('product_id', 'in' , self.ids)
        ]
        bundles = self.env['mrp.bom.line'].search(domain)
        bundleIds = []
        for bundle in bundles:
            bundleIds.append(bundle.id)

        domain = [
            ('state', 'in', ['purchase', 'done']),
            ('product_id', 'in', bundleIds),
        ]
        BundleSOL = self.env['sale.order.line'].search(domain)
        for sl in BundleSOL:
            for move in sl.move_ids:
                if move.state in ['done']:
                    if move.product_id in self.ids:
                        if not move.origin_returned_move_id:
                            qty += move.product_uom_qty
                        else:
                            qty -= move.product_uom_qty
        for product in self:
            product.sales_count = float_round(qty, precision_rounding=product.uom_id.rounding)
        return r

    def calculate_qty(self,qty,product,uom):
        realqty = qty
        if product.uom_id != uom:
            realqty = uom._compute_quantity(qty, product.uom_id)
        return realqty
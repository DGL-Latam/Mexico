from odoo import models


import logging

_logger = logging.getLogger(__name__)

class Picking(models.Model):
    _inherit = "stock.picking"
    
    def button_validate(self):
        action = super().button_validate()
        stock_picking = None
        if self.sale_id:
            self.sudo().sale_logic_int(action)
        elif self.purchase_id:
            self.sudo().purchase_logic_int(action)
        return action
    
    

    
    
    def sale_logic_int(self, action):    
        po = self.sale_id.auto_purchase_order_id
        if not po:
            return
        pickings = po.picking_ids.filtered(lambda x: x.state in ['confirmed','assigned'])
        if len(pickings) == 0:
            return
        to_transfer = {}
        for move in self.move_line_ids_without_package:
            to_transfer[move.product_id.default_code] = move.move_id.product_uom_qty
        picking_to_work = None

        for pick in pickings:
            to_receive = {}
            for move in pick.move_ids_without_package:
                if move.product_id.default_code not in to_transfer:
                    break
                to_receive[move.product_id.default_code] = move.product_uom_qty

            if to_receive == to_transfer:
                picking_to_work = pick
                break
        if not picking_to_work:
            return
        _logger.critical('TO receive')
        _logger.critical(to_receive)
        for line in picking_to_work.move_ids_without_package:
            line.move_line_ids.unlink()
        for move in self.move_line_ids_without_package:
            line = picking_to_work.move_ids_without_package.filtered(lambda x: x.product_id == move.product_id)

            values = {
                    'qty_done' : move.qty_done,
                    'lot_name' : move.lot_id.name ,
                    'product_uom_id' : move.product_uom_id.id,
                    'move_id' : line.id,
                    'location_id' : picking_to_work.location_id.id,
                    'location_dest_id' : picking_to_work.location_dest_id.id,
                    'picking_id' : picking_to_work.id,
                    'product_id' : move.product_id.id,

                }
            _logger.critical(values)
            self.env['stock.move.line'].create(values)
        if type(action) != bool :
            return picking_to_work
        else:
            picking_to_work.button_validate()
        return 
    
    
    def purchase_logic_int(self, action): 
        return
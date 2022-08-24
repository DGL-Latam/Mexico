from odoo import models

class Picking(models.Model):
    _inherit = "stock.picking"
    
    def button_validate(self):
        ctx = dict(self.env.context)
        if 'validate_picking' in ctx and not ctx['validate_picking']:
            return 
        action = super().button_validate()
        to_process = self.env['stock.picking']
        if self.sale_id:
            to_process = self.sudo().sale_logic_int(action)
        elif self.purchase_id:
            to_process = self.sudo().purchase_logic_int(action)
        if type(action) != bool:
            action['context'].pop('quotation_only',None)
            action['context'].pop('default_partner_id',None)
            action['context'].pop('default_origin',None)
            action['context'].pop('default_picking_type_id',None)
            
            action['context']['active_id'] = self.id
            action['context']['allowed_company_ids'] = [self.company_id.id, to_process.company_id.id]
            action['context']['active_ids'] = [self.id, to_process.id]
            action['context']['active_model'] = self._name
            action['context']['active_domain'] = ['|', '|', ['name', 'ilike', self.name], ['origin', 'ilike', self.name], '|', ['name', 'ilike', to_process.name], ['origin', 'ilike', to_process.name]]
            action['context']['button_validate_picking_ids'] = [self.id, to_process.id]
            action['context']['default_pick_ids'] = [(4, self.id), (4, to_process.id)]
        return action
    
    

    
    
    def sale_logic_int(self, action):   
        ctx = dict(self.env.context)
        if 'validate_picking' in ctx and not ctx['validate_picking']:
            return 
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

            self.env['stock.move.line'].create(values)
        picking_to_work.with_context(validate_picking=False).button_validate()
        return picking_to_work
    
    
    def purchase_logic_int(self, action):
        ctx = dict(self.env.context)
        if 'validate_picking' in ctx and not ctx['validate_picking']:
            return 
        so = self.purchase_id.auto_sale_order_id
        if not so:
            return 
        pickings = so.picking_ids.filtered(lambda x: x.state in ['confirmed','assigned'])
        if len(pickings) == 0:
            return
        to_transfer = {}
        for move in self.move_ids_without_package:
            to_transfer[move.product_id.default_code] = move.product_uom_qty

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

        for line in picking_to_work.move_ids_without_package:
            line.move_line_ids.unlink()
        for move in self.move_line_ids_without_package:
            line = picking_to_work.move_ids_without_package.filtered(lambda x: x.product_id == move.product_id)
            
            values = {
                    'qty_done' : move.qty_done,
                    'lot_id' : self.env['stock.production.lot'].sudo().search([('name','=', move.lot_name),('product_id','=',move.product_id.id),('company_id','=',picking_to_work.company_id.id)]).id ,
                    'product_uom_id' : move.product_uom_id.id,
                    'move_id' : line.id,
                    'location_id' : picking_to_work.location_id.id,
                    'location_dest_id' : picking_to_work.location_dest_id.id,
                    'picking_id' : picking_to_work.id,
                    'product_id' : move.product_id.id,

                }
            
            self.env['stock.move.line'].create(values)
        picking_to_work.with_context(validate_picking=False).button_validate()
        return picking_to_work
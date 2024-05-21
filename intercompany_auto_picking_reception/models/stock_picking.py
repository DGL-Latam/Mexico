from odoo import models

class Picking(models.Model):
    _inherit = "stock.picking"
    
    def button_validate(self):
        """
        Se amplia la funcionabilidad del boton de validar en el picking
        para que cuando se valide una recepcion o salida de mercancia en una venta intercompañia
        se valide su contra (recepcion -> salida, salida -> recepcion)
        colocando de forma correspondiente los numeros de serie y lote de los productos
        """
        action = super().button_validate()
        ctx = dict(self.env.context)
        if 'validate_picking' in ctx and not ctx['validate_picking']:
            return  
        #buscamos en la orden de compra o venta relacionada al movimiento que se esta validando si tiene una contra intercompañia
        to_process = self.env['stock.picking']
        if self.sale_id:
            to_process = self.sudo().sale_logic_int(action)
        elif self.purchase_id:
            to_process = self.sudo().purchase_logic_int(action)
        
        """en caso en que la accion que se este regresando no sea de tipo bool actualizamos valores de contexto
        para que en el menu de entrgas parciales se haga lo mismo con ambos movimientos de stock en caso de ser necesario """

        if type(action) != bool and to_process:
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
        """ Si se esta validando el movimiento de inventario de una orden de venta
        se buscara si tiene relacionada la orden de compra (PO), en caso de que la tenga se buscara
        los movimientos de stock relacionados a la PO y se filtraran por una lista que lleva
        los productos y cantidades a procesar, estos tienen que coincidir de forma completa para que
        se lleve acabo la autovalidacion, se agregaron pasos extras para cuando existe dos veces el mismo 
        producto en distintas lineas de movimiento de stock, ya que eso nos indica que son distintos sale.order.lines
        
        TODO : Filtrar tambien que solo se tome en cuenta movimientos de recepcion para que si esta una devolucion pendiente no intente
        auto validarla y mande un error de uso al usuario, salvaria tiempo al equipo de Soporte
        - Colocar un mensaje en el chatter de si se realizo la validacion de la contra o si no encontro para que el equipo de almacen
        sepa si tiene que hacer el paso manualmente

        """
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
            line = picking_to_work.move_ids_without_package.filtered(lambda x: x.product_id == move.product_id and x.product_uom_qty > x.quantity)[0]

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
        """ Si se esta validando el movimiento de inventario de una orden de venta
        se buscara si tiene relacionada la orden de compra (PO), en caso de que la tenga se buscara
        los movimientos de stock relacionados a la PO y se filtraran por una lista que lleva
        los productos y cantidades a procesar, estos tienen que coincidir de forma completa para que
        se lleve acabo la autovalidacion, se agregaron pasos extras para cuando existe dos veces el mismo 
        producto en distintas lineas de movimiento de stock, ya que eso nos indica que son distintos sale.order.lines
        
        TODO : Filtrar tambien que solo se tome en cuenta movimientos de recepcion para que si esta una devolucion pendiente no intente
        auto validarla y mande un error de uso al usuario, salvaria tiempo al equipo de Soporte
        - Colocar un mensaje en el chatter de si se realizo la validacion de la contra o si no encontro para que el equipo de almacen
        sepa si tiene que hacer el paso manualmente
        
        """
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
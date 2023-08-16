from odoo import models,fields,api

import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    @api.depends(
        'product_variant_ids.qty_available',
        'product_variant_ids.virtual_available',
        'product_variant_ids.incoming_qty',
        'product_variant_ids.outgoing_qty',
    )
    def _compute_quantities(self):
        """ Se sobreescribio el metodo para evitar que se calculen las ubicaciones hijas de las ubicaciones
        puestas por el usuario, 
        """
        locations = []
        for company in self.env.companies:
            #recuperamos las ubicaciones puestas por el usuario.
            locations.extend(company.at_hand_stock_locations.ids)
        res = self.with_context(location =  locations,  compute_child = False)._compute_quantities_dict()
        for template in self:
            template.qty_available = res[template.id]['qty_available']
            template.virtual_available = res[template.id]['virtual_available']
            template.incoming_qty = res[template.id]['incoming_qty']
            template.outgoing_qty = res[template.id]['outgoing_qty']
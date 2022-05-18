from odoo import models,fields


class BedBathTransient(models.TransientModel):
    _name = "bedbathtransient"
    _description = "Modelo generado para guardar informacion de forma no persistente para el llenado de la addenda bed bath and beyond"

    x_additional_ref_code = fields.Selection(
        selection = [
            ('AAE', 'Property account'), 
            ('CK', 'Check number'), 
            ('ACE', 'Document number (remission)'), 
            ('ATZ', 'Approval number'), 
            ('AWR', 'Document number that is replaced'), 
            ('ON', 'Order number (buyer)'), 
            ('DQ', 'Merchandise Receipt Folio'), 
            ('IV', 'Invoice Number')
        ],
        string = "Additional Reference Code",
        required = True,        
    )
    x_po_date = fields.Date(
        string = "Date Purchase Order",
        required = True,
        help = "The date of the purchase order.",
    )
    x_additional_reference = fields.Char(
        string = "Additional Reference Number",
        required = True,
    )
    x_order_number = fields.Char(
        string = "Order Number",
        required = True,
        help = "Purchase order number that supports the receipt of merchandise. This number is displayed in the portal.",
    )
    x_invoice_line_ids = fields.Many2many(
        string = "Invoice Lines",
        comodel_name = "account.move.line"
    )

# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'


    def action_post(self):
        res = super().action_post()
        for rec in self:
            rec.invoice_vendor_bill_id = self.env["sale.order"].sudo().search([("name", "=", rec.partner_id)]).id
            self.env["purchase.order"].create_bill()
        return res
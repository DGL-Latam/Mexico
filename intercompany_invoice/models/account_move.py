# -*- coding: utf-8 -*-
from odoo import fields, models, _
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        for record in self:
            company = self.env["res.company"]._find_company_from_partner(record.partner_id.id)

            if company and company.rule_type == 'sale_purchase_invoice_refund' and record.move_type in ['out_invoice', 'out_refund'] :

                sale_orders = self.env['sale.order'].sudo().search([('invoice_ids', 'in', [record.id])])
                purchase_orders = sale_orders.mapped('auto_purchase_order_id')
                bill_view_action = purchase_orders.sudo().with_user(1).with_company(company).with_context({'default_move_type': 'in_invoice'}).action_create_invoice()

                bill = self.env['account.move'].search([('id','=',bill_view_action['res_id'])])

                if not bill:
                    continue
                bill.invoice_date = datetime.today()
        return res

    def _check_duplicate_supplier_reference(self):
        for order in self:
            if not order.company_id:
                continue
            company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
            if company and company.rule_type == 'sale_purchase_invoice_refund':
                continue
            res = super()._check_duplicate_supplier_reference()
        return res
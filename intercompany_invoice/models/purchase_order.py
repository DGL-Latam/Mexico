# -*- coding: utf-8 -*-
from odoo import fields, models, _


class purchase_order(models.Model):
    _inherit = "purchase.order"

    def _prepare_sale_order_data(self):

        res = super(purchase_order, self).button_approve(force=force)
        for order in self:
            # get the company from partner then trigger action of intercompany relation
            company_rec = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company_rec and company_rec.rule_type == 'sale_purchase_invoice_refund' and (not order.auto_generated):
                order.with_user(company_rec.intercompany_user_id).with_context(
                    default_company_id=company_rec.id).with_company(company_rec).inter_company_create_sale_order(company_rec)
        return res

    def action_post_bill(self):
        self.env["account.move"].action_post()
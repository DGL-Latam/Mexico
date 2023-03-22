# -*- coding: utf-8 -*-
from odoo import fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        for rec1 in self:
            rec1.id = self.env["account.move"].search([("state", "=", "draft")], limit=1).id
            for rec2 in self:
                rec2.id = self.env["account.move"].search([("ref", "=", rec1.name)], limit=1).id
                rec2.action_post()



        return res
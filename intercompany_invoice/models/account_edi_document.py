from odoo import models, fields, _, api

import logging
_logger = logging.getLogger(__name__)

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    @api.depends('state')
    def share_xml(self):
        return 
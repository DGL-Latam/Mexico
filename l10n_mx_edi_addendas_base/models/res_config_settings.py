# Part of Odoo. See LICENSE file for full copyright and licensing details.

from os import listdir
from os.path import join

from odoo import fields, models
from odoo.modules import get_module_path
from odoo.tools.convert import convert_file
import logging

_logger = logging.getLogger(__name__)
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    def open_installed_addendas(self):
        return {}

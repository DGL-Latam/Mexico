import logging
import re

from odoo import models, api

_logger = logging.getLogger(__name__)

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'


    def _l10n_mx_edi_get_common_cfdi_values(self, move):
        def format_amount(amount, currency, lang_code = False):
            fmt = "%.{0}f".format(currency.decimal_places)
            langs = [code for code, _ in self.env['res.lang'].get_installed()]
            lang = langs[0]
            if lang_code and lang_code in langs:
                lang = lang_code
            elif self.env.context.get('lang') in langs:
                lang = self.env.context.get('lang')
            elif self.env.user.company_id.partner_id.lang in langs:
                lang = self.env.user.company_id.partner_id.lang

            formatted_amount = lang.format(fmt, currency.round(amount), grouping=True, monetary=True)\
                .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')

            pre = post = u''
            if currency.position == 'before':
                pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
            else:
                post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')

            return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)

        res = super()._l10n_mx_edi_get_common_cfdi_values(move)
        res['format_amount'] = format_amount
        return res


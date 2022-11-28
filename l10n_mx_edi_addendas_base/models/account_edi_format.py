from odoo import models,api
from lxml.objectify import fromstring
from lxml import etree

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    @api.model
    def _l10n_mx_edi_cfdi_append_addenda(self, move, cfdi, addenda):
        ''' Append an additional block to the signed CFDI passed as parameter.
        :param move:    The account.move record.
        :param cfdi:    The invoice's CFDI as a string.
        :param addenda: The addenda to add as a string.
        :return cfdi:   The cfdi including the addenda.
        '''
        folio_serie =  self._l10n_mx_edi_get_serie_and_folio(move)

        addenda_values = {
        'record': move, 
        'cfdi': cfdi, 
        'folio_number': folio_serie['folio_number'], 
        'serie_number':folio_serie['serie_number'],
        'self':self,
        }

        addenda = addenda._render(values=addenda_values).strip()
        if not addenda:
            return cfdi

        cfdi_node = fromstring(cfdi)
        addenda_node = fromstring(addenda)

        # Add a root node Addenda if not specified explicitly by the user.
        if addenda_node.tag != '{http://www.sat.gob.mx/cfd/3}Addenda':
            node = etree.Element(etree.QName('http://www.sat.gob.mx/cfd/3', 'Addenda'))
            node.append(addenda_node)
            addenda_node = node

        cfdi_node.append(addenda_node)
        return etree.tostring(cfdi_node, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    def _get_invoice_edi_content(self, move):
        #OVERRIDE
        if self.code != 'cfdi_3_3':
            return super()._get_invoice_edi_content(move)
        res = self._l10n_mx_edi_export_invoice_cfdi(move)
        addenda = move.partner_id.l10n_mx_edi_addenda or move.partner_id.commercial_partner_id.l10n_mx_edi_addenda
        if addenda:
            res = self._l10n_mx_edi_cfdi_append_addenda(move, res['cfdi_str'], addenda)
        return res

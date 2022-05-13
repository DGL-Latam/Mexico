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
        partner_shipping = move.partner_shipping_id if move.fields_get(['partner_shipping_id']) else move.partner_id.commercial_partner_id if move.partner_id.type != 'invoice' else move.partner_id
        comment = self.env['ir.fields.converter'].text_from_html(html_content=partner_shipping.comment).strip()
        addenda_values = {
        'record': move, 
        'cfdi': cfdi, 
        'folio_number': folio_serie['folio_number'], 
        'serie_number':folio_serie['serie_number'],
        'comment' : comment
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
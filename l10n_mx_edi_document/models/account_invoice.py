# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.tools import float_round
from odoo.exceptions import UserError, ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def xml2record(self):
        """Use the last attachment in the payment (xml) and fill the payment
        data"""
        atts = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ])
        prod_supplier = self.env['product.supplierinfo']
        prod = self.env['product.product']
        sat_code = self.env['l10n_mx_edi.product.sat.code']
        uom_obj = self.env['uom.uom']
        default_account = self.invoice_line_ids.with_context({
            'journal_id': self.journal_id.id, 'type': self.type
        })._default_account()
        for attachment in atts:
            cfdi = attachment.l10n_mx_edi_is_cfdi33()
            if cfdi is False:
                continue
            amount = 0
            currency = self.env['res.currency'].search([
                ('name', '=', cfdi.get('Moneda'))], limit=1)
            self.l10n_mx_edi_set_cfdi_partner(cfdi, currency)
            for rec in cfdi.Conceptos.Concepto:
                name = rec.get('Descripcion', '')
                no_id = rec.get('NoIdentificacion', name)
                uom = rec.get('Unidad', '')
                uom_code = rec.get('ClaveUnidad', '')
                qty = rec.get('Cantidad', '')
                price = rec.get('ValorUnitario', '')
                amount = float(rec.get('Importe', '0.0'))
                supplierinfo = prod_supplier.search([
                    ('name', '=', self.partner_id.id),
                    '|', ('product_name', '=ilike', name),
                    ('product_code', '=ilike', no_id)], limit=1)
                product = supplierinfo.product_tmpl_id.product_variant_id
                product = product or prod.search([
                    '|', ('default_code', '=ilike', no_id),
                    ('name', '=ilike', name)], limit=1)
                account_id = (
                    product.property_account_expense_id.id or
                    product.categ_id.property_account_expense_categ_id.id or
                    default_account)

                discount = 0.0
                if rec.get('Descuento') and amount:
                    discount = (float(rec.get('Descuento', '0.0')) / amount) * 100  # noqa

                domain_uom = [('name', '=ilike', uom)]
                code_sat = sat_code.search([('code', '=', uom_code)], limit=1)
                domain_uom = [('l10n_mx_edi_code_sat_id', '=', code_sat.id)]
                uom_id = uom_obj.with_context(
                    lang='es_MX').search(domain_uom, limit=1)
                # if product_code in self._get_fuel_codes() or \
                #         restaurant_category_id in supplier.category_id:
                #     tax = taxes.get(index)[0] if taxes.get(index, []) else {}
                #     qty = 1.0
                #     price = tax.get('amount') / (tax.get('rate') / 100)
                #     invoice_line_ids.append((0, 0, {
                #         'account_id': account_id,
                #         'name':  _('Non Deductible') if
                #         restaurant_category_id in supplier.category_id else
                #         _('FUEL - IEPS'),
                #         'quantity': qty,
                #         'uom_id': uom_id.id,
                #         'price_unit': float(rec.get('Importe', 0)) - price,
                #     }))
                self.write({'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'account_id': account_id,
                    'name': name,
                    'quantity': float(qty),
                    'uom_id': uom_id.id,
                    'invoice_line_tax_ids': self.get_line_taxes(rec),
                    'price_unit': float(price),
                    'discount': discount,
                })]})

            cfdi_related = ''
            if hasattr(cfdi, 'CfdiRelacionados'):
                cfdi_related = '%s|%s' % (
                    cfdi.CfdiRelacionados.get('TipoRelacion'),
                    ','.join([rel.get('UUID') for
                              rel in cfdi.CfdiRelacionados.CfdiRelacionado]))
            invoice_data = {
                'reference': '%s%s' % (cfdi.get('Serie'), cfdi.get('Folio')),
                'date_invoice': cfdi.get('Fecha').split('T')[0],
                'currency_id': currency.id,
                'l10n_mx_edi_time_invoice': cfdi.get('Fecha').split('T')[1],
                'l10n_mx_edi_origin': cfdi_related,
            }
            self.write(invoice_data)
            try:
                self.with_context(
                    states2omit={'cancel'}).l10n_mx_edi_cfdi_name = attachment.name  # noqa
            except ValidationError as exe:
                self.message_post(body=_(
                    '<b>Error on invoice validation </b><br/>%s') % exe.name)
                return self
            self.l10n_mx_edi_pac_status = 'signed'
            self.compute_taxes()
            try:
                self.action_invoice_open()
            except (UserError, ValidationError) as exe:
                self.message_post(body=_(
                    '<b>Error on invoice validation </b><br/>%s') % exe.name)
                return self
            if cfdi_related.split('|')[0] in ('01', '02', '03'):
                move = self.move_id.line_ids.filtered(
                    lambda line: line.account_id.internal_type in (
                        'payable', 'receivable'))
                for uuid in self.l10n_mx_edi_origin.split('|')[1].split(','):
                    inv = self.search([('l10n_mx_edi_cfdi_uuid', '=', uuid.upper().strip())])
                    if not inv:
                        continue
                    inv.register_payment(move)
        return self

    @api.multi
    def l10n_mx_edi_set_cfdi_partner(self, cfdi, currency):
        self.ensure_one()
        partner = self.env['res.partner']
        domain = []
        partner_cfdi = {}
        if self.type in ('out_invoice', 'out_refund'):
            partner_cfdi = cfdi.Receptor
            domain.append(('vat', '=', partner_cfdi.get('Rfc')))
            domain.append(('customer', '=', True))
        elif self.type in ('in_invoice', 'in_refund'):
            partner_cfdi = cfdi.Emisor
            domain.append(('vat', '=', partner_cfdi.get('Rfc')))
            domain.append(('supplier', '=', True))
        domain.append(('is_company', '=', True))
        cfdi_partner = partner.search(domain, limit=1)
        currency_field = 'property_purchase_currency_id' in partner._fields
        if currency_field:
            domain.append(('property_purchase_currency_id', '=', currency.id))
        if currency_field and not cfdi_partner:
            domain.pop()
            cfdi_partner = partner.search(domain, limit=1)
        if not cfdi_partner:
            domain.pop()
            cfdi_partner = partner.search(domain, limit=1)
        if not cfdi_partner:
            domain.pop()
            cfdi_partner = partner.search(domain, limit=1)
        if not cfdi_partner:
            cfdi_partner = partner.create({
                'name': partner_cfdi.get('Nombre'),
                'vat': partner_cfdi.get('Rfc'),
                'country_id': False,  # TODO
            })
            cfdi_partner.message_post(body=_(
                'This record was generated from DMS'))
        self.partner_id = cfdi_partner
        self._onchange_partner_id()

    def get_line_taxes(self, line):
        taxes_list = []
        if not hasattr(line, 'Impuestos'):
            return taxes_list
        taxes_xml = line.Impuestos
        if hasattr(taxes_xml, 'Traslados'):
            taxes = self.collect_taxes(taxes_xml.Traslados.Traslado)
        if hasattr(taxes_xml, 'Retenciones'):
            taxes += self.collect_taxes(taxes_xml.Retenciones.Retencion)
        for tax in taxes:
            tax_group_id = self.env['account.tax.group'].search(
                [('name', 'ilike', tax['tax'])])
            domain = [
                ('tax_group_id', 'in', tax_group_id.ids),
                ('type_tax_use', '=', 'purchase' if 'in_' in self.type else 'sale')]  # noqa
            if -10.67 <= tax['rate'] <= -10.66:
                domain.append(('amount', '<=', -10.66))
                domain.append(('amount', '>=', -10.67))
            else:
                domain.append(('amount', '=', tax['rate']))
            name = '%s(%s%%)' % (tax['tax'], tax['rate'])

            tax_get = self.env['account.tax'].search(domain, limit=1)
            if not tax_get:
                self.message_post(body=_('The tax %s cannot be found') % name)
                continue
            if not tax_get.account_id.id:
                self.message_post(body=_(
                    'Please configure the tax account in the tax %s') % name)
                continue
            taxes_list.append((4, tax_get.id))
        return taxes_list

    @staticmethod
    def collect_taxes(taxes_xml):
        """ Get tax data of the Impuesto node of the xml and return
        dictionary with taxes datas
        :param taxes_xml: Impuesto node of xml
        :type taxes_xml: etree
        :return: A list with the taxes data
        :rtype: list
        """
        taxes = []
        tax_codes = {'001': 'ISR', '002': 'IVA', '003': 'IEPS'}
        for rec in taxes_xml:
            tax_xml = rec.get('Impuesto', '')
            tax_xml = tax_codes.get(tax_xml, tax_xml)
            amount_xml = float(rec.get('Importe', '0.0'))
            rate_xml = float_round(
                float(rec.get('TasaOCuota', '0.0')) * 100, 4)
            if 'Retenciones' in rec.getparent().tag:
                tax_xml = tax_xml
                amount_xml = amount_xml * -1
                rate_xml = rate_xml * -1

            taxes.append({'rate': rate_xml, 'tax': tax_xml,
                          'amount': amount_xml})
        return taxes

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import base64
import logging

from lxml import objectify

from odoo import _, api, models, fields
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def check_functional(self):
        if not self.l10n_mx_edi_analysis or \
                not json.loads(self.l10n_mx_edi_analysis).get('payments'):
            self.sudo().message_post(
                body=_("This payment is not possible to verify functionally "
                       "because there is not CFDI associated yet, "
                       "please add the xml"))
            return
        errors = self.functional_errors()
        result = errors.copy()
        for error in errors:
            if not errors[error].get('check')():
                continue
            result.pop(error)
        message = self._render_email_check(result)
        self.write({'l10n_mx_edi_functional': 'fail' if result else 'ok',
                    'l10n_mx_edi_functional_details': ''.join(message),
                    'l10n_mx_edi_functionally_approved': bool(not result)})
        return errors

    def functional1(self):
        """Check if the cfdi is generated for this company"""
        if self.partner_type == 'customer':
            return self.l10n_mx_edi_rfc == self.company_id.partner_id.vat
        return self.l10n_mx_edi_received_rfc == self.company_id.partner_id.vat

    def functional2(self):
        uuids = self.mapped('l10n_mx_edi_uuid')
        return uuids and not bool(self.sudo().search(
            [('l10n_mx_edi_uuid', 'in', uuids), ('id', 'not in', self.ids),
             ('l10n_mx_edi_uuid', '!=', False)]))

    def functional3(self):
        return self.partner_id

    def functional4(self):
        pay_currency = json.loads(
            self.l10n_mx_edi_analysis).get('payments')[0].get('currency')
        active_currency = self.env['res.currency'].search(
            [('active', '=', True)])
        return pay_currency in active_currency.mapped('name')

    def functional5(self):
        return True

    def functional6(self):
        return bool(self.mapped('l10n_mx_edi_uuid'))

    def functional7(self):
        references = self.mapped('payment_reference')
        partners = self.mapped('partner_id').ids
        return not bool(self.env['account.payment'].sudo().search(
            [('payment_reference', 'in', references),
             ('id', 'not in', self.ids),
             ('payment_reference', '!=', False),
             ('partner_id', 'in', partners)]))

    def functional8(self):
        return len(json.loads(
            self.l10n_mx_edi_analysis).get('payments')) == 1

    def functional9(self):
        return float_compare(json.loads(self.l10n_mx_edi_analysis).get(
            'total'), self.amount, precision_digits=2) == 0

    def functional10(self):
        uuids = json.loads(
            self.l10n_mx_edi_analysis).get('payments')[0].get('doc_ids')
        for uuid in uuids:
            if uuid not in self.invoice_ids.mapped('l10n_mx_edi_cfdi_uuid'):
                return False
        return True

    def functional_errors(self):
        return {
            1: {
                "title": _("Incorrect RFC"),
                "title_ok": _("Correct RFC"),
                "message": _(
                    "The RFC of this payment is not for this company, maybe "
                    "your customer made a mistake generating the CFDI or it "
                    "simply was sent by mistake."),
                "message_ok": _("The RFC used on this CFDI is the one on "
                                "this company"),
                "check": self.functional1,
            },
            2: {
                "title": _("UUID Duplicated on payments"),
                "title_ok": _("New UUID"),
                "message": _("The XML UUID belongs to other payment already "
                             "loaded on the system."),
                "message_ok": _("No other payment with this uuid has been "
                                "declared in the system"),
                "check": self.functional2,
            },
            3: {
                "title": _("We never sold to this customer."),
                "title_ok": _("This customer has been used  before"),
                "message": _("The administrative team will need to check if "
                             "payments from this customer are valid"),
                "message_ok": _("We have old payments from this customer, stay"
                                "in touch if we need something extra."),
                "check": self.functional3,
            },
            4: {
                "title": "Currency Disabled",
                "title_ok": "Currency Active",
                "message": _("The currency in the XML was not found or is "
                             "disabled"),
                "message_ok": _("The currency declared in the CFDI is valid "
                                "and is configured properly"),
                "check": self.functional4,
            },
            5: {
                "title": "Company Address do not match",
                "title_ok": "Address looks Ok",
                "message": _(
                    "The zip code used in the payment is not the same we have"
                    " in in the company or in the offices (payment address in"
                    " the contacts of the company)"),
                "message_ok": _("We reviewed if the zip code of the receiver "
                                "company is the same than this company"),
                "check": self.functional5,
            },
            6: {
                "title": "It is not deductible.",
                "title_ok": "This has a valid payment",
                "message": _("This payment is not deductible, it looks like "
                             "an payment without valid CFDI"),
                "message_ok": _("I checked if there is a valid xml in the "
                                "payment attached"),
                "check": self.functional6,
            },
            7: {
                "title": _("This payment looks duplicated"),
                "title_ok": _("Payment reference unique"),
                "message": _("This payment reference was loaded for this "
                             "partner payment reference belongs to other "
                             "invoice of the same partner."),
                "message_ok": _("The reference (folio/serie) is first time we "
                                "see it in this system"),
                "check": self.functional7,
            },
            8: {
                "title": _("More than 1 CFDI"),
                "title_ok": _("Only 1 CFDI"),
                "message": _("It looks like you tried to create a payment "
                             "with more than 1 cfdi, please send 1 email per "
                             "cfdi or split them manually throught odoo"),
                "message_ok": _("Ok"),
                "check": self.functional8,
            },
            9: {
                "title": _("Different payment amount"),
                "title_ok": _("Same payment amount"),
                "message": _("It looks like you tried to create a payment "
                             "with amount different than the cfdi amount"),
                "message_ok": _("Ok"),
                "check": self.functional9,
            },
            10: {
                "title": _("UUID of invoice not found"),
                "title_ok": _("UUID of invoice found"),
                "message": _("The UUID of the related document to payment "
                             "not found on the related invoices to payment"),
                "message_ok": _("The UUID of the related document to payment "
                                "found on the related invoices to payment"),
                "check": self.functional10,
            },
        }

    @staticmethod
    def _remove_method(element):
        """check method is not serializable"""
        element.pop('check')
        return element

    def _render_email_check(self, result):
        """If something fail (which frequently will not be all in or all out
        prepare a proper output in order to deliver a readable message for the
        user

        :params: result Json with all errors that not passed the check
                        'ok': {code: {'title': 'Subject',
                                      'message', 'Message'}
                        'fail': {code: {'title': 'Subject',
                                        'message', 'Message'}
        """
        ok = {k: self._remove_method(v) for (k, v)
              in self.functional_errors().items() if k not in result}
        fail = {k: self._remove_method(v) for (k, v) in result.items()}
        return json.dumps({"ok": ok, "fail": fail}, skipkeys='check')

    @api.multi
    def check_fiscal(self):
        atts = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ])

        # In order to discard all CFDI at once that will not be checked and
        # subtract them from the recordset to avoid walk for all of them
        # one by one when heavy check comes forward.
        xmls = atts
        xmls_cache = {}
        for att in atts:
            cfdi = att.l10n_mx_edi_is_cfdi33()
            if not cfdi:
                xmls -= att
                continue
            uuid = self.env['account.invoice'].l10n_mx_edi_get_tfd_etree(
                cfdi).get('UUID')
            xmls_cache[att.id] = uuid
        for payment in self:
            # Now that I have a clear domain of which attachments to check I
            # will read the content to jsonify a compound of payments, now
            # the variable atts contains only the attachments that are actual
            # payments and can be parsed.
            res = []
            for att in xmls.sudo().filtered(
                    lambda inv: inv.res_id == payment.id):
                xml = objectify.fromstring(base64.b64decode(att.datas))
                currency = xml.get('Moneda', '')
                cfdi_related = []
                if hasattr(xml, 'CfdiRelacionados'):
                    for doc in xml.CfdiRelacionados.CfdiRelacionado:
                        cfdi_related.append(doc.get('UUID'))
                data = {
                    'cfdi_related': cfdi_related,
                    'id': att.id,
                    'date': xml.get('Fecha', ' ').replace('T', ' '),
                    'document_type': xml.get('TipoDeComprobante', ' '),
                    'number': xml.get('Folio', ''),
                    'serie': xml.get('Serie', ''),
                    'address': xml.get('LugarExpedicion', ' '),
                    'name': xml.Emisor.get('Nombre', ' '),
                    'fp': xml.Emisor.get('RegimenFiscal', ' '),
                    'sent_by': xml.Emisor.get('Rfc', ' '),
                    'received_by': xml.Receptor.get('Rfc', ' '),
                    'subtotal': float(xml.get('SubTotal', '0.0')),
                    'total': float(xml.get('Total', 0.00)),
                    'use_cfdi': xml.Receptor.get('UsoCFDI', ''),
                    'uuid': xmls_cache.get(att.id),
                }
                payment_comp = self.l10n_mx_edi_get_payment_etree(xml)
                payment_lines = []
                doc_ids = []
                payment_total = 0.0
                for payment_line in payment_comp:
                    if not payment_total:
                        payment_total = float(
                            payment_line.getparent().get('Monto'))
                    payment_amount = float(
                        payment_line.get('ImpPagado')
                        or payment_line.get('ImpSaldoAnt', '0.0'))
                    payment_lines.append({
                        'doc_id': payment_line.get('IdDocumento', ''),
                        'serie': payment_line.get('Serie', ''),
                        'number': payment_line.get('Folio', ''),
                        'pay_way': payment_line.get('MetodoDePagoDR', ' '),
                        'currency': payment_line.get('MonedaDR', ' '),
                        'rate': float(payment_line.get('TipoCambioDR', '1.0')),
                        'amount': payment_amount,
                    })
                    currency = payment_line.get('MonedaDR', '')
                    doc_ids.append(payment_line.get('IdDocumento', ''))
                data.update({
                    'currency': currency,
                    'doc_ids': doc_ids,
                    'payment_lines': payment_lines,
                    'payment_total': payment_total})
                res.append(data)
            # Now I save such analysis in a json in order to render it
            # properly in the payments view.
            if not res:
                _logger.info(
                    'Nothing fiscally valid on payment: %s' % payment.id)
                return {}
            total = sum([i['payment_total'] for i in res])
            uuid = ', '.join([i['uuid'] for i in res])
            rfc = ', '.join([i['sent_by'] for i in res])
            received_rfc = ', '.join([i['received_by'] for i in res])
            date = [i['date'] for i in res][0]
            references = ', '.join(['%s/%s' % (i['serie'], i['number'])
                                    for i in res])
            payment.update({
                'l10n_mx_edi_analysis': json.dumps({
                    'payments': res,
                    'total': total,
                }),
                'payment_reference': references,
                'l10n_mx_edi_date': date,
                'l10n_mx_edi_uuid': uuid,
                'l10n_mx_edi_rfc': rfc,
                'l10n_mx_edi_received_rfc': received_rfc,
            })
            payment.l10n_mx_edi_fiscally_approved = True

    l10n_mx_edi_rfc = fields.Text("Emitter")
    l10n_mx_edi_received_rfc = fields.Text("Received By")
    l10n_mx_edi_uuid = fields.Text(
        "UUID", track_visibility='onchange',
        help="UUID of the xml's attached comma separated if more than one.")

    l10n_mx_edi_date = fields.Date("Date (att)", track_visibility='onchange',
                                   help="Date on the CFDI attached [If 1 if "
                                        "several we will need to split them]")
    l10n_mx_edi_analysis = fields.Text(
        "Analysis", copy=False, track_visibility='onchange',
        help="See in json (and future with a fancy widget) the summary of the"
             " test run and their result [Per fiscal test]")
    l10n_mx_edi_functionally_approved = fields.Boolean(
        "Functionally Approved", copy=False,
        help="Comply with the functional checks?", track_visibility='onchange',
        default=False, readonly=1, force_save=1
    )
    l10n_mx_edi_fiscally_approved = fields.Boolean(
        "Fiscally Approved", copy=False,
        help="Comply with the fiscal checks?", track_visibility='onchange',
        default=False, readonly=1, force_save=1
    )
    l10n_mx_edi_functional_details = fields.Text(
        'Functional Details', copy=False, track_visibility="onchange",
        help="See in json (and future with a fancy widget) the summary of the"
             " test run and their result [Per functional test]")
    l10n_mx_edi_functional = fields.Selection(
        selection=[
            ('undefined', 'Not checked yet'),
            ('fail', 'Something failed, please check the message log'),
            ('ok', 'All the functional checks Ok!'),
            ('error', 'Trying to check occurred an error, check the log'),
        ],
        string='Functional status',
        help="Inform the functional status regarding other data in the system",
        readonly=True,
        copy=False,
        required=True,
        track_visibility='onchange',
        default='undefined'
    )
    l10n_mx_edi_functional_details_html = fields.Html(
        "Functional", compute="_compute_functional_details_html")

    @api.multi
    def validate_checks(self):
        for rec in self:
            rec.check_fiscal()
            rec.check_functional()
            if not rec.l10n_mx_edi_fiscally_approved or not rec.l10n_mx_edi_functionally_approved: # noqa
                continue
            rec.l10n_mx_edi_merge_cfdi()
            rec.l10n_mx_edi_update_sat_status()

    def l10n_mx_edi_merge_cfdi(self):
        attachment = self.env['ir.attachment']
        for record in self:
            att_id = json.loads(record.l10n_mx_edi_analysis).get(
                'payments')[0].get('id')
            attachment = attachment.browse(att_id)
            record.write({
                'l10n_mx_edi_cfdi_name': attachment.name,
                'l10n_mx_edi_pac_status': 'signed',
            })

    def l10n_mx_edi_force_approved(self):
        """Allow force the CFDI validations, to allow get the fiscal data"""
        self.write({'l10n_mx_edi_functionally_approved': True})
        self.l10n_mx_edi_merge_cfdi()
        self.l10n_mx_edi_update_sat_status()

    def _compute_functional_details_html(self):
        for payment in self:
            payment.l10n_mx_edi_functional_details_html = self.json2qweb(
                payment.l10n_mx_edi_functional_details
            )

    def json2qweb(self, json_input=None):
        if not json_input:
            return False
        values = json.loads(json_input)
        result = {**values.get('ok', {}), **values.get('fail', {})}
        template = self.env.ref(
            'l10n_mx_edi_document.payment_checks_content')
        sorted_keys = sorted([int(k) for k in result.keys()])
        qcontext = {
            'animate': self.env.context.get('animate'),
            'sorted_keys': sorted_keys,
            'messages': result,
            'failed': values.get('fail', {}),
            'succeeded': values.get('ok', {}),
        }
        return self.env['ir.qweb'].render(template.id, qcontext)

    @api.multi
    def xml2record(self):
        """Use the last attachment in the payment (xml) and fill the payment
        data"""
        atts = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ])
        avoid_create = self.env['ir.config_parameter'].sudo().get_param(
            'mexico_document_avoid_create_payment')
        incorrect_folder = self.env.ref(
            'l10n_mx_edi_document.documents_cfdi_not_found_folder', False)
        rule_tc = self.env.ref('documents.documents_Finance_validate_tr')
        for attachment in atts:
            cfdi = attachment.l10n_mx_edi_is_cfdi33()
            if cfdi is False:
                continue
            amount = 0
            currency = self.env['res.currency']
            invoices = self.env['account.invoice']
            for elem in self.l10n_mx_edi_get_payment_etree(cfdi):
                parent = elem.getparent()
                if not amount:
                    amount += float(parent.get('Monto'))
                payment_method = self.env['l10n_mx_edi.payment.method'].search(
                    [('code', '=', parent.get('FormaDePagoP'))], limit=1)
                currency = currency.search([
                    ('name', '=', parent.get('MonedaP'))], limit=1)
                invoices |= invoices.search([
                    ('l10n_mx_edi_cfdi_uuid', '=', elem.get('IdDocumento').upper().strip())])
            payment_data = {
                'amount': amount,
                'l10n_mx_edi_payment_method_id': payment_method.id,
                'payment_date': cfdi.get('Fecha').split('T')[0],
                'l10n_mx_edi_time_payment': cfdi.get('Fecha').split('T')[1],
                'invoice_ids': [],
                'currency_id': currency.id,
                'uuid': invoices.l10n_mx_edi_get_tfd_etree(cfdi).get('UUID'),
            }
            payment_match = self.l10n_mx_edi_payment_match(
                payment_data, invoices)
            if payment_match:
                payment_match.l10n_mx_edi_cfdi_name = attachment.name
                payment_match.l10n_mx_edi_pac_status = 'signed'
                return payment_match
            if avoid_create:
                attachment.res_model = False
                attachment.res_id = False
                attachment.tag_ids = False
                rule_tc.apply_actions(attachment.ids)
                attachment.folder_id = incorrect_folder
                self.unlink()
                continue
            self.l10n_mx_edi_set_cfdi_partner(cfdi, currency)
            del payment_data['uuid']
            self.write(payment_data)
            self.l10n_mx_edi_cfdi_name = attachment.name
            self.l10n_mx_edi_pac_status = 'signed'
            self.post()
            move = self.move_line_ids.filtered(
                lambda line: line.account_id.internal_type != 'liquidity')
            for inv in invoices:
                inv.register_payment(move)
        return self.exists()

    @api.multi
    def l10n_mx_edi_payment_match(self, payment_data, invoices):
        """Search a payment with the same data that payment_data and merge with
        it, to avoid 2 payments with the same data."""
        payments = [payment._get_payments_vals() for payment in invoices]
        payments = [payment[0].get(
            'account_payment_id') for payment in payments if payment]
        payments = self.search([('id', 'in', payments)])
        for payment in payments:
            uuid = not payment.l10n_mx_edi_cfdi_uuid or payment_data.get('uuid') == payment.l10n_mx_edi_cfdi_uuid  # noqa
            if float_compare(payment_data['amount'], payment.amount, precision_digits=0) == 0 and uuid:  # noqa
                payment.message_post(body=_(
                    'The CFDI attached to was assigned with DMS.'))
                self.env['ir.attachment'].search([
                    ('res_id', '=', self.id),
                    ('res_model', '=', self._name)]).res_id = payment.id
                self.unlink()
                return payment
        return False

    @api.multi
    def l10n_mx_edi_set_cfdi_partner(self, cfdi, currency):
        # TODO - make method generic
        self.ensure_one()
        partner = self.env['res.partner']
        domain = []
        partner_cfdi = {}
        if self.payment_type == 'inbound':
            partner_cfdi = cfdi.Receptor
            domain.append(('vat', '=', partner_cfdi.get('Rfc')))
            domain.append(('customer', '=', True))
        elif self.payment_type == 'outbound':
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

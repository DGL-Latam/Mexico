# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from os.path import join
from odoo.tools import misc

from openerp.tests.common import TransactionCase


class Xml2Record(TransactionCase):

    def setUp(self):
        super(Xml2Record, self).setUp()
        self.rule = self.env.ref('l10n_mx_edi_document.mexican_document_rule')
        self.invoice_xml = misc.file_open(join(
            'l10n_mx_edi_document', 'tests', 'invoice.xml')).read().encode(
                'UTF-8')
        self.payment_xml = misc.file_open(join(
            'l10n_mx_edi_document', 'tests', 'payment.xml')).read().encode(
                'UTF-8')

    def test_invoice_payment(self):
        """The invoice must be generated based in the payment, after the
        payment must be reconciled with the invoice"""
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.invoice_xml),
            'datas_fname': 'invoice.xml',
            'description': 'Mexican invoice',
        })
        invoice = self.rule.create_record(attachment).get('res_id')
        attachment = attachment.create({
            'name': 'payment.xml',
            'datas': base64.b64encode(self.payment_xml),
            'datas_fname': 'payment.xml',
            'description': 'Mexican payment',
        })
        self.rule.create_record(attachment)
        self.assertEquals(
            self.env['account.invoice'].browse(invoice).state, 'paid',
            'Invoice not paid with the attachment for the payment')

    def test_payment_existent(self):
        """If the payment is found, not must be created a new."""
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.invoice_xml),
            'datas_fname': 'invoice.xml',
            'description': 'Mexican invoice',
        })
        invoice = self.rule.create_record(attachment).get('res_id')
        invoice = self.env['account.invoice'].browse(invoice)
        ctx = {'active_model': 'account.invoice', 'active_ids': invoice.ids}
        self.bank_journal = self.env['account.journal'].search([
            ('type', '=', 'bank')], limit=1)
        register_payments = self.env['account.register.payments'].with_context(
            ctx).create({
                'payment_date': invoice.date_invoice,
                'payment_method_id': self.env.ref(
                    "account.account_payment_method_manual_in").id,
                'journal_id': self.bank_journal.id,
                'communication': invoice.number,
                'amount': invoice.amount_total, })
        payment = register_payments.create_payments()
        payment = self.env['account.payment'].search(payment.get('domain', []))
        attachment = attachment.create({
            'name': 'payment.xml',
            'datas': base64.b64encode(self.payment_xml),
            'datas_fname': 'payment.xml',
            'description': 'Mexican payment',
        })
        new_payment = self.rule.create_record(attachment).get('res_id')
        self.assertEquals(
            payment.id, new_payment,
            'A new payment was created, that is incorrect')

    def test_payment_not_existent(self):
        """2 payments created."""
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.invoice_xml),
            'datas_fname': 'invoice.xml',
            'description': 'Mexican invoice',
        })
        invoice = self.rule.create_record(attachment).get('res_id')
        attachment = attachment.create({
            'name': 'payment.xml',
            'datas': base64.b64encode(self.payment_xml),
            'datas_fname': 'payment.xml',
            'description': 'Mexican payment',
        })
        payment = self.rule.create_record(attachment).get('res_id')
        new_xml = self.payment_xml.replace(b'UUID="0', b'UUID="1')
        attachment = attachment.create({
            'name': 'payment.xml',
            'datas': base64.b64encode(new_xml),
            'datas_fname': 'payment.xml',
            'description': 'Mexican payment',
        })
        new_payment = self.rule.create_record(attachment).get('res_id')
        self.assertNotEquals(
            payment, new_payment,
            'Both payments are the same')
        self.assertEquals(
            self.env['account.invoice'].browse(invoice).state, 'paid',
            'Invoice was not paid')

    def test_payment_not_created(self):
        """Avoid payment creation."""
        self.env['ir.config_parameter'].create({
            'key': 'mexico_document_avoid_create_payment',
            'value': True})
        attachment = self.env['ir.attachment'].create({
            'name': 'payment.xml',
            'datas': base64.b64encode(self.payment_xml),
            'datas_fname': 'payment.xml',
            'description': 'Mexican payment',
        })
        payment = self.rule.create_record(attachment).get('res_id')
        self.assertFalse(
            payment, 'The payment was created with the system parameter')

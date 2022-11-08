from odoo import models, fields, _

import base64

from lxml import etree
from datetime import datetime


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _is_compatible_with_journal(self, journal):
        # TO OVERRIDE
        self.ensure_one()
        return journal.type in  ['sale','general']

    def _check_payslip_configuration(self, payslip):
        errors = []

        return errors

    def _l10n_mx_edi_get_payroll_template(self):
        return 'l10n_mx_edi_nomina.nomina12'

    def _l10n_mx_edi_export_payroll_cfdi(self,move):
        ''' Create the CFDI attachment for the journal entry passed as parameter being a payroll used to pay employees
        
        :param move: an account.move record
        :return: a dictionary with one of the following key:
        + cfdi_str : a string of the unsigned cfdi of the invoice
        + error:    a error if the cfdi was not successfully generated
        '''

        cfdi_values = self._l10n_mx_edi_get_payroll_cfdi_values(move)
        qweb_template = self._l10n_mx_edi_get_payroll_template()
        cfdi = self.env['ir.qweb']._render(qweb_template, cfdi_values)
        decoded_cfdi_values = move._l10n_mx_edi_decode_cfdi(cfdi_data = cfdi)
        cfdi_cadena_crypted = cfdi_values['certificate'].sudo().get_encrypted_cadena(decoded_cfdi_values['cadena'])
        decoded_cfdi_values['cfdi_node'].attrib['Sello'] = cfdi_cadena_crypted

        return {
            'cfdi_str' : etree.tostring(decoded_cfdi_values['cfdi_node'], pretty_print=True, xml_declaration=True, encoding='UTF-8'),
        }
    
    def _l10n_mx_edi_post_payroll_pac(self, move, exported):
        pac_name = move.company_id.l10n_mx_edi_pac
        credentials = getattr(self, '_l10n_mx_edi_get_%s_credentials' % pac_name)(move)
        if credentials.get('errors'):
            return {
                'error': self._l10n_mx_edi_format_error_message(_("PAC authentification error:"), credentials['errors']),
            }

        res = getattr(self, '_l10n_mx_edi_%s_sign' % pac_name)(move,credentials, exported['cfdi_str'])
        if res.get('errors'):
            return {
                'error': self._l10n_mx_edi_format_error_message(_("PAC failed to sign the CFDI:"), res['errors']),
            }

        return res

    def _l10n_mx_edi_xml_payroll_content(self, payroll):
        return self._l10n_mx_edi_export_payroll_cfdi(payroll).get('cfdi_str')

    def _get_move_applicability(self, move):
        self.ensure_one()
        
        if self.code != 'cfdi_3_3':
            return super()._get_move_applicability(move)

        if move.country_code != 'MX':
            return None
        
        if move.move_type == 'entry' and move.company_id.currency_id.name == 'MXN':
            return {
                'post': self._l10n_mx_edi_post_payroll,
                'cancel': self._l10n_mx_edi_cancel_payroll,
                'edi_content': self._l10n_mx_edi_xml_payroll_content,
            }
        return super()._get_move_applicability(move)

    def _l10n_mx_edi_post_payroll(self, payrolls):

        edi_result = super()._post_invoice_edi(payrolls)
        if self.code != 'cfdi_3_3':
            return edi_result
        for payroll in payrolls:
            
            errors = self._l10n_mx_edi_check_configuration(payroll)
            if errors:
                edi_result[payroll] = {
                    'error' : self._l10n_mx_edi_format_error_message(_("Invalid configuration:"), errors),
                }
                continue
            res = self._l10n_mx_edi_export_payroll_cfdi(payroll)
            if res.get('error'):
                edi_result[payroll] = {
                    'error': self._l10n_mx_edi_format_error_message(_("Failure during the generation of the CFDI:"), res['errors']),
                }
                continue

            res = self._l10n_mx_edi_post_payroll_pac(payroll, res)
            if res.get('error'):
                edi_result[payroll] = res
                continue

            cfdi_signed = res['cfdi_signed'] if res['cfdi_encoding'] == 'base64' else base64.encodebytes(res['cfdi_signed'])
            cfdi_filename = f'{payroll.journal_id.code}-{payroll.name}-MX-Payroll-10.xml'.replace('/', '')

            cfdi_attachment = self.env['ir.attachment'].create({
                'name' : cfdi_filename,
                'res_id' : payroll.id,
                'res_model' : payroll._name,
                'type': 'binary',
                'datas' : cfdi_signed,
                'mimetype' : 'application/xml',
                'description' : _('Mexican payroll CFDI generated for the %s document.', payroll.name),
            })
            edi_result = {payroll : {'success' : True, 'attachment': cfdi_attachment}}

            message = _("The CFDI document has been successfully signed.")
            payroll.message_post(body=message, attachment_ids=cfdi_attachment.ids)

        return edi_result

    def _l10n_mx_edi_cancel_payroll(self, payroll):
        errors = self._l10n_mx_edi_check_configuration(payroll)
        if errors: 
            return {payroll : {'error': self._l10n_mx_edi_format_error_message(_("Invalid configuration:"), errors)}}

        pac_name = payroll.company_id.l10n_mx_edi_pac

        credentials = getattr(self, '_l10n_mx_edi_get_%s_credentials' % pac_name)(payroll.company_id)
        if credentials.get('errors'):
            return { payroll: {'error': self._l10n_mx_edi_format_error_message(_("PAC authentification error:"), credentials['errors'])}}

        uuid_replace = payroll.l10n_mx_edi_cancel_move_id.ñ10n_mx_edi_cfdi_uuid
        res = getattr(self, '_l10n_mx_edi_%s_cancel' % pac_name)(payroll.l10n_mx_edi_cfdi_uuid, payroll.company_id,
                                                                 credentials, uuid_replace=uuid_replace)
        if res.get('errors'):
            return {payroll: {'error': self._l10n_mx_edi_format_error_message(_("PAC failed to cancel the CFDI:"), res['errors'])}}

        edi_result = {payroll: res}

        # == Chatter ==
        message = _("The CFDI document has been successfully cancelled.")
        payroll.message_post(body=message)

        return edi_result

    def _l10n_mx_edi_get_payroll_cfdi_values(self, payroll):
        cfdi_date = datetime.combine(
            fields.Datetime.from_string(payroll.invoice_date),
            payroll.l10n_mx_edi_post_time.time(),
        ).strftime('%Y-%m-%dT%H:%M:%S')
        deductionVal = 0
        for ded in payroll.payslip_id.line_ids.filtered(lambda x: x.category_id.code == 'DED'):
            deductionVal += ded.total
        otherVal = 0
        for other in payroll.payslip_id.line_ids.filtered(lambda x: x.category_id.code in ['ALW','OTH','COMP']):
            otherVal += other.total
        cfdi_values = {
            **payroll._prepare_edi_vals_to_export(),
            **self._l10n_mx_edi_get_common_cfdi_values(payroll),
            'cfdi_date': cfdi_date,
            'TipoNomina' : 'O',
            'PaymentDate' : datetime.now().strftime('%Y-%m-%d'),
            'StartDate' : payroll.payslip_id.date_from.strftime('%Y-%m-%d'),
            'EndDate' : payroll.payslip_id.date_to.strftime('%Y-%m-%d'),
            'PayedDays' : 1,
            'NetEarning' :  payroll.payslip_id.line_ids.filtered(lambda x: x.category_id.code == 'NET').total,
            'GrossEarning' : payroll.payslip_id.line_ids.filtered(lambda x: x.category_id.code == 'GROSS').total,
            'Deductions' : deductionVal,
            'OtherEarnings' : otherVal,
            'CompanyReg' : payroll.company_id.l10n_mx_edi_reg_pat,
            'CURP' : payroll.payslip_id.employee_id.l10n_mx_curp,
            'SegSoc' : payroll.payslip_id.employee_id.l10n_mx_seg_soc,
        }
        return cfdi_values
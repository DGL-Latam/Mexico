from odoo import api, models, fields
import datetime
class AccountMove(models.Model):
    _inherit = 'account.move'
    
    l10n_mx_edi_periocidad = fields.Selection([
        ('01','Diaria'),
        ('02','Semanal'),
        ('03','Quincenal'),
        ('04','Mensual'),
        ('05','Bimestral')
    ], string="Periocidad", default='01')
    l10n_mx_edi_mes = fields.Selection([
        ('01','Enero'),
        ('02','Febrero'),
        ('03','Marzo'),
        ('04','Abril'),
        ('05','Mayo'),
        ('06','Junio'),
        ('07','Julio'),
        ('08','Agosto'),
        ('09','Septiembre'),
        ('10','Octubre'),
        ('11','Noviembre'),
        ('12','Diciembre'),
        ('13','Enero-Febrero'),
        ('14','Marzo-Abril'),
        ('15','Mayo-Junio'),
        ('16','Julio-Agosto'),
        ('17','Septiembre-Octubre'),
        ('18','Noviembre-Diciembre')
    ], string="Mes(es)", default=str(datetime.datetime.now().strftime('%m')))
    l10n_mx_edi_year = fields.Selection('_getCurrentYears', string="Año", default=str(datetime.datetime.now().year))

    partner_vat = fields.Char(related="partner_id.vat")

    def _getCurrentYears(self):
        values = [(str(datetime.datetime.now().year),str(datetime.datetime.now().year)),(str(datetime.datetime.now().year-1),str(datetime.datetime.now().year-1))]
        return values
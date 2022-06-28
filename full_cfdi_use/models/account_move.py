from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'
    l10n_mx_edi_usage = fields.Selection(
        selection=[
            ('G01', 'G01 Adquisición de mercancías'),
            ('G02', 'G02 Devoluciones, descuentos o bonificaciones'),
            ('G03', 'G03 Gastos en general'),
            ('I01', 'I01 Construcciones'),
            ('I02', 'I02 Mobilario y equipo de oficina por inversiones'),
            ('I03', 'I03 Equipo de transporte'),
            ('I04', 'I04 Equipo de cómputo y accesorios'),
            ('I05', 'I05 Dados, troqueles, moldes, matrices y herramental'),
            ('I06', 'I06 Comunicaciones telefónicas'),
            ('I07', 'I07 Comunicaciones satelitales'),
            ('I08', 'I08 Otra maquinaria y equipo'),
            ('D01', 'D01 Honorarios médicos, dentales y gastos hospitalarios.'),
            ('D02', 'D02 Gastos médicos por incapacidad o discapacidad'),
            ('D03', 'D03 Gastos funerales'),
            ('D04', 'D04 Donativos'),
            ('D05', 'D05 Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación)'),
            ('D06', 'D06 Aportaciones voluntarias al SAR'),
            ('D07', 'D07 Primas por seguros de gastos médicos'),
            ('D08', 'D08 Gastos de transportación escolar obligatoria'),
            ('D09', 'D09 Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones.'),
            ('D10', 'D10 Pagos por servicios educativos (colegiaturas)'),
            ('P01', 'P01 Por definir'),
        ],
        string="Usage",
        default='P01',
        help="Used in CFDI 3.3 to express the key to the usage that will gives the receiver to this invoice. This "
             "value is defined by the customer.\nNote: It is not cause for cancellation if the key set is not the usage "
             "that will give the receiver of the document.")
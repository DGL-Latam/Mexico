{
    'name': 'Nomina Mexico CFDI 4.0',
    'version': '0.1',
    "author": "DGL-Latam",
    "license": "LGPL-3",
    'summary': 'Modulo para poder emitir recibos de nomina en Mexico junto con su comprobante fiscal en la version 4.0',
    'depends': [
        'l10n_mx_edi_40',
        'hr_payroll',
    ],
    'data': [
        'data/account_edi_data.xml',
        'data/nomina12.xml', 
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
}


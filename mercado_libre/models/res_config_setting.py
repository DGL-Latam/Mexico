from odoo import api, models, fields, http
from odoo.exceptions import UserError



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    ml_seller_id = fields.Char(string="ID del vendedor", help="Valor numerico que pertenece al vendedor en la base de datos de mercado libre", related="company_id.ml_seller_id", readonly=False)
    ml_app_id = fields.Char(string="App id", help="App id, se puede checar en la configuracion de la app en la pagina de developers de ML", related="company_id.ml_app_id", readonly=False)
    ml_app_secret = fields.Char(string="App secret", help="Secret key, se puede checar en la configuracion de la app en la pagina de developers de ML", related="company_id.ml_app_secret", readonly=False)
    ml_access_token = fields.Char(string="Access Token", help="Token para poder acceder a los servicios del api", related="company_id.ml_access_token", readonly=False)
    ml_refresh_token = fields.Char(string="Refresh Token", help="Token para refrescar nuestro token de acceso", related="company_id.ml_refresh_token", readonly=False)
    
    def but_refresh_code(self):
        self.ensure_one()

        if self.ml_refresh_token:
            if not (self.company_id.renew_access_token()):
                raise UserError("Error favor de checar los datos o intentar de nuevo")
        elif  not (self.company_id.get_first_access_code()):
            raise UserError("Error favor de checar los datos o intentar de nuevo")
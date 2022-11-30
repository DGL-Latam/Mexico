from .WebServiceRequestSAT import WebServiceRequestSAT

class DescargaMasiva(WebServiceRequestSAT):

    xml_name = 'descargamasiva.xml'
    soap_url = 'https://cfdidescargamasiva.clouda.sat.gob.mx/DescargaMasivaService.svc'
    soap_action = 'http://DescargaMasivaTerceros.sat.gob.mx/IDescargaMasivaTercerosService/Descargar'
    solicitud_xpath = 's:Body/des:PeticionDescargaMasivaTercerosEntrada/des:peticionDescarga'
    result_xpath = 's:Body/RespuestaDescargaMasivaTercerosSalida/Paquete'

    def DescargarPaquete(self, token, rfc_solicitante, id_paquete) :
        arguments = {
            'RfcSolicitante' : rfc_solicitante,
            'IdPaquete' : id_paquete,
        }
        element_response = self.request(token,arguments)

        response = element_response.getparent().getparent().getparent().find(
            's:Header/h:respuesta', namespaces = self.external_namespaces
        )

        value = {
            'cod_estatus' : response.get('CodEstatus'),
            'mensaje' : response.get('Mensaje'),
            'paquete_b64' : element_response.text,
        }

        return value
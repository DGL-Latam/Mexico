from .WebServiceRequestSAT  import WebServiceRequestSAT

class VerificaSolicitudDescarga(WebServiceRequestSAT):

    xml_name = 'verificasolicituddescarga.xml'
    soap_url = 'https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/VerificaSolicitudDescargaService.svc'
    soap_action = 'http://DescargaMasivaTerceros.sat.gob.mx/IVerificaSolicitudDescargaService/VerificaSolicitudDescarga'
    solicitud_xpath = 's:Body/des:VerificaSolicitudDescarga/des:solicitud'
    result_xpath = 's:Body/VerificaSolicitudDescargaResponse/VerificaSolicitudDescargaResult'

    def VerificarDescarga(self, token, rfc_solicitante, id_solicitud):
        arguments = {
            'RfcSolicitante' : rfc_solicitante,
            'IdSolicitud' : id_solicitud,
        }

        response = self.request(token,arguments)

        value = {
            'cod_estatus': response.get('CodEstatus'),
            'estado_solicitud': response.get('EstadoSolicitud'),
            'codigo_estado_solicitud': response.get('CodigoEstadoSolicitud'),
            'numero_cfdis': response.get('NumeroCFDIs'),
            'mensaje': response.get('Mensaje'),
            'paquetes': []
        }

        for id_paquete in response.iter('{{{}}}IdsPaquetes'.format(self.external_namespaces[''])):
            value['paquetes'].append(id_paquete.text)
    
        return value
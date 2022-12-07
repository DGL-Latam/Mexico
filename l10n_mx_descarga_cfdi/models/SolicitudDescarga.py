from .WebServiceRequestSAT  import WebServiceRequestSAT

class SolicitudDescarga(WebServiceRequestSAT):

    xml_name = 'solicitadescarga.xml'
    soap_url = 'https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/SolicitaDescargaService.svc'
    soap_action = 'http://DescargaMasivaTerceros.sat.gob.mx/ISolicitaDescargaService/SolicitaDescarga'
    solicitud_xpath = 's:Body/des:SolicitaDescarga/des:solicitud'
    result_xpath = 's:Body/SolicitaDescargaResponse/SolicitaDescargaResult'

    def SolicitarDescarga(
        self, token, rfc_solicitante, fecha_inicial, fecha_final,
        rfc_emisor = None, rfc_receptor=None, tipo_solicitud="CFDI",
        tipo_comprobante = None, estado_comprobante = None,
        rfc_a_cuenta_terceros = None, complemento = None, uuid = None 
    ):
        arguments = {
            'RfcSolicitante': rfc_solicitante,
            'FechaFinal': fecha_final.strftime(self.DATE_TIME_FORMAT),
            'FechaInicial': fecha_inicial.strftime(self.DATE_TIME_FORMAT),
            'TipoSolicitud': tipo_solicitud,
            'TipoComprobante': tipo_comprobante,
            'EstadoComprobante': estado_comprobante,
            'RfcACuentaTerceros': rfc_a_cuenta_terceros,
            'Complemento': complemento,
            'UUID': uuid,
        }

        if rfc_emisor:
            arguments['RfcEmisor'] = rfc_emisor
        
        if rfc_receptor:
            arguments['RfcReceptores'] = [rfc_receptor]

        element_res = self.request(token,arguments)

        value = {
            'id_solicitud': element_res.get('IdSolicitud'),
            'cod_estatus': element_res.get('CodEstatus'),
            'mensaje': element_res.get('Mensaje')
        }

        return value
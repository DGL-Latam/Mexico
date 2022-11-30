import base64
import hashlib
import uuid
from datetime import datetime, timedelta

from .WebServiceRequestSAT import WebServiceRequestSAT


class Autentificacion(WebServiceRequestSAT):
    DATE_TIME_FORMAT: str = '%Y-%m-%dT%H:%M:%S.%fZ'

    xml_name = 'autentificacion.xml'
    soap_url = 'https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/Autenticacion/Autenticacion.svc'
    soap_action = 'http://DescargaMasivaTerceros.gob.mx/IAutenticacion/Autentica'
    result_xpath = ''

    internal_namespaces = {
        's': 'http://schemas.xmlsoap.org/soap/envelope/',
        'o': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd',
        'u': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd',
        'des': 'http://DescargaMasivaTerceros.sat.gob.mx',
        '': 'http://www.w3.org/2000/09/xmldsig#',
    }
    external_namespaces = {
        '': 'http://DescargaMasivaTerceros.gob.mx',
        's': 'http://schemas.xmlsoap.org/soap/envelope/',
        'u': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd',
        'o': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd',
    }

    def obtener_token(self, id=uuid.uuid4(), seconds=300):
        date_created = datetime.utcnow()
        date_expires = date_created + timedelta(seconds=seconds)
        date_created = date_created.strftime(self.DATE_TIME_FORMAT)
        date_expires = date_expires.strftime(self.DATE_TIME_FORMAT)


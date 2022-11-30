import logging
logger = logging.getLogger(__name__)

import requests
from lxml import etree

from .Utilidades import Utilidades
from .Fiel import Fiel
from .Signer import Signer

class WebServiceRequestSAT(Utilidades):
    DATE_TIME_FORMAT: str = '%Y-%m-%dT%H:%M:%S'

    soap_url : str = None
    soap_action : str = None
    result_xpath : str = None

    fault_xpath : str = 's:Body/s:Fault/faultstring'

    def __init__(self, fiel : Fiel, verify : bool = True, timeout : int = 30) -> None:
        super().__init__()
        self.signer = Signer(fiel)
        self.verify = verify
        self.timeout = timeout

    def get_headers(self, token : str) -> dict:
        headers = {
            'Content-type': 'text/xml;charset="utf-8"',
            'Accept': 'text/xml',
            'Cache-Control': 'no-cache',
            'SOAPAction': self.soap_action,
            'Authorization': 'WRAP access_token="{}"'.format(token) if token else ''
        }
        return headers
    
    def set_request_arguments(self, arguments : dict) -> etree.Element:
        solicitud = self.get_element(self.solicitud_xpath)
        for key in arguments:
            if key == "RfcReceptores":
                for i, rfc_receptor in enumerate(arguments[key]):
                    if i == 0:
                        self.set_element_text(
                            's:Body/des:SolicitaDescarga/des:solicitud/des:RfcReceptores/des:RfcReceptor',
                            rfc_receptor
                        )
                continue
            if arguments[key] != None:
                solicitud.set(key, arguments[key])
        return solicitud

    def request(self, token : str = None, arguments : dict = None) -> etree.Element:
        if arguments:
            solicitud = self.set_request_arguments(arguments)
            self.signer.sign(solicitud)
        
        headers = self.get_headers(token)

        soap_request = self.element_to_bytes(self.element_root)

        response = requests.post(
            self.soap_url,
            data = soap_request,
            headers= headers,
            verify= self.verify,
            timeout=self.timeout,
        )

        try:
            response_xml = etree.fromstring(
                response.text,
                parser= etree.XMLParser(huge_tree=True)
            )
        except Exception:
            raise Exception(response.text)
        
        if response.status_code != requests.codes['ok']:
            error = self.get_element_external(response_xml, self.fault_xpath)
            raise Exception(error)
        
        return self.get_element_external(response_xml, self.result_xpath)



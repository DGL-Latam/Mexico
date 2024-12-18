# -*- coding: utf-8 -*-
import base64

from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from OpenSSL import crypto
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, pkcs12, PrivateFormat, BestAvailableEncryption, NoEncryption, PublicFormat, load_der_private_key

class Fiel():
    def __init__(self, cer_der, key_der, passphrase):
        self.__importar_cer__(cer_der)
        self.__importar_key__(key_der, passphrase)

    def __importar_cer__(self, cer_der):
        # Cargar certificado en formato DER
        self.cer = crypto.load_certificate(crypto.FILETYPE_ASN1, cer_der)
        
    def public_key(self) -> rsa.RSAPublicKey:
        return self.cer.get_pubkey().to_cryptography_key()
    
    def _compare_public_keys(public_key_a, public_key_b):
        def key_bytes(k):
            return k.public_bytes(
                encoding=Encoding.DER,
                format=PublicFormat.SubjectPublicKeyInfo
            )
        
        return key_bytes(public_key_a) == key_bytes(public_key_b)

    def __importar_key__(self, key_der, password):
        if isinstance(password, str):
            password = password.encode()
            
        key = load_der_private_key(
            data=key,
            password=password
        )
        
        res = _compare_public_keys(key.public_key(), self.cer.public_key())
        
        if not res:
            raise CFDIError("Private Key does not match certificate")

    def firmar_sha1(self, data):
        signature = self.key.sign(
            data = data,
            padding = padding.PKCS1v15(),
            algorithm = hashes.SHA1()
        )

        return base64.b64encode(
            signature
        ).decode()

    def _certificate_bytes(self, encoding: Encoding = Encoding.DER) -> bytes:
        return self.cer.to_cryptography().public_bytes(
            encoding=encoding
        )
        
    def cer_to_base64(self):
        cert = self.certificate_bytes()
        
        return base64.b64encode(cert).decode()

    def cer_issuer(self):
        # Extraer issuer
        d = self.cer.get_issuer().get_components()
        # Generar cadena issuer
        return ','.join(f'{k.decode()}={v.decode()}' for k, v in reversed(d))

    def cer_serial_number(self):
        # Obtener numero de serie del certificado
        serial = self.cer.get_serial_number()
        # Pasar numero de serie a string
        return str(serial)
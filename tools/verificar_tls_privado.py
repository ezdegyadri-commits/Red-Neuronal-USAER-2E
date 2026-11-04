"""Comprobaciones locales previas al arranque HTTPS. La confianza se prueba en el cliente."""

from datetime import datetime, timezone
import os
from pathlib import Path
import ssl

from cryptography import x509


def verificar(certificado, clave, host):
    hoja = x509.load_pem_x509_certificate(Path(certificado).read_bytes())
    ahora = datetime.now(timezone.utc)
    if not hoja.not_valid_before_utc <= ahora < hoja.not_valid_after_utc:
        raise ValueError("El certificado está fuera de vigencia.")
    try:
        alternativas = hoja.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        raise ValueError("El certificado requiere un SAN DNS explícito.") from None
    if host not in alternativas.get_values_for_type(x509.DNSName):
        raise ValueError("El nombre configurado no coincide exactamente con un SAN DNS.")
    # No solicitar contraseñas ni mostrar el contenido de la clave.
    ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(certificado, clave, password="")


if __name__ == "__main__":
    try:
        verificar(os.environ["USAER_SPA_TLS_CERT"], os.environ["USAER_SPA_TLS_KEY"],
                  os.environ["USAER_SPA_TLS_HOST"])
    except (KeyError, OSError, ValueError) as exc:
        raise SystemExit(f"Comprobación TLS fallida: {exc}") from None

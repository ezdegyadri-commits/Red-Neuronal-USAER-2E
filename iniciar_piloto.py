"""Script lanzador del Piloto SPA USAER 2E.

Configura las rutas y el directorio de trabajo automáticamente para evitar
ModuleNotFoundError sin importar desde dónde se ejecute la terminal.
"""
import os
from ipaddress import IPv4Address, IPv4Network
import re
import sys

# Fijar directorio raíz del proyecto
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import uvicorn

if __name__ == "__main__":
    os.environ["USAER_SPA_MODE"] = "local-synthetic"
    os.environ["DATABASE_URL"] = os.environ.get(
        "USAER_SPA_SQLITE_URL", f"sqlite:///{ROOT_DIR}/data/piloto_sintetico.db"
    )
    if "USAER_SPA_POSTGRES_TEST_URL" in os.environ:
        os.environ["USAER_SPA_MODE"] = "postgres-synthetic"
        os.environ["DATABASE_URL"] = os.environ["USAER_SPA_POSTGRES_TEST_URL"]
    port = int(os.environ.get("USAER_SPA_PORT", "8000"))
    cert = os.environ.get("USAER_SPA_TLS_CERT")
    key = os.environ.get("USAER_SPA_TLS_KEY")
    if bool(cert) != bool(key):
        raise SystemExit("Configura juntos USAER_SPA_TLS_CERT y USAER_SPA_TLS_KEY.")
    lan = os.environ.get("USAER_SPA_LAN_IP")
    host_tls = os.environ.get("USAER_SPA_TLS_HOST", "")
    if host_tls and (not cert or len(host_tls) > 253 or not re.fullmatch(
        r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", host_tls
    )):
        raise SystemExit("USAER_SPA_TLS_HOST requiere un nombre DNS exacto y un certificado TLS.")
    if lan:
        redes = tuple(map(IPv4Network, ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")))
        try:
            ip = IPv4Address(lan)
        except ValueError:
            raise SystemExit("USAER_SPA_LAN_IP debe ser una dirección IPv4 privada explícita.")
        if not any(ip in red for red in redes):
            raise SystemExit("USAER_SPA_LAN_IP debe estar dentro de una red RFC 1918.")
        if not cert or os.environ.get("USAER_SPA_MODE") != "postgres-synthetic" or os.environ.get("USAER_SPA_ROLE") != "runtime":
            raise SystemExit("El piloto LAN requiere HTTPS y PostgreSQL sintético con rol operativo.")
    uvicorn.run("piloto_spa.backend.main:app", host=lan or "127.0.0.1", port=port, reload=False,
                proxy_headers=False, access_log=False, ssl_certfile=cert, ssl_keyfile=key)

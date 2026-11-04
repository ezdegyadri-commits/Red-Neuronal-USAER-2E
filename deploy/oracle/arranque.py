"""Entrada exclusiva del piloto sintético en Compose."""
import os
from pathlib import Path
import re
import sys

from sqlalchemy.engine import URL


def secreto(nombre):
    valor = (Path("/run/secrets") / nombre).read_text(encoding="utf-8").strip()
    if len(valor) < 24 or not re.fullmatch(r"[A-Za-z0-9_-]+", valor):
        raise ValueError(f"Secreto inválido: {nombre}")
    return valor


def main():
    tarea = sys.argv[1:]
    if tarea not in (["migrar"], ["servir"]):
        raise SystemExit("Indica migrar o servir.")
    migrar = tarea == ["migrar"]
    perfil = "owner" if migrar else "runtime"
    usuario = "spa_fixture_oracle" if migrar else "spa_runtime_oracle"
    dominio = os.environ.get("USAER_PUBLIC_HOST", "")
    if len(dominio) > 253 or not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", dominio):
        raise SystemExit("Configura un nombre DNS exacto.")
    url = URL.create("postgresql", username=usuario, password=secreto("pg_owner" if migrar else "pg_runtime"),
                     host="db", port=5432, database="usaer_spa_test_oracle")
    os.environ.update(USAER_SPA_MODE="postgres-container-synthetic", USAER_SPA_ROLE=perfil,
                      DATABASE_URL=url.render_as_string(hide_password=False))
    if migrar:
        from data.database import Alumno, Escuela, Usuario, get_session
        from piloto_spa.backend.auth_service import hash_password
        from piloto_spa.backend.main import verificar_base_piloto

        verificar_base_piloto()
        with get_session() as db:
            if not db.query(Usuario.id).first():
                db.add(Usuario(id="direccion-oracle", usuario="direccion.piloto", nombre="Dirección ficticia",
                               rol="DIRECTOR", escuelas_permitidas="TODAS",
                               password=hash_password(secreto("direccion_inicial"))))
                if not db.query(Escuela.id).first() and not db.query(Alumno.id).first():
                    for letra in ("a", "b"):
                        escuela = f"esc-oracle-{letra}"
                        nombre = f"Escuela ficticia {letra.upper()}"
                        db.add(Escuela(id=escuela, nombre_escuela=nombre, nivel="Primaria"))
                        db.add(Alumno(id=f"alu-oracle-{letra}", id_escuela=escuela,
                                      nombre_escuela=nombre, nombre_completo=f"Estudiante ficticio {letra.upper()}",
                                      nivel_educativo="Primaria", grado="3°", grupo="A",
                                      estatus="Activo", tipo_atencion="Individual"))
                db.commit()
        return
    import uvicorn
    uvicorn.run("piloto_spa.backend.main:app", host="0.0.0.0", port=8000,
                proxy_headers=True, forwarded_allow_ips="172.29.83.2", access_log=False)


if __name__ == "__main__":
    main()

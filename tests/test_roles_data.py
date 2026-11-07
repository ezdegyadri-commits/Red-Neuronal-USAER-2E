import sys
from pathlib import Path
ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from piloto_spa.backend.domain_services import (
    obtener_alumnos_autorizados,
    obtener_anexo3_autorizados,
    obtener_anexo4_autorizados,
)
from piloto_spa.backend.auth_service import USUARIOS_CANONICOS

test_users = [
    'cindy.burgos', 'marycruz.caamal', 'cecilia.solis', 'dolores.cortazar',
    'abril.chable', 'marilyn.perez', 'diego.peralta', 'elmy.puerto', 'edgar.director'
]

for u in test_users:
    usr = USUARIOS_CANONICOS.get(u)
    if not usr:
        print(f"User {u} NOT FOUND!")
        continue
    escuelas = usr.get('escuelas_permitidas') or usr.get('escuelas', [])
    alus = obtener_alumnos_autorizados(usr['rol'], escuelas, usr['nombre'])
    an3 = obtener_anexo3_autorizados(usr['rol'], escuelas, usr['nombre'])
    an4 = obtener_anexo4_autorizados(usr['rol'], escuelas, usr['nombre'])
    print(f"{u:22} | Rol: {usr['rol']:15} | Esc: {str(escuelas):25} | Alus: {len(alus):3} | An3: {len(an3):3} | An4: {len(an4):3}")

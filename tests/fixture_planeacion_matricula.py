"""Solo datos ficticios; reproduce las dos representaciones de una escuela."""
from pathlib import Path
# Extiende el mismo recorrido probado y conserva todos sus repositorios simulados.
source=Path(__file__).with_name('fixture_planeacion_completa.py').read_text(encoding='utf-8')
source=source.replace('from ui.planeacion import _planeacion_page_clasica as planeacion_page','from ui.planeacion import planeacion_page')
source=source.replace("s.identidad=lambda:actor;s.padron_autorizado=lambda:pd.DataFrame(alumnos)",
"""from tests.test_planeacion_matricula import matricula
from services.planeacion_matricula import preparar
from services.alumnos import filtrar_alumnos_por_escuelas
s.identidad=lambda:actor
s.padron_autorizado=lambda:preparar(filtrar_alumnos_por_escuelas(matricula(),['ESC-006']))""")
exec(compile(source,__file__,'exec'))

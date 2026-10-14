"""Documento de demostración completamente ficticio, sin acceso a Sheets ni IA."""
from pathlib import Path
source=Path(__file__).with_name('fixture_planeacion_viva.py').read_text(encoding='utf-8')
source=source.replace('from ui.planeacion_viva import pagina as planeacion_page','from ui.planeacion import planeacion_page')
exec(compile(source,__file__,'exec'))

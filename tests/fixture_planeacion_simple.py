"""Mismos datos ficticios y servicios simulados; entrada de producción nueva."""
from pathlib import Path
source=Path(__file__).with_name('fixture_planeacion_completa.py').read_text(encoding='utf-8')
source=source.replace('from ui.planeacion import _planeacion_page_clasica as planeacion_page','from ui.planeacion import planeacion_page')
exec(compile(source,__file__,'exec'))

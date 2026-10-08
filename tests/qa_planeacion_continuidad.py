"""QA local de PDF, solo datos ficticios y sin servicios externos."""
from pathlib import Path
from unittest.mock import patch
import subprocess
from pypdf import PdfReader
from tests.test_planeacion_completa import documento,resultado
from services import planeacion as s,planeacion_generacion as g
from documents.planeacion import generar_pdf

out=Path('tmp/pdfs/continuidad');out.mkdir(parents=True,exist_ok=True)
poppler='C:/Users/edgar/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
with patch.object(s,'autorizar',return_value={'cuenta':'ficticia','director':False}):
    d=documento();req=g.preparar_solicitud(d,g.configuracion(d));d=g.ensamblar(d,resultado(req,'Aprendizaje'),req)
    d['metadatos']['vinculos_documentales']=[{'alumno':'A1','tipo':'EPP','documento':'EPP-ficticia','revision':'r1','referencia':'E1'}]
    d['metadatos']['seguimiento_formativo']=[{'fecha':'2026-10-01','decision':'Ajustar','hallazgos':'Participó al elegir tarjetas. Reducir las instrucciones y ofrecer dos opciones.','referencias':['E1']}]
    d['metadatos']['aportaciones_equipo']={'Comunicación':{'autor':'Profesional ficticio','fecha':'2026-10-01T12:00:00Z','observaciones':'Propuesta para revisar en equipo.','filas':[{'Actividad / cómo trabajar':'Elegir imágenes y comunicar una necesidad.'}]}}
    path=out/'continuidad.pdf';path.write_bytes(generar_pdf(d))
    text='\n'.join(p.extract_text() for p in PdfReader(path).pages)
    assert 'EPP-ficticia' in text and 'Participó al elegir tarjetas' in text and 'Profesional ficticio' in text
    subprocess.run([poppler,'-scale-to','1400','-png',str(path),str(out/'pagina')],check=True,capture_output=True)
    print(len(PdfReader(path).pages),'páginas verificadas')

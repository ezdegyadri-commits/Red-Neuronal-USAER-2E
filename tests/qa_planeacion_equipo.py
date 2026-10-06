"""Genera ejemplos ficticios para verificar visualmente los tres PDF."""
from pathlib import Path
import pymupdf
from tests.test_planeacion_equipo import documento,sesion
from services import planeacion_equipo as e
from documents.planeacion import generar_pdf

def main():
    root=Path('output/qa-equipo');root.mkdir(parents=True,exist_ok=True)
    for area,nombre in [('Psicología','psicologia'),('Comunicación','comunicacion'),('Trabajo Social','trabajo-social')]:
        d=e.guardar_subgrupo(documento(area),'Subgrupo 1',['A1'])
        context='Familia' if area=='Trabajo Social' else 'Aula de apoyo'
        d=e.guardar_sesion(d,{**sesion(contexto=context),'competencias':list(e.COMPETENCIAS) if area=='Psicología' else []})
        if area=='Psicología':
            for r in d['metadatos']['equipo']['competencias']:
                r.update({'Necesidad documentada':'Necesidad educativa por confirmar con el informe.','Descriptor de logro':'El alumno expresa su emoción con un apoyo elegido.','Actividad prevista':'Tarjetas con situaciones cotidianas; inicio, intercambio y cierre.'})
        d['metadatos']['equipo']['grupal'][0]['Situación inicial']='Pendiente de confirmar con la evaluación registrada.'
        d['metadatos']['equipo']['grupal'][0]['Actividades']='Actividad propuesta: identificar apoyos que favorezcan su participación. No es un resultado observado.'
        for key in d['textos']:d['textos'][key]='Registro de ejemplo para verificar el formato; completar con información documentada.'
        pdf=generar_pdf(d);path=root/(nombre+'.pdf');path.write_bytes(pdf)
        with pymupdf.open(stream=pdf,filetype='pdf') as pages:
            print(nombre,len(pages),'páginas')
            assert all(p.rect.width>p.rect.height for p in pages)
            texto=''.join(p.get_text() for p in pages)
            assert 'Planeación grupal ajustada de zona' in texto
            assert 'USAER PREESCOLAR 67' not in texto
            for i,page in enumerate(pages):page.get_pixmap(matrix=pymupdf.Matrix(1.25,1.25)).save(root/(nombre+'-'+str(i+1)+'.png'))

if __name__=='__main__':main()

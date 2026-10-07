"""QA visual con datos ficticios; no lee la base de producción."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fitz
from services.epp_modelo import clave,vacia,AREAS
from documents.epp import generar_pdf

def main():
    out=Path('tmp/epp-qa');out.mkdir(parents=True,exist_ok=True)
    alumno={'ID_Alumno':'FICTICIO','Nombre_Completo':'Alumno ficticio para revisión','Nombre_Escuela':'Escuela ficticia','Nivel_Educativo':'Primaria','Grado':'3','Grupo':'A','CURP':''}
    d={'id':clave('FICTICIO','2026-2027'),'alumno':'FICTICIO','ciclo':'2026-2027','partes':{'META':{'fecha':'2026-10-07'}}}
    for area in AREAS:
        v=vacia(area);v['instrumentos']='Registro de observación ficticio';v['fecha_aplicacion']='07/10/2026'
        for f in v['campos']:v['campos'][f]='Ejemplo ficticio: participa con un apoyo visual y una indicación breve. El equipo debe corroborar los hallazgos registrados.'
        d['partes'][area]={'contenido':v,'fecha':'2026-10-07','autor':'Profesional ficticio'}
    v=vacia('Conclusión');v['campos']['7.1. Conclusión']='Ejemplo de redacción: al contrastar las observaciones de las áreas, el equipo identifica fortalezas de participación con apoyos visuales. Faltan evaluaciones para establecer una conclusión real.'
    v['nee'][0].update({'Características relevantes':'Ejemplo ficticio de observación educativa.','NEE':'Necesita fortalecer la atención sostenida en tareas breves.','Apoyos':'Consigna breve y apoyo visual.','Responsables':'Por acordar','Fecha o período':'Por acordar'})
    v['bap'][0].update({'Tipo de barrera':'Ejemplo ficticio: consignas extensas sin apoyos visuales.','Acciones generales':'Ofrecer una indicación breve y un apoyo visual.'})
    d['partes']['Conclusión']={'contenido':v,'fecha':'2026-10-07','autor':'Docente ficticia'}
    pdf=fitz.open(stream=generar_pdf(d,alumno),filetype='pdf')
    for i,page in enumerate(pdf):
        page.get_pixmap(matrix=fitz.Matrix(1.1,1.1)).save(str(out/f'epp-{i+1}.png'))
        for block in page.get_text('blocks'):
            assert block[0]>=30 and block[2]<=585,(i,block[:4])
    print('Páginas revisables:',len(pdf))
if __name__=='__main__':main()

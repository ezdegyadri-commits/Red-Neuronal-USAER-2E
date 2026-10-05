from pathlib import Path
from services.planeacion_modelo import crear_plantilla
from documents.planeacion import generar_pdf
from services.curriculo import opciones, vincular
import pymupdf

def main():
    output=Path('output/planeacion-qa');output.mkdir(parents=True,exist_ok=True)
    alumno={'ID_Alumno':'A1','Nombre_Completo':'Alumno de demostración','ID_Escuela':'E1','Nombre_Escuela':'Escuela de demostración','CCT_Escuela':'TEST','Grado':'3','Grupo':'A','Nivel_Educativo':'Primaria'}
    for formato in ('XXI','XXIII','XXV'):
        doc=crear_plantilla(formato,['A1'],[alumno],autor='Docente de demostración',funcion='Trabajo Social' if formato=='XXV' else 'Aprendizaje')
        campo='De lo Humano y lo Comunitario' if formato=='XXV' else 'Lenguajes'
        referente=opciones(doc,campo)[0]
        doc=vincular(doc,campo,['Inclusión'],[referente['id']])
        for table,headers in __import__('services.planeacion_modelo',fromlist=['FORMATOS']).FORMATOS[formato]['tablas'].items():
            if table!='evaluacion_final':
                doc['tablas'][table]=[{h:'Ejemplo de contenido revisable para '+h for h in headers}]
        for field in doc['textos']:doc['textos'][field]='Se registran evidencias observables y avances documentados para ajustar los apoyos.'
        path=output/(formato+'.pdf');path.write_bytes(generar_pdf(doc))
        pdf=pymupdf.open(path)
        for i,page in enumerate(pdf):page.get_pixmap(matrix=pymupdf.Matrix(1.4,1.4)).save(output/(formato+'-'+str(i+1)+'.png'))
        print(formato,len(pdf),'páginas')

if __name__=='__main__':main()

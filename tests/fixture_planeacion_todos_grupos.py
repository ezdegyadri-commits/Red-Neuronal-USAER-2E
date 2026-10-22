"""Recorrido real de entrada con grupos A/B ficticios; no usa datos externos."""
from pathlib import Path
source=Path(__file__).with_name('fixture_planeacion_completa.py').read_text(encoding='utf-8')
source=source.replace('from ui.planeacion import _planeacion_page_clasica as planeacion_page',
                      'from ui.planeacion_viva import pagina as planeacion_page')
inicio=source.index('alumnos=[')
fin=source.index('s.identidad=',inicio)
source=source[:inicio]+'''base={'Nombre_Completo':'Estudiante ficticio','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','CCT_Escuela':'TEST','Grado':'1','Tipo_Atencion':'Grupal','Estatus':'Activo'}
alumnos=[{**base,'ID_Alumno':aid,'Nombre_Completo':'Estudiante ficticio '+aid,'Grupo':grupo} for aid,grupo in [('A1','A'),('B1','B'),('S1','')]]
alumnos.append({**base,'ID_Alumno':'I1','Nombre_Completo':'Individual ficticio','Grupo':'B','Tipo_Atencion':'Individual'})
''' + source[fin:]
exec(compile(source,__file__,'exec'))

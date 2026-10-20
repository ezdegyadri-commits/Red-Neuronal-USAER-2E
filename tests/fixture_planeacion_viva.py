"""Entrada productiva con alumnos, repositorio y generación ficticios."""
from pathlib import Path
source=Path(__file__).with_name('fixture_planeacion_completa.py').read_text(encoding='utf-8')
source=source.replace('from ui.planeacion import _planeacion_page_clasica as planeacion_page','from ui.planeacion_viva import pagina as planeacion_page')
source=source.replace("'Tipo_Atencion':'Grupal'}]", "'Tipo_Atencion':'Grupal'}, {'ID_Alumno':'A2','Nombre_Completo':'Alumno ficticio Dos','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','CCT_Escuela':'TEST','Grado':'4','Grupo':'B','Tipo_Atencion':'Grupal'}, {'ID_Alumno':'I1','Nombre_Completo':'Alumno ficticio Individual','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','CCT_Escuela':'TEST','Grado':'1','Grupo':'A','Tipo_Atencion':'Individual'}]")
source=source.replace("'Tipo_Atencion':'Individual'}]", "'Tipo_Atencion':'Individual'}, {'ID_Alumno':'I2','Nombre_Completo':'Alumno ficticio Individual Dos','ID_Escuela':'E1','Nombre_Escuela':'Escuela ficticia','CCT_Escuela':'TEST','Grado':'2','Grupo':'B','Tipo_Atencion':'Individual'}]")
source=source.replace("'Grado':'4','Grupo':'B','Tipo_Atencion':'Grupal'", "'Grado':'5','Grupo':'A','Tipo_Atencion':'Grupal'")
source=source.replace('    st.session_state.llamadas_ficticias+=1\n', "    st.session_state.llamadas_ficticias+=1\n    if st.session_state.get('fallo_ia_ficticio'):raise RuntimeError('IA no disponible (504).')\n")
source=source.replace("def guardar(doc,estado='BORRADOR',observaciones=None):\n", "def guardar(doc,estado='BORRADOR',observaciones=None):\n    if st.session_state.get('fallo_guardado_ficticio'):raise RuntimeError('No se confirmó el guardado ficticio.')\n")
source=source.replace('planeacion_page()',"from ui import planeacion as u\nst.session_state.setdefault(u._prefix()+'_submodulo','revision' if actor['director'] else 'propio')\nplaneacion_page()")
exec(compile(source,__file__,'exec'))

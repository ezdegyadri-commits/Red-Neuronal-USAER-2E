"""Entrada vigente, datos ficticios y fallos controlados de IA/guardado."""
from pathlib import Path
source=Path(__file__).with_name('fixture_planeacion_completa.py').read_text(encoding='utf-8')
source=source.replace('from ui.planeacion import _planeacion_page_clasica as planeacion_page','from ui.planeacion_simple import pagina as planeacion_page')
source=source.replace("'Tipo_Atencion':'Grupal'", "'Tipo_Atencion':('Individual' if st.session_state.get('individual_ficticio') else 'Grupal')")
source=source.replace('def evidencias(doc):\n', "def evidencias(doc):\n    if st.session_state.get('sin_fuentes_ficticio'):return ([],[])\n")
source=source.replace('    st.session_state.llamadas_ficticias+=1\n', "    st.session_state.llamadas_ficticias+=1\n    if st.session_state.get('fallo_ia_ficticio'):raise RuntimeError('IA no disponible (504).')\n")
source=source.replace("def guardar(doc,estado='BORRADOR',observaciones=None):\n", "def guardar(doc,estado='BORRADOR',observaciones=None):\n    if st.session_state.get('fallo_guardado_ficticio'):raise RuntimeError('No se confirmó el guardado ficticio.')\n")
exec(compile(source,__file__,'exec'))

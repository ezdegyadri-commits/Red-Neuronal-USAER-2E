"""Prueba visual local: nunca consulta Sheets, Drive ni Gemini."""
from pathlib import Path

source=Path(__file__).with_name('fixture_planeacion_completa.py').read_text(encoding='utf-8')
source=source.replace('from ui.planeacion import _planeacion_page_clasica as planeacion_page',
                      'from ui.planeacion import planeacion_page')
source=source.replace('planeacion_page()\n', '''
st.toggle('Simular fallo de guardado (solo prueba)',key='fallo_guardado_ficticio')
st.toggle('Simular una confirmación lenta (solo prueba)',key='lento_ficticio')
original_guardar=s.guardar
def guardar_controlado(doc,estado='BORRADOR',observaciones=None):
    if st.session_state.get('fallo_guardado_ficticio'):raise RuntimeError('Conexión ficticia interrumpida; el texto sigue en la sesión.')
    if st.session_state.get('lento_ficticio') and not st.session_state.get('retardo_ficticio_ejecutado'):
        import time
        st.session_state.retardo_ficticio_ejecutado=True
        time.sleep(17)
    return original_guardar(doc,estado,observaciones)
s.guardar=guardar_controlado
planeacion_page()
st.caption('Versiones ficticias guardadas: '+str(len(st.session_state.versiones_ficticias)))
''')
exec(compile(source,__file__,'exec'))

import streamlit as st
from ui.seleccion_contextual import elegir
from services.eventos_continuidad import hojas
from data import repository as repo
from config.settings import ESCUELAS_USAER
from utils.escolar import grado_canonico,grupo_canonico


def recuperar(frame):
    with st.expander('Recuperar una hoja de eventos guardada'):
        if not st.checkbox('Consultar mis hojas',key='evento_recuperar_consultar'):return
        try:opciones=hojas(frame,repo.anexo5().fillna('').to_dict('records'))
        except Exception:
            st.warning('No se pudo leer el historial ahora. Los registros se conservan.');return
        if not opciones:st.info('No hay hojas vinculadas por ID en tu asignación.');return
        porid={r['id']:r for r in opciones}
        elegido=elegir('Hoja a continuar',list(porid),format_func=lambda k:porid[k]['etiqueta']+' · '+porid[k]['fecha']+' · '+str(porid[k]['cantidad'])+' registros',key='evento_recuperar_hoja')
        if st.button('Continuar esta hoja',key='evento_recuperar_abrir'):
            # Los cambios de contexto se respaldan por separado antes de escribir.
            if elegido.startswith('GRUPO-'):
                codigo,grado,grupo=elegido[6:].rsplit('-',2)
                escuela=next((n for n,c in ESCUELAS_USAER.items() if str(c)==codigo),None)
                if not escuela:st.warning('Escuela histórica por verificar.');return
                grados={'1°':'1ro','2°':'2do','3°':'3ro','4°':'4to','5°':'5to','6°':'6to'}
                if grado_canonico(grado) not in grados or grupo_canonico(grupo) not in ('A','B','C','D'):
                    st.warning('El grupo histórico requiere verificar su catálogo; no se modificó la hoja.');return
                st.session_state.update(evento_modo='Grupo / contexto áulico',evento_escuela_grupo=escuela,
                    evento_grado=grados[grado_canonico(grado)],evento_grupo=grupo_canonico(grupo))
            else:
                alumno=frame.loc[frame['ID_Alumno'].astype(str).eq(elegido)].iloc[0]
                st.session_state.update(evento_modo='Alumno individual',evento_alumno=elegido,
                    evento_escuela_individual=str(alumno.get('Nombre_Escuela','')))

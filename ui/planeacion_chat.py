"""Componente de interfaz para el Asistente de Diálogo Pedagógico."""
from copy import deepcopy
import streamlit as st
from ai.planeacion_chat import responder_chat, sintetizar_necesidades


def render_asistente_dialogo(prefix, persist, expandido=True):
    """Muestra un asistente conversacional para docentes cuando falta evidencia en el expediente."""
    doc = st.session_state[prefix + '_doc']
    alumnos = doc['datos'].get('Alumnos', [])
    alumnos_desc = ', '.join(f"{a.get('Nombre_Completo', a.get('Nombre del alumno', 'Alumno'))} ({a.get('Grado', '')}°)" for a in alumnos)
    funcion = doc['datos'].get('Función', 'Docente de Apoyo')
    
    chat_key = prefix + '_chat_mensajes'
    if chat_key not in st.session_state:
        st.session_state[chat_key] = [
            {
                'rol': 'assistant',
                'texto': f"👋 **¡Hola!** Para preparar actividades útiles y adaptadas a **{alumnos_desc or 'tu alumno'}**, cuéntame con tus palabras:\n\n"
                         f"1. ¿Cuáles son sus mayores retos en el salón (lectura, escritura, conteo, atención o lenguaje)?\n"
                         f"2. ¿Qué nivel de desempeño observas y qué apoyos o materiales le han funcionado?"
            }
        ]
    
    mensajes = st.session_state[chat_key]
    
    with st.expander("💬 Asistente de Diálogo Pedagógico (Describir necesidades sin expediente)", expanded=expandido):
        st.caption(
            "Si el expediente no cuenta con informes o antecedentes suficientes, dialoga con el asistente. "
            "Tus respuestas se sintetizarán automáticamente como evidencia docente para habilitar la planeación."
        )
        
        # Historial de mensajes
        for m in mensajes:
            avatar = "👩‍🏫" if m['rol'] == 'user' else "🤖"
            with st.chat_message(m['rol'], avatar=avatar):
                st.markdown(m['texto'])
        
        # Entrada de mensaje
        col_in, col_btn = st.columns([4, 1])
        with col_in:
            nuevo_input = st.text_input(
                "Tu mensaje para el asistente:",
                placeholder="Escribe lo que observas en el alumno (ej. Lee solo vocales, le gustan los dinosaurios, se distrae rápido)...",
                key=prefix + '_chat_text_input',
                label_visibility="collapsed"
            )
        with col_btn:
            enviar = st.button("Enviar 💬", key=prefix + '_chat_enviar', use_container_width=True)
            
        if enviar and nuevo_input and nuevo_input.strip():
            mensajes.append({'rol': 'user', 'texto': nuevo_input.strip()})
            with st.spinner("Pensando respuesta pedagógica..."):
                respuesta = responder_chat(mensajes, alumnos_desc, funcion)
                mensajes.append({'rol': 'assistant', 'texto': respuesta})
            st.rerun()
        
        # Botones de acción
        respuestas_usuario = [m for m in mensajes if m['rol'] == 'user']
        if respuestas_usuario:
            st.markdown("---")
            c1, c2 = st.columns([3, 2])
            with c1:
                st.caption(f"✨ **{len(respuestas_usuario)} aportación(es) registradas.** Cuando estés lista, sintetiza e incorpóralas a tu planeación.")
            with c2:
                if st.button("✨ Incorporar a mi planeación", type="primary", key=prefix + '_chat_incorporar', use_container_width=True):
                    with st.spinner("Estructurando necesidades y apoyos..."):
                        sintesis = sintetizar_necesidades(mensajes, alumnos_desc, funcion)
                        doc_actual = deepcopy(st.session_state[prefix + '_doc'])
                        previas = doc_actual['metadatos'].get('necesidades_confirmadas', '')
                        nueva = f"Antecedente de apoyo documentado por docente:\n{sintesis}"
                        doc_actual['metadatos']['necesidades_confirmadas'] = nueva if not previas else f"{previas}\n\n{nueva}"
                        st.session_state[prefix + '_doc'] = doc_actual
                        persist(prefix, automatic=True)
                        st.success("¡Necesidades educativas incorporadas! La planeación ya cuenta con evidencia para generar.")
                        st.rerun()

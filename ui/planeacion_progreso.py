"""Progreso por hitos reales: no simula el porcentaje interno del proveedor."""
import logging
import streamlit as st


def generar(solicitud,doc,generador=None):
    from ai.planeacion import progreso_generacion
    from ai.planeacion_completa import generar_completa
    generador=generador or generar_completa
    barra=st.progress(10,text='Resumen revisado · preparando la solicitud')
    etapas={'solicitando':(25,'Creando actividades · esperando la respuesta de IA'),
            'reintento':(25,'El servicio está ocupado · reintentando la conexión'),
            'validando':(75,'Respuesta recibida · verificando actividades y evidencias'),
            'corrigiendo':(40,'Corrigiendo la estructura de la propuesta · tu hoja se conserva')}
    ultimo=10
    def avance(etapa):
        nonlocal ultimo
        valor,texto=etapas[etapa];ultimo=max(ultimo,valor);barra.progress(ultimo,text=texto)
    st.caption('La barra avanza por etapas completadas; no representa el tiempo restante del servicio.')
    try:
        with progreso_generacion(avance):
            resultado=generador(solicitud['resumen'],doc['formato'],doc['datos']['Función'],
                solicitud['contexto'],solicitud['ajustes'],solicitud['aliases'],solicitud['evidencias'])
        barra.progress(100,text='Respuesta verificada · lista para revisar')
        return resultado
    except Exception:
        barra.empty()
        raise


def mostrar_error(exc):
    logging.getLogger(__name__).warning('planeacion_ayuda_fallida tipo=%s',type(exc).__name__)
    if isinstance(exc,(ValueError,PermissionError,RuntimeError)):
        st.warning(str(exc))
    else:st.warning('La generación no se completó por un problema del servicio. Tu hoja y el resumen se conservan; puedes reintentar o preparar actividades sin IA.')
    st.caption('No crees otro borrador: puedes continuar desde esta misma hoja. No se incorporó una respuesta sin verificar.')

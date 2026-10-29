"""Activación puntual del motor contextual; no borra sesiones ni reinicia ejecutores."""
import importlib
import sys
import threading

_lock=threading.RLock()
_aplicada=None
_MODULOS=('services.planeacion','services.memoria_pedagogica','ai.planeacion_prompt',
          'ai.planeacion_completa','services.planeacion_generacion',
          'services.planeacion_chat_contextual','services.planeacion_papel',
          'ui.planeacion_memoria','ui.planeacion_chat','ui.planeacion_generacion',
          'ui.planeacion_asistente','ui.planeacion_papel')


def preparar_entrada(version):
    global _aplicada
    with _lock:
        if _aplicada==version:return
        # Solo módulos ya importados. Bloqueos, outbox, transporte de IA y
        # almacenamiento permanecen en sus servicios existentes sin recargar.
        for name in _MODULOS:
            module=sys.modules.get(name)
            if module is not None:importlib.reload(module)
        cliente=sys.modules.get('ai.planeacion')
        prompt=sys.modules.get('ai.planeacion_prompt')
        if cliente is not None and prompt is not None:
            # Refresca funciones/texto, conservando ContextVars de tareas en curso.
            for name in ('INSTRUCCIONES','solicitud','validar_respuesta'):
                setattr(cliente,name,getattr(prompt,name))
        _aplicada=version

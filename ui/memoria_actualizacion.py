"""Activación puntual del motor contextual; no borra sesiones ni reinicia ejecutores."""
import importlib
import sys
import threading

VERSION='2026-10-29-modelos-v2'
_lock=threading.RLock()
_aplicada=None
_MODULOS=('ai.planeacion','ai.documento_json','ai.epp_contextual','services.planeacion','services.memoria_pedagogica','ai.planeacion_prompt',
          'ai.planeacion_completa','services.planeacion_generacion',
          'services.planeacion_chat_contextual','services.planeacion_papel',
          'ui.planeacion_memoria','ui.planeacion_chat','ui.planeacion_generacion',
          'ui.planeacion_asistente','ui.planeacion_papel')


def preparar_entrada(version):
    global _aplicada
    with _lock:
        if _aplicada==version:return
        # Solo módulos ya importados. Bloqueos, outbox, transporte de IA y
        # almacenamiento mantienen sus instancias al actualizar el código.
        for name in _MODULOS:
            module=sys.modules.get(name)
            if module is not None:
                conservados={k:getattr(module,k) for k in ('_pool','_slots','_conexion','_progreso') if hasattr(module,k)}
                importlib.reload(module)
                for k,v in conservados.items():setattr(module,k,v)
        cliente=sys.modules.get('ai.planeacion')
        prompt=sys.modules.get('ai.planeacion_prompt')
        if cliente is not None and prompt is not None:
            # Refresca funciones/texto, conservando ContextVars de tareas en curso.
            for name in ('INSTRUCCIONES','solicitud','validar_respuesta'):
                setattr(cliente,name,getattr(prompt,name))
        generador=sys.modules.get('ai.planeacion')
        if generador is not None:
            for name in ('ui.planeacion','ai.epp'):
                consumidor=sys.modules.get(name)
                if consumidor is not None and hasattr(consumidor,'proponer'):
                    consumidor.proponer=generador.proponer
        _aplicada=version

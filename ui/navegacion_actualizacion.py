"""Actualizar interfaces importadas sin vaciar sesiones ni cachés de datos."""
import importlib
import sys
import threading

VERSION='2026-10-28-documentos-v1'
_lock=threading.RLock()
_ENTRADAS=('ui.planeacion_viva','ui.hub','ui.contenido_modulo')
_MODULOS=('services.navegacion_planeaciones','services.planeacion_papel',
          'documents.planeacion_papel','ui.seleccion_contextual','ui.sidebar',
          'ui.archivo_expediente','ui.eventos_continuidad','ui.estadisticas','ui.pages',
          'ui.planeacion_papel','ui.planeacion_edicion','ui.planeacion_anexo_compartido',
          'ui.planeacion_colaboracion','ui.planeacion_viva','ui.mis_planeaciones',
          'ui.hub','ui.contenido_modulo')


def preparar_entrada():
    from services.navegacion_planeaciones import habilitada
    if not habilitada():return
    with _lock:
        if not any(n in sys.modules and getattr(sys.modules[n],'NAV_VERSION',None)!=VERSION for n in _ENTRADAS):
            return
        # Solo interfaces ya importadas; un arranque nuevo carga desde disco.
        for name in _MODULOS:
            module=sys.modules.get(name)
            if module is not None:importlib.reload(module)
        if any(n in sys.modules and getattr(sys.modules[n],'NAV_VERSION',None)!=VERSION for n in _ENTRADAS):
            raise RuntimeError('La interfaz aún no terminó de actualizarse. La sesión y los documentos se conservan.')

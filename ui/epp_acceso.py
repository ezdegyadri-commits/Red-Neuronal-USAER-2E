"""Entrada versionada: no conservar funciones antiguas tras una actualización parcial de Cloud.

Compatibilidad de despliegue: recargar únicamente el conjunto EPP cuando falta
su marcador. No vacía cachés ni session_state; en un arranque normal no recarga.
"""
import importlib
import threading

VERSION='2026-10-26-colaborativa-v1'
_lock=threading.RLock()
_MODULOS=('services.epp_modelo','services.epp_entrada','services.epp_conclusion',
          'services.epp','services.epp_papel','documents.epp','ui.epp_viva','ui.epp')

def interfaz():
    with _lock:
        module=importlib.import_module('ui.epp')
        if getattr(module,'VERSION_INTERFAZ_EPP',None)!=VERSION:
            for name in _MODULOS:
                loaded=importlib.import_module(name)
                updated=importlib.reload(loaded)
                if name=='ui.epp':module=updated
            if getattr(module,'VERSION_INTERFAZ_EPP',None)!=VERSION:
                raise RuntimeError('La interfaz EPP aún no se actualizó. El informe guardado se conserva.')
        return module.epp_page

def epp_page():
    return interfaz()()

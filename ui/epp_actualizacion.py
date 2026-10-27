"""Comprueba la entrada EPP contra la versión del script principal ejecutado."""
import importlib
import threading

_lock = threading.RLock()


def preparar_entrada(version):
    # No modifica session_state, cachés de datos ni otros módulos. La entrada
    # versionada conserva la responsabilidad de actualizar su interfaz una vez.
    with _lock:
        entrada = importlib.import_module('ui.epp_acceso')
        if getattr(entrada, 'VERSION', None) != version:
            entrada = importlib.reload(entrada)
        if getattr(entrada, 'VERSION', None) != version:
            raise RuntimeError('La actualización EPP aún no está disponible. Tu informe y sesión se conservan.')
        return entrada

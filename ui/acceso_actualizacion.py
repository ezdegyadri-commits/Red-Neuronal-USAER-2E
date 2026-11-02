"""Activación de acceso sin borrar sesiones, motores SQL ni trabajos en curso."""
import importlib,threading
VERSION='A3'
_lock=threading.RLock()
_aplicada=False

def preparar():
    global _aplicada
    with _lock:
        if _aplicada:return
        from data import repository
        from data.acceso_usuarios import usuarios
        from ui import auth
        if getattr(auth,'VERSION_ACCESO',None)!=VERSION:
            importlib.reload(auth)
        # Sustituir referencias importadas antes del cambio sin recargar todo el
        # repositorio: conservar colas, sesiones y conexiones de los documentos.
        repository.usuarios=usuarios
        auth.usuarios=usuarios
        from data.google import clear_cache
        clear_cache('Usuarios')
        _aplicada=True

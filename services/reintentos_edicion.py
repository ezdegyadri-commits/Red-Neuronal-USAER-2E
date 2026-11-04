"""Pausas acotadas de UI; nunca reintenta una escritura dentro del candado."""
import time


def programar(state, prefix, detalle, fecha='_retry_at'):
    intentos=state.get(prefix+'_fallos_io',0)+1
    state[prefix+'_fallos_io']=intentos
    espera=detalle.get('espera',0)
    if intentos>=3 or not espera:
        state[prefix+fecha]=float('inf')
        if intentos>=3:
            detalle={**detalle,'accion':'Se pausaron los reintentos automáticos. Tu edición sigue pendiente; pulsa Reintentar guardado o descarga su respaldo antes de salir.'}
    else:
        state[prefix+fecha]=time.monotonic()+max(15,espera)*2**(intentos-1)
    return detalle

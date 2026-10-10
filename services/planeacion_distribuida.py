"""Puente aditivo: fuente canónica en Sheets, coordinación sin datos educativos."""
from copy import deepcopy
from services.planeacion_estabilidad import GuardadoPendiente


def _confirmado(servicio,values,meta):
    versiones=servicio.reconstruir(values)
    doc=next((v for v in versiones if v['revision']==meta.get('revision')),None)
    if not doc:return None
    headers=values[0];ri=headers.index('Revision');di=headers.index('SHA256')
    if not any(len(row)>max(ri,di) and row[ri]==meta['revision'] and row[di]==meta.get('digest') for row in values[1:]):return None
    return doc


def ejecutar(servicio,cliente,doc,actor,estado,observaciones,aportacion):
    firma=servicio._firma_guardado(doc,estado,observaciones)
    permiso,meta=cliente.solicitar(doc['id'])
    if permiso is None:
        if meta.get('fase')!='INCIERTO':raise GuardadoPendiente(15)
        values=servicio.retry_google(servicio._hoja().get_all_values)
        confirmado=_confirmado(servicio,values,meta)
        if confirmado is None:
            # No caduca por reloj ni se repite un append cuyo resultado se desconoce.
            raise GuardadoPendiente(60)
        if confirmado['id']!=doc['id']:raise RuntimeError('La coordinación requiere revisión. Tu edición se conserva.')
        if not cliente.recuperar(meta):raise GuardadoPendiente(5)
        servicio._confirmar(confirmado)
        for key,value in list(servicio.intentos().items()):
            if key[0]==doc['id'] and value['saved']['revision']==confirmado['revision']:
                servicio.intentos().pop(key,None)
        ultimo=next(v for v in reversed(servicio.reconstruir(values)) if v['id']==doc['id'])
        if meta.get('firma')!=firma or ultimo['revision']!=confirmado['revision']:
            raise RuntimeError('Se confirmó el guardado anterior. Conserva tu edición y concíliala con la versión reciente.')
        return deepcopy(confirmado)
    with permiso:
        # Cada escritor verifica la revisión real dentro de la sección coordinada:
        # los cachés de procesos diferentes nunca autorizan una escritura obsoleta.
        values=servicio.retry_google(servicio._hoja().get_all_values)
        versiones=servicio.reconstruir(values)
        return servicio._guardar_version_local(doc,actor,estado,observaciones,aportacion,versiones,permiso)


def append_confirmable(servicio,rows,permiso,firma):
    if permiso:permiso.iniciar(rows[0][1],rows[0][12],firma)
    try:servicio._hoja().append_rows(rows,value_input_option='RAW')
    except Exception as exc:
        status=getattr(getattr(exc,'response',None),'status_code',None)
        if permiso and (isinstance(exc,GuardadoPendiente) or status in (400,401,403,404,413,429)):
            # Rechazo antes de transmitir o rechazo explícito del servidor.
            permiso.abortar_cierto()
        raise
    if permiso:permiso.confirmar()

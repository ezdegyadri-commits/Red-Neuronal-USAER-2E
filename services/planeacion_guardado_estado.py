"""Causas de guardado legibles, sin trazas ni respuestas privadas del proveedor."""
def diagnostico(exc):
    from services.planeacion_estabilidad import GuardadoPendiente
    from data.google import GoogleTemporal
    if isinstance(exc,GoogleTemporal):
        return {'tipo':'espera' if exc.cuota else 'conexion','causa':str(exc),
                'accion':'Puedes continuar escribiendo. Se reintentará sin crear otra planeación; descarga el respaldo antes de cerrar.','espera':exc.espera}
    status=getattr(getattr(exc,'response',None),'status_code',None)
    if isinstance(exc,GuardadoPendiente) or status==429:
        espera=getattr(exc,'espera',60)
        return {'tipo':'espera','causa':'La conexión alcanzó el límite temporal de guardados.',
                'accion':f'Se reintentará en aproximadamente {espera} segundos. Puedes seguir escribiendo o abrir otra planeación.','espera':espera}
    if status in (500,502,503,504) or isinstance(exc,(TimeoutError,ConnectionError,OSError)) and not isinstance(exc,PermissionError):
        return {'tipo':'conexion','causa':'La base central no respondió o se interrumpió la conexión.',
                'accion':'Revisa tu conexión y pulsa Reintentar guardado. Descarga el respaldo antes de cerrar.','espera':20}
    if status in (401,403) or isinstance(exc,PermissionError):
        return {'tipo':'acceso','causa':'No se pudo validar el acceso a este documento.',
                'accion':'Descarga el respaldo. Revisa la cuenta y escuela asignada antes de volver a entrar.','espera':0}
    if isinstance(exc,ValueError):
        return {'tipo':'validacion','causa':str(exc),
                'accion':'Corrige el dato indicado en el formato y vuelve a guardar. No necesitas crear otro documento.','espera':0}
    if isinstance(exc,RuntimeError):
        if 'eliminado en otra sesión' in str(exc):
            return {'tipo':'archivado','causa':'Este borrador fue marcado como eliminado desde otra sesión; sus versiones siguen conservadas.',
                    'accion':'Descarga esta edición pendiente. En Planeación activa «Mostrar borradores eliminados», selecciona el mismo grado y restaura el borrador. Después recupera el respaldo si contiene texto adicional. Puedes abrir otra planeación sin descartar ésta.','espera':0}
        return {'tipo':'revision','causa':str(exc),
                'accion':'Descarga tu respaldo y consulta la versión reciente. No se sobrescribirá una edición en conflicto.','espera':0}
    return {'tipo':'servicio','causa':'El servicio no confirmó el guardado.',
            'accion':'Conserva la pestaña abierta, descarga el respaldo y pulsa Reintentar guardado. Si persiste, informa a Dirección.','espera':20}

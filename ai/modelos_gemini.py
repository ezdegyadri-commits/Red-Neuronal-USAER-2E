"""Recuperación acotada ante modelos retirados, común a todas las áreas."""
import hashlib
import re
import time
from threading import RLock

_lock=RLock()
_catalogos={}
_resueltos={}
_TTL=300


def _codigo(exc):
    try:return int(getattr(exc,'code',0))
    except (TypeError,ValueError):return 0


def _nombre(value):return str(value or '').removeprefix('models/').strip()


def _disponibles(cli,clave,refrescar=False):
    ahora=time.monotonic()
    with _lock:
        cached=_catalogos.get(clave)
        if not refrescar and cached and ahora-cached[0]<_TTL:return list(cached[1])
        modelos=[]
        # ListModels solo consulta metadatos: no envía el documento al catálogo.
        for i,m in enumerate(cli.models.list(config={'page_size':100})):
            if i>=200:break
            name=_nombre(getattr(m,'name',''))
            actions=getattr(m,'supported_actions',None) or []
            if ('generateContent' in actions and name.startswith('gemini-')
                    and not any(t in name.lower() for t in ('image','audio','tts','live','robotics','computer-use','embedding','deep-research'))):
                modelos.append(name)
        modelos=list(dict.fromkeys(modelos))
        if len(_catalogos)>=16:_catalogos.pop(next(iter(_catalogos)))
        _catalogos[clave]=(ahora,modelos)
        return modelos


def generar(cli,*,model,api_key,**kwargs):
    solicitado=_nombre(model)
    clave=hashlib.sha256(str(api_key).encode()).hexdigest()
    key=(clave,solicitado)
    with _lock:
        cached=_resueltos.get(key)
        efectivo=cached[1] if cached and time.monotonic()-cached[0]<_TTL else solicitado
    def argumentos(nombre):
        config=kwargs.get('config')
        if nombre!=solicitado and isinstance(config,dict) and 'thinking_config' in config:
            config=dict(config);config.pop('thinking_config')
            return {**kwargs,'config':config}
        return kwargs
    try:return cli.models.generate_content(model=efectivo,**argumentos(efectivo))
    except Exception as original:
        if _codigo(original)!=404:raise
        fallidos={solicitado,efectivo}
        try:disponibles=_disponibles(cli,clave,refrescar=efectivo!=solicitado)
        except Exception:raise original from None
        familia='pro' if 'pro' in solicitado.lower() else 'flash'
        def orden(nombre):
            versiones=[int(v) for v in re.findall(r'\d+',nombre)[:2]]
            return (familia not in nombre,any(t in nombre for t in ('preview','experimental','exp-')),
                    tuple(-v for v in versiones),nombre)
        candidatos=sorted((m for m in disponibles if m not in fallidos),key=orden)[:2]
        ultimo=original
        for candidato in candidatos:
            try:
                respuesta=cli.models.generate_content(model=candidato,**argumentos(candidato))
            except Exception as exc:
                if _codigo(exc)!=404:raise
                ultimo=exc;continue
            with _lock:
                if len(_resueltos)>=64:_resueltos.pop(next(iter(_resueltos)))
                _resueltos[key]=(time.monotonic(),candidato)
            return respuesta
        raise ultimo from None

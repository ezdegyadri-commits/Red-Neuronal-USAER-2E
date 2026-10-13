"""Control transaccional PostgreSQL. No recibe contenido educativo ni nombres."""
from contextlib import AbstractContextManager
import hashlib
import logging
import re
from urllib.parse import urlsplit
from uuid import uuid4
import requests
import streamlit as st
from utils.guardado import GuardadoPendiente

logger=logging.getLogger(__name__)


class SupabaseRest:
    def __init__(self,url,token):
        p=urlsplit(str(url))
        if p.scheme!='https' or not p.hostname or not p.hostname.endswith('.supabase.co') or p.username or p.password or p.query or p.fragment or p.path not in ('','/') or p.port not in (None,443) or not token:
            raise ValueError('La coordinación necesita una URL HTTPS de Supabase y una clave secreta de servidor en Secrets.')
        self.url=str(url).rstrip('/');self.token=str(token)

    def operar(self,namespace,accion,**kwargs):
        if accion not in ('ADQUIRIR','INICIAR','LIBERAR','RECUPERAR','PRESUPUESTO') or not set(kwargs)<={'clave','token','revision','digest','firma','tipo'}:
            raise ValueError('Solo se admiten metadatos operativos de coordinación.')
        headers={'apikey':self.token,'Content-Type':'application/json'}
        if self.token.startswith('eyJ'):headers['Authorization']='Bearer '+self.token
        try:
            response=requests.post(self.url+'/rest/v1/rpc/usaer_coord_operar',json={'p_namespace':namespace,'p_accion':accion,**{'p_'+k:v for k,v in kwargs.items()}},headers=headers,timeout=(3,5),allow_redirects=False)
            if response.status_code!=200:raise ValueError('Respuesta no válida')
            body=response.json()
            if not isinstance(body,dict) or 'ok' not in body:raise ValueError('Respuesta no válida')
            return body
        except Exception:
            # Nunca mostrar tokens, URL, cuerpos ni texto de errores remotos.
            logger.warning('coordinacion_compartida_no_disponible')
            raise GuardadoPendiente(30) from None


class Coordinador:
    def __init__(self,backend,namespace):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{3,64}',str(namespace)):
            raise ValueError('Revisa el namespace: debe ser idéntico en todas las instancias.')
        self.backend=backend;self.namespace=str(namespace)

    def clave(self,documento):return hashlib.sha256(str(documento).encode()).hexdigest()

    def solicitar(self,documento):
        key=self.clave(documento);token=uuid4().hex
        response=self.backend.operar(self.namespace,'ADQUIRIR',clave=key,token=token)
        if response.get('ok') is True:return Permiso(self,key,token),None
        meta=response.get('meta')
        if not isinstance(meta,dict):raise GuardadoPendiente(30)
        return None,{'clave':key,**meta}

    def recuperar(self,meta):
        return self.backend.operar(self.namespace,'RECUPERAR',clave=meta['clave'],token=meta['token'],revision=meta['revision'],digest=meta['digest']).get('ok') is True

    def reservar(self,tipo):
        if tipo not in ('lectura','escritura'):raise ValueError('Presupuesto desconocido.')
        response=self.backend.operar(self.namespace,'PRESUPUESTO',tipo=tipo)
        espera=response.get('espera')
        if response.get('ok') is not True or not isinstance(espera,int) or isinstance(espera,bool):raise GuardadoPendiente(30)
        if espera:raise GuardadoPendiente(espera)


class Permiso(AbstractContextManager):
    def __init__(self,coordinador,key,token):
        self.coordinador,self.key,self.token=coordinador,key,token
        self.incierto=False;self.completo=False

    def iniciar(self,revision,digest,firma):
        if not re.fullmatch('[a-f0-9]{32}',revision) or any(not re.fullmatch('[a-f0-9]{64}',v) for v in (digest,firma)):
            raise ValueError('Metadatos de operación no válidos.')
        self.incierto=True
        result=self.coordinador.backend.operar(self.coordinador.namespace,'INICIAR',clave=self.key,token=self.token,revision=revision,digest=digest,firma=firma)
        if result.get('ok') is not True:raise GuardadoPendiente(15)

    def abortar_cierto(self):self.incierto=False
    def confirmar(self):self.completo=True

    def __exit__(self,*args):
        if self.incierto and not self.completo:return False
        try:self.coordinador.backend.operar(self.coordinador.namespace,'LIBERAR',clave=self.key,token=self.token)
        except GuardadoPendiente:logger.warning('coordinacion_liberacion_pendiente')
        return False


@st.cache_resource(show_spinner=False)
def coordinador():
    try:config=dict(st.secrets.get('coordinacion_planeacion',{}))
    except (FileNotFoundError,KeyError):return None
    enabled=config.get('habilitada',False)
    if not isinstance(enabled,bool):raise ValueError('habilitada debe ser true o false en Secrets.')
    if not enabled:return None
    # No caer a candados locales si se activó una configuración incompleta.
    return Coordinador(SupabaseRest(config.get('url',''),config.get('token','')),config.get('namespace',''))

"""Actualización aditiva de Spark existente: respaldo previo, mismo supervisor y secretos."""
import argparse
import getpass
import hashlib
import shlex
import http.cookiejar
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
RELEASE='usaer-rc1-spark-20261105'


def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL).decode().strip()


def columnas_pendientes(db,metadata):
    from sqlalchemy import inspect
    i=inspect(db);presentes=set(i.get_table_names(schema='public'))
    incompatibles=[]
    for tabla in metadata.sorted_tables:
        if tabla.name in presentes:
            columnas={c['name'] for c in i.get_columns(tabla.name,schema='public')}
            if set(tabla.columns.keys())-columnas:incompatibles.append(tabla.name)
    if incompatibles:raise RuntimeError('Hay columnas pendientes de migración controlada. No se cambia el código activo.')
    return [t for t in metadata.sorted_tables if t.name not in presentes]


def migracion_aditiva(engine,cfg):
    from sqlalchemy import create_engine,text
    from sqlalchemy.engine import make_url
    from data.database import Base
    from deploy import uppcoder
    with engine.connect() as db:pendientes=columnas_pendientes(db,Base.metadata)
    if not pendientes:return
    usuario=input('Usuario PostgreSQL de migración ['+uppcoder.USUARIO_DB+']: ').strip() or uppcoder.USUARIO_DB
    if usuario==cfg['db_user']:raise RuntimeError('La migración requiere una cuenta distinta del rol operativo.')
    clave=getpass.getpass('Contraseña PostgreSQL de migración (sin eco; no se guarda): ')
    url=make_url(os.environ['DATABASE_URL']).set(username=usuario,password=clave)
    motor=create_engine(url,hide_parameters=True,connect_args={'connect_timeout':8,'options':'-c search_path=public'})
    previo=os.environ['USAER_UPPCODER_DB_USER']
    try:
        os.environ['USAER_UPPCODER_DB_USER']=usuario
        with motor.begin() as db:
            uppcoder.verificar_instalacion(db,migracion=True)
            db.execute(text("SET LOCAL lock_timeout='5s'"))
            db.execute(text('SELECT pg_advisory_xact_lock(17002200)'))
            pendientes=columnas_pendientes(db,Base.metadata)
            Base.metadata.create_all(db,tables=pendientes)
            citar=db.dialect.identifier_preparer.quote_identifier
            for t in pendientes:
                db.exec_driver_sql('GRANT SELECT, INSERT, UPDATE, DELETE ON public.'+citar(t.name)+' TO '+citar(cfg['db_user']))
    finally:
        os.environ['USAER_UPPCODER_DB_USER']=previo
        motor.dispose();clave=None
    print('Tablas adicionales preparadas; usuarios y registros existentes conservados.',flush=True)


class RedireccionPrivada(urllib.request.HTTPRedirectHandler):
    def __init__(self,host):self.host=host
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        destino=urllib.parse.urlsplit(newurl)
        if destino.scheme!='https' or destino.netloc!=self.host:
            raise RuntimeError('La puerta de acceso requiere autenticación manual; no se reenvían credenciales a otro host.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def cliente_https(host):
    return urllib.request.build_opener(RedireccionPrivada(host),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def solicitar(cliente,host,ruta,datos=None,token=None):
    headers={'X-USAER-Client':'browser','Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    inicio=time.perf_counter()
    req=urllib.request.Request('https://'+host+ruta,data=None if datos is None else json.dumps(datos).encode(),headers=headers)
    with cliente.open(req,timeout=25) as r:contenido=r.read()
    return contenido,round((time.perf_counter()-inicio)*1000,1)


def comprobar_https(cliente,host,usuario,clave):
    html,apertura=solicitar(cliente,host,'/')
    if b'/assets/app.js' not in html:raise RuntimeError('HTTPS no está entregando React.')
    salud,_=solicitar(cliente,host,'/api/health')
    if json.loads(salud).get('release')!=RELEASE:raise RuntimeError('El supervisor aún no sirve esta candidata.')
    respuesta,_=solicitar(cliente,host,'/api/auth/login',{'usuario':usuario,'password':clave})
    token=json.loads(respuesta).get('token')
    # El navegador recibe cookie HttpOnly; no se necesita imprimir ni persistir un token.
    alumnos,_=solicitar(cliente,host,'/api/alumnos',token=token)
    alumnos=json.loads(alumnos)
    ficticios=[a for a in alumnos if a['id'].startswith('alu-uppcoder-') and 'fictici' in a['nombre_completo'].lower()]
    if not ficticios:raise RuntimeError('No hay alumnos iniciales ficticios autorizados para la prueba.')
    tiempos=[]
    for escuela in dict.fromkeys(a['id_escuela'] for a in ficticios):
        _,ms=solicitar(cliente,host,'/api/alumnos?escuela='+urllib.parse.quote(escuela),token=token);tiempos.append(ms)
    creado,_=solicitar(cliente,host,'/api/planeaciones/nueva',{'modalidad':'individual','alumnos':[ficticios[0]['id']]},token)
    ruta='/api/planeaciones/'+json.loads(creado)['id']
    doc=json.loads(solicitar(cliente,host,ruta,token=token)[0])
    marca='Comprobación ficticia RC1 '+datetime.now(timezone.utc).isoformat()
    doc['metadatos']['titulo']=marca
    _,guardar=solicitar(cliente,host,'/api/planeaciones',doc,token)
    reabierto=json.loads(solicitar(cliente,host,ruta,token=token)[0])
    if reabierto['metadatos']['titulo']!=marca:raise RuntimeError('No se confirmó el guardado y reapertura.')
    pdf,_=solicitar(cliente,host,ruta+'/pdf',token=token)
    if not pdf.startswith(b'%PDF'):raise RuntimeError('La exportación no es PDF.')
    solicitar(cliente,host,'/api/auth/logout',{},token)
    return {'https':'https://'+host,'react':'comprobado','login':'correcto','guardado_reapertura_pdf':'correctos',
            'apertura_ms':apertura,'cambio_escuela_api_ms':tiempos,'guardado_ms':guardar}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--revision',required=True)
    args=p.parse_args();repo=args.repo.expanduser().resolve()
    if sys.platform!='linux' or repo!=Path.home().resolve()/'app/usaer2e':raise RuntimeError('Solo el clon existente ~/app/usaer2e de Spark.')
    if not re.fullmatch('[0-9a-f]{40}',args.revision):raise RuntimeError('Fija un commit completo revisado.')
    if git(repo,'rev-parse',args.revision)!=args.revision:raise RuntimeError('El commit no está disponible.')
    if git(repo,'status','--porcelain') or git(repo,'branch','--show-current')=='main':raise RuntimeError('El clon debe estar limpio y fuera de main; no se descartan cambios.')
    original=git(repo,'rev-parse','HEAD')
    inicio=repo.parent/'main.py'
    if inicio.is_symlink() or inicio.read_bytes()!=(ROOT/'deploy/main_spark.py').read_bytes():raise RuntimeError('El adaptador del supervisor no coincide; se conserva sin cambios.')
    from deploy import uppcoder
    uppcoder.cargar_spark();uppcoder.configurar();uppcoder.verificar_url()
    cfg=json.loads(uppcoder.CONFIG_SPARK.read_text())
    if not cfg.get('separado'):raise RuntimeError('Conserva la separación entre rol operativo y migración.')
    from data.database import get_engine
    engine=get_engine(initialize_schema=False)
    with engine.connect() as db:uppcoder.verificar_instalacion(db)
    if shutil.disk_usage(repo).free<64*1024*1024:raise RuntimeError('No hay 64 MiB libres; no se modifica el servicio.')
    dump=shutil.which('pg_dump');restore=shutil.which('pg_restore')
    if not dump or not restore:raise RuntimeError('Faltan pg_dump y pg_restore 17 en el entorno; no se cambia el servicio.')
    if not all(re.search(r'\b17\.',subprocess.check_output([x,'--version']).decode()) for x in (dump,restore)):
        raise RuntimeError('Los clientes de respaldo deben ser PostgreSQL 17.')
    carpeta=uppcoder.CONFIG_SPARK.parent/'respaldos';carpeta.mkdir(mode=0o700,exist_ok=True)
    if carpeta.is_symlink():raise RuntimeError('El directorio de respaldo no admite enlaces.')
    carpeta.chmod(0o700)
    respaldo=carpeta/('antes-rc1-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'.dump')
    from deploy.respaldo_spark import respaldar
    from sqlalchemy.engine import make_url
    respaldar(make_url(os.environ['DATABASE_URL']),respaldo,pg_dump=dump)
    lista=subprocess.check_output([restore,'--list',str(respaldo)],stderr=subprocess.DEVNULL)
    if b'TABLE DATA public spa_sesiones ' in lista or b'TABLE DATA public spa_intentos_acceso ' in lista:
        raise RuntimeError('El respaldo no debe reactivar sesiones.')
    with respaldo.open('rb') as archivo:
        resumen=hashlib.file_digest(archivo,'sha256').hexdigest()
    respaldo.with_suffix('.sha256').write_text(resumen+'  '+respaldo.name+'\n',encoding='ascii')
    reversion=respaldo.with_suffix('.revertir-codigo.sh')
    instrucciones=['#!/bin/sh','set -eu','cd '+shlex.quote(str(repo)),
                   'git diff --quiet','git diff --cached --quiet','git switch --detach '+original,
                   'touch '+shlex.quote(str(inicio))]
    reversion.write_text('\n'.join(instrucciones)+'\n',encoding='utf-8')
    reversion.chmod(0o700)
    (respaldo.with_suffix('.codigo.json')).write_text(json.dumps({'anterior':original,'nuevo':args.revision,'sesiones_restaurables':False}),encoding='utf-8')
    print('Respaldo PostgreSQL privado creado y archivo verificado; sesiones excluidas.',flush=True)
    host=uppcoder.host_publico();cliente=cliente_https(host)
    enlace=getpass.getpass('Enlace privado HTTPS del stack, si exige puerta de acceso (Enter si no): ').strip()
    if enlace:
        u=urllib.parse.urlsplit(enlace)
        if u.scheme!='https' or u.netloc!=host or u.username or u.password:raise RuntimeError('El enlace privado debe pertenecer exactamente al host configurado.')
        with cliente.open(enlace,timeout=25) as r:r.read(1)
    usuario=input('Usuario del piloto [direccion.piloto]: ').strip() or 'direccion.piloto'
    clave=getpass.getpass('Contraseña actual del piloto (sin eco; no se guarda): ')
    # Validar las credenciales antes de cambiar código; nunca se crean cuentas ni contraseñas.
    solicitar(cliente,host,'/api/auth/login',{'usuario':usuario,'password':clave})
    migracion_aditiva(engine,cfg)
    engine.dispose()
    cambiado=False
    try:
        subprocess.run(['git','-C',str(repo),'switch','--detach',args.revision],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        cambiado=True
        # Uppcoder documenta uvicorn main:app --reload; no se crea otro Uvicorn.
        inicio.touch()
        confirmado=False
        for _ in range(15):
            try:
                salud=json.loads(solicitar(cliente,host,'/api/health')[0])
                if salud.get('release')==RELEASE:confirmado=True;break
            except (OSError,ValueError):pass
            time.sleep(2)
        if not confirmado:raise RuntimeError('El supervisor no recargó la candidata; requiere Restart de FastAPI en el panel.')
        resultado=comprobar_https(cliente,host,usuario,clave)
        print(json.dumps({**resultado,'commit':args.revision,'respaldo':str(respaldo),'reversion_codigo':str(reversion),'sha256_respaldo':resumen},ensure_ascii=False),flush=True)
    except Exception:
        if cambiado:
            subprocess.run(['git','-C',str(repo),'switch','--detach',original],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            inicio.touch()
            print('Se repuso el código anterior. PostgreSQL y las cuentas no se borraron.',flush=True)
        raise
    finally:clave=None


if __name__=='__main__':
    try:main()
    except Exception as exc:
        if isinstance(exc,RuntimeError):print(str(exc),file=sys.stderr)
        else:print('Actualización detenida con seguridad. No se imprimen credenciales ni errores SQL. Revisa acceso HTTPS, credenciales o permisos de migración.',file=sys.stderr)
        raise SystemExit(1) from None

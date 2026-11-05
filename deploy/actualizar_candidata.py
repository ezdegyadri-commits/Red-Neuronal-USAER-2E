"""Aplica o revierte exclusivamente archivos de código de una candidata local."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile
from datetime import datetime, timezone

RAICES=('piloto_spa/','services/','documents/','tests/','deploy/')

def huella(data):
    # Git conserva LF; una copia Windows puede tener CRLF.
    return hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()

def ruta_segura(raiz,nombre):
    p=PurePosixPath(nombre)
    if p.is_absolute() or '..' in p.parts or '\\' in nombre or ':' in nombre or not nombre.startswith(RAICES):
        raise ValueError('Ruta de código no permitida.')
    if p.name.startswith('.env') or p.suffix.lower() in {'.db','.sqlite','.dump','.xlsx','.csv','.dpapi','.pem','.key','.log'}:
        raise ValueError('El paquete contiene un archivo privado o ajeno al código.')
    destino=(raiz/Path(*p.parts)).resolve()
    if not destino.is_relative_to(raiz.resolve()):raise ValueError('Ruta fuera del clon.')
    return destino

def ejecutar(destino,paquete,aplicar=False,revertir=False):
    destino=destino.resolve()
    branch=subprocess.run(['git','-C',str(destino),'branch','--show-current'],capture_output=True,text=True,check=True).stdout.strip()
    if not branch or branch=='main':raise ValueError('Selecciona un clon de prueba en una rama independiente de main.')
    with zipfile.ZipFile(paquete) as z:
        if z.testzip():raise ValueError('ZIP con error de integridad.')
        m=json.loads(z.read('manifest.json'))
        if m.get('tipo')!=('USAER-reversion-codigo-v1' if revertir else 'USAER-candidata-codigo-v1'):
            raise ValueError('Tipo de paquete incorrecto.')
        preparados=[]
        for f in m['archivos']:
            p=ruta_segura(destino,f['ruta'])
            actual=p.read_bytes() if p.exists() else None
            esperado=f['actual'] if revertir else f['anterior']
            objetivo=f['anterior'] if revertir else f['actual']
            if (huella(actual) if actual is not None else None) not in (esperado,objetivo):
                raise ValueError('Hay cambios locales en '+f['ruta']+'; no se sobrescribieron.')
            contenido=z.read('codigo/'+f['ruta']) if objetivo is not None else None
            if contenido is not None and huella(contenido)!=objetivo:raise ValueError('Huella de código incorrecta.')
            preparados.append((p,actual,contenido,f))
        if not aplicar:return {'estado':'previsualizado','archivos':len(preparados),'base':m.get('base','')}
        respaldo=None
        if not revertir:
            respaldo=destino.parent/('reversion-codigo-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.zip')
            with zipfile.ZipFile(respaldo,'x',zipfile.ZIP_DEFLATED) as b:
                filas=[]
                for p,actual,contenido,f in preparados:
                    filas.append({**f,'anterior':huella(actual) if actual is not None else None})
                    if actual is not None:b.writestr('codigo/'+f['ruta'],actual)
                b.writestr('manifest.json',json.dumps({'tipo':'USAER-reversion-codigo-v1','archivos':filas}))
        escritos=[]
        try:
            for p,actual,contenido,f in preparados:
                escritos.append((p,actual))
                if contenido is None:
                    if p.exists():p.unlink()
                else:
                    p.parent.mkdir(parents=True,exist_ok=True)
                    temporal=p.with_name(p.name+'.usaer-candidata-tmp')
                    if temporal.exists():raise ValueError('Hay una actualización temporal pendiente.')
                    temporal.write_bytes(contenido);temporal.replace(p)
        except Exception:
            for p,actual in reversed(escritos):
                if actual is None:
                    if p.exists():p.unlink()
                else:p.write_bytes(actual)
            raise
        return {'estado':'revertido' if revertir else 'aplicado','archivos':len(preparados),'reversion':str(respaldo) if respaldo else None,
                'base_de_datos':'sin cambios','servicios':'sin reinicios'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destino',type=Path,required=True)
    p.add_argument('--paquete',type=Path,required=True)
    p.add_argument('--aplicar',action='store_true')
    p.add_argument('--revertir',action='store_true')
    a=p.parse_args()
    try:print(json.dumps(ejecutar(a.destino,a.paquete,a.aplicar,a.revertir),ensure_ascii=False))
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError,zipfile.BadZipFile):
        raise SystemExit('Actualización detenida: verifica rama de prueba, paquete íntegro y ausencia de cambios locales. No se reiniciaron servicios ni se alteró PostgreSQL.')

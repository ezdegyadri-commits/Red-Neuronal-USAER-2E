"""Empaqueta exclusivamente código confirmado desde la base de la candidata."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile
from deploy.actualizar_candidata import huella, ruta_segura

ROOT=Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])

def empaquetar(base,salida):
    revision=git('rev-parse','HEAD').decode().strip()
    base=git('rev-parse',base+'^{commit}').decode().strip()
    subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',base,revision],check=True)
    archivos=git('diff','--name-only','--diff-filter=AM',base,revision).decode().splitlines()
    if not archivos:raise ValueError('No hay cambios confirmados.')
    contenido={};filas=[]
    for nombre in archivos:
        ruta_segura(ROOT,nombre)
        datos=git('show',revision+':'+nombre)
        if re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{25,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|AIza[0-9A-Za-z_-]{30,}|postgres(?:ql)?(?:\+\w+)?://[^\s:/]+:[^\s@]+@)',datos):
            raise ValueError('El código requiere revisión de secretos antes de empaquetarse.')
        existe=subprocess.run(['git','-C',str(ROOT),'cat-file','-e',base+':'+nombre],capture_output=True).returncode==0
        anterior=huella(git('show',base+':'+nombre)) if existe else None
        filas.append({'ruta':nombre,'anterior':anterior,'actual':huella(datos)})
        contenido['codigo/'+nombre]=datos
    manifest={'tipo':'USAER-candidata-codigo-v1','version':'RC1','base':base,'commit':revision,
              'integridad':'SHA256 con finales de línea LF','archivos':filas,'migracion_sql':False}
    salida=salida.resolve();salida.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(salida,'x',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        for nombre,datos in contenido.items():z.writestr(nombre,datos)
    with zipfile.ZipFile(salida) as z:
        if z.testzip():raise ValueError('ZIP no verificable.')
        for f in filas:
            if huella(z.read('codigo/'+f['ruta']))!=f['actual']:raise ValueError('Huella incorrecta.')
    digest=hashlib.sha256(salida.read_bytes()).hexdigest()
    salida.with_suffix('.zip.sha256').write_text(digest+'  '+salida.name+'\n',encoding='ascii')
    return {'zip':str(salida),'archivos':len(filas),'commit':revision,'sha256':digest,'integridad':'verificada'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',default='d0f4067')
    p.add_argument('--salida',required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(empaquetar(a.base,a.salida),ensure_ascii=False))

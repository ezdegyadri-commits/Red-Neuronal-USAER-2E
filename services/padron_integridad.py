"""Diagnóstico puro y propuesta reversible; nunca escribe ni fusiona registros."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import re
from utils.escolar import separar_grado_grupo


def huella(rows):
    return hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()


def diagnosticar(alumnos,escuelas,documentos=()):
    avisos=[];cambios=[];esc={str(e.get('ID_Escuela','')):e for e in escuelas}
    ids=Counter(str(r.get('ID_Alumno','')) for r in alumnos)
    curps=Counter(str(r.get('CURP','')).strip().upper() for r in alumnos if str(r.get('CURP','')).strip())
    ccts=Counter(str(e.get('CCT_Escuela',e.get('CCT',''))).strip().upper() for e in escuelas)
    for c,n in ccts.items():
        if c and n>1:avisos.append({'tipo':'CCT repetida en catálogo','registro':'escuelas','detalle':'Revisar identidades; no se fusiona automáticamente.'})
    for r in alumnos:
        aid=str(r.get('ID_Alumno',''));eid=str(r.get('ID_Escuela',''));propuesta={}
        if not aid or ids[aid]>1:avisos.append({'tipo':'ID de alumno ausente o repetido','registro':aid,'detalle':'Identidad no apta para migración automática.'});continue
        if curps.get(str(r.get('CURP','')).strip().upper(),0)>1:avisos.append({'tipo':'CURP repetida','registro':aid,'detalle':'Conciliar por identificadores y documentos; no por nombre.'})
        if eid not in esc:avisos.append({'tipo':'Escuela sin referencia','registro':aid,'detalle':'Confirmar ID y CCT con Dirección.'})
        try:
            grado,grupo=separar_grado_grupo(r.get('Grado',''),r.get('Grupo',''))
            if grado and not re.fullmatch(r'[1-6]°',grado):raise ValueError()
            for k,v in (('Grado',grado),('Grupo',grupo)):
                if v!=str(r.get(k,'') or '').strip():propuesta[k]=v
        except ValueError:avisos.append({'tipo':'Grado/grupo ambiguo','registro':aid,'detalle':'No normalizar hasta confirmar la asignación.'})
        if eid in esc:
            oficial=str(esc[eid].get('CCT_Escuela',esc[eid].get('CCT',''))).strip().upper()
            actual=str(r.get('CCT_Escuela','')).strip()
            if actual and oficial and actual.upper()!=oficial:avisos.append({'tipo':'CCT contradictoria','registro':aid,'detalle':'Confirmar la escuela; no reasignar automáticamente.'})
            elif actual and actual!=actual.upper():propuesta['CCT_Escuela']=actual.upper()
        if propuesta:cambios.append({'ID_Alumno':aid,'antes':{k:r.get(k,'') for k in propuesta},'despues':propuesta})
    for d in documentos:
        did=str(d.get('id',''))
        for a in d.get('datos',{}).get('Alumnos',[]):
            if str(a.get('ID_Alumno','')) not in ids:avisos.append({'tipo':'Documento con referencia histórica no presente','registro':did,'detalle':'Conservar documento; revisar baja o referencia histórica.'})
        ciclo=str(d.get('datos',{}).get('Curso escolar',''))
        m=re.fullmatch(r'(\d{4})[-–](\d{4})',ciclo)
        if not m or int(m[2])!=int(m[1])+1:avisos.append({'tipo':'Ciclo documental no canónico','registro':did,'detalle':'Revisar sin convertir documentos históricos.'})
    return {'base':huella(alumnos),'avisos':avisos,'cambios_propuestos':cambios,
        'conteos':{'alumnos':len(alumnos),'escuelas':len(escuelas),'documentos':len(documentos)},
        'regla':'Diagnóstico de sólo lectura. Ninguna ausencia autoriza bajas ni eliminación. Validar respaldo y equivalencias antes de migrar.'}


def simular(alumnos,plan,revertir=False):
    """Usado para ensayos y reversión sobre una copia, con precondiciones exactas."""
    if not revertir and huella(alumnos)!=plan['base']:raise ValueError('Cambió la base; repite el diagnóstico.')
    result=deepcopy(alumnos);index={str(r.get('ID_Alumno')):r for r in result}
    if len(index)!=len(result):raise ValueError('Hay identificadores duplicados.')
    for cambio in plan['cambios_propuestos']:
        r=index[cambio['ID_Alumno']];antes,despues=(cambio['despues'],cambio['antes']) if revertir else (cambio['antes'],cambio['despues'])
        if any(r.get(k,'')!=v for k,v in antes.items()):raise ValueError('El registro cambió; no se sobrescribirá.')
        r.update(deepcopy(despues))
    return result

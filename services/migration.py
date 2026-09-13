from datetime import date
from data import repository as repo
from utils.ids import expediente_id
from utils.text import normalizar_texto

def _next_id(values, prefix):
    nums=[]
    for v in values:
        try: nums.append(int(str(v).split('-')[-1]))
        except Exception: pass
    return f'{prefix}-{(max(nums)+1 if nums else 1):03d}'

def migrate_existing_data():
    """Migración aditiva, idempotente y sin modificar ninguna hoja histórica."""
    repo.ensure_integrated_sheets()
    alumnos=repo.alumnos()
    if alumnos.empty or 'ID_Alumno' not in alumnos.columns:
        return {'alumnos':0,'relaciones':0,'timeline':0,'no_encontrados':0}
    a3,a4,a5=repo.anexo3(),repo.anexo4(),repo.anexo5()
    exps=repo.read('Expedientes'); rels=repo.read('Relaciones_Expediente'); tls=repo.read('Linea_Tiempo')
    existing_exp=set(exps.get('ID_Expediente',[]).astype(str)) if not exps.empty else set()
    existing_rel=set(zip(rels.get('ID_Expediente',[]).astype(str),rels.get('Tipo_Registro',[]).astype(str),rels.get('ID_Registro',[]).astype(str))) if not rels.empty else set()
    existing_tl=set(zip(tls.get('ID_Expediente',[]).astype(str),tls.get('Tipo',[]).astype(str),tls.get('Titulo',[]).astype(str),tls.get('Fecha',[]).astype(str))) if not tls.empty else set()
    today=str(date.today())
    exp_rows=[]; rel_rows=[]; tl_rows=[]
    exp_ids=list(existing_exp); rel_ids=list(rels.get('ID_Relacion',[]).astype(str)) if not rels.empty else []; tl_ids=list(tls.get('ID_Evento_Timeline',[]).astype(str)) if not tls.empty else []
    name_to_id={}
    for _,r in alumnos.iterrows():
        aid=str(r.get('ID_Alumno','')).strip(); name=normalizar_texto(r.get('Nombre_Completo',''))
        if name and name not in name_to_id: name_to_id[name]=aid
        eid=expediente_id(aid)
        if aid and eid not in existing_exp:
            exp_rows.append({'ID_Expediente':eid,'ID_Alumno':aid,'Estatus':'ACTIVO','Fecha_Apertura':today,'Ultima_Actualizacion':today}); existing_exp.add(eid); exp_ids.append(eid)
    if exp_rows: repo.google_append_rows_raw('Expedientes',exp_rows)
    for df,tipo,idcol,datecol,title,usr in [(a3,'ANEXO3','ID_Anexo3','Fecha','BAP','ID_Personal'),(a4,'ANEXO4','ID_Anexo4','Fecha_Elaboracion','SUGERENCIA','Quien_Brinda_Sugerencias'),(a5,'ANEXO5','ID_Evento','Fecha','SEGUIMIENTO','Especialista')]:
        for _,r in (df.iterrows() if not df.empty else []):
            aid=str(r.get('ID_Alumno','')).strip() if tipo=='ANEXO3' else name_to_id.get(normalizar_texto(r.get('Nombre_Alumno','')),'')
            if not aid: continue
            eid=expediente_id(aid); rid=str(r.get(idcol,'')); fecha=str(r.get(datecol,today)); key=(eid,tipo,rid)
            if rid and key not in existing_rel:
                new_rel_id=_next_id(rel_ids,'REL'); rel_rows.append({'ID_Relacion':new_rel_id,'ID_Expediente':eid,'ID_Alumno':aid,'Tipo_Registro':tipo,'ID_Registro':rid,'Fecha':fecha,'Estado':'ACTIVO'}); rel_ids.append(new_rel_id); existing_rel.add(key)
            tkey=(eid,tipo,title,fecha)
            if tkey not in existing_tl:
                descripcion=str(r.get('Estatus_IA','')) if tipo=='ANEXO3' else (str(r.get('Sugerencias',''))[:500] if tipo=='ANEXO4' else str(r.get('Evento',''))[:500])
                tid=_next_id(tl_ids,'TL'); tl_rows.append({'ID_Evento_Timeline':tid,'ID_Expediente':eid,'ID_Alumno':aid,'Fecha':fecha,'Tipo':tipo,'Titulo':title,'Descripcion':descripcion,'Usuario':str(r.get(usr,''))}); tl_ids.append(tid); existing_tl.add(tkey)
    if rel_rows: repo.google_append_rows_raw('Relaciones_Expediente',rel_rows)
    if tl_rows: repo.google_append_rows_raw('Linea_Tiempo',tl_rows)
    return {'alumnos':len(alumnos),'relaciones':len(rel_rows),'timeline':len(tl_rows),'no_encontrados':0}

"""Corte único, aditivo y cotejado: Streamlit original sobre PostgreSQL.

Sin --apply sólo prepara y compara. Google siempre tiene alcance readonly.
"""
import argparse,json,os,sys
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dotenv import dotenv_values
from sqlalchemy import select,text,inspect
from sqlalchemy.orm import Session
from tools.sync_central_pg import cliente,snapshot,engine,leer_google
from data.sincronizacion_pg import Copia,Pestana,preparar,manifiesto,registros,DESTINOS,Integridad,crear_esquema,huella
from data import pg_documental as pg
from config.settings import URL_SPREADSHEET_MAESTRO,URL_SPREADSHEET_RESPUESTAS_PERSONAL,CRONOGRAMAS_SPREADSHEET_ID

def identificador(url):return url.split('/d/')[1].split('/')[0]
LIBROS=[identificador(URL_SPREADSHEET_MAESTRO),identificador(URL_SPREADSHEET_RESPUESTAS_PERSONAL),CRONOGRAMAS_SPREADSHEET_ID]

def tres_vias(base,source,target):
    # Devuelve cambios de ambos lados sólo si son compatibles, nunca último-gana.
    out=dict(source)
    for key,value in target.items():
        old=str(base.get(key,""));incoming=str(source.get(key,""));value=str(value or "")
        if incoming!=old and value!=old and incoming!=value:raise Integridad("Ambas fuentes cambiaron el mismo campo de un registro. Se detuvo el corte sin sobrescribirlo.")
        if value!=old:out[key]=value
    return out

def reconciliar(s,source,baseline):
    result=deepcopy(source);planned,_=preparar(source);old,_=preparar(baseline);report={}
    for name,rows in planned.items():
        model,key=DESTINOS[name];prior={r["id"]:r for r in old.get(name,[])}
        current={r.id:r for r in s.scalars(select(model))};updated=0
        headers=result[name][0] if result.get(name) else []
        if not headers:
            # El catálogo institucional ya existe aunque la pestaña Escuelas esté vacía.
            headers=["ID_Escuela","CCT","Nombre_Escuela","Nivel","Turno"] if name=="Escuelas" else [key]+[c.name for c in model.__table__.columns if c.name not in {"id","creado_en","actualizado_en"}]
        import re
        mapping={h:("maestra_apoyo" if h=="Maestra de Apoyo" else re.sub(r"[^a-z0-9]+","_",h.lower()).strip("_")) for h in headers};mapping[key]="id"
        by_id={str(dict(zip(headers,list(rawrow)+['']*len(headers))).get(key,'')):i for i,rawrow in enumerate(result.get(name,[[]])[1:],1) if any(str(v).strip() for v in rawrow)}
        for row in rows:
            item=current.get(row["id"])
            values={k:str(getattr(item,k) or "") for k in row} if item else row
            merged=tres_vias(prior.get(row["id"],{}),row,values)
            if item is None:item=model(id=row["id"]);s.add(item)
            for k,v in merged.items():
                if k!="id" and str(getattr(item,k) or "")!=v:setattr(item,k,v);updated+=1
            # Mantener la celda original excepto cuando Neon tenga un cambio posterior compatible.
            index=by_id.get(row["id"])
            if index is not None:
                data=list(result[name][index]);data+=['']*max(0,len(headers)-len(data))
                for h,k in mapping.items():
                    if k in merged:data[headers.index(h)]=merged[k]
                result[name][index]=data
            elif name=="Escuelas":
                if not result.get(name):result[name]=[headers]
                result[name].append([str(merged.get(mapping[h],'')) for h in headers])
        # Capturas que existen únicamente en las tablas SQL también deben aparecer.
        source_ids={r['id'] for r in rows};extras=[item for keyid,item in current.items() if keyid not in source_ids]
        for item in extras:
            result[name].append([str(getattr(item,mapping[h],"") or "") for h in headers])
        report[name]={"origen_valido":len(rows),"solo_neon_conservados":len(extras),"campos_actualizados":updated}
    return result,report

def incluir_historia_neon(s,source):
    result=deepcopy(source);counts={"planeacion":0,"epp":0}
    plan=result['Planeaciones_Versiones'];header=plan[0];known={str(r.get('Revision','')) for r in registros(plan)}
    if inspect(s.bind).has_table('nucleo_planeacion_revisiones'):
        keys=s.execute(text('SELECT document_id,revision FROM nucleo_planeacion_revisiones')).all()
        for doc,rev in keys:
            if rev in known:continue
            d=s.execute(text('SELECT snapshot FROM nucleo_planeacion_revisiones WHERE document_id=:d AND revision=:r'),{'d':doc,'r':rev}).scalar_one()
            d.pop('_orden',None);payload=json.dumps(d,ensure_ascii=False,sort_keys=True);parts=[payload[i:i+38000] for i in range(0,len(payload),38000)];digest=__import__('hashlib').sha256(payload.encode()).hexdigest()
            for i,part in enumerate(parts):
                row=dict(Documento=d['id'],Revision=rev,Anterior=d.get('anterior',''),Fecha=d['guardado_en'],Cuenta=d['cuenta'],Autor=d['datos'].get('Nombre del especialista',''),Escuela_ID=d['datos']['ID_Escuela'],Alumnos_JSON=json.dumps([a['ID_Alumno'] for a in d['datos']['Alumnos']]),Formato=d['formato'],Estado=d['estado'],Parte=str(i),Total=str(len(parts)),SHA256=digest,Contenido=part)
                plan.append([row.get(h,'') for h in header])
            counts['planeacion']+=1
    epp=result['EPP_Versiones'];headers=epp[0];known={(r.get('Alumno'),r.get('Ciclo'),r.get('Parte'),r.get('Revision')) for r in registros(epp)}
    if inspect(s.bind).has_table('nucleo_epp_revisiones'):
        q='SELECT d.student_id,d.cycle,r.section,r.revision,r.parent,r.source_date,r.account,r.author,r.state,r.content FROM nucleo_epp_revisiones r JOIN nucleo_epp d ON d.id=r.document_id'
        for values in s.execute(text(q)):
            if tuple(values[:4]) in known:continue
            row=dict(zip(['Alumno','Ciclo','Parte','Revision','Anterior','Fecha','Cuenta','Autor','Estado','Contenido'],values));row['Contenido']=json.dumps(row['Contenido'],ensure_ascii=False,sort_keys=True);epp.append([row.get(h,'') for h in headers]);counts['epp']+=1
    return result,counts

def guardar_copia(s,book,raw):
    manifest=manifiesto(raw);key=huella({'origen':book,'manifiesto':manifest})
    if s.get(Copia,key) is None:
        s.add(Copia(id=key,origen=book,iniciado_en=datetime.now(timezone.utc),verificado_en=datetime.now(timezone.utc),estado='COPIA_VERIFICADA',manifiesto=manifest))
        for name,values in raw.items():s.add(Pestana(copia=key,nombre=name,sha256=huella(values),filas=len(registros(values)),valores=values))
    s.flush();return key

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--env-file',type=Path,required=True);parser.add_argument('--apply',action='store_true');parser.add_argument('--catch-up',action='store_true');parser.add_argument('--report',type=Path);args=parser.parse_args()
    stage='lectura_solo_lectura'
    try:
        cfg={**dotenv_values(args.env_file),**os.environ};gc=cliente(cfg,args.env_file.resolve().parent)
        books={key:leer_google(lambda key=key:gc.open_by_key(key)) for key in LIBROS};raw={key:snapshot(book,require_core=i==0) for i,(key,book) in enumerate(books.items())}
        eng=engine(cfg);central=LIBROS[0];stage='cotejo_tres_vias'
        with Session(eng,autoflush=False) as s:
            s.execute(text('SET TRANSACTION READ ONLY'))
            previous=s.scalars(select(Copia).where(Copia.origen==central,Copia.estado=='COPIA_VERIFICADA').order_by(Copia.verificado_en.desc())).first()
            if previous is None:raise Integridad('Falta la copia base para comprobar cambios concurrentes.')
            baseline={r.nombre:r.valores for r in s.scalars(select(Pestana).where(Pestana.copia==previous.id))}
            bases={central:baseline}
            for bookid in LIBROS[1:]:
                prior=s.scalars(select(Copia).where(Copia.origen==bookid,Copia.estado=='COPIA_VERIFICADA').order_by(Copia.verificado_en.desc())).first()
                bases[bookid]={r.nombre:r.valores for r in s.scalars(select(Pestana).where(Pestana.copia==prior.id))} if prior else {}
            planned,changes=reconciliar(s,raw[central],baseline)
            planned,history=incluir_historia_neon(s,planned)
            s.rollback()
        report={'modo':'solo_validacion','libros':len(raw),'pestanas':{key:{name:len(registros(values)) for name,values in snap.items()} for key,snap in raw.items()},'reconciliacion':changes,'historia_solo_neon_conservada':history,'google_escrito':False}
        if args.apply:
            stage='corte_atomico'
            # Último cotejo antes de bloquear el destino, sin mantener un lock durante la red Google.
            if any(manifiesto(snapshot(book,require_core=key==central))!=manifiesto(raw[key]) for key,book in books.items()):raise Integridad('El origen cambió durante la preparación; reintenta el corte.')
            with eng.begin() as connection:
                connection.execute(text("SET LOCAL statement_timeout='90s'"));connection.execute(text("SET LOCAL lock_timeout='5s'"));connection.execute(text('SELECT pg_advisory_xact_lock(1785206207)'))
                crear_esquema(connection);pg.Base.metadata.create_all(connection)
                with Session(bind=connection,expire_on_commit=False,autoflush=False) as s:
                    planned,changes=reconciliar(s,raw[central],baseline);planned,history=incluir_historia_neon(s,planned)
                    for key,snap in raw.items():
                        guardar_copia(s,key,snap)
                        if args.catch_up:
                            pg.conciliar_origen(s,key,bases.get(key,{}),planned if key==central else snap)
                        else:pg.importar_libro(s,key,planned if key==central else snap)
                    s.flush()
                    for key,snap in raw.items():
                        for name,values in (planned if key==central else snap).items():
                            sheet=pg.Hoja(key,name,connection.engine)
                            tab=s.get(pg.Tabla,(key,name));rows=[r.valores for r in s.scalars(select(pg.Fila).where(pg.Fila.libro==key,pg.Fila.hoja==name).order_by(pg.Fila.posicion))]
                            current=[tab.columnas]+rows if values else []
                            if not args.catch_up and pg.sha(current)!=pg.sha(values):raise Integridad('Una pestaña no coincide después del corte; se revirtió toda la transacción.')
            report['modo']='aplicado_verificado';report['reconciliacion']=changes;report['historia_solo_neon_conservada']=history
            stage='verificacion_commit'
            with Session(eng,autoflush=False) as s:
                report['tablas_operativas']=s.scalar(select(__import__('sqlalchemy').func.count()).select_from(pg.Tabla))
                if report['tablas_operativas']<sum(len(v) for v in raw.values()):raise Integridad('No se confirmó el conjunto completo de pestañas operativas.')
        if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False));return 0
    except Exception as exc:
        message=str(exc) if isinstance(exc,(Integridad,pg.Conflicto)) else 'No se confirmó el corte. No se modificó Google Sheets ni se activó otra fuente.'
        print(json.dumps({'estado':'ERROR','etapa':stage,'tipo':type(exc).__name__,'motivo':message},ensure_ascii=False));return 1
if __name__=='__main__':raise SystemExit(main())

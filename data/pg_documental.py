"""Persistencia documental PostgreSQL para la interfaz original. Sin llamadas a Google.

Conserva posiciones, columnas e históricos; cada escritura es transaccional.
La API compatible evita reescribir formularios, permisos y generadores existentes.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import hashlib, json, re, threading, uuid
from sqlalchemy import Column, String, Integer, BigInteger, Text, JSON, DateTime, create_engine, select, text, event, update, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, Session
from gspread.exceptions import WorksheetNotFound
from gspread.utils import a1_to_rowcol, rowcol_to_a1

Base=declarative_base(); J=JSON().with_variant(JSONB(),"postgresql")
_CTX=ContextVar("pg_documento_transaccion",default=None)

class Tabla(Base):
    __tablename__="streamlit_hojas"
    libro=Column(String(128),primary_key=True)
    nombre=Column(String(256),primary_key=True)
    columnas=Column(J,nullable=False)
    ancho=Column(Integer,nullable=False)
    siguiente=Column(BigInteger,nullable=False)
    revision=Column(BigInteger,nullable=False,default=0)
    origen_sha256=Column(String(64),nullable=False)

class Fila(Base):
    __tablename__="streamlit_filas"
    libro=Column(String(128),primary_key=True)
    hoja=Column(String(256),primary_key=True)
    posicion=Column(BigInteger,primary_key=True)
    valores=Column(J,nullable=False)

class Envio(Base):
    __tablename__="streamlit_envios"
    libro=Column(String(128),primary_key=True)
    hoja=Column(String(256),primary_key=True)
    clave=Column(String(64),primary_key=True)
    respuesta=Column(J,nullable=False)

class Cambio(Base):
    __tablename__="streamlit_cambios"
    id=Column(String(64),primary_key=True)
    libro=Column(String(128),nullable=False,index=True)
    hoja=Column(String(256),nullable=False)
    posicion=Column(BigInteger,nullable=False)
    antes=Column(J,nullable=False)
    despues=Column(J,nullable=False)
    fecha=Column(DateTime(timezone=True),nullable=False)

class Contador(Base):
    __tablename__="streamlit_contadores"
    libro=Column(String(128),primary_key=True)
    hoja=Column(String(256),primary_key=True)
    prefijo=Column(String(128),primary_key=True)
    valor=Column(BigInteger,nullable=False)

class VersionPlaneacion(Base):
    __tablename__="streamlit_plan_versiones"
    libro=Column(String(128),primary_key=True)
    documento=Column(String(128),primary_key=True)
    revision=Column(String(128),primary_key=True)
    fecha=Column(String(128),nullable=False,index=True)
    orden=Column(BigInteger,nullable=False)
    contenido=Column(J,nullable=False)

class Conflicto(RuntimeError):pass

def sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

@lru_cache(maxsize=1)
def motor():
    from data.database import get_database_url
    u=make_url(get_database_url())
    if u.drivername.split("+",1)[0]!="postgresql":
        engine=create_engine(u,connect_args={"check_same_thread": False} if u.drivername.startswith("sqlite") else {})
        Base.metadata.create_all(engine)
        return engine
    from sqlalchemy.pool import NullPool
    engine=create_engine(u.set(drivername="postgresql+psycopg2"),poolclass=NullPool,pool_pre_ping=True,hide_parameters=True,connect_args={"connect_timeout":10})
    return engine

@contextmanager
def sesion(engine=None):
    current=_CTX.get()
    if current is not None:
        yield current;return
    s = Session(engine or motor(), expire_on_commit=False)
    try:
        with s.begin():
            yield s
    finally:
        s.close()

@contextmanager
def bloqueo(documento,engine=None):
    current=_CTX.get()
    if current is not None:
        if current.bind.dialect.name=="postgresql":
            current.execute(text("SELECT pg_advisory_xact_lock(:k)"),{"k":int.from_bytes(hashlib.sha256(documento.encode()).digest()[:8],"big",signed=True)})
        current.info.setdefault('ambitos',[]).append(documento)
        try:yield
        finally:current.info['ambitos'].pop()
        return
    with Session(engine or motor(),expire_on_commit=False) as s:
        token=_CTX.set(s)
        try:
            s.begin();s.info['ambitos']=[documento]
            if s.bind.dialect.name=="postgresql":s.execute(text("SELECT pg_advisory_xact_lock(:k)"),{"k":int.from_bytes(hashlib.sha256(documento.encode()).digest()[:8],"big",signed=True)})
            yield
            if s.in_transaction():s.commit()
        except Exception:
            s.rollback();raise
        finally:_CTX.reset(token)

def confirmar():
    # El acuse y las cachés sólo se actualizan DESPUÉS del commit real.
    s=_CTX.get()
    if s is not None:s.commit()

class Hoja:
    def __init__(self,libro,nombre,engine=None):
        self.libro,self.title,self.engine=libro,nombre,engine
        self._local=threading.local()
    def _tabla(self,s,lock=False):
        q=select(Tabla).where(Tabla.libro==self.libro,Tabla.nombre==self.title)
        if lock:q=q.with_for_update()
        item=s.scalars(q).one_or_none()
        if item is None:raise WorksheetNotFound(self.title)
        return item
    def _recordar(self,numero,valores):
        if numero!=1 and self.title in {"Planeaciones_Versiones","EPP_Versiones","Archivos_Expediente","Sesiones_Recuperables"}:return
        if not hasattr(self._local,"filas"):self._local.filas={}
        if len(self._local.filas)>1000:self._local.filas.clear()
        self._local.filas[numero]=deepcopy(valores)
    @property
    def col_count(self):
        with sesion(self.engine) as s:return self._tabla(s).ancho
    @property
    def row_count(self):
        with sesion(self.engine) as s:return max(2000,self._tabla(s).siguiente)
    def get_all_values(self,**kwargs):
        with sesion(self.engine) as s:
            tab=self._tabla(s);result=[deepcopy(tab.columnas)];last=1
            q=select(Fila).where(Fila.libro==self.libro,Fila.hoja==self.title).order_by(Fila.posicion)
            # Cursor acotado; no repetir lecturas por cada celda.
            for r in s.scalars(q.execution_options(yield_per=200)):
                while last+1<r.posicion:result.append([]);last+=1
                result.append(deepcopy(r.valores));last=r.posicion
            for n,row in enumerate(result,1):self._recordar(n,row)
            return result
    def row_values(self,row,**kwargs):
        with sesion(self.engine) as s:
            tab=self._tabla(s)
            found=None if row==1 else s.get(Fila,(self.libro,self.title,int(row)))
            values=deepcopy(tab.columnas if row==1 else found.valores if found else [])
            self._recordar(int(row),values);return values
    def col_values(self,col,**kwargs):
        if col<1:raise ValueError("Columna inválida.")
        with sesion(self.engine) as s:
            tab=self._tabla(s);values=[tab.columnas[col-1] if col<=len(tab.columnas) else ""];last=1
            for row,cell in s.execute(select(Fila.posicion,Fila.valores[col-1]).where(Fila.libro==self.libro,Fila.hoja==self.title).order_by(Fila.posicion)):
                values.extend([""]*max(0,row-last-1));values.append(cell if cell is not None else "");last=row
            while values and values[-1]=="":values.pop()
            return values
    def get(self,range_name=None,**kwargs):
        if not range_name:return self.get_all_values()
        area=range_name.split("!")[-1].replace("$","")
        parts=area.split(":");first=parts[0];end=parts[-1]
        if not re.fullmatch(r"[A-Za-z]+[1-9][0-9]*",first) or not re.fullmatch(r"[A-Za-z]+[1-9][0-9]*",end):raise ValueError("Se requiere un rango A1 acotado.")
        r1,c1=a1_to_rowcol(first);r2,c2=a1_to_rowcol(end)
        if r2<r1 or c2<c1:raise ValueError("Rango inválido.")
        with sesion(self.engine) as s:
            tab=self._tabla(s);found={r.posicion:r.valores for r in s.scalars(select(Fila).where(Fila.libro==self.libro,Fila.hoja==self.title,Fila.posicion>=max(2,r1),Fila.posicion<=r2))}
            if r1==1:found[1]=tab.columnas
            out=[]
            for pos in range(r1,r2+1):
                values=deepcopy(found.get(pos,[]));self._recordar(pos,values);out.append(values[c1-1:c2])
            while out and not out[-1]:out.pop()
            return out
    def por_clave(self,columna,valor):
        with sesion(self.engine) as s:
            headers=self._tabla(s).columnas
            if columna not in headers:raise ValueError('Falta la clave documental.')
            return [deepcopy(r.valores) for r in s.scalars(select(Fila).where(Fila.libro==self.libro,Fila.hoja==self.title,Fila.valores[headers.index(columna)].as_string()==str(valor)).order_by(Fila.posicion))]
    def get_all_records(self,**kwargs):
        from data.google import _records_from_values
        return _records_from_values(self.get_all_values())
    def add_cols(self,cols):
        with sesion(self.engine) as s:
            tab=self._tabla(s,True);tab.ancho+=max(0,int(cols))
    def append_row(self,values,**kwargs):return self.append_rows([values],**kwargs)
    def append_rows(self,values,**kwargs):
        rows=[[str(v) if v is not None else "" for v in row] for row in values]
        key=sha(rows)
        with sesion(self.engine) as s:
            tab=self._tabla(s);sent=s.get(Envio,(self.libro,self.title,key))
            if sent:return deepcopy(sent.respuesta)
            if not rows:return {"updates":{"updatedRows":0}}
            if not tab.columnas:
                tab.columnas=rows.pop(0);tab.ancho=max(tab.ancho,len(tab.columnas))
                if not rows:return {"updates":{"updatedRows":1,"updatedRange":"'"+self.title+"'!A1:"+rowcol_to_a1(1,len(tab.columnas))}}
            reservation=s.bind.dialect.name=="postgresql" and tab not in s.new and tab not in s.dirty
            if reservation:
                start=s.execute(update(Tabla).where(Tabla.libro==self.libro,Tabla.nombre==self.title).values(siguiente=Tabla.siguiente+len(rows),ancho=func.greatest(Tabla.ancho,max(len(r) for r in rows)),revision=Tabla.revision+1).returning(Tabla.siguiente-len(rows))).scalar_one()
                s.expire(tab,['siguiente','ancho','revision'])
            else:
                tab=self._tabla(s,True);start=tab.siguiente
            new=[{"libro":self.libro,"hoja":self.title,"posicion":start+i,"valores":row} for i,row in enumerate(rows)]
            for offset in range(0,len(new),100):s.execute(Fila.__table__.insert(),new[offset:offset+100])
            if not reservation:
                tab.siguiente+=len(rows);tab.ancho=max([tab.ancho]+[len(r) for r in rows]);tab.revision+=1
            _proyectar(s,self.title,tab.columnas,rows,libro=self.libro,nuevo=True)
            reply={"updates":{"updatedRows":len(rows),"updatedRange":"'"+self.title+"'!A"+str(start)+":"+rowcol_to_a1(start+len(rows)-1,max(len(r) for r in rows))}}
            s.add(Envio(libro=self.libro,hoja=self.title,clave=key,respuesta=reply));s.flush()
            return reply
    def update_cell(self,row,col,value):return self.batch_update([{"range":rowcol_to_a1(row,col),"values":[[value]]}])
    def update(self,values=None,range_name=None,**kwargs):
        if isinstance(values,str) and isinstance(range_name,list):values,range_name=range_name,values
        return self.batch_update([{"range":range_name,"values":values}],**kwargs)
    def batch_update(self,data,**kwargs):
        patches={}
        for item in data:
            anchor=item["range"].split("!")[-1].split(":")[0].replace("$","");r,c=a1_to_rowcol(anchor)
            for i,row in enumerate(item["values"]):
                for j,v in enumerate(row):patches.setdefault(r+i,{})[c+j-1]="" if v is None else str(v)
        with sesion(self.engine) as s:
            tab=self._tabla(s,True);project=[]
            for number,changes in sorted(patches.items()):
                r=None if number==1 else s.get(Fila,(self.libro,self.title,number))
                before=deepcopy(tab.columnas if number==1 else r.valores if r else []);after=deepcopy(before)
                baselines=getattr(self._local,"filas",{}).get(number)
                for index,value in changes.items():
                    current=before[index] if index<len(before) else ""
                    if baselines is not None:
                        base=baselines[index] if index<len(baselines) else ""
                        if value==base:continue
                        if current not in {base,value}:raise Conflicto("Otra sesión cambió esta celda. Tu texto se conserva; actualiza y vuelve a guardar.")
                    after.extend([""]*max(0,index+1-len(after)));after[index]=value
                if after==before:continue
                s.add(Cambio(id=uuid.uuid4().hex,libro=self.libro,hoja=self.title,posicion=number,antes=before,despues=after,fecha=datetime.now(timezone.utc)))
                if number==1:tab.columnas=after
                elif r:r.valores=after;project.append(after)
                else:s.add(Fila(libro=self.libro,hoja=self.title,posicion=number,valores=after));project.append(after)
                tab.siguiente=max(tab.siguiente,number+1);tab.ancho=max(tab.ancho,len(after));tab.revision+=1
            _proyectar(s,self.title,tab.columnas,project,libro=self.libro);s.flush()
        return {"totalUpdatedRows":len(patches)}

def _proyectar(s,name,headers,rows,libro=None,nuevo=False):
    if name=="Planeaciones_Versiones" and libro:
        _indexar_envio(s,libro,headers,rows)
        return
    # Las tablas relacionales existentes y el documento se actualizan juntos.
    from data.sincronizacion_pg import DESTINOS
    if name not in DESTINOS:return
    model,identity=DESTINOS[name]
    for row in rows:
        values=dict(zip(headers,list(row)+[""]*max(0,len(headers)-len(row))));ident=str(values.get(identity,""))
        if not ident:continue
        if name=="Alumnos" and not str(values.get("Nombre_Completo","")).strip() and not str(values.get("CURP","")).strip():continue
        item=s.get(model,ident)
        if name=='Alumnos':
            curp=str(values.get('CURP','')).strip().upper()
            if curp and (nuevo or item is None or str(item.curp or '').strip().upper()!=curp):
                if s.bind.dialect.name=='postgresql':s.execute(text('SELECT pg_advisory_xact_lock(:k)'),{'k':int.from_bytes(hashlib.sha256(('curp:'+curp).encode()).digest()[:8],'big',signed=True)})
                existing=s.scalar(select(model.id).where(func.upper(model.curp)==curp,model.id!=ident).limit(1))
                if existing:raise Conflicto('Esa CURP ya tiene un registro. No se creó un duplicado.')
        if nuevo and item is not None:
            changes={k:v for k,v in values.items() if k!=identity and str(v).strip()}
            for k,v in changes.items():
                attr="maestra_apoyo" if k=="Maestra de Apoyo" else re.sub(r"[^a-z0-9]+","_",k.lower()).strip("_")
                if attr in model.__table__.columns and str(getattr(item,attr) or "")!=str(v):raise Conflicto('Ese identificador ya corresponde a otro registro. No se sobrescribió; actualiza y vuelve a intentar.')
        if item is None:item=model(id=ident);s.add(item)
        for key,value in values.items():
            attr="maestra_apoyo" if key=="Maestra de Apoyo" else re.sub(r"[^a-z0-9]+","_",key.lower()).strip("_")
            if attr in model.__table__.columns and attr not in {"id","creado_en","actualizado_en"}:setattr(item,attr,str(value))

class Libro:
    def __init__(self,ident,engine=None):self.id,self.engine=ident,engine
    def worksheet(self,name):
        sheet=Hoja(self.id,name,self.engine)
        with sesion(self.engine) as s:sheet._tabla(s)
        return sheet
    def add_worksheet(self,title,rows=2000,cols=10):
        with sesion(self.engine) as s:
            # Serializa creación concurrente sin reemplazar tablas existentes.
            if s.bind.dialect.name=="postgresql":s.execute(text("SELECT pg_advisory_xact_lock(:k)"),{"k":int.from_bytes(hashlib.sha256((self.id+title).encode()).digest()[:8],"big",signed=True)})
            if s.get(Tabla,(self.id,title)) is None:s.add(Tabla(libro=self.id,nombre=title,columnas=[],ancho=int(cols),siguiente=2,revision=0,origen_sha256=sha([])))
        return Hoja(self.id,title,self.engine)

class Cliente:
    def open_by_key(self,key):return Libro(key)
    def open_by_url(self,url):
        match=re.search(r"/spreadsheets/d/([^/]+)",url)
        if not match:raise ValueError("Libro no reconocido.")
        return self.open_by_key(match[1])


def importar_libro(s,ident,snapshot):
    report={}
    for name,values in snapshot.items():
        digest=sha(values);old=s.get(Tabla,(ident,name))
        if old:
            if old.origen_sha256!=digest:raise Conflicto("El origen cambió respecto al corte importado. No se sobrescribirá una tabla operativa.")
            report[name]="ya_importada";continue
        headers=values[0] if values else []
        s.add(Tabla(libro=ident,nombre=name,columnas=headers,ancho=max([10,len(headers)]+[len(r) for r in values]),siguiente=max(2,len(values)+1),revision=0,origen_sha256=digest))
        rows=[{"libro":ident,"hoja":name,"posicion":i,"valores":r} for i,r in enumerate(values[1:],2)]
        for start in range(0,len(rows),100):s.execute(Fila.__table__.insert(),rows[start:start+100])
        report[name]=len(rows)
    s.flush();return report


def _guardar_version(s,book,doc,orden):
    key=(book,doc['id'],doc['revision']);old=s.get(VersionPlaneacion,key)
    doc=deepcopy(doc);doc['_orden']=orden
    if old:
        original=deepcopy(old.contenido);original.pop('_orden',None);new=deepcopy(doc);new.pop('_orden',None)
        if sha(original)!=sha(new):raise Conflicto('Una revisión existente contiene otra redacción. No se sobrescribió.')
        return
    s.add(VersionPlaneacion(libro=book,documento=doc['id'],revision=doc['revision'],fecha=doc.get('guardado_en',''),orden=orden,contenido=doc))

def _indexar_envio(s,book,headers,rows):
    if not rows:return
    from services.planeacion import reconstruir
    if 'Revision' not in headers:return
    index=headers.index('Revision')
    for revision in {r[index] for r in rows if len(r)>index}:
        parts=list(s.scalars(select(Fila).where(Fila.libro==book,Fila.hoja=='Planeaciones_Versiones',Fila.valores[index].as_string()==revision).order_by(Fila.posicion)))
        for doc in reconstruir([headers]+[p.valores for p in parts]):_guardar_version(s,book,doc,max(p.posicion for p in parts)-2)



def planes_resumen(cuenta=None, es_director=False, engine=None, libro=None):
    """Reescritura de SQLAlchemy: Trae EXCLUSIVAMENTE la vista resumida de los documentos del usuario activo.
    
    No descarga tablas ni textos pesados ni el historial completo de la USAER.
    Filtra por cuenta en PostgreSQL y selecciona únicamente la versión vigente de cada planeación.
    """
    from sqlalchemy import func
    if libro is None:
        from config.settings import URL_SPREADSHEET_MAESTRO
        libro = URL_SPREADSHEET_MAESTRO.split('/d/')[1].split('/')[0]
    with sesion(engine) as s:
        rank_q = select(
            VersionPlaneacion.documento,
            VersionPlaneacion.revision,
            func.row_number().over(
                partition_by=VersionPlaneacion.documento,
                order_by=(VersionPlaneacion.fecha.desc(), VersionPlaneacion.orden.desc())
            ).label('n')
        ).where(VersionPlaneacion.libro == libro)
        
        if not es_director and cuenta:
            if s.bind.dialect.name == "postgresql":
                rank_q = rank_q.where(VersionPlaneacion.contenido['cuenta'].as_string() == str(cuenta).strip())
            else:
                rank_q = rank_q.where(func.json_extract(VersionPlaneacion.contenido, '$.cuenta') == str(cuenta).strip())
        
        rank = rank_q.subquery()
        latest = select(rank.c.revision).where(rank.c.n == 1)
        
        q = select(VersionPlaneacion).where(VersionPlaneacion.libro == libro, VersionPlaneacion.revision.in_(latest))
        if not es_director and cuenta:
            if s.bind.dialect.name == "postgresql":
                q = q.where(VersionPlaneacion.contenido['cuenta'].as_string() == str(cuenta).strip())
            else:
                q = q.where(func.json_extract(VersionPlaneacion.contenido, '$.cuenta') == str(cuenta).strip())
            
        rows = list(s.scalars(q.order_by(VersionPlaneacion.fecha.desc(), VersionPlaneacion.orden.desc()).limit(50)))
        result = []
        for r in rows:
            c = r.contenido
            if isinstance(c, str):
                try: c = json.loads(c)
                except Exception: c = {}
            elif c is None:
                c = {}
            result.append({
                'id': c.get('id'),
                'cuenta': c.get('cuenta'),
                'formato': c.get('formato'),
                'estado': c.get('estado'),
                'revision': c.get('revision', r.revision),
                'anterior': c.get('anterior', ''),
                'guardado_en': c.get('guardado_en', r.fecha),
                'datos': c.get('datos', {}),
                'metadatos': c.get('metadatos', {}),
                'tablas': c.get('tablas', {}),
                'textos': c.get('textos', {}),
                'observaciones_director': c.get('observaciones_director', ''),
                '_orden': r.orden,
            })
        return sorted(result, key=lambda d: d.get('guardado_en', ''), reverse=True)

def planes(todas=False,documento=None,engine=None,libro=None):
    from sqlalchemy import func,or_
    if libro is None:
        from config.settings import URL_SPREADSHEET_MAESTRO
        libro=URL_SPREADSHEET_MAESTRO.split('/d/')[1].split('/')[0]
    with sesion(engine) as s:
        q=select(VersionPlaneacion).where(VersionPlaneacion.libro==libro)
        if todas:
            if documento:q=q.where(VersionPlaneacion.documento==documento)
        else:
            rank=select(VersionPlaneacion.documento,VersionPlaneacion.revision,func.row_number().over(partition_by=VersionPlaneacion.documento,order_by=(VersionPlaneacion.fecha.desc(),VersionPlaneacion.orden.desc())).label('n')).where(VersionPlaneacion.libro==libro).subquery()
            latest=select(rank.c.revision).where(rank.c.n==1)
            selected=[]
            ctx=_CTX.get()
            if ctx is not None:selected=[key for key in ctx.info.get('ambitos',[]) if not key.startswith(('grupo:','epp:'))]
            condition=VersionPlaneacion.revision.in_(latest)
            if selected:condition=or_(condition,VersionPlaneacion.documento.in_(selected))
            q=q.where(condition)
        rows=list(s.scalars(q.order_by(VersionPlaneacion.fecha,VersionPlaneacion.orden)))
        result=[deepcopy(row.contenido) for row in rows]
        if not todas:
            # Mantener las revisiones de referencia usadas al conciliar copias antiguas.
            refs={rev for d in result for rev in d.get('metadatos',{}).get('unificacion_grupal',{}).get('fuentes',{}).values()}
            known={d['revision'] for d in result};missing=refs-known
            if missing:result.extend(deepcopy(row.contenido) for row in s.scalars(select(VersionPlaneacion).where(VersionPlaneacion.libro==libro,VersionPlaneacion.revision.in_(missing))))
        return sorted(result,key=lambda d:d.get('guardado_en',''))


def siguiente_id(book,hoja,columna,prefijo,engine=None):
    with sesion(engine) as s:
        if s.bind.dialect.name=="postgresql":s.execute(text("SELECT pg_advisory_xact_lock(:k)"),{'k':int.from_bytes(hashlib.sha256(('id:'+book+hoja+prefijo).encode()).digest()[:8],'big',signed=True)})
        item=s.get(Contador,(book,hoja,prefijo))
        if item is None:
            sheet=Hoja(book,hoja,engine);headers=sheet._tabla(s).columnas
            if columna not in headers:raise ValueError('La columna identificadora no existe.')
            values=s.scalars(select(Fila.valores[headers.index(columna)].as_string()).where(Fila.libro==book,Fila.hoja==hoja))
            nums=[]
            for value in values:
                if isinstance(value,str) and value.startswith(prefijo+'-'):
                    try:nums.append(int(value.rsplit('-',1)[1]))
                    except ValueError:pass
            item=Contador(libro=book,hoja=hoja,prefijo=prefijo,valor=max(nums,default=0));s.add(item)
        item.valor+=1;s.flush();return f'{prefijo}-{item.valor:03d}'


def conciliar_origen(s,book,baseline,incoming):
    """Incorpora la cola del origen tras el despliegue sin reemplazar capturas Neon."""
    token=_CTX.set(s);report={}
    try:
        for name,source in incoming.items():
            old=baseline.get(name,[])
            if sha(source)==sha(old):continue
            existing=s.get(Tabla,(book,name))
            if existing is None:importar_libro(s,book,{name:source});report[name]={'nuevas':max(0,len(source)-1)};continue
            sheet=Hoja(book,name);live=sheet.get_all_values()
            base_headers=old[0] if old else [];headers=source[0] if source else []
            if headers[:len(base_headers)]!=base_headers:raise Conflicto('Cambió el orden de columnas del origen; no se reemplazó el documento operativo.')
            if len(source)<len(old):raise Conflicto('El origen tiene menos filas que el corte anterior. No se eliminarán registros operativos.')
            live_headers=list(live[0]);missing=[h for h in headers if h not in live_headers]
            for h in missing:sheet.update_cell(1,len(live_headers)+1,h);live_headers.append(h)
            updates=[]
            for pos in range(1,min(len(old),len(source))):
                before=list(old[pos])+['']*len(base_headers);new=list(source[pos])+['']*len(headers)
                current=list(live[pos]) if pos<len(live) else [];current+=['']*len(live_headers)
                for j,h in enumerate(headers):
                    base=before[j] if j<len(base_headers) else '';value=new[j];col=live_headers.index(h)
                    if value==base:continue
                    if name in {'Planeaciones_Versiones','EPP_Versiones'}:raise Conflicto('Una revisión histórica del origen fue modificada. Se conserva sin sobrescribir la versión operativa.')
                    if current[col] not in {base,value}:raise Conflicto('La misma celda cambió en ambos orígenes. Se conservaron ambas fuentes; requiere conciliación.')
                    if current[col]!=value:updates.append({'range':rowcol_to_a1(pos+1,col+1),'values':[[value]]})
            if updates:sheet.batch_update(updates)
            signatures={sha(list(r)+['']*max(0,len(live_headers)-len(r))) for r in live[1:]}
            tail=[]
            for raw in source[max(1,len(old)):]:
                row=['']*len(live_headers)
                for j,h in enumerate(headers):row[live_headers.index(h)]=raw[j] if j<len(raw) else ''
                digest=sha(row)
                if digest not in signatures:signatures.add(digest);tail.append(row)
            if tail:sheet.append_rows(tail)
            post=sheet.get_all_values()
            post_signatures={sha(list(r)+['']*max(0,len(live_headers)-len(r))) for r in post[1:]}
            if any(sha(r) not in post_signatures for r in tail):raise Conflicto('No se confirmó una fila de la cola del origen.')
            for item in updates:
                r,c=a1_to_rowcol(item['range'])
                if len(post)<r or len(post[r-1])<c or post[r-1][c-1]!=item['values'][0][0]:raise Conflicto('No se confirmó una celda conciliada.')
            report[name]={'filas_nuevas':len(tail),'celdas_conciliadas':len(updates)}
        s.flush();return report
    finally:_CTX.reset(token)

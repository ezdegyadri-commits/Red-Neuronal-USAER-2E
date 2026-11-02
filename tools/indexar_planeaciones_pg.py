"""Índice de revisiones de lectura: conserva el diario original completo."""
import sys,argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sqlalchemy.orm import Session
from sqlalchemy import select,text,func
from dotenv import dotenv_values
from tools.sync_central_pg import engine
from data import pg_documental as pg
from services.planeacion import reconstruir
from config.settings import URL_SPREADSHEET_MAESTRO

def main():
 p=argparse.ArgumentParser();p.add_argument('--env-file',type=Path,required=True);p.add_argument('--apply',action='store_true');args=p.parse_args();e=engine(dotenv_values(args.env_file));book=URL_SPREADSHEET_MAESTRO.split('/d/')[1].split('/')[0]
 values=pg.Hoja(book,'Planeaciones_Versiones',e).get_all_values();docs=reconstruir(values)
 if args.apply:
  with e.begin() as c:
   c.execute(text("SET LOCAL statement_timeout='90s'"));pg.VersionPlaneacion.__table__.create(c,checkfirst=True)
   with Session(bind=c,autoflush=False) as s:
    existing={(r.documento,r.revision) for r in s.scalars(select(pg.VersionPlaneacion))}
    new=[dict(libro=book,documento=d['id'],revision=d['revision'],fecha=d.get('guardado_en',''),orden=d['_orden'],contenido=d) for d in docs if (d['id'],d['revision']) not in existing]
    for start in range(0,len(new),50):s.execute(pg.VersionPlaneacion.__table__.insert(),new[start:start+50])
    s.flush()
    if s.scalar(select(func.count()).select_from(pg.VersionPlaneacion).where(pg.VersionPlaneacion.libro==book))<len(docs):raise RuntimeError('Índice incompleto.')
 print(json.dumps({'modo':'aplicado' if args.apply else 'solo_validacion','revisiones':len(docs),'documentos':len({d['id'] for d in docs}),'diario_original_intacto':True}));return 0
if __name__=='__main__':raise SystemExit(main())

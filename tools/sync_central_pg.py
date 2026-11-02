"""Copia total de Sheets a PostgreSQL. Por defecto valida sin escribir."""
import argparse, json, os, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from dotenv import dotenv_values
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from data.sincronizacion_pg import preparar, manifiesto, crear_esquema, importar, Integridad, Pestana, Copia, huella

READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"

def cliente(config, env_dir):
    import gspread
    from google.oauth2.service_account import Credentials
    raw=config.get("USAER_GOOGLE_CREDENTIALS_JSON")
    path=Path(config.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json"))
    if not path.is_absolute(): path=env_dir/path
    info=json.loads(raw) if raw else json.loads(path.read_text(encoding="utf-8"))
    client=gspread.authorize(Credentials.from_service_account_info(info, scopes=[READONLY_SCOPE]))
    client.set_timeout((5,30)); return client

def leer_google(operation):
    from gspread.exceptions import APIError
    for intento in range(4):
        try:return operation()
        except APIError as exc:
            code=getattr(getattr(exc,'response',None),'status_code',None)
            if code not in {429,500,502,503,504} or intento==3:raise
            print(json.dumps({'lectura_google':'reintentando','estado_http':code,'intento':intento+1}),flush=True)
            time.sleep(10*(intento+1))

def snapshot(book, *, require_core=True):
    # batchGet devuelve sólo los valores usados de rangos delimitados por metadata.
    from gspread.utils import rowcol_to_a1
    meta=leer_google(book.fetch_sheet_metadata); sheets=meta["sheets"]
    ranges=[]; names=[]
    for sheet in sheets:
        p=sheet["properties"]; grid=p["gridProperties"]; name=p["title"]
        ranges.append("'"+name.replace("'", "''")+"'!A1:"+rowcol_to_a1(grid["rowCount"],grid["columnCount"]))
        names.append(name)
    result={}
    for start in range(0,len(ranges),4):
        response=leer_google(lambda:book.values_batch_get(ranges[start:start+4], params={"valueRenderOption":"FORMATTED_VALUE"}))
        blocks=response.get("valueRanges",[])
        if len(blocks)!=len(names[start:start+4]): raise Integridad("La lectura de pestañas fue parcial.")
        for name,block in zip(names[start:start+4],blocks): result[name]=block.get("values",[])
    if require_core and not {"Alumnos","Usuarios","Planeaciones_Versiones","EPP_Versiones"}<=set(result):
        raise Integridad("Falta una pestaña obligatoria.")
    return result

def engine(config):
    url=make_url(config.get("DATABASE_URL_UNPOOLED") or config["DATABASE_URL"])
    if url.drivername.split("+",1)[0]!="postgresql": raise Integridad("El destino debe ser PostgreSQL.")
    if url.host and url.host.endswith(".neon.tech") and "-pooler." in url.host:
        url=url.set(host=url.host.replace("-pooler.",".",1))
    return create_engine(url.set(drivername="postgresql+psycopg2"),hide_parameters=True,pool_pre_ping=True,connect_args={"connect_timeout":10})

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--env-file",type=Path,required=True)
    ap.add_argument("--apply",action="store_true")
    ap.add_argument("--init-schema",action="store_true")
    ap.add_argument("--report",type=Path)
    args=ap.parse_args()
    if args.init_schema and not args.apply: ap.error("--init-schema requiere --apply")
    stage="lectura_origen"
    try:
        cfg={**dotenv_values(args.env_file),**os.environ}
        book=cliente(cfg,args.env_file.resolve().parent).open_by_key(cfg["USAER_SPREADSHEET_ID"])
        source=snapshot(book); stage="validacion_mapeo"
        rows,excluded=preparar(source)
        report={"modo":"solo_validacion", "pestanas":manifiesto(source),"destinos":{name:len(items) for name,items in rows.items()},"fila_vacia_excluida_del_padron":excluded,"google_sheets_escrito":False}
        dest=engine(cfg)
        with dest.connect() as c:
            c.execute(text("SELECT 1"))
        if args.apply:
            stage="transaccion_destino"
            with dest.begin() as c:
                c.execute(text("SET LOCAL lock_timeout='5s'")); c.execute(text("SET LOCAL statement_timeout='90s'"))
                c.execute(text("SELECT pg_advisory_xact_lock(1785206207)"))
                if args.init_schema: crear_esquema(c)
                with Session(bind=c,expire_on_commit=False) as s:
                    report=importar(s,source,cfg["USAER_SPREADSHEET_ID"])
                    # Volver a leer el origen antes del commit para detectar capturas concurrentes.
                    stage="relectura_origen"
                    if manifiesto(snapshot(book))!=manifiesto(source): raise Integridad("Google Sheets cambió durante la copia; se revirtió el destino. Reintenta para incluir la captura nueva.")
                    s.flush()
            stage="verificacion_post_commit"
            with Session(dest) as s:
                copied=s.get(Copia,report["copia"])
                if copied is None or copied.estado!="COPIA_VERIFICADA": raise Integridad("No se confirmó el commit de la copia.")
                for name,values in source.items():
                    row=s.get(Pestana,(report["copia"],name))
                    if row is None or huella(row.valores)!=huella(values): raise Integridad("El cotejo posterior al commit no coincide.")
            report["modo"]="aplicado_y_verificado"
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(report,ensure_ascii=False)); return 0
    except Exception as exc:
        # Nunca imprimir excepciones de drivers con DSN, contraseñas o parámetros.
        reason=str(exc) if isinstance(exc,Integridad) else "No se completó la operación; revisar conectividad/configuración sin exponer credenciales."
        print(json.dumps({"estado":"ERROR","etapa":stage,"tipo":type(exc).__name__,"motivo":reason,"google_sheets_escrito":False},ensure_ascii=False)); return 1
if __name__=="__main__": raise SystemExit(main())

"""Inventario estático y carga sintética reproducible; nunca conecta con Google.

Ejecutar desde la raíz. --baseline carga EPP de una revisión Git explícita.
Los tiempos incluyen Python/pandas y 30 ms de escritura ficticia, no latencia real.
"""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import logging
from pathlib import Path
import subprocess
from threading import RLock
from time import perf_counter, sleep
from unittest.mock import patch


def inventario():
    result=[]
    controles={'button','form_submit_button','expander','popover','selectbox','tabs','text_input','data_editor'}
    for folder in ('ui','services','data'):
        for path in sorted(Path(folder).rglob('*.py')):
            tree=ast.parse(path.read_text(encoding='utf-8-sig'))
            widgets=[];writes=[]
            for n in ast.walk(tree):
                if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Attribute):continue
                nombre=n.func.attr
                if folder=='ui' and nombre in controles:
                    label=n.args[0].value if n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str) else '(dinámico)'
                    widgets.append({'linea':n.lineno,'tipo':nombre,'etiqueta':label})
                if nombre in {'append_row','append_rows','batch_update','update_cell','update','get_all_values'}:
                    writes.append({'linea':n.lineno,'operacion':nombre})
            if widgets or writes:result.append({'archivo':path.as_posix(),'interacciones':widgets,'operaciones_datos':writes})
    return result


def medir(baseline=None):
    import pandas as pd
    from services import epp as s
    from services.epp_modelo import vacia
    from tests.test_epp import ALUMNO,ACTOR
    if baseline:
        source=subprocess.check_output(['git','show',baseline+':services/epp.py'])
        exec(compile(source,'services/epp.py','exec'),s.__dict__)
    resultados=[]
    for n in (15,20,25):
        rows=[];lock=RLock()
        alumnos=[{**ALUMNO,'ID_Alumno':f'QA-{i}'} for i in range(n)]
        def frame(*_):
            with lock:return pd.DataFrame(deepcopy(rows),columns=s.HEADERS)
        class Sheet:
            def append_rows(self,items,value_input_option):
                sleep(.03)
                with lock:rows.extend(deepcopy(items))
        s.recientes().clear();s._DOCS_CACHE.clear()
        with patch.object(s,'actor',return_value=ACTOR),patch.object(s.planes,'padron_autorizado',return_value=pd.DataFrame(alumnos)),patch.object(s,'df_sheet',side_effect=frame),patch.object(s,'hoja',return_value=Sheet()),patch.object(s,'clear_cache'),patch('services.planeacion_estabilidad.reservar_escritura'):
            docs=[s.crear(a['ID_Alumno'],'2026-2027') for a in alumnos]
            def editar(doc):
                started=perf_counter();v=vacia('Aprendizaje')
                v['campos']['5.1. Competencia curricular']='Hallazgo ficticio de control'
                saved=s.guardar_cambios(doc,'Aprendizaje',vacia('Aprendizaje'),v,'')
                assert saved['contenido']==v
                return (perf_counter()-started)*1000
            start=perf_counter()
            with ThreadPoolExecutor(max_workers=4) as pool:
                tiempos=list(pool.map(editar,docs))
            total=(perf_counter()-start)*1000
            assert len(rows)==n*2
            assert len(s.listar())==n
            resultados.append({'usuarios_ficticios':n,'workers':4,'escritura_simulada_ms':30,'total_ms':round(total,2),'media_guardado_ms':round(sum(tiempos)/n,2),'p95_guardado_ms':round(sorted(tiempos)[int((n-1)*.95)],2),'versiones_verificadas':len(rows)})
    return resultados


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline')
    parser.add_argument('--salida',required=True)
    args=parser.parse_args()
    logging.disable(logging.CRITICAL)
    result={'alcance':'Local, datos ficticios y red simulada; no mide Cloud ni Google Sheets real','baseline':args.baseline,'carga_epp':medir(args.baseline),'inventario_estatico':inventario()}
    output=Path(args.salida);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result['carga_epp'],ensure_ascii=False))

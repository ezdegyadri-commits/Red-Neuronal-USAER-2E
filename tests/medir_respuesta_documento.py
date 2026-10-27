"""Benchmark reproducible sin Google, IA, credenciales ni alumnos reales.

python -m tests.medir_respuesta_documento
Compara la misma petición simulada con el camino síncrono y el de fondo.
"""
from copy import deepcopy
import json
from time import perf_counter,sleep
from unittest.mock import patch
from tests.test_planeacion_panel import ACTOR,documento
from services import planeacion as s
from ui import planeacion as ui


def medir():
    state={'p_doc':documento(),'p_papel_nonce':'ficticio','escuelas_permitidas':'E1'}
    def remoto(doc,estado):
        sleep(1)
        return {**deepcopy(doc),'revision':'confirmada','guardado_en':'ficticio'}
    with patch.object(ui.st,'session_state',state),patch.object(s,'identidad',return_value=ACTOR),patch.object(s,'guardar',side_effect=remoto) as write:
        inicio=perf_counter();ui._persist('p');sincrono=(perf_counter()-inicio)*1000
        state['p_doc']['textos']['Observaciones']='Cambio ficticio'
        inicio=perf_counter();ui._persist('p',background=True);asincrono=(perf_counter()-inicio)*1000
        for _ in range(20):ui._persist('p',background=True)
        state['p_trabajo_io']['future'].result(timeout=3)
        ui._persist('p',background=True)
        print(json.dumps({'red_simulada_ms':1000,'clic_sincrono_ms':round(sincrono,2),
            'clic_segundo_plano_ms':round(asincrono,2),'operaciones_remotas':write.call_count,
            'esperadas':2,'guardado_confirmado':not state['p_pending']},ensure_ascii=False))


if __name__=='__main__':medir()

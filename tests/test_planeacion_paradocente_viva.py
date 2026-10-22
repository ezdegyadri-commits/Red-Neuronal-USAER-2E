"""Round trips del formato, sus sesiones y fuentes; sin datos ni red reales."""
from copy import deepcopy
from io import BytesIO
import json
import unittest
from unittest.mock import patch
try:
    from pypdf import PdfReader
except ImportError:
    import pymupdf
    class PdfReader:
        def __init__(self, stream):
            doc = pymupdf.open(stream=stream.getvalue() if hasattr(stream, 'getvalue') else stream, filetype="pdf")
            class _P:
                def __init__(self, p): self.p = p
                def extract_text(self): return self.p.get_text()
            self.pages = [_P(p) for p in doc]
from services import planeacion as s,planeacion_equipo as equipo,planeacion_papel as papel
from services import planeacion_social as social,planeacion_local as local,planeacion_edicion as ed
from tests.test_planeacion_completa import documento
from tests.test_planeacion_equipo import sesion


class FormatoParadocenteTests(unittest.TestCase):
    def setUp(self):
        self.auth=patch.object(s,'autorizar',return_value={});self.auth.start();self.addCleanup(self.auth.stop)

    def con_sesion(self,area):
        doc=equipo.guardar_subgrupo(documento(area),'Subgrupo 1',['A1'])
        return equipo.guardar_sesion(doc,{**sesion(contexto='Familia' if area=='Trabajo Social' else 'Aula de apoyo'),
            'competencias':list(equipo.COMPETENCIAS) if area=='Psicología' else []})

    def evento(self,doc,**kw):return {'documento':doc['id'],'huella':papel.huella(doc),'cambios':{},'accion':'guardar',**kw}
    def key(self,doc,target):return next(k for k,c in papel.hoja(doc)['cells'].items() if c['target']==target)

    def test_sesion_se_edita_en_hoja_y_persiste_en_calendario_y_pdf(self):
        from documents.planeacion_papel import generar_pdf
        for area in equipo.AREAS:
            with self.subTest(area=area):
                doc=self.con_sesion(area);antes=deepcopy(doc);sid=doc['metadatos']['equipo']['sesiones'][0]['id']
                fecha='Fecha' if area=='Trabajo Social' else 'Temporalidad'
                cambios={self.key(doc,('sesion',sid,c)):v for c,v in {
                    'Actividades':'REDACCION REVISADA EN MI HOJA','Contextos':'Escuela',fecha:'2026-10-20','Recursos':'Material acordado'}.items()}
                nuevo=papel.aplicar(doc,self.evento(doc,cambios=cambios))
                e=equipo.sesion_vinculada(nuevo,sid)
                self.assertEqual(e['fecha'],'2026-10-20');self.assertEqual(e['contexto'],'Escuela')
                self.assertEqual(e['texto_formato'],'REDACCION REVISADA EN MI HOJA')
                self.assertEqual(equipo.sincronizar(nuevo),nuevo);self.assertEqual(doc,antes)
                actualizado=equipo.guardar_sesion(nuevo,{**e,'recursos':'Recurso actualizado'},sid)
                row=next(r for r in actualizado['tablas']['dosificacion'] if r.get('_sesion_equipo')==sid)
                self.assertEqual(row['Actividades'],e['texto_formato']);self.assertEqual(row['Recursos'],'Recurso actualizado')
                texto='\n'.join(p.extract_text() for p in PdfReader(BytesIO(generar_pdf(actualizado))).pages)
                self.assertIn('REDACCION REVISADA EN MI HOJA',texto)
                self.assertNotIn('Observan tarjetas, eligen una emoción',texto)
                propuestas=ed.actividades(actualizado)
                ref=next(k for k,v in propuestas.items() if v['tabla']=='sesion')
                revisado=ed.aplicar_revision(actualizado,{'huella':ed.huella(actualizado),'cambios':[{'referencia':ref,'actividad':'Nuevo texto aceptado'}]})
                self.assertEqual(equipo.sesion_vinculada(revisado,sid)['texto_formato'],'Nuevo texto aceptado')

    def test_vaciar_y_retirar_no_reaparece_al_sincronizar(self):
        for area in equipo.AREAS:
            doc=self.con_sesion(area);sid=doc['metadatos']['equipo']['sesiones'][0]['id']
            nuevo=papel.aplicar(doc,self.evento(doc,cambios={self.key(doc,('sesion',sid,'Actividades')):''}))
            self.assertEqual(equipo.sesion_vinculada(nuevo,sid)['texto_formato'],'')
            idx=next(i for i,r in enumerate(nuevo['tablas']['dosificacion']) if r.get('_sesion_equipo')==sid)
            quitado=papel.aplicar(nuevo,self.evento(nuevo,accion='retirar',tabla='dosificacion',fila=idx,confirmado=True))
            self.assertEqual(quitado['metadatos']['equipo']['sesiones'],[])
            self.assertEqual(equipo.sincronizar(quitado),quitado)
            self.assertEqual(len(doc['metadatos']['equipo']['sesiones']),1)

    def test_contexto_fecha_y_aportacion_se_validan(self):
        doc=self.con_sesion('Trabajo Social');sid=doc['metadatos']['equipo']['sesiones'][0]['id']
        for campo,value in [('Contextos','Otro'),('Fecha','2028-01-01')]:
            with self.assertRaises(ValueError):papel.aplicar(doc,self.evento(doc,cambios={self.key(doc,('sesion',sid,campo)):value}))
        row=next(r for r in doc['tablas']['dosificacion'] if r.get('_sesion_equipo'));row['_aporte']='Otro profesional'
        spec=papel.hoja(doc);t=next(t for t in spec['tables'] if t['id']=='dosificacion')
        self.assertTrue(all(not c['editable'] for c in t['rows'][-1]))

    def test_competencias_y_familia_editables_en_formato_psicologia(self):
        doc=equipo.preparar(documento('Psicología'));antes=deepcopy(doc)
        nuevo=papel.aplicar(doc,self.evento(doc,cambios={
            self.key(doc,('competencia',0,'Descriptor de logro')):'Identifica dos emociones.',
            self.key(doc,('equipo','sugerencia_familia')):'Proponer un recurso accesible.'}))
        self.assertEqual(nuevo['metadatos']['equipo']['competencias'][0]['Descriptor de logro'],'Identifica dos emociones.')
        self.assertEqual(nuevo['metadatos']['equipo']['sugerencia_familia'],'Proponer un recurso accesible.')
        equipo.validar(nuevo);self.assertEqual(doc,antes)
        for area in ['Comunicación','Trabajo Social']:
            self.assertNotIn('competencias',[t['id'] for t in papel.hoja(equipo.preparar(documento(area)))['tables']])

    def test_ts_precarga_bap_epp_con_destinatarios_y_no_resultados(self):
        doc=documento('Trabajo Social',dos=True)
        doc['metadatos']['fuentes'][0].update(tipo='EPP',parte='Conclusión',revision='r1',texto=json.dumps({'BAP':[
            {'Contextos':'Escolar','Tipo de barrera':'La información se entrega en un medio inaccesible.','Acciones generales':'Ofrecer una alternativa accesible.'}]}))
        doc['metadatos']['fuentes'][1].update(tipo='III',texto='BAP_Fisicas: {"Item_1":{"pregunta":"Pregunta del instrumento","frecuencia":"Siempre"}}')
        antes=deepcopy(doc);nuevo=social.proponer(doc)
        self.assertEqual(len(nuevo['tablas']['barreras']),1);row=nuevo['tablas']['barreras'][0]
        self.assertEqual(row['_alumnos_apartados'],['A1']);self.assertEqual(row['_origenes_apartados'][0]['revision'],'r1')
        self.assertIn('información se entrega',row[social.BARRERA]);self.assertEqual(row[social.APOYO],'Ofrecer una alternativa accesible.')
        self.assertNotIn('Pregunta del instrumento',str(row));self.assertEqual(social.proponer(nuevo),nuevo)
        self.assertEqual(nuevo['textos'],doc['textos']);self.assertEqual(doc,antes)
        spec=papel.hoja(nuevo)
        self.assertEqual(spec['tables'][0]['headers'],['Nombre del alumno','Grado','Grupo'])
        self.assertNotIn('Condición:',str(spec['header']))
        nuevo['tablas']['barreras'][0][social.APOYO]='Decisión de TS'
        self.assertEqual(social.proponer(nuevo)['tablas']['barreras'][0][social.APOYO],'Decisión de TS')

    def test_ts_no_infiere_barrera_por_lectura_ni_copia_ajenos(self):
        doc=documento('Trabajo Social');self.assertFalse(social.proponer(doc)['tablas']['barreras'])
        f=doc['metadatos']['fuentes'][0];f.update(alumno='AJENO',texto='BAP: Barrera ajena')
        self.assertFalse(social.proponer(doc)['tablas']['barreras'])
        f.update(alumno='A1',vinculo_verificado=False)
        self.assertFalse(social.proponer(doc)['tablas']['barreras'])

    def test_continuidad_usa_formato_sin_ia_y_respeta_contexto(self):
        for area in equipo.AREAS:
            doc=documento(area);doc['metadatos']['fuentes']=[]
            tabla='barreras' if area=='Trabajo Social' else 'aprendizajes'
            campo=social.BARRERA if area=='Trabajo Social' else 'Necesidades educativas específicas'
            doc['tablas'][tabla]=[{campo:'Orientación redactada por el profesional'}]
            with patch('ai.planeacion.proponer') as ia:
                req=local.preparar(doc,contexto_actividad='Familia')
                nuevo=local.aplicar(doc,req,[r['id'] for r in req['propuestas']])
            ia.assert_not_called();self.assertEqual(nuevo['tablas']['dosificacion'][-1]['Contextos'],'Familia')
            self.assertEqual(nuevo['textos'],doc['textos']);self.assertEqual(nuevo['tablas'][tabla],doc['tablas'][tabla])

    def test_formato_completo_no_exige_recapturar_en_sesiones(self):
        for area in equipo.AREAS:
            d=equipo.preparar(documento(area));fecha='Fecha' if area=='Trabajo Social' else 'Temporalidad'
            if area=='Psicología':
                for row in d['metadatos']['equipo']['competencias']:
                    row.update({'Necesidad documentada':'Necesidad revisada','Descriptor de logro':'El alumno elige una respuesta accesible.'})
                d['metadatos']['equipo']['sugerencia_familia']='Sugerencia prevista para revisar.'
                d['tablas']['dosificacion']=[{'Contextos':'Aula de apoyo','Actividades':'Trabajar '+c,'Recursos':'Tarjetas',fecha:'2026-10-'+str(i+10)} for i,c in enumerate(equipo.COMPETENCIAS)]
                d['tablas']['dosificacion'].append({'Contextos':'Aula regular','Actividades':'Aplicar apoyo acordado.','Recursos':'Material disponible',fecha:'2026-10-20'})
                d['textos']['Evaluación']='Observar la participación durante las actividades.'
            else:
                d['tablas']['dosificacion']=[{'Contextos':'Familia','Actividades':'Revisar un apoyo acordado.','Recursos':'Material disponible',fecha:'2026-10-20'}]
                if area=='Trabajo Social':d['tablas']['barreras']=[{social.BARRERA:'Información en un medio inaccesible.',social.APOYO:'Medio accesible acordado.'}]
                else:
                    d['tablas']['aprendizajes']=[{'Necesidades educativas específicas':'Necesidad revisada','Aprendizaje y/u objetivo':'Comunicar una elección.','Descriptor de logro':'El alumno comunica una elección.'}]
                    d['textos']['Evaluación']='Observar el intercambio.'
            self.assertEqual(s.revisar(d),[],area)
            self.assertFalse(d['metadatos']['equipo']['sesiones'])

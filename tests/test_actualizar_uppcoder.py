"""Regresión de actualización Spark: migración aditiva, HTTPS y aislamiento del destino."""
import json
from io import BytesIO
import unittest
import urllib.parse
from sqlalchemy import Column,Integer,MetaData,Table,create_engine
from deploy.actualizar_uppcoder import columnas_pendientes,comprobar_https,RELEASE,RedireccionPrivada

class Respuesta(BytesIO):
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

class ClienteFicticio:
    def __init__(self):self.doc={'id':'plan-ficticio','metadatos':{}}
    def open(self,request,timeout):
        u=urllib.parse.urlsplit(request.full_url)
        assert u.scheme=='https' and u.netloc=='ficticio.example.invalid'
        path=u.path
        if path=='/':r=b'<script src="/assets/app.js"></script>'
        elif path=='/api/health':r={'release':RELEASE}
        elif path=='/api/auth/login':r={'user':{'usuario':'direccion.piloto'}}
        elif path=='/api/auth/logout':r={'ok':True}
        elif path=='/api/alumnos':r=[{'id':'alu-uppcoder-a','id_escuela':'esc-uppcoder-a','nombre_completo':'Estudiante ficticio A'}]
        elif path=='/api/planeaciones/nueva':r={'id':self.doc['id']}
        elif path=='/api/planeaciones':self.doc=json.loads(request.data);r={'status':'success'}
        elif path=='/api/planeaciones/plan-ficticio':r=self.doc
        elif path.endswith('/pdf'):r=b'%PDF-ficticio'
        else:raise AssertionError('Ruta inesperada')
        return Respuesta(r if isinstance(r,bytes) else json.dumps(r).encode())

class ActualizarSpark(unittest.TestCase):
    def test_https_guardado_reapertura_pdf_y_mediciones(self):
        c=ClienteFicticio();r=comprobar_https(c,'ficticio.example.invalid','direccion.piloto','Clave ficticia aislada')
        self.assertEqual(r['guardado_reapertura_pdf'],'correctos')
        self.assertIn('guardado_ms',r)
        self.assertEqual(len(r['cambio_escuela_api_ms']),1)
    def test_no_reenvia_credenciales_fuera_del_host(self):
        with self.assertRaises(RuntimeError):
            RedireccionPrivada('ficticio.example.invalid').redirect_request(None,None,302,'',{},'https://ajeno.example.invalid/')
    def test_no_altera_columnas_ni_datos_existentes(self):
        from unittest.mock import patch
        viejo=MetaData();Table('existente',viejo,Column('id',Integer,primary_key=True))
        nuevo=MetaData();Table('existente',nuevo,Column('id',Integer,primary_key=True),Column('pendiente',Integer))
        motor=create_engine('sqlite://')
        viejo.create_all(motor)
        with motor.connect() as db:
            from sqlalchemy import inspect
            inspeccion=inspect(db)
            class Inspectar:
                def get_table_names(self,**kw):return inspeccion.get_table_names()
                def get_columns(self,nombre,**kw):return inspeccion.get_columns(nombre)
            with patch('sqlalchemy.inspect',return_value=Inspectar()):
                with self.assertRaises(RuntimeError):columnas_pendientes(db,nuevo)
            self.assertEqual([c['name'] for c in inspeccion.get_columns('existente')],['id'])

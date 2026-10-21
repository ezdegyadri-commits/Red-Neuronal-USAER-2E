"""Catálogos de captura y ordenamiento; nunca migra filas al consultarlas."""
from datetime import date,datetime
import pandas as pd
from utils.escolar import grado_canonico,grupo_canonico
from utils.text import normalizar_texto

CONDICIONES=('INTELECTUAL','BAJA VISIÓN','CEGUERA','HIPOACUSIA','SORDERA','MOTORA','MÚLTIPLE','SORDOCEGUERA','TEA','PSICOSOCIAL','AS','TDA/TDAH','APRENDIZAJE','COMUNICACIÓN','CONDUCTA')
CATALOGOS={'Sexo':('H','M'),'Situacion_Alumno':('NI','RI'),
 'Nivel_Educativo':('Preescolar','Primaria','Secundaria'),
 'Grado':tuple(f'{i}°' for i in range(1,7)),'Grupo':tuple('ABCDEFGHIJKLMNOPQRSTUVWXYZ')+('ÚNICO',),
 'Condicion_Discapacidad':CONDICIONES,'Estatus':('Activo','Baja','Inactivo','Retirado'),
 'Tipo_Atencion':('Individual','Grupal'),
 **{k:('Sí','No','No especificado') for k in ('Lengua_Indigena_Mayahablante','Afrodescendiente','Migrante')}}

def canonico(campo,valor):
    valor=str(valor or '').strip()
    if campo=='Grado':valor=grado_canonico(valor)
    if campo=='Grupo':valor=grupo_canonico(valor)
    return next((v for v in CATALOGOS.get(campo,()) if normalizar_texto(v)==normalizar_texto(valor)),valor)

def fecha_documental(valor):
    if isinstance(valor,datetime):return valor.date()
    if isinstance(valor,date):return valor
    valor=str(valor or '').strip()
    if not valor:return None
    for fmt in ('%Y-%m-%d','%d/%m/%Y','%d-%m-%Y'):
        try:return datetime.strptime(valor[:10],fmt).date()
        except ValueError:pass
    raise ValueError('La fecha debe capturarse con el calendario (día, mes y año).')

def ordenar(frame,criterio='Grado',descendente=False):
    resultado=frame.copy()
    if resultado.empty:return resultado
    nombre=resultado.get('Nombre_Completo',pd.Series('',index=resultado.index)).fillna('').map(normalizar_texto)
    resultado['_orden_nombre']=nombre
    if criterio=='Edad':
        resultado['_orden_valor']=pd.to_numeric(resultado.get('Edad_1_Septiembre'),errors='coerce')
    elif criterio=='Apellido':resultado['_orden_valor']=nombre
    else:
        resultado['_orden_valor']=pd.to_numeric(resultado.get('Grado',pd.Series('',index=resultado.index)).map(grado_canonico).str.extract(r'^([1-6])°$',expand=False),errors='coerce')
    return resultado.sort_values(['_orden_valor','_orden_nombre'],ascending=[not descendente,True],na_position='last',kind='stable').drop(columns=['_orden_valor','_orden_nombre'])

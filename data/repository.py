from datetime import date
from data.google import clear_cache, df_sheet, append_dict, ensure_sheet, ensure_headers, google_append_rows_raw, next_numeric_id, retry_google, worksheet
from config.settings import ANEXO4_FIELDS

BASE_HEADERS={
'Escuelas':['ID_Escuela','CCT','Nombre_Escuela','Nivel','Turno'],
'Personal':['ID_Personal','Nombre_Completo','Rol','Email','Telefono'],
'Asignaciones':['ID_Asignacion','ID_Personal','ID_Escuela'],
'Alumnos':['ID_Alumno','Nombre_Completo','CURP','Edad_1_Septiembre','Sexo','Situacion_Alumno','Nivel_Educativo','Grado','Grupo','ID_Escuela','Maestra de Apoyo','ID_Maestro_Regular','Condicion_Discapacidad','Estatus','Tipo_Atencion','Lengua_Indigena_Mayahablante','Afrodescendiente','Migrante','Nombre_Escuela','Turno_Escuela','CCT_Escuela','Direccion_Escuela','Localidad_Escuela','Municipio_Escuela'],
'Anexo3_Deteccion':['ID_Anexo3','Fecha','ID_Alumno','ID_Personal','BAP_Fisicas','BAP_Actitudinales','BAP_Pedagogicas','BAP_Organizativas','Estatus_IA'],
'Anexo4_Sugerencias':ANEXO4_FIELDS,
'Anexo5_Eventos':['ID_Evento','Fecha','Nombre_Alumno','Grado_Grupo','Especialista','Evento'],
'Usuarios':['ID_Usuario','Nombre','Usuario','Password','Rol','Escuelas_Permitidas'],
'Registro_Visitas':['ID_Visita','Fecha','Escuela','Personal','Motivo','Observaciones','Evidencia','Estatus']}
INTEGRATED_HEADERS={
'Expedientes':['ID_Expediente','ID_Alumno','Estatus','Fecha_Apertura','Ultima_Actualizacion'],
'Relaciones_Expediente':['ID_Relacion','ID_Expediente','ID_Alumno','Tipo_Registro','ID_Registro','Fecha','Estado'],
'Linea_Tiempo':['ID_Evento_Timeline','ID_Expediente','ID_Alumno','Fecha','Tipo','Titulo','Descripcion','Usuario']}

def read(name): return df_sheet(name)
def alumnos(): return read('Alumnos')
def personal(): return read('Personal')
def asignaciones(): return read('Asignaciones')
def usuarios(): return read('Usuarios')
def anexo3(): return read('Anexo3_Deteccion')
def anexo4(): return read('Anexo4_Sugerencias')
def anexo5(): return read('Anexo5_Eventos')
def escuelas(): return read('Escuelas')
def visitas(): return read('Registro_Visitas')

def save_alumno(data):
 ensure_headers('Alumnos', BASE_HEADERS['Alumnos'])
 data=dict(data); data.setdefault('ID_Alumno',next_numeric_id('Alumnos','ID_Alumno','ALU')); append_dict('Alumnos',data); return data['ID_Alumno']

def save_alumnos(rows):
 ensure_headers('Alumnos', BASE_HEADERS['Alumnos'])
 existing = alumnos()
 numbers = []
 if not existing.empty and 'ID_Alumno' in existing.columns:
  for value in existing['ID_Alumno'].astype(str):
   try: numbers.append(int(value.split('-')[-1]))
   except Exception: pass
 next_number = max(numbers) + 1 if numbers else 1
 prepared = []
 for row in rows:
  data = dict(row)
  data.setdefault('ID_Alumno', f"ALU-{next_number:03d}")
  next_number += 1
  prepared.append(data)
 google_append_rows_raw('Alumnos', prepared)
 return [row['ID_Alumno'] for row in prepared]

def upsert_alumnos(rows):
 """Consolida padrones por CURP: agrega nuevos y completa únicamente campos vacíos."""
 ensure_headers('Alumnos', BASE_HEADERS['Alumnos'])
 if not rows:
  return 0, 0
 ws = worksheet('Alumnos')
 values = retry_google(ws.get_all_values)
 headers = values[0] if values else []
 if 'CURP' not in headers:
  raise ValueError("La hoja central no tiene la columna CURP.")
 curp_col = headers.index('CURP')
 existing = {
  str(row[curp_col]).strip().upper(): index
  for index, row in enumerate(values[1:], start=2)
  if len(row) > curp_col and str(row[curp_col]).strip()
 }
 id_col = headers.index('ID_Alumno') if 'ID_Alumno' in headers else -1
 numbers = []
 for row in values[1:]:
  if id_col >= 0 and len(row) > id_col:
   try:
    numbers.append(int(str(row[id_col]).split('-')[-1]))
   except (TypeError, ValueError):
    pass
 next_number = max(numbers) + 1 if numbers else 1
 nuevos, actualizados, append_rows, updates = 0, 0, [], []
 for registro in rows:
  data = dict(registro)
  curp = str(data.get('CURP', '')).strip().upper()
  fila = existing.get(curp)
  if fila:
   actual = values[fila - 1] + [''] * max(0, len(headers) - len(values[fila - 1]))
   nombre_actual = str(actual[headers.index('Nombre_Completo')]).strip() if 'Nombre_Completo' in headers else ''
   escuela_importada = str(data.get('Nombre_Escuela', '')).strip()
   cambio = False
   for col, header in enumerate(headers):
    nuevo = str(data.get(header, '')).strip()
    debe_reparar_nombre = header == 'Nombre_Completo' and nombre_actual and nombre_actual == escuela_importada
    if nuevo and (not str(actual[col]).strip() or debe_reparar_nombre):
     actual[col] = nuevo
     cambio = True
   if cambio:
    final_col = chr(64 + len(headers))
    updates.append({"range": f'A{fila}:{final_col}{fila}', "values": [actual[:len(headers)]]})
    actualizados += 1
  else:
   data['ID_Alumno'] = f"ALU-{next_number:03d}"
   next_number += 1
   append_rows.append(data)
   nuevos += 1
 if updates:
  retry_google(lambda: ws.batch_update(updates, value_input_option='USER_ENTERED'))
 if append_rows:
  google_append_rows_raw('Alumnos', append_rows)
 if actualizados:
  clear_cache('Alumnos')
 return nuevos, actualizados

def repair_nombres_alumnos(rows):
 """Corrige solo nombres cuando un padrón previo guardó el nombre de la escuela."""
 if not rows:
  return 0
 ws = worksheet('Alumnos')
 headers = ws.row_values(1)
 if 'CURP' not in headers or 'Nombre_Completo' not in headers:
  return 0
 col_curp = headers.index('CURP') + 1
 col_nombre = headers.index('Nombre_Completo') + 1
 filas_por_curp = {
  str(valor).strip().upper(): indice
  for indice, valor in enumerate(ws.col_values(col_curp), start=1)
  if indice > 1 and str(valor).strip()
 }
 corregidos = 0
 for registro in rows:
  fila = filas_por_curp.get(str(registro.get('CURP', '')).strip().upper())
  nombre = str(registro.get('Nombre_Completo', '')).strip()
  if fila and nombre:
   ws.update_cell(fila, col_nombre, nombre)
   corregidos += 1
 if corregidos:
  clear_cache('Alumnos')
 return corregidos

def save_anexo3(data):
 data=dict(data); data.setdefault('ID_Anexo3',next_numeric_id('Anexo3_Deteccion','ID_Anexo3','AN3')); append_dict('Anexo3_Deteccion',data); return data['ID_Anexo3']
def save_anexo4(data):
 data=dict(data); data.setdefault('ID_Anexo4',next_numeric_id('Anexo4_Sugerencias','ID_Anexo4','AN4')); append_dict('Anexo4_Sugerencias',data); return data['ID_Anexo4']
def save_anexo5(data):
 data=dict(data); data.setdefault('ID_Evento',next_numeric_id('Anexo5_Eventos','ID_Evento','AN5')); append_dict('Anexo5_Eventos',data); return data['ID_Evento']
def save_visita(data):
 data=dict(data); data.setdefault('ID_Visita',next_numeric_id('Registro_Visitas','ID_Visita','VIS')); append_dict('Registro_Visitas',data); return data['ID_Visita']

def ensure_integrated_sheets():
 for name,headers in {**INTEGRATED_HEADERS,'Registro_Visitas':BASE_HEADERS['Registro_Visitas']}.items(): ensure_sheet(name,headers)

def ensure_expediente(id_expediente,id_alumno,estatus='ACTIVO'):
 ensure_integrated_sheets(); df=read('Expedientes')
 if not df.empty and 'ID_Expediente' in df.columns and str(id_expediente) in set(df['ID_Expediente'].astype(str)): return False
 hoy=str(date.today()); append_dict('Expedientes',{'ID_Expediente':id_expediente,'ID_Alumno':id_alumno,'Estatus':estatus,'Fecha_Apertura':hoy,'Ultima_Actualizacion':hoy}); return True

def existing_relations():
 df=read('Relaciones_Expediente')
 if df.empty: return set()
 return set(zip(df['ID_Expediente'].astype(str),df['Tipo_Registro'].astype(str),df['ID_Registro'].astype(str)))

def link_record(id_expediente,id_alumno,tipo,id_registro,fecha,estado='ACTIVO'):
 ensure_integrated_sheets(); key=(str(id_expediente),str(tipo),str(id_registro))
 if key in existing_relations(): return None
 rid=next_numeric_id('Relaciones_Expediente','ID_Relacion','REL'); append_dict('Relaciones_Expediente',{'ID_Relacion':rid,'ID_Expediente':id_expediente,'ID_Alumno':id_alumno,'Tipo_Registro':tipo,'ID_Registro':id_registro,'Fecha':fecha,'Estado':estado}); return rid

def timeline(id_expediente,id_alumno,fecha,tipo,titulo,descripcion,usuario):
 ensure_integrated_sheets(); df=read('Linea_Tiempo')
 if not df.empty:
  mask=(df['ID_Expediente'].astype(str)==str(id_expediente))&(df['Tipo'].astype(str)==str(tipo))&(df['Titulo'].astype(str)==str(titulo))&(df['Fecha'].astype(str)==str(fecha))
  if mask.any(): return None
 tid=next_numeric_id('Linea_Tiempo','ID_Evento_Timeline','TL'); append_dict('Linea_Tiempo',{'ID_Evento_Timeline':tid,'ID_Expediente':id_expediente,'ID_Alumno':id_alumno,'Fecha':fecha,'Tipo':tipo,'Titulo':titulo,'Descripcion':descripcion,'Usuario':usuario}); return tid

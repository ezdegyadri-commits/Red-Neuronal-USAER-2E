from datetime import date
from data.google import clear_cache, df_sheet, append_dict, ensure_sheet, ensure_headers, google_append_rows_raw, next_numeric_id, retry_google, worksheet
from config.settings import ANEXO4_FIELDS

BASE_HEADERS={
'Escuelas':['ID_Escuela','CCT','Nombre_Escuela','Nivel','Turno'],
'Personal':['ID_Personal','Nombre_Completo','Rol','Email','Telefono'],
'Asignaciones':['ID_Asignacion','ID_Personal','ID_Escuela'],
'Alumnos':['ID_Alumno','Nombre_Completo','CURP','Edad_1_Septiembre','Sexo','Situacion_Alumno','Nivel_Educativo','Grado','Grupo','ID_Escuela','Maestra de Apoyo','ID_Maestro_Regular','Condicion_Discapacidad','Estatus','Tipo_Atencion','Lengua_Indigena_Mayahablante','Afrodescendiente','Migrante','Nombre_Escuela','Turno_Escuela','CCT_Escuela','Direccion_Escuela','Localidad_Escuela','Municipio_Escuela','Condiciones_Adicionales'],
'Anexo3_Deteccion':['ID_Anexo3','Fecha','ID_Alumno','ID_Personal','BAP_Fisicas','BAP_Actitudinales','BAP_Pedagogicas','BAP_Organizativas','Estatus_IA'],
'Anexo4_Sugerencias':ANEXO4_FIELDS,
'Anexo5_Eventos':['ID_Evento','Fecha','Nombre_Alumno','Grado_Grupo','Especialista','Evento'],
'Usuarios':['ID_Usuario','Nombre','Usuario','Password','Rol','Escuelas_Permitidas'],
'Registro_Visitas':['ID_Visita','Fecha','Escuela','Personal','Motivo','Observaciones','Evidencia','Estatus'],
'Oficios_Comision':['ID_Oficio','Folio','Clave_Operacion','Fecha_Emision','Fecha_Comision','Escuela','ID_Escuela','Maestra_Apoyo','Director_Escuela','Asunto','Destino','Horario','Estado'],
'Configuracion_Oficios':['ID_Configuracion','Fecha_Comision','Asunto','Destino','Horario','Actualizado_Por','Actualizado_En'],
'Anexo7_Derivacion':['ID_Anexo7','Fecha','ID_Alumno','Escuela','Docente_Regular','Fecha_Nacimiento','Respuestas_JSON','Salud','Seguimiento_Medico','Aspecto_Relevante','Elaborado_Por']}
INTEGRATED_HEADERS={
'Expedientes':['ID_Expediente','ID_Alumno','Estatus','Fecha_Apertura','Ultima_Actualizacion'],
'Relaciones_Expediente':['ID_Relacion','ID_Expediente','ID_Alumno','Tipo_Registro','ID_Registro','Fecha','Estado'],
'Linea_Tiempo':['ID_Evento_Timeline','ID_Expediente','ID_Alumno','Fecha','Tipo','Titulo','Descripcion','Usuario']}

def read(name): return df_sheet(name)
def alumnos():
 """Lee solo la base interna vigente y omite columnas duplicadas heredadas."""
 frame = read('Alumnos')
 columnas = [col for col in BASE_HEADERS['Alumnos'] if col in frame.columns]
 frame = frame[columnas].copy() if columnas else frame
 if {'Nombre_Completo', 'CURP'}.issubset(frame.columns):
  con_alumno = (
   frame['Nombre_Completo'].fillna('').astype(str).str.strip().ne('')
   | frame['CURP'].fillna('').astype(str).str.strip().ne('')
  )
  frame = frame.loc[con_alumno].reset_index(drop=True)
 return frame
def personal(): return read('Personal')
def asignaciones(): return read('Asignaciones')
def usuarios(): return read('Usuarios')
def anexo3(): return read('Anexo3_Deteccion')
def anexo4(): return read('Anexo4_Sugerencias')
def anexo5(): return read('Anexo5_Eventos')
def escuelas(): return read('Escuelas')
def visitas(): return read('Registro_Visitas')
def oficios_comision(): return read('Oficios_Comision')
def configuracion_oficios():
 """Lee la configuración sin validar la hoja en cada navegación."""
 try:
  return read('Configuracion_Oficios')
 except Exception:
  ensure_headers('Configuracion_Oficios', BASE_HEADERS['Configuracion_Oficios'])
  return read('Configuracion_Oficios')
def configuracion_oficios_actual():
 configuracion = configuracion_oficios()
 return configuracion.tail(1).iloc[0].to_dict() if not configuracion.empty else {}
def anexo7(): return read('Anexo7_Derivacion')

PADRON_FIELDS = {
 'Nombre_Completo', 'CURP', 'Edad_1_Septiembre', 'Sexo', 'Situacion_Alumno',
 'Nivel_Educativo', 'Grado', 'Grupo', 'ID_Escuela', 'Maestra de Apoyo',
 'ID_Maestro_Regular', 'Condicion_Discapacidad', 'Estatus', 'Tipo_Atencion',
 'Lengua_Indigena_Mayahablante', 'Afrodescendiente', 'Migrante',
 'Nombre_Escuela', 'Turno_Escuela', 'CCT_Escuela', 'Direccion_Escuela',
 'Localidad_Escuela', 'Municipio_Escuela', 'Condiciones_Adicionales',
}


def _a1_column(number):
 """Convierte un número de columna de base 1 a referencia A1."""
 result = ""
 while number:
  number, remainder = divmod(number - 1, 26)
  result = chr(65 + remainder) + result
 return result


def save_alumno(data):
 """Registra o actualiza un alumno por CURP sin duplicar su expediente."""
 _, _, ids = upsert_alumnos([data], return_ids=True)
 return ids[0] if ids else ""


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


def upsert_alumnos(rows, return_ids=False):
 """Consolida padrones por CURP.

 Los valores no vacíos del padrón que se está cargando son la fuente de verdad
 para los datos del alumno. Se conservan el ID y todos los campos que el
 archivo no aporta, por lo que no se eliminan expedientes ni información útil.
 """
 ensure_headers('Alumnos', BASE_HEADERS['Alumnos'])
 if not rows:
  return (0, 0, []) if return_ids else (0, 0)

 ws = worksheet('Alumnos')
 values = retry_google(ws.get_all_values)
 headers = values[0] if values else []
 if 'CURP' not in headers:
  raise ValueError("La hoja central no tiene la columna CURP.")

 curp_col = headers.index('CURP')
 id_col = headers.index('ID_Alumno') if 'ID_Alumno' in headers else -1
 existing = {
  str(row[curp_col]).strip().upper(): index
  for index, row in enumerate(values[1:], start=2)
  if len(row) > curp_col and str(row[curp_col]).strip()
 }

 numbers = []
 for row in values[1:]:
  if id_col >= 0 and len(row) > id_col:
   try:
    numbers.append(int(str(row[id_col]).split('-')[-1]))
   except (TypeError, ValueError):
    pass
 next_number = max(numbers) + 1 if numbers else 1

 nuevos, actualizados, append_rows, updates, ids = 0, 0, [], [], []
 for registro in rows:
  data = dict(registro)
  curp = str(data.get('CURP', '')).strip().upper()
  if not curp:
   continue
  data['CURP'] = curp
  fila = existing.get(curp)

  if fila:
   actual = values[fila - 1] + [''] * max(0, len(headers) - len(values[fila - 1]))
   student_id = str(actual[id_col]).strip() if id_col >= 0 else ""
   cambio = False
   for col, header in enumerate(headers):
    nuevo = str(data.get(header, '')).strip()
    if header in PADRON_FIELDS and nuevo and nuevo != str(actual[col]).strip():
     updates.append({
      "range": f"{_a1_column(col + 1)}{fila}",
      "values": [[nuevo]],
     })
     cambio = True
   if cambio:
    actualizados += 1
   ids.append(student_id)
  else:
   data['ID_Alumno'] = f"ALU-{next_number:03d}"
   next_number += 1
   append_rows.append(data)
   ids.append(data['ID_Alumno'])
   nuevos += 1

 if updates:
  retry_google(lambda: ws.batch_update(updates, value_input_option='USER_ENTERED'))
 if append_rows:
  google_append_rows_raw('Alumnos', append_rows)
 if actualizados or append_rows:
  clear_cache('Alumnos')

 result = (nuevos, actualizados)
 return (*result, ids) if return_ids else result




def guardar_configuracion_oficios(data):
 """Registra la configuración vigente definida exclusivamente por Dirección."""
 headers = BASE_HEADERS['Configuracion_Oficios']
 ensure_headers('Configuracion_Oficios', headers)
 registro = dict(data)
 registro.setdefault(
  'ID_Configuracion',
  next_numeric_id('Configuracion_Oficios', 'ID_Configuracion', 'CFG-OFI')
 )
 append_dict('Configuracion_Oficios', registro)
 clear_cache('Configuracion_Oficios')
 return registro

def guardar_oficio_comision(data):
 """Guarda una emisión por clave única y asigna un folio consecutivo."""
 headers = BASE_HEADERS['Oficios_Comision']
 ensure_headers('Oficios_Comision', headers)
 ws = worksheet('Oficios_Comision')
 values = retry_google(ws.get_all_values)
 actuales = values[1:] if values else []
 indice_clave = headers.index('Clave_Operacion')
 indice_id = headers.index('ID_Oficio')
 indice_folio = headers.index('Folio')

 clave = str(data.get('Clave_Operacion', '')).strip()
 for fila in actuales:
  fila = fila + [''] * max(0, len(headers) - len(fila))
  if clave and str(fila[indice_clave]).strip() == clave:
   return {
    'ID_Oficio': fila[indice_id],
    'Folio': fila[indice_folio],
    **data,
   }

 folios = []
 for fila in actuales:
  try:
   folios.append(int(str(fila[indice_folio]).strip()))
  except (ValueError, IndexError):
   pass
 folio = max(folios) + 1 if folios else 1
 registro = dict(data)
 registro['ID_Oficio'] = f"OFI-{folio:03d}"
 registro['Folio'] = folio
 registro.setdefault('Estado', 'GENERADO')
 google_append_rows_raw('Oficios_Comision', [registro])
 clear_cache('Oficios_Comision')
 return registro

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

def update_anexo4(id_anexo4, cambios):
 """Actualiza un Anexo IV existente sin borrar columnas ni crear duplicados."""
 ws=worksheet('Anexo4_Sugerencias')
 headers=retry_google(lambda: ws.row_values(1))
 if 'ID_Anexo4' not in headers:
  raise ValueError('La hoja Anexo4_Sugerencias no contiene ID_Anexo4.')
 id_col=headers.index('ID_Anexo4')+1
 ids=retry_google(lambda: ws.col_values(id_col))
 fila=next((i for i,v in enumerate(ids,start=1) if str(v).strip()==str(id_anexo4).strip()),None)
 if not fila:
  raise ValueError(f'No se encontró el Anexo IV {id_anexo4}.')
 actual=retry_google(lambda: ws.row_values(fila))
 actual += [''] * (len(headers)-len(actual))
 for campo,valor in dict(cambios).items():
  if campo in headers and campo!='ID_Anexo4':
   actual[headers.index(campo)]=valor
 def columna(numero):
  letras=''
  while numero:
   numero,resto=divmod(numero-1,26)
   letras=chr(65+resto)+letras
  return letras
 rango=f"A{fila}:{columna(len(headers))}{fila}"
 retry_google(lambda: ws.update(range_name=rango,values=[actual[:len(headers)]]))
 clear_cache('Anexo4_Sugerencias')
 return str(id_anexo4)
def save_anexo5(data):
 data=dict(data); data.setdefault('ID_Evento',next_numeric_id('Anexo5_Eventos','ID_Evento','AN5')); append_dict('Anexo5_Eventos',data); return data['ID_Evento']
def save_anexo7(data):
 ensure_headers('Anexo7_Derivacion', BASE_HEADERS['Anexo7_Derivacion'])
 data=dict(data); data.setdefault('ID_Anexo7',next_numeric_id('Anexo7_Derivacion','ID_Anexo7','AN7')); append_dict('Anexo7_Derivacion',data); return data['ID_Anexo7']
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

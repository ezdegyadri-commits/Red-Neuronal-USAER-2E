import pandas as pd
from datetime import date
from data.google import clear_cache, df_sheet, append_dict, ensure_sheet, ensure_headers, google_append_rows_raw, next_numeric_id, read_personal_responses, retry_google, worksheet
from config.settings import ANEXO4_FIELDS

BASE_HEADERS={
'Escuelas':['ID_Escuela','CCT','Nombre_Escuela','Nivel','Turno'],
'Personal':['ID_Personal','Nombre_Completo','Rol','Email','Telefono'],
'Asignaciones':['ID_Asignacion','ID_Personal','ID_Escuela'],
'Alumnos':['ID_Alumno','Nombre_Completo','CURP','Edad_1_Septiembre','Sexo','Situacion_Alumno','Nivel_Educativo','Grado','Grupo','ID_Escuela','Maestra de Apoyo','ID_Maestro_Regular','Condicion_Discapacidad','Estatus','Tipo_Atencion','Lengua_Indigena_Mayahablante','Afrodescendiente','Migrante','Nombre_Escuela','Turno_Escuela','CCT_Escuela','Direccion_Escuela','Localidad_Escuela','Municipio_Escuela','Condiciones_Adicionales'],
'Anexo3_Deteccion':['ID_Anexo3','Fecha','ID_Alumno','ID_Personal','BAP_Fisicas','BAP_Actitudinales','BAP_Pedagogicas','BAP_Organizativas','Estatus_IA'],
'Anexo4_Sugerencias':ANEXO4_FIELDS,
'Anexo5_Eventos':['ID_Evento','Fecha','Nombre_Alumno','Grado_Grupo','Especialista','Evento','Estado','ID_Alumno'],
'Usuarios':['ID_Usuario','Nombre','Usuario','Password','Rol','Escuelas_Permitidas'],
'Registro_Visitas':['ID_Visita','Fecha','Escuela','Personal','Motivo','Observaciones','Evidencia','Estatus'],
'Oficios_Comision':['ID_Oficio','Folio','Clave_Operacion','Fecha_Emision','Fecha_Comision','Escuela','ID_Escuela','Maestra_Apoyo','Director_Escuela','Asunto','Destino','Horario','Estado'],
'Configuracion_Oficios':['ID_Configuracion','Fecha_Comision','Asunto','Destino','Horario','Actualizado_Por','Actualizado_En'],
'Anexo7_Derivacion':['ID_Anexo7','Fecha','ID_Alumno','Escuela','Docente_Regular','Fecha_Nacimiento','Respuestas_JSON','Salud','Seguimiento_Medico','Aspecto_Relevante','Elaborado_Por']}
INTEGRATED_HEADERS={
'Expedientes':['ID_Expediente','ID_Alumno','Estatus','Fecha_Apertura','Ultima_Actualizacion'],
'Relaciones_Expediente':['ID_Relacion','ID_Expediente','ID_Alumno','Tipo_Registro','ID_Registro','Fecha','Estado'],
'Linea_Tiempo':['ID_Evento_Timeline','ID_Expediente','ID_Alumno','Fecha','Tipo','Titulo','Descripcion','Usuario']}
-
def read(name): return df_sheet(name)
def alumnos():
 """Lee la base central y deja una sola fila operativa por CURP.

 La hoja conserva duplicados y pendientes para auditoría, pero los procesos
 de la plataforma trabajan con el registro activo preferente.
 """
 frame = read('Alumnos')
 columnas = [col for col in BASE_HEADERS['Alumnos'] if col in frame.columns]
 frame = frame[columnas].copy() if columnas else frame
 if {'Nombre_Completo', 'CURP'}.issubset(frame.columns):
  con_alumno = (
   frame['Nombre_Completo'].fillna('').astype(str).str.strip().ne('')
   | frame['CURP'].fillna('').astype(str).str.strip().ne('')
  )
  frame = frame.loc[con_alumno].reset_index(drop=True)
  if 'CURP' in frame.columns and not frame.empty:
   frame['_curp_operativa'] = frame['CURP'].fillna('').astype(str).str.strip().str.upper()
   estado = frame.get('Estatus', pd.Series('', index=frame.index)).fillna('').astype(str).str.strip().str.upper()
   frame['_prioridad_operativa'] = 1
   frame.loc[estado.eq('ACTIVO'), '_prioridad_operativa'] = 0
   frame.loc[estado.str.startswith('PENDIENTE') | estado.str.startswith('DUPLICADO'), '_prioridad_operativa'] = 2
   frame = (
    frame.sort_values(['_curp_operativa', '_prioridad_operativa'], kind='stable')
    .drop_duplicates(subset=['_curp_operativa'], keep='first')
    .drop(columns=['_curp_operativa', '_prioridad_operativa'])
    .reset_index(drop=True)
   )
 return frame
def personal(): return read('Personal')
-
-
def personal_para_formato():
 """Obtiene personal del formulario; usa la hoja central como respaldo."""
 respuestas = pd.DataFrame(read_personal_responses())
 if respuestas.empty:
  return personal()
-
 def normalizar(texto):
  import re
  import unicodedata
  texto = unicodedata.normalize('NFD', str(texto)).encode('ascii', 'ignore').decode('ascii')
  return re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()
-
 encabezados = {normalizar(columna): columna for columna in respuestas.columns}
 aliases = {
  'ID_Personal': ('direccion de correo electronico',),
  'Nombre_Completo': ('nombre del docente de apoyo paradocentes',),
  'Rol': ('funcion que desempena',),
  'Email': ('direccion de correo electronico',),
  'Telefono': ('telefono 10 digitos',),
  'Sexo': ('sexo',),
  'Base_Contrato': ('base contrato',),
  'Sostenimiento': ('sostenimiento',),
  'Presenta_Discapacidad': ('presenta alguna discapacidad',),
  'Horario': ('horario de trabajo',),
  'Discapacidad': ('elija la categoria de discapacidad',),
  'Maya_Hablante': ('es usted maya hablante',),
  'Zona': ('zona',),
  'Numero_USAER': ('n usaer',),
  'CCT_USAER': ('clave de centro de trabajo de la usaer',),
  'Turno_USAER': ('turno',),
  'Numero_Escuelas': ('numero de escuelas',),
  'Escuelas_Atendidas': ('nombre de la escuela que atiende',),
  'CCT_Escuela': ('clave de centro de trabajo de la escuela regular',),
  'Nivel_Escuela': ('nivel educativo de la escuela regular',),
  'Modalidad_Escuela': ('modalidad general indigena',),
  'Horario_Escuela': ('horario en el que la escuela regular permanece abierta',),
  'Grupos_Escuela': ('total de grupos que tiene la escuela',),
  'Direccion_Escuela': ('direccion de la escuela calle numero',),
  'Localidad_Escuela': ('localidad de la escuela regular',),
  'Municipio_Escuela': ('municipio de la escuela regular',),
 }
 columnas = {}
 for destino, candidatos in aliases.items():
  for encabezado, original in encabezados.items():
   if any(candidato in encabezado for candidato in candidatos):
    columnas[destino] = original
    break
-
 requeridas = {'Nombre_Completo', 'Rol', 'Email'}
 faltantes = requeridas - set(columnas)
 if faltantes:
  raise ValueError(
   'La hoja de respuestas no contiene los encabezados requeridos: '
   + ', '.join(sorted(faltantes))
  )
-
 personal_formulario = pd.DataFrame(index=respuestas.index)
 for destino, origen in columnas.items():
  personal_formulario[destino] = respuestas[origen].fillna('').astype(str).str.strip()
 if 'Telefono' in personal_formulario.columns:
  def limpiar_telefono(valor):
   import re
   digitos = re.sub(r'\D', '', valor)
   return digitos if len(digitos) == 10 else valor
  personal_formulario['Telefono'] = personal_formulario['Telefono'].map(limpiar_telefono)
 personal_formulario['Fuente_Formulario'] = True
 personal_formulario['Escuela_Asignada'] = personal_formulario.get('Escuelas_Atendidas', '')
 personal_formulario['Fuente_Fecha'] = respuestas.get('Marca temporal', '')
 return personal_formulario.reset_index(drop=True)
def asignaciones(): return read('Asignaciones')
def usuarios(): return read('Usuarios')
def anexo3(): return read('Anexo3_Deteccion')
def anexo4(): return read('Anexo4_Sugerencias')
def anexo5(): return read('Anexo5_Eventos')
-
def eventos_alumno(id_alumno, nombre="", grado_grupo=""):
 """Reúne eventos del expediente y eventos históricos sin modificar sus filas."""
 eventos = anexo5()
 if eventos.empty or "ID_Evento" not in eventos.columns:
  return eventos.iloc[0:0].copy() if not eventos.empty else eventos
-
 ligados = set()
 ids_ligados = set()
 try:
  relaciones = read("Relaciones_Expediente")
  if not relaciones.empty and {"Tipo_Registro", "ID_Registro"}.issubset(relaciones.columns):
   rel_anexo5 = relaciones[
    relaciones["Tipo_Registro"].fillna("").astype(str).str.upper().eq("ANEXO5")
   ].copy()
   ids_ligados = set(rel_anexo5["ID_Registro"].dropna().astype(str).str.strip())
   if "ID_Alumno" in rel_anexo5.columns:
    ligados = set(
     rel_anexo5.loc[
      rel_anexo5["ID_Alumno"].astype(str).str.strip().eq(str(id_alumno).strip()),
      "ID_Registro",
     ].dropna().astype(str).str.strip()
    )
 except Exception:
  pass
-
 ids_evento = eventos["ID_Evento"].fillna("").astype(str).str.strip()
 precisos = eventos.loc[ids_evento.isin(ligados)].copy() if ligados else eventos.iloc[0:0].copy()
 if "ID_Alumno" in eventos.columns:
  directos = eventos["ID_Alumno"].fillna("").astype(str).str.strip().eq(
   str(id_alumno).strip()
  )
  precisos = pd.concat([precisos, eventos.loc[directos]], ignore_index=True)
 legados = eventos.iloc[0:0].copy()
 if nombre and "Nombre_Alumno" in eventos.columns:
  nombre_normal = str(nombre).strip().casefold()
  coincide = eventos["Nombre_Alumno"].fillna("").astype(str).map(
   lambda valor: valor.strip().casefold() == nombre_normal
  )
  sin_vinculo = ~ids_evento.isin(ids_ligados)
  if "ID_Alumno" in eventos.columns:
   sin_id_directo = eventos["ID_Alumno"].fillna("").astype(str).str.strip().eq("")
   sin_vinculo &= sin_id_directo
  if grado_grupo and "Grado_Grupo" in eventos.columns:
   grado_normal = " ".join(str(grado_grupo).split()).casefold()
   grado_evento = eventos["Grado_Grupo"].fillna("").astype(str).map(
    lambda valor: " ".join(valor.split()).casefold()
   )
   coincide &= grado_evento.eq("") | grado_evento.eq(grado_normal)
  legados = eventos.loc[coincide & sin_vinculo].copy()
-
 resultado = pd.concat([precisos, legados], ignore_index=True)
 if "ID_Evento" in resultado.columns:
  resultado = resultado.drop_duplicates(subset=["ID_Evento"], keep="first")
 if not resultado.empty and "Fecha" in resultado.columns:
  resultado["_orden_cronologico"] = pd.to_datetime(
   resultado["Fecha"], errors="coerce", dayfirst=True
  )
  resultado = (
   resultado.sort_values("_orden_cronologico", na_position="last", kind="stable")
   .drop(columns="_orden_cronologico")
   .reset_index(drop=True)
  )
 return resultado
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
-
PADRON_FIELDS = {
 'Nombre_Completo', 'CURP', 'Edad_1_Septiembre', 'Sexo', 'Situacion_Alumno',
 'Nivel_Educativo', 'Grado', 'Grupo', 'ID_Escuela', 'Maestra de Apoyo',
 'ID_Maestro_Regular', 'Condicion_Discapacidad', 'Estatus', 'Tipo_Atencion',
 'Lengua_Indigena_Mayahablante', 'Afrodescendiente', 'Migrante',
 'Nombre_Escuela', 'Turno_Escuela', 'CCT_Escuela', 'Direccion_Escuela',
 'Localidad_Escuela', 'Municipio_Escuela', 'Condiciones_Adicionales',
}
-
-
def _a1_column(number):
 """Convierte un número de columna de base 1 a referencia A1."""
 result = ""
 while number:
  number, remainder = divmod(number - 1, 26)
  result = chr(65 + remainder) + result
 return result
-
-
def save_alumno(data):
 """Crea un alumno manual y rechaza CURP que ya existan en la base central."""
 _, _, ids = upsert_alumnos([data], return_ids=True, reject_existing=True)
 return ids[0] if ids else ""
-
def save_alumnos(rows):
 """Guarda altas nuevas solo si sus CURP no existen previamente."""
 _, _, ids = upsert_alumnos(rows, return_ids=True, reject_existing=True)
 return ids
-
def upsert_alumnos(rows, return_ids=False, reject_existing=False):
 """Consolida padrones por CURP.
-
 Los valores no vacíos del padrón que se está cargando son la fuente de verdad
 para los datos del alumno. Se conservan el ID y todos los campos que el
 archivo no aporta, por lo que no se eliminan expedientes ni información útil.
 """
 ensure_headers('Alumnos', BASE_HEADERS['Alumnos'])
 if not rows:
  return (0, 0, []) if return_ids else (0, 0)
-
 ws = worksheet('Alumnos')
 values = retry_google(ws.get_all_values)
 headers = values[0] if values else []
 if 'CURP' not in headers:
  raise ValueError("La hoja central no tiene la columna CURP.")
-
 curp_col = headers.index('CURP')
 id_col = headers.index('ID_Alumno') if 'ID_Alumno' in headers else -1
 status_col = headers.index('Estatus') if 'Estatus' in headers else -1
 existing_rows = {}
 for index, row in enumerate(values[1:], start=2):
  if len(row) > curp_col and str(row[curp_col]).strip():
   if status_col >= 0 and len(row) > status_col:
    estado = str(row[status_col]).strip().upper()
    if estado.startswith('DUPLICADO'):
     continue
   existing_rows.setdefault(str(row[curp_col]).strip().upper(), []).append(index)
 existing = {curp: rows[-1] for curp, rows in existing_rows.items()}
-
 numbers = []
 for row in values[1:]:
  if id_col >= 0 and len(row) > id_col:
   try:
    numbers.append(int(str(row[id_col]).split('-')[-1]))
   except (TypeError, ValueError):
    pass
 next_number = max(numbers) + 1 if numbers else 1
-
 nuevos, actualizados, append_rows, updates, ids = 0, 0, [], [], []
 seen_input = set()
 for registro in rows:
  data = dict(registro)
  curp = str(data.get('CURP', '')).strip().upper()
  if not curp:
   continue
  if curp in seen_input:
   raise ValueError(
    "El archivo contiene la misma CURP más de una vez. "
    "Corrige esa duplicación antes de consolidarlo."
   )
  seen_input.add(curp)
  data['CURP'] = curp
  coincidencias = existing_rows.get(curp, [])
  if len(coincidencias) > 1:
   ids_ambiguos = []
   for numero_fila in coincidencias:
    fila_existente = values[numero_fila - 1]
    if id_col >= 0 and len(fila_existente) > id_col:
     valor_id = str(fila_existente[id_col]).strip()
     if valor_id:
      ids_ambiguos.append(valor_id)
   detalle = f" ({', '.join(ids_ambiguos)})" if ids_ambiguos else ""
   raise ValueError(
    "No se actualizó este registro porque su CURP aparece en más de un "
    "expediente de la base central" + detalle + ". Dirección debe revisar cuál es el registro correcto."
   )
  fila = existing.get(curp)
-
  if fila:
   if reject_existing:
    raise ValueError(
     "No se creó el alumno: esa CURP ya existe en la base central. "
     "Verifica la CURP o consulta el expediente existente."
    )
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
-
 if updates:
  retry_google(lambda: ws.batch_update(updates, value_input_option='USER_ENTERED'))
 if append_rows:
  google_append_rows_raw('Alumnos', append_rows)
 if actualizados or append_rows:
  clear_cache('Alumnos')
-
 result = (nuevos, actualizados)
 return (*result, ids) if return_ids else result
-
-
-
-
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
-
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
-
 clave = str(data.get('Clave_Operacion', '')).strip()
 for fila in actuales:
  fila = fila + [''] * max(0, len(headers) - len(fila))
  if clave and str(fila[indice_clave]).strip() == clave:
   return {
    'ID_Oficio': fila[indice_id],
    'Folio': fila[indice_folio],
    **data,
   }
-
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
-
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
-
def save_anexo3(data):
 data=dict(data); data.setdefault('ID_Anexo3',next_numeric_id('Anexo3_Deteccion','ID_Anexo3','AN3')); append_dict('Anexo3_Deteccion',data); return data['ID_Anexo3']
def save_anexo4(data):
 ensure_headers('Anexo4_Sugerencias', BASE_HEADERS['Anexo4_Sugerencias'])
 data=dict(data); data.setdefault('ID_Anexo4',next_numeric_id('Anexo4_Sugerencias','ID_Anexo4','AN4')); data.setdefault('Estado','ACTIVO'); append_dict('Anexo4_Sugerencias',data); return data['ID_Anexo4']
-
def update_anexo4(id_anexo4, cambios):
 """Actualiza un Anexo IV existente sin borrar columnas ni crear duplicados."""
 ensure_headers('Anexo4_Sugerencias', BASE_HEADERS['Anexo4_Sugerencias'])
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
-
def delete_anexo4(id_anexo4):
 """Retira una sugerencia de la vista activa sin borrar su historial."""
 return update_anexo4(id_anexo4, {'Estado': 'ANULADO'})
def save_anexo5(data):
 ensure_headers('Anexo5_Eventos', BASE_HEADERS['Anexo5_Eventos'])
 data=dict(data); data.setdefault('ID_Evento',next_numeric_id('Anexo5_Eventos','ID_Evento','AN5')); append_dict('Anexo5_Eventos',data); return data['ID_Evento']
-
def update_anexo5(id_evento, cambios):
 """Corrige un evento o lo marca como duplicado sin borrar la fila."""
 ws=ensure_headers('Anexo5_Eventos', BASE_HEADERS['Anexo5_Eventos'])
 headers=retry_google(lambda: ws.row_values(1))
 if 'ID_Evento' not in headers:
  raise ValueError('La hoja Anexo5_Eventos no contiene ID_Evento.')
 id_col=headers.index('ID_Evento')+1
 ids=retry_google(lambda: ws.col_values(id_col))
 fila=next((i for i,v in enumerate(ids,start=1) if str(v).strip()==str(id_evento).strip()),None)
 if not fila:
  raise ValueError(f'No se encontró el evento {id_evento}.')
 actual=retry_google(lambda: ws.row_values(fila))
 actual += [''] * (len(headers)-len(actual))
 for campo,valor in dict(cambios).items():
  if campo in headers and campo!='ID_Evento':
   actual[headers.index(campo)]=valor
 def columna(numero):
  letras=''
  while numero:
   numero,resto=divmod(numero-1,26)
   letras=chr(65+resto)+letras
  return letras
 rango=f"A{fila}:{columna(len(headers))}{fila}"
 retry_google(lambda: ws.update(range_name=rango,values=[actual[:len(headers)]]))
 clear_cache('Anexo5_Eventos')
 return str(id_evento)
def save_anexo7(data):
 ensure_headers('Anexo7_Derivacion', BASE_HEADERS['Anexo7_Derivacion'])
 data=dict(data); data.setdefault('ID_Anexo7',next_numeric_id('Anexo7_Derivacion','ID_Anexo7','AN7')); append_dict('Anexo7_Derivacion',data); return data['ID_Anexo7']
def save_visita(data):
 data=dict(data); data.setdefault('ID_Visita',next_numeric_id('Registro_Visitas','ID_Visita','VIS')); append_dict('Registro_Visitas',data); return data['ID_Visita']
-
def ensure_integrated_sheets():
 for name,headers in {**INTEGRATED_HEADERS,'Registro_Visitas':BASE_HEADERS['Registro_Visitas']}.items(): ensure_sheet(name,headers)
-
def ensure_expediente(id_expediente,id_alumno,estatus='ACTIVO'):
 ensure_integrated_sheets(); df=read('Expedientes')
 if not df.empty and 'ID_Expediente' in df.columns and str(id_expediente) in set(df['ID_Expediente'].astype(str)): return False
 hoy=str(date.today()); append_dict('Expedientes',{'ID_Expediente':id_expediente,'ID_Alumno':id_alumno,'Estatus':estatus,'Fecha_Apertura':hoy,'Ultima_Actualizacion':hoy}); return True
-
def existing_relations():
 df=read('Relaciones_Expediente')
 if df.empty: return set()
 return set(zip(df['ID_Expediente'].astype(str),df['Tipo_Registro'].astype(str),df['ID_Registro'].astype(str)))
-
def link_record(id_expediente,id_alumno,tipo,id_registro,fecha,estado='ACTIVO'):
 ensure_integrated_sheets(); key=(str(id_expediente),str(tipo),str(id_registro))
 if key in existing_relations(): return None
 rid=next_numeric_id('Relaciones_Expediente','ID_Relacion','REL'); append_dict('Relaciones_Expediente',{'ID_Relacion':rid,'ID_Expediente':id_expediente,'ID_Alumno':id_alumno,'Tipo_Registro':tipo,'ID_Registro':id_registro,'Fecha':fecha,'Estado':estado}); return rid
-
def timeline(id_expediente,id_alumno,fecha,tipo,titulo,descripcion,usuario):
 ensure_integrated_sheets(); df=read('Linea_Tiempo')
 if not df.empty:
  mask=(df['ID_Expediente'].astype(str)==str(id_expediente))&(df['Tipo'].astype(str)==str(tipo))&(df['Titulo'].astype(str)==str(titulo))&(df['Fecha'].astype(str)==str(fecha))
  if mask.any(): return None
 tid=next_numeric_id('Linea_Tiempo','ID_Evento_Timeline','TL'); append_dict('Linea_Tiempo',{'ID_Evento_Timeline':tid,'ID_Expediente':id_expediente,'ID_Alumno':id_alumno,'Fecha':fecha,'Tipo':tipo,'Titulo':titulo,'Descripcion':descripcion,'Usuario':usuario}); return tid
-

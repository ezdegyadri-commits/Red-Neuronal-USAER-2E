import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import json
import google.generativeai as genai
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- RECONSTRUCCIÓN DE BÓVEDA EN LA NUBE ---
import os
import json
import streamlit as st

def reconstruir_json(nombre_secreto, nombre_archivo):
    if nombre_secreto in st.secrets:
        datos = st.secrets[nombre_secreto]
        
        # Convertimos a diccionario
        if isinstance(datos, str):
            datos = json.loads(datos)
        else:
            datos = dict(datos)
            
        # Forzamos la sobrescritura del archivo SIEMPRE para limpiar errores pasados
        with open(nombre_archivo, 'w') as f:
            json.dump(datos, f)

try:
    reconstruir_json("token_json", "token.json")
    reconstruir_json("credenciales_json", "credenciales.json")
except Exception as e:
    st.error(f"Error descifrando la bóveda: {e}")

# --- 1. CONFIGURACIÓN DE CONEXIONES (REEMPLAZA TUS DATOS AQUÍ) ---
URL_SPREADSHEET = "https://docs.google.com/spreadsheets/d/15hEvBOkaUvUFvTPx38yn8D_O6zWpkDm6ReiQbNK3ewc"
API_KEY_GEMINI = "AQ.Ab8RN6Lg2KCR-L0SUqRqsk7IGKPHneuENhZH_d4J1SUeHrz79g"
FOLDER_ID_MAESTRO = "1btFuNK8l9BI5C2s3-Q0_RZBZkUOBhvtr"

gc = gspread.service_account(filename="credenciales.json")
sheet = gc.open_by_url(URL_SPREADSHEET)
genai.configure(api_key=API_KEY_GEMINI)
modelo_ia = genai.GenerativeModel('gemini-3.6-flash')

escuelas_usaer = {
    "Damián Carmona (31DPR0414P)": "ESC-001",
    "Ichcaanziho (31DPR0232G)": "ESC-002",
    "Gregorio Torres Quintero (31DPR0466V)": "ESC-003",
    "Remigio Aguilar Sosa (31DPR0711P)": "ESC-004",
    "Elvira Parra Ávila (31EPR0039A)": "ESC-005",
    "Manuel Sarrado (31EPR0040Q)": "ESC-006",
    "Domingo Solís Rodríguez (31EPR0075F)": "ESC-007",
    "Quintana Roo (31EPR0092W)": "ESC-008"
}

items_anexo3 = [
    "1. El salón de clases cuenta con áreas de trabajo delimitadas (higiene, rincón de lectura, área de material didáctico).",
    "2. El docente se asegura de que el material didáctico con que cuenta en el aula sea pertinente a las características de todos sus alumnos.",
    "3. El docente emplea los materiales de que dispone en el aula para asegurar el aprendizaje significativo de todos los alumnos.",
    "4. El docente se asegura de que, en el salón de clases, el material didáctico sea accesible para todos.",
    "5. El docente contempla en la planeación las ayudas necesarias en las actividades de acuerdo con los ritmos y estilos de aprendizaje.",
    "6. El docente dedica el tiempo suficiente para motivar a todos los alumnos en su aprendizaje.",
    "7. El docente indaga y toma en cuenta el conocimiento previo que los alumnos tienen sobre el tema.",
    "8. El docente propicia el trabajo colaborativo.",
    "9. El docente realiza una evaluación continua y formativa.",
    "10. El docente realiza las evaluaciones tomando en cuenta las características de los alumnos.",
    "11. El docente diversifica la metodología para favorecer el logro de los aprendizajes esperados.",
    "12. El docente diseña actividades que permitan la accesibilidad de los aprendizajes esperados.",
    "13. El docente propicia el respeto y la empatía en las relaciones entre él y sus alumnos.",
    "14. El docente realiza actividades para fomentar la convivencia sana y pacífica.",
    "15. El docente trabaja de manera colaborativa con el personal de la escuela regular y de educación especial."
]

# --- 2. SISTEMA DE LOGIN Y SEGURIDAD ---
if 'usuario_activo' not in st.session_state:
    st.session_state.usuario_activo = False
    st.session_state.rol = ""
    st.session_state.nombre = ""
    st.session_state.escuelas = []

if not st.session_state.usuario_activo:
    st.title("Red Neuronal USAER 2E 🏫")
    st.subheader("Acceso al Sistema")
    with st.form("login_form"):
        # --- EFECTO VISUAL DE ENCENDIDO (INICIO DE SESIÓN) ---
        st.markdown("""
        <style>
        /* Oscurecemos el fondo sutilmente para que resalte el formulario */
        .stApp {
            background-color: #121417; 
            color: white;
        }
        
        /* Animación de la "lámpara" encendiéndose sobre el formulario */
        @keyframes encendidoLampara {
            0% { opacity: 0; transform: translateY(-20px); box-shadow: 0 0 0px rgba(255, 223, 100, 0); }
            100% { opacity: 1; transform: translateY(0); box-shadow: 0 10px 40px rgba(255, 223, 100, 0.15); }
        }
        
        /* Aplicamos la animación al contenedor del formulario */
        [data-testid="stForm"] {
            animation: encendidoLampara 1.2s ease-out forwards;
            background-color: #1c1f24;
            border-radius: 16px;
            border: 1px solid #333;
            padding: 2.5rem;
            max-width: 450px;
            margin: 0 auto;
        }

        /* Animación suave para la guía visual de las maestras */
        @keyframes latido {
            0% { opacity: 0.6; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.02); color: #ffdf64; }
            100% { opacity: 0.6; transform: scale(1); }
        }
        .guia-visual {
            animation: latido 2.5s infinite;
            text-align: center;
            font-size: 1.1rem;
            margin-bottom: 20px;
            font-weight: 500;
        }
        </style>
        
        <div class="guia-visual">
            👋 ¡Bienvenida! <br>
            👇 Por favor, ingresa tu usuario y contraseña aquí abajo para comenzar.
        </div>
    """, unsafe_allow_html=True)
        user = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            try:
                df_usuarios = pd.DataFrame(sheet.worksheet("Usuarios").get_all_records())
                usuario_valido = df_usuarios[(df_usuarios['Usuario'] == user) & (df_usuarios['Password'] == str(pwd))]
                
                if not usuario_valido.empty:
                    st.session_state.usuario_activo = True
                    st.session_state.rol = usuario_valido['Rol'].values[0]
                    st.session_state.nombre = usuario_valido['Nombre'].values[0]
                    st.session_state.escuelas = str(usuario_valido['Escuelas_Permitidas'].values[0]).split(",")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")
            except Exception as e:
                st.error("Error al conectar con la base de datos de usuarios. Verifica la pestaña 'Usuarios'.")
    st.stop()

st.sidebar.success(f"Sesión iniciada: {st.session_state.nombre} ({st.session_state.rol})")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.usuario_activo = False
    st.rerun()

st.title("Red Neuronal USAER 2E 🏫")

# --- 3. EXTRAER LISTA DE ALUMNOS (FILTRADA POR ROL) ---
try:
    df_alumnos = pd.DataFrame(sheet.worksheet("Alumnos").get_all_records())
    if not df_alumnos.empty and 'ID_Alumno' in df_alumnos.columns:
        # Filtramos los alumnos para que el especialista solo vea los de sus escuelas asignadas
        if st.session_state.rol != "Director" and "TODAS" not in st.session_state.escuelas:
            df_alumnos = df_alumnos[df_alumnos['ID_Escuela'].isin(st.session_state.escuelas)]
        lista_alumnos = df_alumnos[df_alumnos['ID_Alumno'] != '']['Nombre_Completo'].tolist()
    else:
        lista_alumnos = []
except Exception:
    lista_alumnos = []
    df_alumnos = pd.DataFrame()


# --- 4. CONTROL DE PESTAÑAS POR ROL ---
tabs = ["🔍 BAPs Colaborativas (Anexos 3 y 4)", "📋 Eventos (Anexo 5)", "🗂️ Visor y Exportación"]
if st.session_state.rol == "Apoyo" or st.session_state.rol == "Director":
    tabs.insert(0, "📝 Alta de Alumnos")
if st.session_state.rol == "Director":
    tabs.append("📊 Panel de Dirección")

paneles = st.tabs(tabs)

# --- MAPEO DE PESTAÑAS SEGÚN EL ROL ---
idx_alta = tabs.index("📝 Alta de Alumnos") if "📝 Alta de Alumnos" in tabs else -1
idx_bap = tabs.index("🔍 BAPs Colaborativas (Anexos 3 y 4)")
idx_evt = tabs.index("📋 Eventos (Anexo 5)")
idx_visor = tabs.index("🗂️ Visor y Exportación")
idx_dir = tabs.index("📊 Panel de Dirección") if "📊 Panel de Dirección" in tabs else -1


# --- MÓDULO: ALTA DE ALUMNOS (Solo Apoyo y Director) ---
if idx_alta != -1:
    with paneles[idx_alta]:
        st.markdown("Utiliza este panel para registrar nuevos alumnos en la red neuronal.")
        with st.form("registro_alumno", clear_on_submit=True):
            nombre = st.text_input("Nombre Completo del Alumno")
            curp = st.text_input("CURP", max_chars=18)
            col1, col2 = st.columns(2)
            with col1:
                grado = st.selectbox("Grado", ["1ro", "2do", "3ro", "4to", "5to", "6to"])
            with col2:
                grupo = st.selectbox("Grupo", ["A", "B", "C", "D"])
                
            nombre_escuela = st.selectbox("Escuela Asignada", list(escuelas_usaer.keys()))
            maestro_regular = st.text_input("Nombre del Maestro Regular")
            condicion = st.selectbox("Condición / Discapacidad", ["Intelectual", "Auditiva", "Visual", "Motora", "TEA", "TDAH", "Aptitudes Sobresalientes", "Dificultades severas de aprendizaje", "Dificultades severas de conducta", "Dificultades severas de comunicación", "Ninguna"])
            estatus = st.selectbox("Estatus", ["Activo", "Baja", "Egresado"])
            submit_button_alta = st.form_submit_button("Guardar Registro")

        if submit_button_alta:
            if nombre == "" or curp == "":
                st.error("Por favor, llena al menos el Nombre y la CURP.")
            else:
                try:
                    id_escuela_seleccionada = escuelas_usaer[nombre_escuela]
                    nuevo_registro = ["", nombre, curp, grado, grupo, id_escuela_seleccionada, maestro_regular, condicion, estatus]
                    sheet.worksheet("Alumnos").append_row(nuevo_registro)
                    st.success(f"¡El alumno {nombre} ha sido registrado exitosamente!")
                except Exception as e:
                    st.error(f"Error en la operación: {e}")


# --- MÓDULO: BAPs COLABORATIVAS ---
with paneles[idx_bap]:
    st.subheader("Evaluación de Barreras en el Contexto Áulico")
    with st.form("anexo3_form", clear_on_submit=False):
        alumno_seleccionado = st.selectbox("Selecciona al Alumno a evaluar", lista_alumnos if lista_alumnos else ["Sin registros"])
        
        st.markdown("---")
        st.markdown("### Instrumento de Observación")
        
        respuestas_bap = {}
        for i, item in enumerate(items_anexo3):
            st.markdown(f"**{item}**")
            col_freq, col_ori = st.columns([3, 1])
            with col_freq:
                freq = st.radio("Frecuencia", ["Siempre", "Muchas veces", "Pocas veces", "Nunca"], horizontal=True, key=f"freq_{i}", label_visibility="collapsed")
            with col_ori:
                st.markdown("<br>", unsafe_allow_html=True)
                ori = st.checkbox("Requiere Orientación", key=f"ori_{i}")
            
            respuestas_bap[f"Item_{i+1}"] = {"pregunta": item, "frecuencia": freq, "orientacion": ori}
            st.markdown("---")
            
        contexto_extra = st.text_area("Añade observaciones cualitativas, detalles sobre el estilo de aprendizaje del alumno o estrategias previas intentadas.", height=100)
        submit_button_anexo3 = st.form_submit_button("Guardar Evaluación y Generar Sugerencias")
        
    if submit_button_anexo3:
        if alumno_seleccionado == "Sin registros" or df_alumnos.empty:
            st.error("No hay alumnos disponibles para evaluar.")
        else:
            with st.spinner("Conectando a la red neuronal y procesando datos... 🧠"):
                try:
                    fila_alumno = df_alumnos.loc[df_alumnos['Nombre_Completo'] == alumno_seleccionado]
                    id_alumno = str(fila_alumno['ID_Alumno'].values[0])
                    condicion_alumno = str(fila_alumno['Condicion_Discapacidad'].values[0])
                    fecha = datetime.now().strftime("%Y-%m-%d")
                    
                    baps_detectadas = [data for key, data in respuestas_bap.items() if data['frecuencia'] in ["Nunca", "Pocas veces"] or data['orientacion']]
                    
                    paquete_respuestas = json.dumps(respuestas_bap, ensure_ascii=False)
                    nuevo_anexo3 = ["", fecha, id_alumno, st.session_state.nombre, paquete_respuestas, contexto_extra, "", "", "Procesado"]
                    sheet.worksheet("Anexo3_Deteccion").append_row(nuevo_anexo3)
                    
                    prompt = f"""
                    Eres un experto en Educación Especial y educación inclusiva de la USAER.
                    Tu objetivo es generar sugerencias pedagógicas para el "Anexo 4".
                    
                    DATOS DEL ALUMNO:
                    - Condición: {condicion_alumno}
                    - Contexto de la maestra: {contexto_extra}
                    
                    BARRERAS DETECTADAS:
                    {json.dumps(baps_detectadas, ensure_ascii=False, indent=2)}
                    
                    INSTRUCCIÓN:
                    Redacta sugerencias específicas, aplicables y concretas en 3 bloques cortos utilizando viñetas:
                    1. Sugerencias Organizativas
                    2. Sugerencias Metodológicas
                    3. Sugerencias de Evaluación
                    No incluyas saludos ni introducciones largas.
                    """
                    
                    respuesta_ia = modelo_ia.generate_content(prompt)
                    sugerencias_finales = respuesta_ia.text
                    
                    grado_grupo = f"{fila_alumno['Grado'].values[0]} {fila_alumno['Grupo'].values[0]}"
                    motivo = "Resultados del Anexo 3: Barreras identificadas en el contexto áulico"
                    escuela_nombre = [k for k, v in escuelas_usaer.items() if v == fila_alumno['ID_Escuela'].values[0]][0]

                    nuevo_anexo4 = [
                        "", 
                        alumno_seleccionado, 
                        grado_grupo, 
                        escuela_nombre, 
                        "USAER 2E", 
                        st.session_state.rol, 
                        fecha, 
                        motivo, 
                        "", 
                        sugerencias_finales, 
                        "Pendiente de revisión", 
                        st.session_state.nombre 
                    ]
                    sheet.worksheet("Anexo4_Sugerencias").append_row(nuevo_anexo4)
                    
                    st.success("¡Operación Completada! Anexo 3 y Anexo 4 han sido procesados y guardados.")
                    st.info(sugerencias_finales)
                    
                except Exception as e:
                    st.error(f"Error en el procesamiento: {e}")


# --- MÓDULO: EVENTOS (ANEXO 5) ---
with paneles[idx_evt]:
    st.subheader("Portal de Eventos Significativos (Anexo V)")
    
    # Memoria de sesión para el autollenado
    if 'ia_evento_sugerido' not in st.session_state:
        st.session_state.ia_evento_sugerido = ""
        
    alum_evt = st.selectbox("1. Selecciona al alumno involucrado", lista_alumnos if lista_alumnos else ["Sin registros"])
    evento_borrador = st.text_area("2. Redacta el evento (borrador)", height=150)
    
    if st.button("✨ Mejorar Redacción con IA"):
        if evento_borrador != "":
            with st.spinner("Pulido ortográfico en proceso... 🧠"):
                meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                hoy = datetime.now()
                fecha_ext = f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"
                
                prompt_estilo = f"""
                Reescribe este evento significativo para un expediente oficial (Anexo V). 
                Debe ser un solo párrafo profesional, objetivo y respetuoso. 
                Al final añade textualmente: 'Fecha de registro: {fecha_ext}.'
                REGLA ESTRICTA INQUEBRANTABLE: Devuelve ÚNICAMENTE el texto corregido. NO incluyas saludos, ni introducciones, ni frases como 'Aquí tienes' o 'Esta es la versión'.
                Borrador original: {evento_borrador}
                """
                respuesta_ia = modelo_ia.generate_content(prompt_estilo)
                
                st.session_state.ia_evento_sugerido = respuesta_ia.text
                st.rerun() 

    st.markdown("---")
    with st.form("anexo5_guardar", clear_on_submit=True):
        evento_definitivo = st.text_area("3. Evento Definitivo a Guardar", value=st.session_state.ia_evento_sugerido, height=150)
        
        with st.expander("👁️ Vista Previa del Formato SEGEY (Historial Completo)"):
            try:
                df_historico_a5 = pd.DataFrame(sheet.worksheet("Anexo5_Eventos").get_all_records())
                registros_previos = df_historico_a5[df_historico_a5['Nombre_Alumno'] == alum_evt].sort_values(by='Fecha') if not df_historico_a5.empty else pd.DataFrame()
            except:
                registros_previos = pd.DataFrame()
            
            grado_grupo_visor = ""
            if alum_evt != "Sin registros" and not df_alumnos.empty:
                fila_alum_evt = df_alumnos.loc[df_alumnos['Nombre_Completo'] == alum_evt]
                if not fila_alum_evt.empty:
                    grado_grupo_visor = f"{fila_alum_evt['Grado'].values[0]} {fila_alum_evt['Grupo'].values[0]}"

# ATENCIÓN: Este bloque HTML debe ir pegado a la izquierda para evitar que Streamlit lo vuelva código crudo.
            html_preview = f"""
<div style="background-color: white; color: black; padding: 20px; border-radius: 8px; border: 1px solid #ccc; font-family: Arial, sans-serif;">
<h3 style="text-align: center; margin-top: 0;">Anexo V. Hoja de Eventos Significativos.</h3>
<p style="font-size: 14px;"><b>Nombre del alumno:</b> {alum_evt}<br>
<b>Grado y grupo:</b> {grado_grupo_visor}</p>
<table style="width: 100%; border-collapse: collapse; border: 1px solid black; font-size: 14px;">
<tr style="background-color: #f2f2f2;">
<th style="border: 1px solid black; padding: 10px; width: 15%;">Fecha</th>
<th style="border: 1px solid black; padding: 10px; width: 60%;">Evento</th>
<th style="border: 1px solid black; padding: 10px; width: 25%;">Especialista, firma, fecha.</th>
</tr>
"""
            
            if not registros_previos.empty:
                for idx, row in registros_previos.iterrows():
                    html_preview += f"""
<tr>
<td style="border: 1px solid black; padding: 10px; vertical-align: top;">{row.get('Fecha','')}</td>
<td style="border: 1px solid black; padding: 10px; vertical-align: top;">{str(row.get('Evento','')).replace(chr(10), '<br>')}</td>
<td style="border: 1px solid black; padding: 10px; text-align: center; vertical-align: bottom;"><br><br>____________________<br><i>{row.get('Especialista','')}</i></td>
</tr>
"""
            
            if evento_definitivo:
                html_preview += f"""
<tr style="background-color: #e6f7ff;">
<td style="border: 1px solid black; padding: 10px; vertical-align: top;"><b>Hoy</b></td>
<td style="border: 1px solid black; padding: 10px; vertical-align: top;"><b>{str(evento_definitivo).replace(chr(10), '<br>')}</b></td>
<td style="border: 1px solid black; padding: 10px; text-align: center; vertical-align: bottom;"><br><br>____________________<br><b><i>{st.session_state.nombre}</i> (Nuevo)</b></td>
</tr>
"""
                
            html_preview += """
</table>
</div>
"""
            
            st.markdown(html_preview, unsafe_allow_html=True)
            
        submit_button_anexo5 = st.form_submit_button("💾 Guardar Evento Oficial")
        
    if submit_button_anexo5:
        if alum_evt != "Sin registros" and evento_definitivo != "":
            try:
                fecha_evt = datetime.now().strftime("%Y-%m-%d")
                sheet.worksheet("Anexo5_Eventos").append_row(["", fecha_evt, alum_evt, grado_grupo_visor, st.session_state.nombre, evento_definitivo])
                st.session_state.ia_evento_sugerido = "" 
                
                # --- ANIMACIONES DE ÉXITO ---
                st.balloons() # Lluvia de globos en pantalla
                st.toast('¡Evento guardado exitosamente en la base de datos!', icon='✅') # Notificación emergente
                st.success("Evento guardado. El historial ha sido actualizado.")
                
            except Exception as e:
                # --- ANIMACIÓN DE ERROR ---
                st.toast('Ocurrió un problema de conexión', icon='❌')
                st.error(f"Error al guardar el evento: {e}")
        else:
            st.toast('Faltan datos por llenar', icon='⚠️')
            st.warning("Por favor, selecciona un alumno y llena el evento definitivo.")

# --- MÓDULO: VISOR Y EXPORTACIÓN ---
with paneles[idx_visor]:
    st.subheader("Visor de Documentos Oficiales y Exportación")
    alum_visor = st.selectbox("Selecciona al alumno para consultar su expediente", lista_alumnos if lista_alumnos else ["Sin registros"], key="visor_alum")
    
    if st.button("Buscar y Preparar Expediente"):
        if alum_visor == "Sin registros":
            st.error("No hay alumnos registrados.")
        else:
            with st.spinner("Extrayendo documentos y ensamblando formatos oficiales... 🗂️"):
                try:
                    df_anexo4 = pd.DataFrame(sheet.worksheet("Anexo4_Sugerencias").get_all_records())
                    df_anexo5 = pd.DataFrame(sheet.worksheet("Anexo5_Eventos").get_all_records())
                    
                    escuela_alumno = "USAER_General"
                    st.markdown(f"## Expediente Digital: {alum_visor}")
                    
                    # --- INICIO DE CONSTRUCCIÓN DEL DOCUMENTO OFICIAL (HTML) ---
                    html_content = "<html><head><meta charset='UTF-8'></head><body style='font-family: Arial, sans-serif;'>"
                    html_content += f"<h1 style='text-align: center;'>Expediente Digital Oficial: {alum_visor}</h1>"
                    
                    # --- PROCESAR ANEXO 4 EN ORDEN CRONOLÓGICO ---
                    st.markdown("### 📄 Anexo IV. Hoja de Sugerencias")
                    html_content += "<h2 style='text-align: center;'>Anexo IV. Hoja de Sugerencias.</h2>"
                    
                    if not df_anexo4.empty and 'Nombre_Alumno' in df_anexo4.columns:
                        # Ordenar por fecha de más antiguo a más reciente
                        registros_a4 = df_anexo4[df_anexo4['Nombre_Alumno'] == alum_visor].sort_values(by='Fecha_Elaboracion')
                        
                        if not registros_a4.empty:
                            for idx, row in registros_a4.iterrows():
                                escuela_alumno = row.get('Escuela', 'USAER_General')
                                grado_grupo = row.get('Grado_Grupo', '')
                                fecha_doc = row.get('Fecha_Elaboracion', '')
                                especialista_doc = row.get('Quien_Brinda_Sugerencias', '')
                                motivo_doc = row.get('Motivo', '')
                                area_doc = row.get('Sugerencias_Area', 'Aprendizaje')
                                nivel_cump = row.get('Nivel_Cumplimiento_Resultados', '')
                                sugerencias_doc = str(row.get('Sugerencias', '')).replace(chr(10), '<br>')
                                
                                # Mostrar en pantalla
                                with st.expander(f"Sugerencias del {fecha_doc} - Especialista: {especialista_doc}"):
                                    st.write(f"**Motivo:** {motivo_doc}")
                                    st.info(row.get('Sugerencias', ''))
                                    
                                # Ensamblar en el formato exacto de la SEGEY
                                html_content += f"""
                                <div style='margin-bottom: 40px;'>
                                    <p><b>Nombre del alumno:</b> {alum_visor}<br>
                                    <b>Grado y grupo:</b> {grado_grupo}<br>
                                    <b>Escuela:</b> {escuela_alumno}<br>
                                    <b>Servicio de EE:</b> USAER 2E</p>
                                    
                                    <p><b>Sugerencias del área:</b> {area_doc} [ X ]<br>
                                    <b>Fecha de elaboración:</b> {fecha_doc}<br>
                                    <b>Motivo por el que se brindan las sugerencias:</b> {motivo_doc}<br>
                                    <b>Fecha de seguimiento:</b> ___________________</p>
                                    
                                    <table border='1' cellpadding='8' cellspacing='0' style='width: 100%; border-collapse: collapse;'>
                                        <tr style='background-color: #f2f2f2;'>
                                            <th>Sugerencias</th>
                                            <th>Indique el nivel de cumplimiento y describa los resultados</th>
                                            <th>Nombre y firma de quien recibe</th>
                                            <th>Nombre y firma de quien brinda</th>
                                        </tr>
                                        <tr>
                                            <td style='width: 40%; vertical-align: top;'>{sugerencias_doc}</td>
                                            <td style='width: 20%; vertical-align: top;'>{nivel_cump}</td>
                                            <td style='width: 20%; vertical-align: bottom; text-align: center;'><br><br>_____________________<br>Maestro(a) de Grupo</td>
                                            <td style='width: 20%; vertical-align: bottom; text-align: center;'><br><br>_____________________<br>{especialista_doc}</td>
                                        </tr>
                                    </table>
                                </div>
                                <hr>
                                """
                        else:
                            st.warning("No hay Anexos IV generados para este alumno.")
                    
                    # --- PROCESAR ANEXO 5 EN ORDEN CRONOLÓGICO ---
                    st.markdown("### 📄 Anexo V. Hoja de Eventos Significativos")
                    # Salto de página para el Anexo V
                    html_content += "<div style='page-break-before: always;'></div>"
                    html_content += "<h2 style='text-align: center;'>Anexo V. Hoja de Eventos Significativos.</h2>"
                    
                    if not df_anexo5.empty and 'Nombre_Alumno' in df_anexo5.columns:
                        # Ordenar cronológicamente
                        registros_a5 = df_anexo5[df_anexo5['Nombre_Alumno'] == alum_visor].sort_values(by='Fecha')
                        
                        if not registros_a5.empty:
                            grado_grupo_a5 = registros_a5.iloc[0].get('Grado_Grupo', '')
                            
                            # Encabezado del Anexo V
                            html_content += f"""
                            <p><b>Nombre del alumno:</b> {alum_visor}<br>
                            <b>Grado y grupo:</b> {grado_grupo_a5}</p>
                            <table border='1' cellpadding='8' cellspacing='0' style='width: 100%; border-collapse: collapse;'>
                                <tr style='background-color: #f2f2f2;'>
                                    <th>Fecha</th>
                                    <th>Evento</th>
                                    <th>Especialista, firma, fecha.</th>
                                </tr>
                            """
                            
                            for idx, row in registros_a5.iterrows():
                                fecha_evt = row.get('Fecha', '')
                                esp_evt = row.get('Especialista', '')
                                evt_desc = str(row.get('Evento', '')).replace(chr(10), '<br>')
                                
                                # Mostrar en pantalla
                                with st.expander(f"Evento del {fecha_evt} - Especialista: {esp_evt}"):
                                    st.write(row.get('Evento', ''))
                                
                                # Añadir fila a la tabla del Anexo V
                                html_content += f"""
                                <tr>
                                    <td style='width: 15%; vertical-align: top;'>{fecha_evt}</td>
                                    <td style='width: 60%; vertical-align: top;'>{evt_desc}</td>
                                    <td style='width: 25%; vertical-align: bottom; text-align: center;'><br><br>_____________________<br>{esp_evt}</td>
                                </tr>
                                """
                            html_content += "</table>"
                        else:
                            st.warning("No hay eventos registrados para este alumno en el Anexo V.")
                    
                    html_content += "</body></html>"
                    
                    # --- GUARDAR EN SESSION STATE PARA EL BOTÓN DE EXPORTACIÓN ---
                    st.session_state['html_export'] = html_content
                    st.session_state['escuela_export'] = escuela_alumno
                    st.session_state['alumno_export'] = alum_visor

                except Exception as e:
                    st.error(f"Error crítico al ensamblar: {e}")

    # --- BOTÓN DE EXPORTACIÓN A GOOGLE DOCS ---
    st.markdown("---")
    st.markdown("### 📤 Opciones de Exportación")
    
    if st.button("Exportar Archivos a Google Docs", key="btn_export"):
        if 'html_export' not in st.session_state:
            st.warning("Primero debes buscar y preparar el expediente.")
        else:
            with st.spinner("Creando documentos independientes en Google Docs..."):
                try:
                    SCOPES = ['https://www.googleapis.com/auth/drive']
                    creds = None
                    if os.path.exists('token.json'):
                        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                    if not creds or not creds.valid:
                        if creds and creds.expired and creds.refresh_token:
                            creds.refresh(Request())
                            with open('token.json', 'w') as token:
                                token.write(creds.to_json())
                                
                    drive_service = build('drive', 'v3', credentials=creds)
                    
                    escuela_alumno = st.session_state['escuela_export']
                    alum_visor = st.session_state['alumno_export']
                    fecha_hoy = datetime.now().strftime('%Y%m%d')
                    
                    query = f"name='{escuela_alumno}' and '{FOLDER_ID_MAESTRO}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                    resultados = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
                    carpetas = resultados.get('files', [])
                    
                    if not carpetas:
                        carpeta_escuela = drive_service.files().create(body={'name': escuela_alumno, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [FOLDER_ID_MAESTRO]}, fields='id').execute()
                        folder_escuela_id = carpeta_escuela.get('id')
                    else:
                        folder_escuela_id = carpetas[0].get('id')
                    
                    # Para lograr archivos separados, dividimos el HTML generado previamente
                    html_completo = st.session_state['html_export']
                    partes = html_completo.split("<div style='page-break-before: always;'></div>")
                    html_a4 = partes[0] + "</body></html>"
                    html_a5 = "<html><head><meta charset='UTF-8'></head><body style='font-family: Arial, sans-serif;'>" + partes[1] if len(partes) > 1 else ""
                    
                    # Exportar Anexo IV
                    doc_id_4 = drive_service.files().create(
                        body={'name': f"Anexo_IV_{alum_visor}_{fecha_hoy}", 'mimeType': 'application/vnd.google-apps.document', 'parents': [folder_escuela_id]}, 
                        media_body=MediaIoBaseUpload(io.BytesIO(html_a4.encode('utf-8')), mimetype='text/html', resumable=True), 
                        fields='id'
                    ).execute().get('id')
                    
                    st.success(f"✅ Anexo IV guardado: [Abrir en Google Docs](https://docs.google.com/document/d/{doc_id_4}/edit)")
                    
                    # Exportar Anexo V (si existe)
                    if html_a5:
                        doc_id_5 = drive_service.files().create(
                            body={'name': f"Anexo_V_{alum_visor}_{fecha_hoy}", 'mimeType': 'application/vnd.google-apps.document', 'parents': [folder_escuela_id]}, 
                            media_body=MediaIoBaseUpload(io.BytesIO(html_a5.encode('utf-8')), mimetype='text/html', resumable=True), 
                            fields='id'
                        ).execute().get('id')
                        st.success(f"✅ Anexo V guardado: [Abrir en Google Docs](https://docs.google.com/document/d/{doc_id_5}/edit)")
                    
                except Exception as e:
                    st.error(f"Error al subir a Drive: {e}")


# --- MÓDULO: PANEL DE DIRECCIÓN (Solo Director) ---
if idx_dir != -1:
    with paneles[idx_dir]:
        st.subheader("Centro de Monitoreo")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Alumnos en Red", len(df_alumnos) if not df_alumnos.empty else 0)
        
        try:
            df_anexo4_dir = pd.DataFrame(sheet.worksheet("Anexo4_Sugerencias").get_all_records())
            df_anexo5_dir = pd.DataFrame(sheet.worksheet("Anexo5_Eventos").get_all_records())
            
            col2.metric("Sugerencias Generadas (Anexo 4)", len(df_anexo4_dir) if not df_anexo4_dir.empty else 0)
            col3.metric("Eventos Registrados (Anexo 5)", len(df_anexo5_dir) if not df_anexo5_dir.empty else 0)
            
            st.markdown("### Auditoría de Registros (Anexo 4)")
            if not df_anexo4_dir.empty:
                st.dataframe(df_anexo4_dir[['Nombre_Alumno', 'Escuela', 'Fecha_Elaboracion', 'Quien_Brinda_Sugerencias']])
            else:
                st.info("No hay registros en el Anexo 4.")
                
            st.markdown("### Auditoría de Eventos (Anexo 5)")
            if not df_anexo5_dir.empty:
                st.dataframe(df_anexo5_dir[['Nombre_Alumno', 'Fecha', 'Especialista', 'Evento']])
            else:
                st.info("No hay eventos en el Anexo 5.")
                
        except Exception as e:
            st.error(f"Error al cargar métricas del director: {e}")

import time
import streamlit as st
import pandas as pd
import gspread
import json
import google.generativeai as genai
import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# 1. CONFIGURACIÓN DE PÁGINA (Debe ser la línea 1 operativa)
st.set_page_config(page_title="USAER 2E", layout="wide")

# 2. VARIABLES MAESTRAS (Coloca aquí tus datos)
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "AQ.Ab8RN6Lg2KCR-L0SUqRqsk7IGKPHneuENhZH_d4J1SUeHrz79g")
FOLDER_ID_MAESTRO = "1btFuNK8l9BI5C2s3-Q0_RZBZkUOBhvtr"
URL_SPREADSHEET_MAESTRO = "https://docs.google.com/spreadsheets/d/15hEvBOkaUvUFvTPx38yn8D_O6zWpkDm6ReiQbNK3ewc"

genai.configure(api_key=GEMINI_API_KEY)
modelo_ia = genai.GenerativeModel("gemini-1.5-flash")

# 3. CONEXIÓN A GOOGLE (MÉTODO SIN ARCHIVOS - A PRUEBA DE ERRORES)
def obtener_diccionario_secreto(nombre_secreto):
    secreto = st.secrets[nombre_secreto]
    if isinstance(secreto, str):
        try:
            return json.loads(secreto)
        except json.JSONDecodeError:
            # Limpieza forzada en caso de que Streamlit agregue comillas extra
            return json.loads(secreto.replace('\\"', '"').strip())
    return dict(secreto)

try:
    # Leemos directamente de la bóveda a la memoria de la app
    credenciales_dict = obtener_diccionario_secreto("credenciales_json")
    token_dict = obtener_diccionario_secreto("token_json")
    
    # Conexión a Sheets DIRECTA (Adiós al error de filename="credenciales.json")
    gc = gspread.service_account_from_dict(credenciales_dict)
    sheet = gc.open_by_url(URL_SPREADSHEET_MAESTRO)
    
    # Conexión a Drive 5TB DIRECTA
    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    drive_service = build('drive', 'v3', credentials=creds)

except Exception as e:
    st.error(f"❌ Error crítico de conexión. Verifica que el texto en 'Secrets' esté completo: {e}")
    st.stop()


# 4 y 5. PANTALLA DE INICIO Y LOGIN (CON IDENTIDAD USAER 2E GIGANTE)
if not st.session_state.get("autenticado", False):
    st.markdown("""
        <style>
        /* Fondo nocturno y cálido para resaltar la luz */
        .stApp {
            background-color: #1a1e23;
            color: #ecf0f1;
        }
        
        /* Animaciones */
        @keyframes encenderLuz { 0% { opacity: 0; } 100% { opacity: 1; } }
        @keyframes flotar { 0% { transform: translateY(0px); } 50% { transform: translateY(-5px); } 100% { transform: translateY(0px); } }

        /* Estructura de la lámpara de techo CSS */
        .lampara-contenedor {
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            margin-top: -60px; 
            margin-bottom: 20px;
            z-index: 10;
        }
        .cable { width: 4px; height: 60px; background-color: #555; }
        .campana { width: 0; height: 0; border-left: 35px solid transparent; border-right: 35px solid transparent; border-bottom: 45px solid #d4af37; border-radius: 4px; }
        .foco { width: 24px; height: 12px; background-color: #fff; border-radius: 0 0 20px 20px; box-shadow: 0 5px 15px rgba(255, 235, 100, 0.8); }
        .haz-de-luz {
            position: absolute;
            top: 115px;
            width: 450px;
            height: 450px;
            background: linear-gradient(to bottom, rgba(255, 223, 100, 0.15) 0%, rgba(255, 223, 100, 0) 100%);
            clip-path: polygon(35% 0, 65% 0, 100% 100%, 0 100%);
            animation: encenderLuz 2s ease-in-out forwards;
            pointer-events: none; 
            z-index: 0;
        }

        /* Contenedor del mensaje de bienvenida con el GRAN TÍTULO */
        .mensaje-bienvenida {
            text-align: center;
            max-width: 650px;
            margin: 0 auto 30px auto;
            position: relative;
            z-index: 1;
            animation: flotar 4s ease-in-out infinite;
        }
        
        /* EL NUEVO TÍTULO GIGANTE DE USAER */
        .titulo-usaer {
            font-size: 4.5rem;
            font-weight: 900;
            color: #ffdf64; /* Dorado iluminado */
            text-shadow: 0 0 25px rgba(255, 223, 100, 0.5);
            margin-bottom: 5px;
            line-height: 1;
            letter-spacing: 2px;
        }

        .titulo-calido {
            font-size: 1.8rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 12px;
        }
        .texto-calido {
            font-size: 1.1rem;
            color: #d1d5db;
            line-height: 1.6;
        }

        /* Estilo del formulario de login */
        [data-testid="stForm"] {
            background-color: rgba(30, 35, 40, 0.8);
            border-radius: 16px;
            border: 1px solid #444;
            padding: 2.5rem;
            max-width: 400px;
            margin: 0 auto;
            position: relative;
            z-index: 2;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            animation: encenderLuz 1.5s ease-out forwards;
        }
        </style>

        <div class="lampara-contenedor">
            <div class="cable"></div>
            <div class="campana"></div>
            <div class="foco"></div>
            <div class="haz-de-luz"></div>
        </div>

        <div class="mensaje-bienvenida">
            <div class="titulo-usaer">USAER 02-E</div>
            <div class="titulo-calido">¡Hola! Qué alegría tenerte aquí.</div>
            <div class="texto-calido">
                Sabemos que tu labor transforma vidas en nuestras escuelas todos los días. 
                Hemos creado este rincón digital especialmente para ti, para hacer tu trabajo más ligero, 
                rápido y colaborativo.<br><br>
                <b>👇 Por favor, ingresa tus datos para encender tu espacio de trabajo:</b>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        usuario = st.text_input("Tu usuario:")
        password = st.text_input("Tu contraseña:", type="password")
        submit = st.form_submit_button("Entrar a mi espacio ✨")
        
        if submit:
            try:
                # 1. Leemos la pestaña Usuarios de tu Sheets maestro
                df_usuarios = pd.DataFrame(sheet.worksheet("Usuarios").get_all_records())
                
                # 2. Limpiamos espacios en blanco accidentales (AHORA APUNTA A 'Password')
                df_usuarios['Usuario'] = df_usuarios['Usuario'].astype(str).str.strip()
                df_usuarios['Password'] = df_usuarios['Password'].astype(str).str.strip()
                
                # 3. Buscamos coincidencia exacta usando tu columna 'Password'
                usuario_valido = df_usuarios[
                    (df_usuarios['Usuario'] == usuario.strip()) & 
                    (df_usuarios['Password'] == password.strip())
                ]
                
                if not usuario_valido.empty:
                    # Si los datos coinciden, guardamos su nombre y le damos acceso
                    st.session_state.autenticado = True
                    st.session_state.nombre = str(usuario_valido['Nombre'].values[0]) 
                    
                    # --- NUEVO: GUARDAMOS EL ROL Y LAS ESCUELAS DESDE EL LOGIN ---
                    col_rol = next((c for c in df_usuarios.columns if "ROL" in c.upper() or "PUESTO" in c.upper()), None)
                    if col_rol:
                        st.session_state.rol = str(usuario_valido[col_rol].values[0])
                        
                    col_escuelas = next((c for c in df_usuarios.columns if "ESCUELA" in c.upper() or "PERMITIDA" in c.upper() or "ASIGNADA" in c.upper()), None)
                    if col_escuelas:
                        st.session_state.escuelas_permitidas = str(usuario_valido[col_escuelas].values[0])
                    
                    st.rerun()
                else:
                    st.error("Mmm, parece que hay un error en tus datos. ¡Intenta de nuevo!")
                    
            except Exception as e:
                st.error(f"⚠️ Error conectando con la base de datos de usuarios. Detalle: {e}")
    
    st.stop()
# --- PANEL LATERAL Y CERRAR SESIÓN ---
with st.sidebar:
    st.markdown(f"### 👤 Sesión activa")
    st.write(f"**Usuario:** {st.session_state.get('nombre', 'Docente')}")
    st.markdown("---")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        # Limpiamos el estado de autenticación
        st.session_state.autenticado = False
        st.session_state.pop("nombre", None)
        st.session_state.pop("rol", None)
        st.session_state.pop("ia_evento_sugerido", None)
        st.session_state.pop("html_export", None)
        st.rerun()
# SI EL USUARIO ESTÁ AUTENTICADO, SE SALTA EL STOP Y VE TUS PESTAÑAS:


# --- AQUÍ ABAJO PEGAS TUS PESTAÑAS (pestañas = st.tabs(...)) Y TUS MÓDULOS DE ALUMNOS, BAP, EVENTOS ---
# ==========================================
# ==========================================
# ==========================================
# ==========================================
# ==========================================
# --- CARGA DE DATOS PARA LOS FORMULARIOS ---
# ==========================================

# 1. DICCIONARIOS GLOBALES (Soluciona el NameError de la línea 338)
escuelas_usaer = {
    "Damián Carmona": "ESC-001",
    "Ichcaanziho": "ESC-002",
    "Gregorio Torres Quintero": "ESC-003",
    "Remigio Aguilar Sosa": "ESC-004",
    "Elvira Parra Ávila": "ESC-005",
    "Manuel Sarrado": "ESC-006",
    "Domingo Solís Rodríguez": "ESC-007",
    "Quintana Roo": "ESC-008"
}

try:
    df_todos_alumnos = pd.DataFrame(sheet.worksheet("Alumnos").get_all_records())
    
    # 2. RECUPERAR DATOS EXACTOS DE LA SESIÓN
    escuelas_usuario = str(st.session_state.get("escuelas_permitidas", "")).strip()
    rol_activo = str(st.session_state.get("rol", "")).upper()
    
    # Si es Director, Trabajo Social, o dice TODAS, forzamos el acceso total
    if "DIRECTOR" in rol_activo or "TRABAJO" in rol_activo or "TODAS" in escuelas_usuario.upper():
        escuelas_usuario = "TODAS"
    
    # 3. DICCIONARIO MAESTRO DE LA ZONA 001
    mapeo_zona = {
        "ESC-001": ["ESC-001", "DAMIÁN CARMONA", "DAMIAN CARMONA"],
        "ESC-002": ["ESC-002", "ICHCAANZIHO"],
        "ESC-003": ["ESC-003", "GREGORIO TORRES QUINTERO", "GREGORIO TORRES"],
        "ESC-004": ["ESC-004", "REMIGIO AGUILAR SOSA", "REMIGIO AGUILAR"],
        "ESC-005": ["ESC-005", "ELVIRA PARRA"],
        "ESC-006": ["ESC-006", "MANUEL SARRADO"],
        "ESC-007": ["ESC-007", "DOMINGO SOLIS", "DOMINGO SOLÍS"],
        "ESC-008": ["ESC-008", "QUINTANA"]
    }
    
    # 4. APLICAR FILTRO DE SEGURIDAD ESTRICTO
    if escuelas_usuario == "TODAS":
        df_alumnos = df_todos_alumnos
    elif escuelas_usuario:
        lista_permitidas = [e.strip().upper() for e in escuelas_usuario.split(",")]
        terminos_autorizados = []
        for clave in lista_permitidas:
            if clave in mapeo_zona:
                terminos_autorizados.extend(mapeo_zona[clave])
            else:
                terminos_autorizados.append(clave)
        
        col_esc = next((c for c in df_todos_alumnos.columns if "ESCUELA" in c.upper() or "ASIGNADA" in c.upper()), None)
        
        if col_esc:
            mascara = df_todos_alumnos[col_esc].astype(str).str.upper().apply(
                lambda x: any(termino in x for termino in terminos_autorizados)
            )
            df_alumnos = df_todos_alumnos[mascara]
        else:
            df_alumnos = pd.DataFrame(columns=df_todos_alumnos.columns)
    else:
        df_alumnos = pd.DataFrame(columns=df_todos_alumnos.columns)
        st.error("⚠️ Acceso restringido: No se detectaron escuelas asignadas en tu sesión.")
        
    # 5. Generar la lista final para los menús
    col_nombre = 'Nombre_Completo' if 'Nombre_Completo' in df_alumnos.columns else 'Nombre'
    lista_alumnos = sorted([nom for nom in df_alumnos[col_nombre].astype(str).tolist() if nom.strip() != ""])

except Exception:
    df_alumnos = pd.DataFrame()
    lista_alumnos = []

items_anexo3 = [
    "1. El salón de clases cuenta con áreas de trabajo delimitadas (higiene, rincón de lectura, área de material didáctico).",
    "2. El docente se asegura de que el material didáctico con que cuenta en el aula sea pertinente a las características de todos sus alumnos.",
    "3. El docente emplea los materiales de que dispone en el aula para asegurar el aprendizaje significativo de todos los alumnos.",
    "4. El docente se asegura de que, en el salón de clases, el material didáctico (material concreto, libros, cuentos, fichas, etc.) sea accesible para todos.",
    "5. El docente contempla en la planeación las ayudas necesarias en las actividades de acuerdo con los ritmos y estilos de aprendizaje, para desarrollar el potencial de cada uno de los alumnos.",
    "6. El docente dedica el tiempo suficiente para motivar a todos los alumnos en su aprendizaje, antes, durante y después de las actividades.",
    "7. El docente indaga y toma en cuenta el conocimiento previo que los alumnos tienen sobre el tema que trata la actividad antes de abordarlo.",
    "8. El docente propicia el trabajo colaborativo.",
    "9. El docente realiza una evaluación continua y formativa, es decir, mediante las actividades diarias y tareas, que le permiten conocer los avances de sus alumnos.",
    "10. El docente realiza las evaluaciones tomando en cuenta las características de los alumnos.",
    "11. El docente diversifica la metodología para favorecer el logro de los aprendizajes esperados de los alumnos.",
    "12. El docente diseña actividades que permitan la accesibilidad de los aprendizajes esperados de los alumnos y mejoren el nivel de logro.",
    "13. El docente propicia el respeto y la empatia en las relaciones entre él y sus alumnos.",
    "14. El docente realiza actividades para fomentar la convivencia sana y pacífica entre los alumnos (respeto, compañerismo, ayuda mutua, práctica de valores, disciplina, otros).",
    "15. El docente trabaja de manera colaborativa con el personal de la escuela regular y de educación especial para favorecer el aprendizaje y la participación de los estudiantes con necesidades educativas específicas."
]
# ==========================================
# --- DEFINICIÓN DE PESTAÑAS (TODAS INCLUIDAS) ---
tabs = [
    "📝 Alta de Alumnos", 
    "🔍 BAPs Colaborativas (Anexos 3 y 4)", 
    "📋 Eventos (Anexo 5)",
    "🗂️ Visor y Exportación",
    "📊 Panel de Dirección",
    "🏫 Constancias de Visita"
]
paneles = st.tabs(tabs)

# Agrega también su índice debajo de los demás:
idx_visitas = tabs.index("🏫 Constancias de Visita") if "🏫 Constancias de Visita" in tabs else -1

# --- MAPEO DE PESTAÑAS (BLINDADO CONTRA ERRORES) ---
# Si por alguna razón cambias un nombre después, el código no colapsará, solo ocultará el panel.
idx_alta = tabs.index("📝 Alta de Alumnos") if "📝 Alta de Alumnos" in tabs else -1
idx_bap = tabs.index("🔍 BAPs Colaborativas (Anexos 3 y 4)") if "🔍 BAPs Colaborativas (Anexos 3 y 4)" in tabs else -1
idx_evt = tabs.index("📋 Eventos (Anexo 5)") if "📋 Eventos (Anexo 5)" in tabs else -1
idx_visor = tabs.index("🗂️ Visor y Exportación") if "🗂️ Visor y Exportación" in tabs else -1
idx_dir = tabs.index("📊 Panel de Dirección") if "📊 Panel de Dirección" in tabs else -1

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
        
        modo_ingreso = st.radio("Método de registro:", ["📝 Carga Manual (Uno por uno)", "📂 Carga Masiva (Subir Excel)"], horizontal=True)
        
        if modo_ingreso == "📝 Carga Manual (Uno por uno)":
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
                        
        else:
            st.info("Sube el padrón oficial de alumnos de la USAER. El sistema adaptará los campos automáticamente.")
            archivo_subido = st.file_uploader("Selecciona el archivo Excel o CSV", type=['xlsx', 'xls', 'csv'])
            
            if archivo_subido is not None:
                try:
                    # --- 1. LECTURA INTELIGENTE DE PESTAÑAS ---
                    if archivo_subido.name.endswith('.csv'):
                        df_raw = pd.read_csv(archivo_subido)
                    else:
                        excel_libro = pd.ExcelFile(archivo_subido)
                        hojas = excel_libro.sheet_names
                        hoja_objetivo = next((h for h in hojas if "USAER" in h.upper()), hojas[-1] if len(hojas) > 1 else hojas[0])
                        df_raw = pd.read_excel(archivo_subido, sheet_name=hoja_objetivo)
                    
                    # --- 2. ESCÁNER Y BLINDAJE ANTIDUPLICADOS ---
                    if not any("APELLIDO" in str(c).upper() for c in df_raw.columns):
                        header_idx = None
                        for idx, row in df_raw.head(15).iterrows():
                            if any("APELLIDO" in str(val).upper() for val in row.values):
                                header_idx = idx
                                break
                        
                        if header_idx is not None:
                            # Unimos la fila de títulos principal con la de abajo para rescatar "Grupo" o "Primaria"
                            row1 = df_raw.iloc[header_idx].fillna('').astype(str).replace('nan', '')
                            row2 = df_raw.iloc[header_idx + 1].fillna('').astype(str).replace('nan', '') if header_idx + 1 < len(df_raw) else row1
                            
                            nuevas_cols = []
                            for r1, r2 in zip(row1, row2):
                                col_name = f"{r1} {r2}".strip()
                                if not col_name: col_name = "Vacia"
                                
                                # Si el nombre se repite (ej. varios 'nan' o 'Vacia'), le ponemos un número
                                base = col_name
                                cont = 1
                                while col_name in nuevas_cols:
                                    col_name = f"{base}_{cont}"
                                    cont += 1
                                nuevas_cols.append(col_name)
                                
                            df_raw.columns = nuevas_cols
                            # Saltamos las 2 filas de títulos combinados
                            df_raw = df_raw.iloc[header_idx+2:].reset_index(drop=True)
                    else:
                        # Deduplicar si por casualidad ya venían repetidas desde el CSV
                        nuevas_cols = []
                        for c in df_raw.columns:
                            col_name = str(c).strip().replace('\n', ' ').replace('\r', '')
                            base = col_name
                            cont = 1
                            while col_name in nuevas_cols:
                                col_name = f"{base}_{cont}"
                                cont += 1
                            nuevas_cols.append(col_name)
                        df_raw.columns = nuevas_cols
                        
                    # --- 3. LIMPIEZA DE ALUMNOS FANTASMA ---
                    col_nom = next((c for c in df_raw.columns if "APELLIDO" in c.upper()), None)
                    if not col_nom:
                        st.error("❌ No se encontró la columna de Nombres en el archivo.")
                        st.stop()
                        
                    df_valido = df_raw[df_raw[col_nom].astype(str).str.strip() != ""]
                    df_valido = df_valido[df_valido[col_nom].notna()]
                    df_valido = df_valido[df_valido[col_nom].astype(str).str.lower() != 'nan']
                    
                    # --- 4. VISTA PREVIA LIMPIA ---
                    st.write(f"✅ Vista previa ({len(df_valido)} alumnos listos para procesar):")
                    st.dataframe(df_valido.head(3))
                    
                    # --- 5. BOTÓN DE CARGA ---
                    # (A partir de aquí se queda exactamente igual tu código de 'if st.button("📤 Procesar...")')
                    if st.button("📤 Procesar y subir a la Base de Datos"):
                        with st.spinner("Subiendo padrón a Google Sheets..."):
                            try:
                                df_final = pd.DataFrame()
                                df_final['ID_Alumno'] = [""] * len(df_valido)
                                df_final['Nombre'] = df_valido[col_nom]
                                
                                col_curp = next((c for c in df_valido.columns if "CURP" in c.upper()), None)
                                df_final['CURP'] = df_valido[col_curp] if col_curp else ""
                                
                                # --- EXTRACCIÓN AUTOMATIZADA DE RAYOS X (CERO FRICCIÓN MÁXIMA) ---
                                col_grado = next((c for c in df_valido.columns if "GRADO" in str(c).upper() or "NIVEL" in str(c).upper()), None)
                                col_grp = next((c for c in df_valido.columns if "GRUPO" in str(c).upper()), None)
                                
                                if not col_grp and col_grado:
                                    idx_g = df_valido.columns.get_loc(col_grado)
                                    if idx_g + 1 < len(df_valido.columns): 
                                        col_grp = df_valido.columns[idx_g + 1]
                                
                                grados_list = []
                                grupos_list = []
                                
                                for _, row in df_valido.iterrows():
                                    val_g = str(row.get(col_grado, '')).strip().upper() if col_grado else ""
                                    val_gr = str(row.get(col_grp, '')).strip().upper() if col_grp else ""
                                    
                                    # Si la columna oficial viene vacía, el robot barre toda la fila buscando el Grado
                                    if not val_g or val_g == 'NAN':
                                        val_g = "S/G"
                                        for v in row.values:
                                            v_str = str(v).strip().upper()
                                            if v_str in ['1', '2', '3', '4', '5', '6', '1RO', '2DO', '3RO', '4TO', '5TO', '6TO']:
                                                val_g = v_str
                                                break
                                                
                                    # Si la columna oficial viene vacía, el robot barre toda la fila buscando el Grupo
                                    if not val_gr or val_gr == 'NAN':
                                        val_gr = ""
                                        for v in row.values:
                                            v_str = str(v).strip().upper()
                                            if v_str in ['A', 'B', 'C', 'D', 'E', 'F']:
                                                val_gr = v_str
                                                break
                                                
                                    grados_list.append(val_g)
                                    grupos_list.append(val_gr)
                                    
                                df_final['Grado'] = grados_list
                                df_final['Grupo'] = grupos_list
                                # ------------------------------------------------
                                
                                col_esc = next((c for c in df_valido.columns if "ESCUELA" in c.upper()), None)
                                df_final['Escuela_Asignada'] = df_valido[col_esc].fillna('ESC-005') if col_esc else "ESC-005"
                                
                                df_final['Maestro_Regular'] = "Pendiente"
                                
                                col_cond = next((c for c in df_valido.columns if "DISCAPACIDAD" in c.upper() or "CONDICION" in c.upper()), None)
                                df_final['Condicion'] = df_valido[col_cond].fillna('Ninguna') if col_cond else "Ninguna"
                                
                                col_stat = next((c for c in df_valido.columns if "SITUACION" in c.upper()), None)
                                df_final['Estatus'] = df_valido[col_stat].fillna('Activo') if col_stat else "Activo"
                                
                                col_atn = next((c for c in df_valido.columns if "TIPO DE ATENCION" in c.upper()), None)
                                df_final['Tipo_Atencion'] = df_valido[col_atn].fillna('Grupal') if col_atn else "Grupal"
                                
                                df_final = df_final.fillna("")
                                sheet.worksheet("Alumnos").append_rows(df_final.values.tolist())
                                
                                st.balloons()
                                st.success(f"¡Carga exitosa! Se guardaron {len(df_final)} alumnos.")
                            except Exception as e:
                                st.error(f"Error procesando los datos: {e}")
                                
                except KeyError as e:
                    st.error(f"Error de formato: No se encontró la columna {e} en el archivo subido. Asegúrate de subir el padrón oficial inalterado.")
                except Exception as e:
                    st.error(f"Error al leer el archivo: {e}")


  # --- MÓDULO: BAPs COLABORATIVAS ---
with paneles[idx_bap]:
    st.subheader("Evaluación de Barreras en el Contexto Áulico")
    
    # REGRESAMOS EL SELECTOR MANUAL
    tipo_evaluacion = st.radio("Tipo de Observación y Sugerencias:", ["👥 Grupal (Contexto del Aula)", "👤 Individual (Alumno Específico)"], horizontal=True)
    
    with st.form("anexo3_form", clear_on_submit=False):
        
        # Lógica condicional según la selección del usuario
        if tipo_evaluacion == "👤 Individual (Alumno Específico)":
            col_nom_db = 'Nombre_Completo' if 'Nombre_Completo' in df_alumnos.columns else 'Nombre'
            
            # Buscador flexible de la columna de atención
            col_atn_db = next((c for c in df_alumnos.columns if "ATENCION" in c.upper().replace('Ó', 'O') or "MODALIDAD" in c.upper()), None)
            
            if not df_alumnos.empty and col_atn_db:
                mascara_ind = df_alumnos[col_atn_db].astype(str).str.strip().str.upper() == 'INDIVIDUAL'
                df_ind = df_alumnos[mascara_ind]
                alumnos_individuales = sorted([nom for nom in df_ind[col_nom_db].astype(str).tolist() if nom.strip() != ""])
            else:
                alumnos_individuales = []

            if not alumnos_individuales:
                st.warning("⚠️ No se encontraron alumnos con tipo de atención 'Individual' en la base de datos.")

            objetivo_seleccionado = st.selectbox(
                "Selecciona al Alumno a evaluar",
                alumnos_individuales if alumnos_individuales else ["Sin registros individuales"]
            )
            prompt_contexto = f"Eres un experto de la USAER. Genera sugerencias INDIVIDUALES para el alumno {objetivo_seleccionado} considerando sus barreras específicas detectadas."
            
        else:
            # --- AQUÍ ESTÁN LOS SELECTORES DEL MODO GRUPAL ---
            
            # 1. Definir qué escuelas puede ver este especialista
            rol_activo_bap = str(st.session_state.get("rol", "")).upper()
            escuelas_perm_bap = str(st.session_state.get("escuelas_permitidas", "")).strip().upper()
            
            # Diego (Trabajo Social) y Director ven todas, los demás solo sus asignadas
            if "DIRECTOR" in rol_activo_bap or "TRABAJO" in rol_activo_bap or "TODAS" in escuelas_perm_bap:
                opciones_escuela_bap = list(escuelas_usaer.keys())
            else:
                claves_permitidas = [e.strip() for e in escuelas_perm_bap.split(",")]
                opciones_escuela_bap = [nombre for nombre, clave in escuelas_usaer.items() if clave in claves_permitidas]

            # Selector de Escuela
            escuela_grupal = st.selectbox("Escuela a observar", opciones_escuela_bap if opciones_escuela_bap else ["Sin escuelas asignadas"])
            
            # Selectores de Grado y Grupo
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                grado_grupal = st.selectbox("Grado a observar", ["1ro", "2do", "3ro", "4to", "5to", "6to"])
            with col_g2:
                grupo_grupal = st.selectbox("Grupo a observar", ["A", "B", "C", "D"])
            
            objetivo_seleccionado = f"Grupo {grado_grupal} {grupo_grupal} de la escuela {escuela_grupal}"
            prompt_contexto = f"Eres un experto de la USAER. Genera sugerencias GRUPALES para el contexto áulico del {objetivo_seleccionado}, enfocadas en el Diseño Universal para el Aprendizaje (DUA) y dinámicas colectivas."
        
        st.markdown("---")
        st.markdown("### Instrumento de Observación (Anexo III)")
        
        # CICLO DE PREGUNTAS
        respuestas_bap = {}
        for i, item in enumerate(items_anexo3):
            st.markdown(f"**{item}**")
            col_freq, col_ori = st.columns([3, 1])
            with col_freq:
                freq = st.radio("Frecuencia", ["Siempre", "Muchas veces", "Pocas veces", "Nunca"], horizontal=True, key=f"freq_{i}_{tipo_evaluacion}", label_visibility="collapsed")
            with col_ori:
                st.markdown("<br>", unsafe_allow_html=True)
                ori = st.checkbox("Requiere Orientación", key=f"ori_{i}_{tipo_evaluacion}")
            
            respuestas_bap[f"Item_{i+1}"] = {"pregunta": item, "frecuencia": freq, "orientacion": ori}
            st.markdown("---")
        
        # AQUÍ IRÁN LOS REACTIVOS COMPLETOS

            
        contexto_extra = st.text_area("Añade observaciones cualitativas, detalles sobre la dinámica del grupo o estrategias previas intentadas.", height=100)
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
            with st.spinner("La red neuronal está analizando y puliendo el texto... 🧠"):
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
                
                # --- SISTEMA DE REINTENTO SILENCIOSO ---
                intentos_maximos = 3
                exito = False
                
                for intento in range(intentos_maximos):
                    try:
                        respuesta_ia = modelo_ia.generate_content(prompt_estilo)
                        st.session_state.ia_evento_sugerido = respuesta_ia.text
                        exito = True
                        break  # Si la IA responde bien, rompemos el ciclo inmediatamente
                    except Exception:
                        if intento < intentos_maximos - 1:
                            time.sleep(2)  # Pausa silenciosa de 2 segundos antes de volver a intentar
                        else:
                            pass # Si ya falló 3 veces, nos rendimos
                
                if exito:
                    st.rerun()
                else:
                    st.error("⚠️ La red neuronal está experimentando un tráfico inusual. Por favor, intenta presionar el botón una vez más.") 

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
                # Buscador flexible del nombre del alumno
                col_nom = 'Nombre_Completo' if 'Nombre_Completo' in df_alumnos.columns else 'Nombre'
                fila_alum_evt = df_alumnos.loc[df_alumnos[col_nom] == alum_evt]
                
                if not fila_alum_evt.empty:
                    # Búsqueda flexible de columnas de grado y grupo en la base de datos
                    col_g = next((c for c in df_alumnos.columns if "GRADO" in str(c).upper()), 'Grado')
                    col_gr = next((c for c in df_alumnos.columns if "GRUPO" in str(c).upper()), 'Grupo')
                    
                    val_grado = str(fila_alum_evt[col_g].values[0]) if col_g in df_alumnos.columns else ""
                    val_grupo = str(fila_alum_evt[col_gr].values[0]) if col_gr in df_alumnos.columns else ""
                    
                    grado_grupo_visor = f"{val_grado} {val_grupo}".strip()
                    if grado_grupo_visor == "S/G" or grado_grupo_visor == "":
                        grado_grupo_visor = "S/G (Falta actualizar en Base de Datos)"

# ATENCIÓN: Este bloque HTML debe ir pegado a la izquierda
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
                # AQUÍ REEMPLAZAMOS "HOY" POR LA FECHA EXACTA
                fecha_hoy_str = datetime.now().strftime("%d/%m/%Y")
                html_preview += f"""
<tr style="background-color: #e6f7ff;">
<td style="border: 1px solid black; padding: 10px; vertical-align: top;"><b>{fecha_hoy_str}</b></td>
<td style="border: 1px solid black; padding: 10px; vertical-align: top;"><b>{str(evento_definitivo).replace(chr(10), '<br>')}</b></td>
<td style="border: 1px solid black; padding: 10px; text-align: center; vertical-align: bottom;"><br><br>____________________<br><b><i>{st.session_state.get('nombre', '')}</i> (Nuevo)</b></td>
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

# --- MÓDULO: CONSTANCIAS DE VISITA (Exclusivo Paradocentes) ---
if idx_visitas != -1:
    with paneles[idx_visitas]:
        # Filtro estricto de seguridad por Rol
        rol_actual = str(st.session_state.get('rol', '')).upper()
        roles_permitidos = ["PSICOLOG", "COMUNICACI", "TRABAJO_SOCIAL", "TRABAJO SOCIAL"]
        
        if not any(rol in rol_actual for rol in roles_permitidos):
            st.warning("🔒 Acceso denegado: Este módulo es de uso exclusivo para los equipos de Psicología, Comunicación y Trabajo Social.")
        else:
            st.subheader("Generador Automático de Constancias de Visita")
            st.markdown("Selecciona la escuela y las actividades. La red neuronal ensamblará el documento oficial con las firmas correspondientes.")
            
            # Base de conocimiento interna para autollenado de firmas
            directorio_firmas = {
                "ESC-001": {"escuela": "Damián Carmona", "dir_primaria": "Mtra. Maribel Vargas Arana", "apoyo": "Mtra. Cindy Mayanín Burgos González"},
                "ESC-002": {"escuela": "Ichcaanziho", "dir_primaria": "Mtra. Rennaty Maribel Puga Jimenez", "apoyo": "Mtra. Marycruz Caamal Coral"},
                "ESC-003": {"escuela": "Gregorio Torres Quintero", "dir_primaria": "Mtro. Elmer Ariel Ontiveros Requena", "apoyo": "Mtra. Dolores Eugenia Cortázar Navarrete"},
                "ESC-004": {"escuela": "Remigio Aguilar Sosa", "dir_primaria": "Mtro. Carlos Esteban Heredia GCantón", "apoyo": "Mtra. Dianely de Sugeidy Caamal Tamay"},
                "ESC-005": {"escuela": "Elvira Parra Ávila", "dir_primaria": "Mtro. Manuel Jesús Alcocer Vázquez", "apoyo": "Mtro. Luis Jorge García Herrera"},
                "ESC-006": {"escuela": "Manuel Sarrado", "dir_primaria": "Mtro. José Alberto Reyna Martínez", "apoyo": "Mtra. María del Rosario Pérez Vitorin"},
                "ESC-007": {"escuela": "Domingo Solís Rodríguez", "dir_primaria": "Mtra. Erika Basto Ek", "apoyo": "Mtra. Zuemmy del Carmen Pérez Basto"},
                "ESC-008": {"escuela": "Quintana Roo", "dir_primaria": "Mtro. Jorge Adrián Cetina Cach", "apoyo": "Mtro. Pedro Manuel Torres May"}
            }
            
            # Identificar escuelas permitidas para el especialista activo
            escuelas_usuario_visita = str(st.session_state.get("escuelas_permitidas", "")).strip().upper()
            claves_permitidas = [e.strip() for e in escuelas_usuario_visita.split(",")]
            
            opciones_escuela = []
            if escuelas_usuario_visita == "TODAS":
                opciones_escuela = [datos["escuela"] for datos in directorio_firmas.values()]
            else:
                opciones_escuela = [directorio_firmas[clave]["escuela"] for clave in claves_permitidas if clave in directorio_firmas]
            
            with st.form("form_constancia", clear_on_submit=False):
                col1, col2 = st.columns([2, 1])
                with col1:
                    escuela_seleccionada = st.selectbox("Escuela visitada", opciones_escuela if opciones_escuela else ["Sin escuelas asignadas"])
                with col2:
                    fecha_visita = st.date_input("Fecha de la visita")
                
                st.markdown("**Motivo de la visita (Selecciona las aplicables):**")
                col_mot1, col_mot2 = st.columns(2)
                with col_mot1:
                    motivos_izq = st.multiselect("Actividades de Seguimiento y Apoyo", [
                        "Observación en grupo", "Entrevista con...", "Trabajo interdisciplinario",
                        "Sugerencias a Maestra(o)", "Sugerencias a Padres de...", "Valoración a...",
                        "Revaloración de sugerencias con...", "Elaboración o actualización de EPP"
                    ])
                with col_mot2:
                    motivos_der = st.multiselect("Intervención y Juntas", [
                        "Intervención en Grupo", "Apoyo individual en aula", "Elaboración del Plan de Intervención",
                        "Consejo Técnico Escolar", "Junta del Servicio de Apoyo", "Junta Académica del Servicio de Apoyo", "Otros"
                    ])
                    
                detalles_motivos = st.text_input("Especifica nombres si seleccionaste 'Entrevista con...', 'Sugerencias a...', etc. (Opcional)")
                descripcion_actividad = st.text_area("Breve descripción de las actividades desarrolladas", height=100)
                
                generar_acta = st.form_submit_button("Generar Constancia Oficial")
                
            if generar_acta:
                # Localizar la clave de la escuela seleccionada
                clave_escuela = next((k for k, v in directorio_firmas.items() if v["escuela"] == escuela_seleccionada), None)
                
                if clave_escuela:
                    dir_prim = directorio_firmas[clave_escuela]["dir_primaria"]
                    apoyo_prim = directorio_firmas[clave_escuela]["apoyo"]
                    
                    # Identificar la especialidad para el formato oficial
                    rol_actual_texto = str(st.session_state.get('rol', '')).upper()
                    if "PSICOLOG" in rol_actual_texto:
                        especialidad_visita = "Área de Psicología - USAER 02-E"
                    elif "COMUNICACI" in rol_actual_texto:
                        especialidad_visita = "Área de Comunicación - USAER 02-E"
                    elif "TRABAJO" in rol_actual_texto:
                        especialidad_visita = "Área de Trabajo Social - USAER 02-E"
                    else:
                        especialidad_visita = st.session_state.get('rol', 'USAER 02-E')
                    
                    def m(opcion):
                        return "( X )" if opcion in motivos_izq or opcion in motivos_der else "( &nbsp;&nbsp; )"
                        
                    def d(opcion, linea="___________________"):
                        return f"<b>{detalles_motivos}</b>" if detalles_motivos and (opcion in motivos_izq or opcion in motivos_der) else linea

# ATENCIÓN: A partir de aquí, CERO espacios a la izquierda
                    html_constancia = f"""<div style="background-color: white; color: black; padding: 40px; font-family: Arial, sans-serif; max-width: 800px; margin: auto;">
<table style="width: 100%; margin-bottom: 20px; border: none;">
<tr>
<td style="width: 25%; text-align: left; vertical-align: middle;">
<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Logo_de_la_Secretar%C3%ADa_de_Educaci%C3%B3n_P%C3%BAblica_%28M%C3%A9xico%29.svg/512px-Logo_de_la_Secretar%C3%ADa_de_Educaci%C3%B3n_P%C3%BAblica_%28M%C3%A9xico%29.svg.png" alt="SEP" style="max-width: 120px;">
</td>
<td style="width: 50%; text-align: center; vertical-align: middle; font-size: 13px; line-height: 1.2;">
<b>DIRECCIÓN DE EDUCACIÓN ESPECIAL</b><br>
<b>USAER 02 ESTATAL CCT. 31FUA0002Y</b><br>
<b>ZONA No. 001</b>
</td>
<td style="width: 25%; text-align: right; vertical-align: middle;">
<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Escudo_de_Yucat%C3%A1n.svg/200px-Escudo_de_Yucat%C3%A1n.svg.png" alt="Yucatan" style="max-height: 70px;">
</td>
</tr>
</table>

<h3 style="text-align: center; font-weight: bold; text-decoration: underline; margin-bottom: 25px;">Constancia de visita</h3>

<div style="font-size: 14px; margin-bottom: 5px;">Servicio de educación especial que realiza la visita: <u>{especialidad_visita}</u></div>
<div style="font-size: 14px; margin-bottom: 5px;">Curso escolar: <u>2026 – 2027</u> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Fecha de la visita: <u>{fecha_visita.strftime('%d/%m/%Y')}</u> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Hora: <u>de 7:00 a 12:00hrs</u></div>
<div style="font-size: 14px; margin-bottom: 20px;">Escuela: <u>{escuela_seleccionada}</u> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Localidad: <u>MÉRIDA</u></div>

<div style="font-size: 14px; margin-bottom: 2px;">Motivo de la visita:</div>
<table style="width: 100%; font-size: 13px; margin-bottom: 20px; border-collapse: collapse;">
<tr>
<td style="width: 50%; vertical-align: top; border: 1px dashed #ccc; padding: 5px; line-height: 1.5;">
{m('Observación en grupo')} Observación en grupo {d('Observación en grupo', '_________________')}<br>
{m('Entrevista con...')} Entrevista con {d('Entrevista con...', '______________________')}<br>
{m('Trabajo interdisciplinario')} Trabajo interdisciplinario<br>
{m('Sugerencias a Maestra(o)')} Sugerencias a Maestra (o) {d('Sugerencias a Maestra(o)', '_____________')}<br>
{m('Sugerencias a Padres de...')} Sugerencias a Padres de {d('Sugerencias a Padres de...', '______________')}<br>
{m('Valoración a...')} Valoración a {d('Valoración a...', '________________________')}<br>
{m('Revaloración de sugerencias con...')} Revaloración de sugerencias con: {d('Revaloración de sugerencias con...', '______')}<br>
{m('Elaboración o actualización de EPP')} Elaboración o actualización de EPP _______
</td>
<td style="width: 50%; vertical-align: top; border: 1px dashed #ccc; padding: 5px; line-height: 1.5;">
{m('Intervención en Grupo')} Intervención en Grupo {d('Intervención en Grupo', '_________________')}<br>
{m('Apoyo individual en aula')} Apoyo individual a ___________en aula de __<br>
{m('Elaboración del Plan de Intervención')} Elaboración del Plan de Intervención _______<br>
{m('Consejo Técnico Escolar')} Consejo Técnico Escolar<br>
{m('Junta del Servicio de Apoyo')} Junta del Servicio de Apoyo_______________<br>
{m('Junta Académica del Servicio de Apoyo')} Junta Académica del Servicio de Apoyo<br>
{m('Otros')} Otros: {d('Otros', '______________________________')}
</td>
</tr>
</table>

<div style="font-size: 14px; margin-bottom: 10px;">Breve descripción de las actividades desarrolladas:</div>
<div style="font-size: 14px; min-height: 120px; line-height: 1.6;">
{descripcion_actividad.replace(chr(10), '<br>') if descripcion_actividad else '<br><br><br><br>'}
</div>

<table style="width: 100%; font-size: 12px; text-align: center; margin-top: 50px; border: none;">
<tr>
<td style="width: 50%; padding-bottom: 40px; padding-right: 20px;">
___________________________<br>
<b>{dir_prim}</b><br>
Directora(or) de la primaria
</td>
<td style="width: 50%; padding-bottom: 40px; padding-left: 20px;">
_______________________<br>
<b>{apoyo_prim}</b><br>
Maestra(o) de apoyo
</td>
</tr>
<tr>
<td style="width: 50%; padding-right: 20px;">
___________________________<br>
<b>Psic. Edgar Adrián Yam Briceño MD</b><br>
Director de la USAER 02-E
</td>
<td style="width: 50%; padding-left: 20px;">
______________________<br>
<b>Dra. Diana A. Durán González</b><br>
Supervisora de la zona 001 EE
</td>
</tr>
</table>
</div>"""

                    html_impresion = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Constancia de Visita - {escuela_seleccionada}</title>
<style>
@media print {{
@page {{ margin: 1cm; }}
body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
table td {{ border: 1px dashed #ccc !important; }}
}}
</style>
</head>
<body onload="window.print()" style="padding: 0; margin: 0; display: flex; justify-content: center;">
{html_constancia}
</body>
</html>"""

                    st.success("¡Constancia generada exitosamente!")
                    st.markdown(html_constancia, unsafe_allow_html=True)
                    
                    st.download_button(
                        label="🖨️ Descargar Constancia para Imprimir",
                        data=html_impresion,
                        file_name=f"Constancia_Visita_{escuela_seleccionada.replace(' ', '_')}.html",
                        mime="text/html"
                    )

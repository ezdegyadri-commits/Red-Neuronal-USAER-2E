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
# --- CARGA DE DATOS PARA LOS FORMULARIOS ---
# ==========================================
try:
    # 1. Cargar Alumnos de Sheets
    df_alumnos = pd.DataFrame(sheet.worksheet("Alumnos").get_all_records())
    col_nombre = 'Nombre_Completo' if 'Nombre_Completo' in df_alumnos.columns else 'Nombre'
    
    # Extraemos solo los nombres reales, ignorando celdas vacías, y los ordenamos alfabéticamente
    lista_alumnos = [nom for nom in df_alumnos[col_nombre].astype(str).tolist() if nom.strip() != ""]
    lista_alumnos = sorted(list(set(lista_alumnos)))
    
except Exception:
    df_alumnos = pd.DataFrame()
    lista_alumnos = []

# 2. Diccionario de Escuelas (Ajusta los nombres de las escuelas reales después)
escuelas_usaer = {
    "Primaria 1": "ESC-001",
    "Primaria 2": "ESC-002",
    "Preescolar 3": "ESC-003",
    "Primaria 4": "ESC-004",
    "Primaria 5": "ESC-005",
    "Preescolar 6": "ESC-006",
    "Secundaria 7": "ESC-007",
    "Secundaria 8": "ESC-008"
}

# 3. Elementos de Evaluación (BAPs) para el Anexo III Oficial SEGEY
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
    "📊 Panel de Dirección"
]
paneles = st.tabs(tabs)

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
                                
                                def obtener_grado(row):
                                    for col in df_valido.columns:
                                        if "NIVEL" in col.upper() and ("PRIMARIA" in col.upper() or "PREESCOLAR" in col.upper() or "SECUNDARIA" in col.upper()):
                                            val = str(row.get(col, '')).strip()
                                            if val and val.lower() != 'nan':
                                                return val
                                    return "S/G"
                                
                                df_final['Grado'] = df_valido.apply(obtener_grado, axis=1)
                                
                                col_grp = next((c for c in df_valido.columns if "GRUPO" in c.upper()), None)
                                df_final['Grupo'] = df_valido[col_grp].fillna('').astype(str).replace('nan', '') if col_grp else ""
                                
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
                except Exception as e:
                    st.error(f"Error leyendo el archivo: {e}")
                                
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
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                grado_grupal = st.selectbox("Grado a observar", ["1ro", "2do", "3ro", "4to", "5to", "6to"])
            with col_g2:
                grupo_grupal = st.selectbox("Grupo a observar", ["A", "B", "C", "D"])
            
            objetivo_seleccionado = f"Grupo {grado_grupal} {grupo_grupal}"
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
        
        respuestas_bap = {}
        for i, item in enumerate(items_anexo3):
            st.markdown(f"**{item}**")
            col_freq, col_ori = st.columns([3, 1])
            with col_freq:
                freq = st.radio("Frecuencia", ["Siempre", "Muchas veces", "Pocas veces", "Nunca"], horizontal=True, key=f"bap_frecuencia_{i}", label_visibility="collapsed")
            with col_ori:
                st.markdown("<br>", unsafe_allow_html=True)
                ori = st.checkbox("Requiere Orientación", key=f"bap_orientacion_{i}")
            
            respuestas_bap[f"Item_{i+1}"] = {"pregunta": item, "frecuencia": freq, "orientacion": ori}
            st.markdown("---")
            
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

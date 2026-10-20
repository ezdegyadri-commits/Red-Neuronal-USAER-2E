"""Identidad institucional y diseño SaaS de alta gama para USAER 02-E."""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');

:root {
  /* Paleta SaaS Moderna, Cálida y Profesional */
  --bs-primary: #0F3A4A;
  --bs-primary-dark: #0A2732;
  --bs-primary-light: #165668;
  --bs-primary-subtle: #E6F4F7;
  --bs-teal: #0D9488;
  --bs-teal-dark: #0F766E;
  --bs-teal-light: #F0FDFA;
  --bs-teal-subtle: #CCFBF1;
  --bs-accent: #D97706;
  --bs-accent-light: #FFFBEB;
  --bs-accent-hover: #B45309;
  --bs-blue: #2563EB;
  --bs-blue-light: #EFF6FF;
  --bs-emerald: #059669;
  --bs-emerald-light: #ECFDF5;
  --bs-danger: #DC2626;
  --bs-danger-light: #FEF2F2;

  /* Superficies y Neutros */
  --bs-body-bg: #F8FAFC;
  --bs-surface: #FFFFFF;
  --bs-surface-alt: #F1F5F9;
  --bs-surface-card: #FFFFFF;
  --bs-body-color: #0F172A;
  --bs-secondary-color: #475569;
  --bs-muted-color: #64748B;
  --bs-border-color: #E2E8F0;
  --bs-border-hover: #CBD5E1;
  --bs-border-subtle: #F1F5F9;
  --bs-focus-ring: rgba(13, 148, 136, 0.22);
  --usaer-accent: #D97706;

  /* Escala de Sombras SaaS Multicapa (Depth & Elevation) */
  --shadow-xs: 0 1px 2px 0 rgba(15, 23, 42, 0.04);
  --shadow-sm: 0 1px 3px 0 rgba(15, 23, 42, 0.06), 0 1px 2px -1px rgba(15, 23, 42, 0.04);
  --shadow-md: 0 4px 12px -2px rgba(15, 23, 42, 0.06), 0 2px 4px -2px rgba(15, 23, 42, 0.04);
  --shadow-lg: 0 12px 28px -6px rgba(15, 23, 42, 0.08), 0 4px 10px -4px rgba(15, 23, 42, 0.04);
  --shadow-xl: 0 20px 35px -8px rgba(15, 23, 42, 0.12), 0 8px 16px -6px rgba(15, 23, 42, 0.06);
  --shadow-hover: 0 14px 30px -4px rgba(15, 23, 42, 0.1), 0 4px 10px -2px rgba(15, 23, 42, 0.05);
  --shadow-glow-teal: 0 0 18px rgba(13, 148, 136, 0.28);
  --shadow-glow-blue: 0 0 18px rgba(37, 99, 235, 0.25);

  /* Radios de Curvatura Suaves */
  --radius-xs: 6px;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 9999px;

  /* Curvas de Transición Suaves */
  --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);
}

/* ========================================================================== */
/* KEYFRAME ANIMATIONS (SaaS Polish & Micro-Interactions)                     */
/* ========================================================================== */
@keyframes saasFadeInUp {
  0% { transform: translateY(4px); }
  100% { transform: translateY(0); }
}

@keyframes saasFadeInScale {
  0% { transform: scale(0.99); }
  100% { transform: scale(1); }
}

@keyframes saasPulseDot {
  0% {
    transform: scale(0.92);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6);
  }
  70% {
    transform: scale(1.1);
    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
  }
  100% {
    transform: scale(0.92);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

@keyframes saasShimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* ========================================================================== */
/* BASE, FONDO MESH Y TIPOGRAFÍA WCAG AA                                      */
/* ========================================================================== */
html, body {
  font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  scroll-behavior: smooth;
}

/* Fondo principal SaaS: Gradiente Mesh Sutil con Profundidad */
.stApp, [data-testid="stAppViewContainer"] {
  background-color: var(--bs-body-bg) !important;
  background-image:
    radial-gradient(at 0% 0%, rgba(13, 148, 136, 0.055) 0px, transparent 48%),
    radial-gradient(at 100% 0%, rgba(37, 99, 235, 0.045) 0px, transparent 45%),
    radial-gradient(at 50% 100%, rgba(217, 119, 6, 0.035) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(15, 76, 92, 0.04) 0px, transparent 45%) !important;
  background-attachment: fixed !important;
  color: var(--bs-body-color) !important;
  font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

.stApp, .stApp * {
  color-scheme: light;
}

.block-container {
  max-width: 1440px;
  padding-top: 1.75rem;
  padding-bottom: 4rem;
  padding-left: 2rem;
  padding-right: 2rem;
}

.stApp p, .stApp label, .stApp li, [data-testid="stMarkdownContainer"] {
  color: var(--bs-body-color);
  font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  line-height: 1.6;
}

[data-testid="stCaptionContainer"], .stCaption {
  color: var(--bs-secondary-color) !important;
  font-size: 0.84rem !important;
  font-weight: 500 !important;
}

/* Jerarquía de Encabezados */
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  letter-spacing: -0.025em;
  color: var(--bs-primary-dark);
  font-weight: 750;
}

.stApp h1 { font-size: 2.2rem; line-height: 1.2; margin-bottom: 0.65rem; }
.stApp h2 { font-size: 1.65rem; line-height: 1.25; margin-bottom: 0.55rem; }
.stApp h3 { font-size: 1.28rem; line-height: 1.32; margin-bottom: 0.45rem; }
.stApp h4 { font-size: 1.08rem; line-height: 1.38; margin-bottom: 0.35rem; }

/* Barra Superior con Glassmorphism */
[data-testid="stHeader"] {
  background: rgba(248, 250, 252, 0.88) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8) !important;
}

/* ========================================================================== */
/* SIDEBAR DASHBOARD ELEGANTE (DARK GLASS SAAS)                               */
/* ========================================================================== */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0F2D3C 0%, #091E28 100%) !important;
  border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
  box-shadow: 2px 0 16px rgba(0, 0, 0, 0.12);
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6 {
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 700 !important;
}

[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
  color: #FBBF24 !important;
  -webkit-text-fill-color: #FBBF24 !important;
  font-size: 0.88rem !important;
  font-weight: 750 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  margin-top: 1.25rem !important;
  margin-bottom: 0.5rem !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span:not(.badge):not(.status-dot),
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:not([data-testid="stExpander"] *) {
  color: #E2EFF2 !important;
  -webkit-text-fill-color: #E2EFF2 !important;
}

[data-testid="stSidebar"] hr,
[data-testid="stSidebar"] [data-testid="stDivider"] {
  border-color: rgba(255, 255, 255, 0.12) !important;
  margin: 1.15rem 0 !important;
}

/* Pill de Sesión Activa en Sidebar */
.sidebar-user-pill {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: var(--radius-md);
  margin-bottom: 1.25rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(8px);
  transition: all 0.22s var(--ease-spring);
}

.sidebar-user-pill:hover {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(255, 255, 255, 0.22);
  transform: translateY(-1px);
}

.sidebar-user-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-user-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94A3B8 !important;
  -webkit-text-fill-color: #94A3B8 !important;
  font-weight: 700;
  line-height: 1.2;
}

.sidebar-user-name {
  font-size: 0.9rem;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 750;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Brand Card en Sidebar */
.brand {
  padding: 1.1rem 1.2rem;
  margin-bottom: 1.15rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
  box-shadow: var(--shadow-sm);
}

.brand h1 {
  font-size: 1.55rem;
  letter-spacing: -0.015em;
  color: #FFFFFF !important;
  margin: 0;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.brand p {
  font-size: 0.82rem;
  line-height: 1.5;
  margin: 0.5rem 0 0;
  color: #CBD5E1 !important;
}

.brand .brand-overline {
  display: inline-block;
  background: rgba(217, 119, 6, 0.22);
  color: #FCD34D !important;
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 3px 9px;
  border-radius: var(--radius-xs);
  margin-bottom: 0.5rem;
  border: 1px solid rgba(217, 119, 6, 0.4);
}

/* Menú de Navegación Lateral (Pills Modernos con Micro-Interacciones) */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label > div:first-child {
  display: none !important;
}

[data-testid="stSidebar"] .stRadio label {
  padding: 0.68rem 1rem !important;
  border-radius: 11px !important;
  margin-bottom: 4px !important;
  transition: all 0.22s var(--ease-spring) !important;
  color: #CBD5E1 !important;
  font-size: 0.91rem !important;
  font-weight: 550 !important;
  cursor: pointer !important;
  border: 1px solid transparent !important;
  width: 100% !important;
  box-sizing: border-box !important;
  display: flex !important;
  align-items: center !important;
}

[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(255, 255, 255, 0.08) !important;
  color: #FFFFFF !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
  transform: translateX(4px) !important;
}

[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: linear-gradient(90deg, rgba(13, 148, 136, 0.9) 0%, rgba(15, 76, 92, 0.65) 100%) !important;
  color: #FFFFFF !important;
  font-weight: 700 !important;
  border-color: rgba(13, 148, 136, 0.6) !important;
  box-shadow: inset 4px 0 0 #F59E0B, 0 4px 12px rgba(0, 0, 0, 0.18) !important;
}

/* ========================================================================== */
/* BOTONES SAAS: PRIMARIOS, SECUNDARIOS, DESTRUCTIVOS Y MICRO-INTERACCIONES    */
/* ========================================================================== */

/* Herencia de color y estilo para textos internos en botones de Streamlit */
div[data-testid="stButton"] button p,
div[data-testid="stDownloadButton"] button p,
div.stButton > button p,
div.stDownloadButton > button p,
[data-testid="stFormSubmitButton"] button p {
  color: inherit !important;
  font-size: inherit !important;
  font-weight: inherit !important;
  line-height: inherit !important;
  margin: 0 !important;
  letter-spacing: inherit !important;
}

/* Base Universal para Todos los Botones */
div.stButton > button,
div.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button,
div.stLinkButton > a {
  border-radius: var(--radius-md) !important;
  font-weight: 650 !important;
  font-size: 0.96rem !important;
  letter-spacing: 0.01em !important;
  min-height: 46px !important;
  padding: 0.65rem 1.35rem !important;
  transition: all 0.22s var(--ease-spring) !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 0.55rem !important;
  border: 1.5px solid var(--bs-border-color) !important;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
  color: var(--bs-primary-dark) !important;
  box-shadow: var(--shadow-xs) !important;
  will-change: transform, box-shadow !important;
}

/* Micro-interacción: Hover (Ligera elevación suave y resplandor) */
div.stButton > button:hover,
div.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover,
div.stLinkButton > a:hover {
  background: #F0FDFA !important;
  border-color: var(--bs-teal) !important;
  color: var(--bs-teal-dark) !important;
  box-shadow: var(--shadow-md) !important;
  transform: translateY(-2px) !important;
}

/* Micro-interacción: Active (Escalado táctil scale(0.98) solicitado por el usuario) */
div.stButton > button:active,
div.stDownloadButton > button:active,
[data-testid="stFormSubmitButton"] button:active,
div.stLinkButton > a:active {
  transform: scale(0.98) translateY(0) !important;
  box-shadow: var(--shadow-xs) !important;
}

/* Estado Disabled */
div.stButton > button:disabled,
div.stDownloadButton > button:disabled,
[data-testid="stFormSubmitButton"] button:disabled {
  background: #E2E8F0 !important;
  color: #94A3B8 !important;
  border-color: #CBD5E1 !important;
  box-shadow: none !important;
  transform: none !important;
  cursor: not-allowed !important;
  filter: grayscale(30%) !important;
}

/* 1. Botones Primarios (Llamados a la Acción Fuertes SaaS) */
div.stButton > button[kind="primary"],
div.stDownloadButton > button[kind="primary"],
div.stButton > button[data-testid="baseButton-primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg, #0F4C5C 0%, #0D9488 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  font-weight: 750 !important;
  box-shadow: 0 4px 14px rgba(13, 148, 136, 0.35) !important;
}

div.stButton > button[kind="primary"]:hover,
div.stDownloadButton > button[kind="primary"]:hover,
div.stButton > button[data-testid="baseButton-primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover {
  background: linear-gradient(135deg, #0A3742 0%, #0F766E 100%) !important;
  box-shadow: 0 8px 24px rgba(13, 148, 136, 0.48) !important;
  transform: translateY(-2px) !important;
  color: #FFFFFF !important;
}

/* 2. Botones de Acción Destructiva / Peligro (Eliminar, Borrar, Cancelar) */
div.stButton > button:has(p:contains("Eliminar")),
div.stButton > button:has(p:contains("eliminar")),
div.stButton > button:has(p:contains("Borrar")),
div.stButton > button:has(p:contains("borrar")),
div[class*="st-key-"][class*="eliminar"] button,
div[class*="st-key-"][class*="borrar"] button,
div[class*="st-key-"][class*="danger"] button {
  background: linear-gradient(135deg, #DC2626 0%, #EF4444 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 14px rgba(220, 38, 38, 0.3) !important;
}

div.stButton > button:has(p:contains("Eliminar")):hover,
div.stButton > button:has(p:contains("eliminar")):hover,
div.stButton > button:has(p:contains("Borrar")):hover,
div.stButton > button:has(p:contains("borrar")):hover,
div[class*="st-key-"][class*="eliminar"] button:hover,
div[class*="st-key-"][class*="borrar"] button:hover,
div[class*="st-key-"][class*="danger"] button:hover {
  background: linear-gradient(135deg, #B91C1C 0%, #DC2626 100%) !important;
  box-shadow: 0 8px 22px rgba(220, 38, 38, 0.45) !important;
  color: #FFFFFF !important;
  transform: translateY(-2px) !important;
}

/* Focus Visible Accesible */
.stApp button:focus-visible,
.stApp input:focus-visible,
.stApp textarea:focus-visible,
.stApp select:focus-visible {
  outline: 3px solid var(--bs-teal) !important;
  outline-offset: 2px !important;
}

/* ========================================================================== */
/* FORMULARIOS, INPUTS Y SELECTORES MODERNOS                                  */
/* ========================================================================== */
.stApp [data-baseweb="input"] > div,
.stApp [data-baseweb="textarea"] > div,
.stApp [data-baseweb="select"] > div,
.stApp input,
.stApp textarea {
  background: #FFFFFF !important;
  color: var(--bs-body-color) !important;
  -webkit-text-fill-color: var(--bs-body-color) !important;
  border: 1.5px solid var(--bs-border-color) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-xs);
  transition: all 0.2s var(--ease-smooth);
}

.stApp [data-baseweb="input"]:focus-within > div,
.stApp [data-baseweb="textarea"]:focus-within > div,
.stApp [data-baseweb="select"]:focus-within > div {
  border-color: var(--bs-teal) !important;
  box-shadow: 0 0 0 3.5px var(--bs-focus-ring) !important;
}

.stApp [data-baseweb="select"] *,
.stApp [data-baseweb="input"] input,
.stApp [data-baseweb="textarea"] textarea {
  color: var(--bs-body-color) !important;
  -webkit-text-fill-color: var(--bs-body-color) !important;
  font-family: inherit;
}

.stApp input::placeholder,
.stApp textarea::placeholder {
  color: #94A3B8 !important;
  -webkit-text-fill-color: #94A3B8 !important;
}

.stApp [data-baseweb="select"] svg {
  fill: var(--bs-teal-dark) !important;
}

/* Multiselect Tags */
[data-baseweb="tag"] {
  background: var(--bs-teal-light) !important;
  color: var(--bs-teal-dark) !important;
  border-radius: var(--radius-xs) !important;
  font-weight: 650 !important;
  border: 1px solid var(--bs-teal-subtle) !important;
}

[data-baseweb="tag"] span {
  color: var(--bs-teal-dark) !important;
}

/* ========================================================================== */
/* DATA TABLES Y VISTAS DE REPORTES MODERNAS                                  */
/* ========================================================================== */
[data-testid="stDataFrame"],
.stTable,
[data-testid="stDataEditor"] {
  border: 1px solid var(--bs-border-color) !important;
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--shadow-sm) !important;
  overflow: hidden !important;
  background: #FFFFFF !important;
  transition: box-shadow 0.25s var(--ease-spring) !important;
}

[data-testid="stDataFrame"]:hover,
[data-testid="stDataEditor"]:hover {
  box-shadow: var(--shadow-md) !important;
}

/* Estilo para Tablas Nativas / Data Tables */
.stTable table {
  width: 100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
}

.stTable thead th,
[data-testid="stDataFrame"] thead th {
  background: #F8FAFC !important;
  color: var(--bs-secondary-color) !important;
  font-weight: 750 !important;
  font-size: 0.82rem !important;
  letter-spacing: 0.05em !important;
  text-transform: uppercase !important;
  padding: 0.85rem 1.1rem !important;
  border-bottom: 2px solid var(--bs-border-color) !important;
  text-align: left !important;
}

.stTable tbody td {
  padding: 0.85rem 1.1rem !important;
  border-bottom: 1px solid var(--bs-border-subtle) !important;
  font-size: 0.91rem !important;
  color: var(--bs-body-color) !important;
  transition: background-color 0.18s ease !important;
}

/* Hover Effect moderno en filas de la tabla */
.stTable tbody tr:hover,
.stTable tbody tr:hover td {
  background-color: var(--bs-teal-light) !important;
}

/* Data Table Component SaaS estilizada */
.saas-data-table-container {
  border: 1px solid var(--bs-border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  background: #FFFFFF;
  overflow: hidden;
  margin: 1.25rem 0;
}

.saas-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}

.saas-data-table th {
  background: #F8FAFC;
  color: var(--bs-secondary-color);
  font-weight: 750;
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 0.9rem 1.15rem;
  border-bottom: 2px solid var(--bs-border-color);
  text-align: left;
}

.saas-data-table td {
  padding: 0.9rem 1.15rem;
  border-bottom: 1px solid var(--bs-border-subtle);
  color: var(--bs-body-color);
  transition: background-color 0.15s ease;
}

.saas-data-table tr:last-child td {
  border-bottom: none;
}

.saas-data-table tbody tr:hover {
  background-color: var(--bs-teal-light);
}

/* ========================================================================== */
/* TARJETAS, MÉTRICAS KPI Y CONTENEDORES SAAS                                 */
/* ========================================================================== */
.card, [data-testid="stMetric"] {
  background: #FFFFFF;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: all 0.25s var(--ease-spring);
}

.card {
  padding: 1.5rem;
  height: 100%;
}

.card:hover, [data-testid="stMetric"]:hover {
  border-color: #CBD5E1;
  box-shadow: var(--shadow-hover);
  transform: translateY(-3px);
}

[data-testid="stMetric"] {
  padding: 1.25rem 1.5rem;
}

[data-testid="stMetricLabel"] {
  font-weight: 650;
  color: var(--bs-secondary-color) !important;
  font-size: 0.88rem !important;
  letter-spacing: 0.01em;
}

[data-testid="stMetricValue"] {
  color: var(--bs-primary-dark) !important;
  font-weight: 800 !important;
  letter-spacing: -0.025em;
  font-size: 2.1rem !important;
}

.kpi {
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--bs-primary-dark) !important;
  margin: 0.4rem 0;
  line-height: 1.15;
  letter-spacing: -0.025em;
}

/* Hero Banner SaaS */
.hero {
  background: linear-gradient(135deg, #FFFFFF 0%, #F0FDFA 55%, #F8FAFC 100%);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-left: 5px solid var(--bs-teal);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: 1.85rem 2.25rem;
  margin: 0 0 1.6rem;
  position: relative;
  overflow: hidden;
}

.hero .eyebrow {
  display: inline-flex;
  align-items: center;
  background: var(--bs-teal-light);
  color: var(--bs-teal-dark) !important;
  font-size: 0.74rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.3rem 0.75rem;
  border-radius: var(--radius-full);
  margin-bottom: 0.85rem;
  border: 1px solid var(--bs-teal-subtle);
}

.hero h1 {
  font-size: clamp(1.75rem, 2.6vw, 2.35rem);
  line-height: 1.22;
  margin: 0;
  font-weight: 800;
  color: var(--bs-primary-dark) !important;
  letter-spacing: -0.025em;
}

.hero p {
  color: var(--bs-secondary-color) !important;
  max-width: 62rem;
  margin: 0.65rem 0 0;
  line-height: 1.65;
  font-size: 0.98rem;
}

/* Expanders y Acordeones */
.stApp [data-testid="stExpander"] {
  background: #FFFFFF;
  border: 1px solid var(--bs-border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
  overflow: hidden;
  transition: all 0.22s var(--ease-smooth);
}

.stApp [data-testid="stExpander"]:hover {
  border-color: #CBD5E1;
  box-shadow: var(--shadow-sm);
}

.stApp [data-testid="stExpander"] summary {
  padding: 0.85rem 1.15rem !important;
  font-weight: 700 !important;
  color: var(--bs-primary-dark) !important;
}

/* Modales y Diálogos con Efecto Frosted Glass */
[data-testid="stModal"],
div[role="dialog"] {
  border-radius: var(--radius-xl) !important;
  box-shadow: var(--shadow-xl) !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  background: #FFFFFF !important;
}

/* Pestañas (Tabs) Estilo SaaS */
.stApp [data-baseweb="tab-list"] {
  gap: 0.5rem;
  border-bottom: 2px solid var(--bs-border-color);
  padding-bottom: 3px;
}

.stApp [data-baseweb="tab"] {
  font-weight: 650;
  font-size: 0.94rem;
  color: var(--bs-secondary-color);
  padding: 0.7rem 1.25rem;
  border-radius: 10px 10px 0 0;
  transition: all 0.2s var(--ease-smooth);
}

.stApp [data-baseweb="tab"]:hover {
  color: var(--bs-teal);
  background: rgba(13, 148, 136, 0.06);
}

.stApp [data-baseweb="tab"][aria-selected="true"] {
  color: var(--bs-teal-dark) !important;
  border-bottom: 2.5px solid var(--bs-teal) !important;
  font-weight: 750;
}

/* Badges y Puntos de Estado */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: #87621B !important;
  background: var(--bs-accent-light);
  border: 1px solid rgba(217, 119, 6, 0.28);
  padding: 0.28rem 0.65rem;
  font-size: 0.72rem;
  letter-spacing: 0.07em;
  font-weight: 750;
  border-radius: var(--radius-xs);
  text-transform: uppercase;
}

.badge-success {
  background-color: var(--bs-emerald-light);
  color: #047857 !important;
  border: 1px solid #A7F3D0;
}

.badge-warning {
  background-color: var(--bs-accent-light);
  color: #B45309 !important;
  border: 1px solid #FDE68A;
}

.badge-danger {
  background-color: var(--bs-danger-light);
  color: #B91C1C !important;
  border: 1px solid #FECACA;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background-color: #10B981;
  display: inline-block;
  animation: saasPulseDot 2.2s infinite ease-in-out;
  flex-shrink: 0;
}

/* User Badge Header */
.user-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #FFFFFF;
  border: 1px solid var(--bs-border-color);
  padding: 0.45rem 0.95rem;
  border-radius: var(--radius-full);
  font-size: 0.86rem;
  font-weight: 650;
  color: var(--bs-primary-dark);
  box-shadow: var(--shadow-xs);
}

/* Custom Scrollbars */
::-webkit-scrollbar {
  width: 7px;
  height: 7px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #CBD5E1;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94A3B8;
}

/* Card Header Icon Box */
.card-header-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background-color: var(--bs-teal-light);
  color: var(--bs-teal-dark);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.35rem;
  flex-shrink: 0;
  border: 1px solid var(--bs-teal-subtle);
  margin-bottom: 0.75rem;
}

/* Action Directive Callouts */
.action-directive-box {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  background-color: var(--bs-accent-light);
  border-left: 4px solid var(--bs-accent);
  border-radius: 12px;
  padding: 1.1rem 1.3rem;
  font-size: 0.92rem;
  color: var(--bs-body-color);
  box-shadow: var(--shadow-xs);
  margin: 0.85rem 0;
}

.action-directive-box strong {
  display: block;
  margin-bottom: 0.25rem;
  color: #87621B;
  font-size: 0.98rem;
}

.action-directive-box.teal {
  background-color: var(--bs-teal-light);
  border-left-color: var(--bs-teal);
}
.action-directive-box.teal strong {
  color: var(--bs-teal-dark);
}

/* Progress Bar Continuo */
.progress-bar-container {
  width: 100%;
  height: 8px;
  background-color: var(--bs-surface-alt);
  border-radius: 9999px;
  overflow: hidden;
  margin: 0.4rem 0;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--bs-teal) 0%, var(--bs-accent) 100%);
  border-radius: 9999px;
  transition: width 0.4s ease;
}

/* Alerts Callout con bordes acentuados */
div[data-testid="stAlert"] {
  border-left-width: 4px !important;
  border-left-style: solid !important;
  border-radius: var(--radius-md) !important;
}

div[data-testid="stAlert"]:has([data-testid="stAlertSuccessIcon"]) {
  border-left-color: #10B981 !important;
  background-color: #F0FDF4 !important;
}
div[data-testid="stAlert"]:has([data-testid="stAlertWarningIcon"]) {
  border-left-color: #F59E0B !important;
  background-color: #FFFBEB !important;
}
div[data-testid="stAlert"]:has([data-testid="stAlertErrorIcon"]) {
  border-left-color: #EF4444 !important;
  background-color: #FEF2F2 !important;
}
div[data-testid="stAlert"]:has([data-testid="stAlertInfoIcon"]) {
  border-left-color: var(--bs-teal) !important;
  background-color: #F0FDFA !important;
}

/* Responsive Mobile */
@media(max-width: 768px) {
  .block-container {
    padding-top: 0.85rem !important;
    padding-bottom: 3.5rem !important;
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
  }
  [data-testid="stSidebar"] {
    width: 86vw !important;
    max-width: 360px !important;
  }
  .hero {
    padding: 1.25rem 1.35rem !important;
  }
  .hero h1 {
    font-size: 1.5rem !important;
  }
  div.stButton > button,
  div.stDownloadButton > button,
  [data-testid="stFormSubmitButton"] button {
    width: 100% !important;
    min-height: 48px !important;
  }
}

/* Capa SaaS: superficies tranquilas, estados accesibles y movimiento discreto.
   No selecciona tablas oficiales HTML ni el formato vivo aislado en Shadow DOM. */
.stApp, [data-testid="stAppViewContainer"] {
  background-color:#f4f8fa;
  background-image:radial-gradient(ellipse at 6% 0%,rgba(56,139,143,.075),transparent 48%),
    radial-gradient(ellipse at 96% 24%,rgba(107,130,180,.06),transparent 48%);
}
[data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"] {
  border-radius:16px;
  box-shadow:0 2px 5px rgba(18,51,62,.025),0 14px 30px -22px rgba(18,51,62,.25);
}
.stApp button:not([disabled]),.stApp a[data-testid="stLinkButton"] {
  transition:background-color .22s ease,border-color .22s ease,box-shadow .22s ease,transform .12s ease;
}
.stApp div.stButton > button:active:not([disabled]),.stApp div.stDownloadButton > button:active:not([disabled]) {transform:scale(.98)}
.stApp button:disabled {opacity:.6;cursor:not-allowed;transform:none;box-shadow:none}
.stApp button[kind="primary"] p,.stApp button[kind="primaryFormSubmit"] p {color:#fff !important}
.st-key-padron_baja button[kind="primary"] {background:#9f2330 !important;border-color:#9f2330 !important;color:#fff !important}
.st-key-padron_baja button[kind="primary"]:hover:not([disabled]) {background:#801b26 !important;border-color:#801b26 !important}
.stApp button:focus-visible,.stApp input:focus-visible,.stApp select:focus-visible,
.stApp textarea:focus-visible,.stApp a:focus-visible {
  outline:3px solid #257d8e !important;outline-offset:3px;
}
[data-testid="stDataFrame"],[data-testid="stDataEditor"] {
  border:1px solid #d5e2e7;border-radius:14px;overflow:hidden;
  box-shadow:0 8px 24px -20px rgba(18,51,62,.3);
}
.usaer-table-wrap {overflow-x:auto;border:1px solid #d5e2e7;border-radius:16px;background:white;box-shadow:0 10px 28px -22px rgba(18,51,62,.3);margin:0 0 1rem}
.usaer-data-table {width:100%;border-collapse:collapse;font:14px/1.5 'Inter','Segoe UI',sans-serif;color:#1e333c}
.usaer-data-table th {background:#eef4f6;color:#12333e;font-weight:600;text-align:left;padding:13px 16px;white-space:nowrap}
.usaer-data-table td {padding:12px 16px;border-top:1px solid #edf2f4;transition:background-color .18s ease;vertical-align:top}
.usaer-data-table tbody tr:hover td {background:#edf6f7}
.usaer-table-wrap:focus-visible {outline:3px solid #257d8e;outline-offset:3px}
[data-testid="stDialog"] [role="dialog"] {
  border-radius:20px;box-shadow:0 20px 70px -24px rgba(18,51,62,.35);
  animation:usaer-enter .2s ease-out;
}
@keyframes usaer-enter {from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}

@media(prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition: none !important;
    animation: none !important;
  }
}
</style>
"""

def inject():
    st.markdown(CSS, unsafe_allow_html=True)

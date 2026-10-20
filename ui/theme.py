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
* {
  -webkit-tap-highlight-color: transparent !important;
}

button, a, input, select, textarea, [role="button"], [role="tab"] {
  touch-action: manipulation;
}

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
/* VISTA MINIMALISTA: SUPRESIÓN COMPLETA DE SIDEBAR                           */
/* ========================================================================== */
[data-testid="stSidebar"],
section[data-testid="stSidebar"],
[data-testid="collapsedControl"],
button[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarNav"] {
  display: none !important;
  visibility: hidden !important;
  width: 0 !important;
  height: 0 !important;
  max-width: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

[data-testid="stAppViewContainer"] > .main {
  margin-left: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
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

/* ========================================================================== */
/* SIDEBAR: MENÚ DE NAVEGACIÓN MODERNO (TABS LIMPIOS, CERO RADIO BUTTONS)     */
/* ========================================================================== */

/* Eliminación de Radio Buttons residuales */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label > div:first-child,
[data-testid="stSidebar"] input[type="radio"] {
  display: none !important;
}

/* Encabezados de Categoría (GENERAL, ANEXOS, ADMINISTRACIÓN) */
.nav-category-header {
  font-size: 0.72rem !important;
  font-weight: 750 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: #94A3B8 !important;
  -webkit-text-fill-color: #94A3B8 !important;
  margin-top: 1.2rem !important;
  margin-bottom: 0.45rem !important;
  padding-left: 0.5rem !important;
  padding-right: 0.5rem !important;
  display: flex !important;
  align-items: center !important;
}

.nav-category-header::after {
  content: "";
  flex: 1;
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin-left: 0.6rem;
}

/* Botones de Navegación del Menú Lateral (Pestañas / Tabs Táctiles 48px) */
[data-testid="stSidebar"] div.stButton > button {
  width: 100% !important;
  min-height: 48px !important; /* Zona de toque táctil mínima 48x48px */
  padding: 0.65rem 1rem !important;
  border-radius: 12px !important;
  margin-bottom: 5px !important;
  justify-content: flex-start !important;
  text-align: left !important;
  font-size: 0.92rem !important;
  font-weight: 550 !important;
  color: #CBD5E1 !important;
  -webkit-text-fill-color: #CBD5E1 !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  border-left: 4px solid transparent !important;
  box-shadow: none !important;
  gap: 0.75rem !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
  display: flex !important;
  align-items: center !important;
  touch-action: manipulation !important;
  -webkit-tap-highlight-color: transparent !important;
}

/* Hover en Escritorio */
[data-testid="stSidebar"] div.stButton > button:hover {
  background: rgba(255, 255, 255, 0.08) !important;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
  border-left: 4px solid rgba(255, 255, 255, 0.3) !important;
  transform: translateX(4px) !important;
}

/* Estado Activo / Seleccionado */
[data-testid="stSidebar"] div.stButton > button[kind="primary"],
[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
  background: linear-gradient(90deg, rgba(13, 148, 136, 0.35) 0%, rgba(15, 76, 92, 0.15) 100%) !important;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 750 !important;
  border-left: 4px solid #F59E0B !important; /* Línea de acento a la izquierda */
  border-top: 1px solid rgba(13, 148, 136, 0.35) !important;
  border-right: 1px solid rgba(13, 148, 136, 0.2) !important;
  border-bottom: 1px solid rgba(13, 148, 136, 0.35) !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.22), inset 0 0 10px rgba(13, 148, 136, 0.12) !important;
  transform: none !important;
}

/* Feedback táctil :active al tocar o presionar */
[data-testid="stSidebar"] div.stButton > button:active {
  transform: scale(0.96) !important;
  opacity: 0.95 !important;
}

/* Compatibilidad para stRadio estilizado como tabs si fuese necesario */
[data-testid="stSidebar"] .stRadio label {
  padding: 0.72rem 1rem !important;
  border-radius: 12px !important;
  margin-bottom: 5px !important;
  min-height: 48px !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
  color: #CBD5E1 !important;
  font-size: 0.92rem !important;
  font-weight: 550 !important;
  cursor: pointer !important;
  border: 1px solid transparent !important;
  border-left: 4px solid transparent !important;
  width: 100% !important;
  box-sizing: border-box !important;
  display: flex !important;
  align-items: center !important;
  touch-action: manipulation !important;
}

[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(255, 255, 255, 0.08) !important;
  color: #FFFFFF !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
  border-left: 4px solid rgba(255, 255, 255, 0.3) !important;
  transform: translateX(4px) !important;
}

[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: linear-gradient(90deg, rgba(13, 148, 136, 0.35) 0%, rgba(15, 76, 92, 0.15) 100%) !important;
  color: #FFFFFF !important;
  font-weight: 750 !important;
  border-left: 4px solid #F59E0B !important;
  border-top: 1px solid rgba(13, 148, 136, 0.35) !important;
  border-right: 1px solid rgba(13, 148, 136, 0.2) !important;
  border-bottom: 1px solid rgba(13, 148, 136, 0.35) !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.22), inset 0 0 10px rgba(13, 148, 136, 0.12) !important;
}

[data-testid="stSidebar"] .stRadio label:active {
  transform: scale(0.96) !important;
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

/* Base Universal para Todos los Botones (48px Touch Target) */
div.stButton > button,
div.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button,
div.stLinkButton > a {
  border-radius: var(--radius-md) !important;
  font-weight: 650 !important;
  font-size: 0.96rem !important;
  letter-spacing: 0.01em !important;
  min-height: 48px !important; /* WCAG AA: Área interactiva mínima 48x48px */
  padding: 0.72rem 1.35rem !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
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
  touch-action: manipulation !important;
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

/* Micro-interacción: Active (Escalado táctil scale(0.96) solicitado) */
div.stButton > button:active,
div.stDownloadButton > button:active,
[data-testid="stFormSubmitButton"] button:active,
div.stLinkButton > a:active {
  transform: scale(0.96) translateY(0) !important;
  opacity: 0.95 !important;
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

/* 1. Botones Primarios (Llamados a la Acción Fuertes SaaS - Alto Contraste WCAG AA) */
div.stButton > button[kind="primary"],
div.stDownloadButton > button[kind="primary"],
div.stButton > button[data-testid="baseButton-primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg, #0F4C5C 0%, #0D9488 100%) !important;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
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
  -webkit-text-fill-color: #FFFFFF !important;
}
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
.stApp [data-baseweb="select"] > div,
.stApp input {
  min-height: 48px !important; /* Zona táctil mínima 48x48px WCAG AA */
}

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
/* ========================================================================== */
/* CENTRO DE CONTROL CENTRAL (HUB / LAUNCHPAD)                               */
/* ========================================================================== */

.hub-hero {
  background: linear-gradient(135deg, rgba(15, 58, 74, 0.95) 0%, rgba(13, 148, 136, 0.88) 100%);
  border-radius: var(--radius-xl);
  padding: 2.2rem 2.4rem;
  color: #FFFFFF !important;
  margin-bottom: 1.75rem;
  box-shadow: 0 10px 30px -5px rgba(15, 58, 74, 0.25);
  position: relative;
  overflow: hidden;
}

.hub-hero::after {
  content: "◈";
  position: absolute;
  right: 1.5rem;
  bottom: -1rem;
  font-size: 8rem;
  color: rgba(255, 255, 255, 0.06);
  pointer-events: none;
}

.hub-hero-badge {
  display: inline-block;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 0.3rem 0.85rem;
  border-radius: var(--radius-full);
  font-size: 0.72rem;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #FFFFFF !important;
  margin-bottom: 0.75rem;
}

.hub-hero h1 {
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-size: 2.1rem !important;
  margin: 0 0 0.5rem 0 !important;
  font-weight: 800 !important;
}

.hub-hero p {
  color: #E2EFF2 !important;
  -webkit-text-fill-color: #E2EFF2 !important;
  font-size: 0.98rem !important;
  margin: 0 !important;
  max-width: 800px;
}

/* Tarjetas de Métricas Rápidas */
.hub-metric-card {
  background: #FFFFFF;
  border: 1.5px solid var(--bs-border-color);
  border-radius: var(--radius-lg);
  padding: 1.1rem 1.25rem;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  justify-content: center;
  margin-bottom: 1rem;
}

.hub-metric-card:hover {
  border-color: var(--bs-teal);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.hub-metric-num {
  font-size: 1.85rem;
  font-weight: 800;
  color: var(--bs-primary-dark);
  line-height: 1.1;
}

.hub-metric-label {
  font-size: 0.8rem;
  color: var(--bs-secondary-color);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 0.25rem;
}

/* Encabezados de Sección en el Hub */
.hub-section-title {
  font-size: 0.88rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--bs-primary-dark);
  margin-top: 1.5rem;
  margin-bottom: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding-bottom: 0.45rem;
  border-bottom: 1.5px solid var(--bs-border-color);
}

/* ========================================================================== */
/* DOCK INTERACTIVO DE ACCESOS RÁPIDOS (FLOATING HOVER DOCK)                  */
/* ========================================================================== */
.hub-dock-wrapper {
  display: flex;
  justify-content: center;
  margin: 0.75rem 0 1.5rem 0;
  width: 100%;
}

.hub-dock {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  padding: 0.6rem 1rem;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--bs-border-color);
  box-shadow: 0 8px 24px -4px rgba(15, 58, 74, 0.1), 0 2px 6px rgba(0,0,0,0.04);
  overflow-x: auto;
  max-width: 100%;
  scrollbar-width: none;
}
.hub-dock::-webkit-scrollbar { display: none; }

.hub-dock-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: var(--radius-lg);
  background: var(--bs-surface-alt);
  color: var(--bs-primary-dark);
  font-size: 1.45rem;
  cursor: pointer;
  transition: all 0.24s cubic-bezier(0.34, 1.56, 0.64, 1);
  text-decoration: none;
  border: 1.5px solid transparent;
  flex-shrink: 0;
}

.hub-dock-item:hover {
  transform: translateY(-8px) scale(1.18);
  background: #FFFFFF;
  border-color: var(--bs-teal);
  box-shadow: 0 10px 22px rgba(13, 148, 136, 0.28);
}

.hub-dock-item .dock-tooltip {
  position: absolute;
  bottom: -32px;
  background: var(--bs-primary-dark);
  color: #FFFFFF !important;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transform: translateY(4px);
  transition: all 0.18s ease;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  z-index: 50;
}

.hub-dock-item:hover .dock-tooltip {
  opacity: 1;
  transform: translateY(0);
}

/* ========================================================================== */
/* TARJETAS UNIFICADAS CON VISTA PREVIA FLOTANTE AL PASAR EL CURSOR           */
/* ========================================================================== */
.hub-tile {
  background: #FFFFFF;
  border: 1.5px solid var(--bs-border-color);
  border-radius: var(--radius-lg);
  padding: 1.25rem 1.3rem;
  box-shadow: var(--shadow-sm);
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  margin-bottom: 0.5rem;
}

div[class*="st-key-hub_card_"] {
  background: #FFFFFF !important;
  border: 1.5px solid var(--bs-border-color) !important;
  border-radius: var(--radius-lg) !important;
  padding: 1.25rem 1.3rem !important;
  box-shadow: var(--shadow-sm) !important;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: space-between !important;
  height: 100% !important;
  margin-bottom: 0.75rem !important;
}

div[class*="st-key-hub_card_"]:hover {
  border-color: var(--bs-teal) !important;
  box-shadow: 0 14px 28px -4px rgba(13, 148, 136, 0.18), 0 4px 10px -2px rgba(15, 23, 42, 0.05) !important;
  transform: translateY(-5px) !important;
}

/* Botón interno integrado perfectamente en la tarjeta */
div[class*="st-key-hub_card_"] button {
  margin-top: 0.9rem !important;
  border-radius: var(--radius-md) !important;
  font-weight: 750 !important;
  font-size: 0.9rem !important;
  background: var(--bs-surface-alt) !important;
  color: var(--bs-primary-dark) !important;
  border: 1px solid var(--bs-border-color) !important;
  transition: all 0.22s ease !important;
  min-height: 44px !important;
}

div[class*="st-key-hub_card_"]:hover button {
  background: linear-gradient(135deg, var(--bs-primary) 0%, var(--bs-teal) 100%) !important;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  border-color: transparent !important;
  box-shadow: 0 4px 16px rgba(13, 148, 136, 0.32) !important;
  transform: scale(1.01) !important;
}

.hub-tile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.hub-tile-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  box-shadow: var(--shadow-xs);
  transition: transform 0.2s ease;
}

div[class*="st-key-hub_card_"]:hover .hub-tile-icon {
  transform: scale(1.08) rotate(3deg);
}

.hub-tile-badge {
  font-size: 0.68rem;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0.22rem 0.6rem;
  background: var(--bs-surface-alt);
  color: var(--bs-secondary-color);
  border-radius: var(--radius-full);
}

.hub-tile-title {
  font-size: 1.05rem;
  font-weight: 750;
  color: var(--bs-primary-dark);
  margin-bottom: 0.35rem;
  line-height: 1.3;
}

.hub-tile-desc {
  font-size: 0.84rem;
  color: var(--bs-secondary-color);
  line-height: 1.45;
  flex: 1;
}

/* Vista previa de etiquetas flotantes (Hover Chips) */
.hub-preview-chips {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
  margin-top: 0.65rem;
  margin-bottom: 0.25rem;
}

.hub-chip {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.18rem 0.5rem;
  background: var(--bs-teal-light);
  color: var(--bs-teal-dark);
  border: 1px solid var(--bs-teal-subtle);
  border-radius: var(--radius-full);
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  transition: all 0.2s ease;
}

div[class*="st-key-hub_card_"]:hover .hub-chip {
  background: var(--bs-teal-subtle);
  border-color: var(--bs-teal);
  color: var(--bs-teal-dark);
}

/* Breadcrumb y Barra de Retorno en Módulos */
.module-breadcrumb {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.65rem 1.1rem;
  background: #FFFFFF;
  border: 1.5px solid var(--bs-border-color);
  border-radius: var(--radius-md);
  font-size: 0.88rem;
  color: var(--bs-secondary-color);
  box-shadow: var(--shadow-xs);
  margin-bottom: 1.25rem;
  min-height: 48px;
}

.module-breadcrumb strong {
  color: var(--bs-primary-dark);
}

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

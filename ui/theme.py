"""Identidad institucional, diseño contemporáneo para USAER 02-E."""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');

:root {
  --bs-primary: #1B4958;
  --bs-primary-dark: #12333E;
  --bs-primary-light: #2A6478;
  --bs-primary-subtle: #E8F2F5;
  --bs-accent: #C49339;
  --bs-accent-light: #FBF4E8;
  --bs-accent-hover: #AF7F2B;
  --bs-body-bg: #F8FAFB;
  --bs-surface: #FFFFFF;
  --bs-surface-alt: #F1F5F7;
  --bs-body-color: #1E333C;
  --bs-secondary-color: #5D727B;
  --bs-border-color: #E2E8EB;
  --bs-border-subtle: #EDF2F4;
  --bs-focus-ring: rgba(27, 73, 88, 0.18);
  --usaer-accent: #C49339;
  --shadow-xs: 0 1px 2px rgba(15, 34, 42, 0.04);
  --shadow-sm: 0 1px 3px rgba(15, 34, 42, 0.06), 0 1px 2px rgba(15, 34, 42, 0.04);
  --shadow-md: 0 4px 10px -2px rgba(15, 34, 42, 0.06), 0 2px 4px -2px rgba(15, 34, 42, 0.03);
  --shadow-lg: 0 12px 24px -4px rgba(15, 34, 42, 0.08), 0 4px 8px -4px rgba(15, 34, 42, 0.03);
  --shadow-hover: 0 8px 20px -3px rgba(15, 34, 42, 0.09), 0 3px 6px -2px rgba(15, 34, 42, 0.04);
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 18px;
}

/* Base and Typography */
html, body {
  font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.stApp, [data-testid="stAppViewContainer"] {
  background: var(--bs-body-bg);
  color: var(--bs-body-color);
  font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

.stApp, .stApp * {
  color-scheme: light;
}

.stApp p, .stApp label, .stApp li, [data-testid="stMarkdownContainer"] {
  color: var(--bs-body-color);
  font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

[data-testid="stCaptionContainer"] {
  color: var(--bs-secondary-color) !important;
  font-size: 0.83rem;
}

.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  letter-spacing: -0.025em;
  color: var(--bs-primary-dark);
  font-weight: 700;
}

.stApp h1 { font-size: 2.15rem; line-height: 1.22; margin-bottom: 0.6rem; }
.stApp h2 { font-size: 1.6rem; line-height: 1.28; margin-bottom: 0.5rem; }
.stApp h3 { font-size: 1.25rem; line-height: 1.35; margin-bottom: 0.4rem; }
.stApp h4 { font-size: 1.05rem; line-height: 1.4; margin-bottom: 0.35rem; }

.block-container {
  max-width: 1440px;
  padding-top: 1.75rem;
  padding-bottom: 4rem;
  padding-left: 2rem;
  padding-right: 2rem;
}

[data-testid="stHeader"] {
  background: rgba(248, 250, 251, 0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(226, 232, 235, 0.6);
}

/* Sidebar Dashboard Styling */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #13333F 0%, #0B222A 100%) !important;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

/* Sidebar Headings: High-Contrast White and Institutional Gold */
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
  color: #E7C37A !important;
  -webkit-text-fill-color: #E7C37A !important;
  font-size: 0.95rem !important;
  font-weight: 750 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
  margin-top: 1.15rem !important;
  margin-bottom: 0.5rem !important;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

/* Sidebar General Text, Labels, and Captions */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span:not(.badge):not(.status-dot),
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:not([data-testid="stExpander"] *) {
  color: #E2EFF2 !important;
  -webkit-text-fill-color: #E2EFF2 !important;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] small {
  color: #CFE0E5 !important;
  -webkit-text-fill-color: #CFE0E5 !important;
  font-size: 0.84rem !important;
  line-height: 1.45 !important;
}

[data-testid="stSidebar"] a {
  color: #E7C37A !important;
  text-decoration: none;
}

[data-testid="stSidebar"] a:hover {
  color: #FFFFFF !important;
  text-decoration: underline;
}

[data-testid="stSidebar"] hr,
[data-testid="stSidebar"] [data-testid="stDivider"] {
  border-color: rgba(255, 255, 255, 0.12) !important;
  margin: 1.1rem 0 !important;
}

/* Sidebar User Session Pill */
.sidebar-user-pill {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.7rem 0.9rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  margin-bottom: 1.15rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
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
  color: #A3C0C9 !important;
  -webkit-text-fill-color: #A3C0C9 !important;
  font-weight: 700;
  line-height: 1.2;
}

.sidebar-user-name {
  font-size: 0.88rem;
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
  font-weight: 700;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}


/* Sidebar Brand Block */
.brand {
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  backdrop-filter: blur(4px);
}

.brand h1 {
  font-size: 1.5rem;
  letter-spacing: -0.01em;
  color: #FFFFFF !important;
  margin: 0;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.brand p {
  font-size: 0.82rem;
  line-height: 1.5;
  margin: 0.5rem 0 0;
  color: #ADC4CC !important;
}

.brand .brand-overline {
  display: inline-block;
  background: rgba(196, 147, 57, 0.22);
  color: #E7C37A !important;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 0.45rem;
  border: 1px solid rgba(196, 147, 57, 0.35);
}

/* Navigation items in sidebar */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] {
  gap: 4px;
}

/* Modernize native radio into clean sidebar menu pills */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label > div:first-child {
  display: none !important;
}

[data-testid="stSidebar"] .stRadio label {
  padding: 0.65rem 0.95rem !important;
  border-radius: 9px !important;
  margin-bottom: 3px !important;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  color: #CFE0E5 !important;
  font-size: 0.89rem !important;
  font-weight: 500 !important;
  cursor: pointer;
  border: 1px solid transparent;
  width: 100%;
  box-sizing: border-box;
}

[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(255, 255, 255, 0.08) !important;
  color: #FFFFFF !important;
  border-color: rgba(255, 255, 255, 0.1);
  transform: translateX(3px);
}

[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: linear-gradient(90deg, rgba(27, 73, 88, 0.95) 0%, rgba(27, 73, 88, 0.55) 100%) !important;
  color: #FFFFFF !important;
  font-weight: 600 !important;
  border-color: rgba(196, 147, 57, 0.5) !important;
  box-shadow: inset 3px 0 0 #C49339, 0 2px 6px rgba(0, 0, 0, 0.15);
}

[data-testid="stSidebar"] button[kind="headerNoPadding"] {
  color: white !important;
}

/* Hero Section */
.hero {
  background: linear-gradient(135deg, #FFFFFF 0%, #F5FAFB 100%);
  border: 1px solid var(--bs-border-color);
  border-left: 4px solid var(--bs-primary);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  padding: 1.75rem 2.2rem;
  margin: 0 0 1.5rem;
  position: relative;
  overflow: hidden;
}

.hero .eyebrow {
  display: inline-flex;
  align-items: center;
  background: var(--bs-primary-subtle);
  color: var(--bs-primary) !important;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.25rem 0.7rem;
  border-radius: 20px;
  margin-bottom: 0.75rem;
  border: 1px solid rgba(27, 73, 88, 0.12);
}

.hero h1 {
  font-size: clamp(1.65rem, 2.5vw, 2.25rem);
  line-height: 1.25;
  margin: 0;
  font-weight: 750;
  color: var(--bs-primary-dark) !important;
  letter-spacing: -0.025em;
}

.hero p {
  color: var(--bs-secondary-color) !important;
  max-width: 60rem;
  margin: 0.6rem 0 0;
  line-height: 1.6;
  font-size: 0.96rem;
}

/* Modern Cards and Metrics */
.card, [data-testid="stMetric"] {
  background: #FFFFFF;
  border: 1px solid var(--bs-border-color);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.card {
  padding: 1.4rem;
  height: 100%;
}

.card:hover, [data-testid="stMetric"]:hover {
  border-color: #D1DDE2;
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

[data-testid="stMetric"] {
  padding: 1.15rem 1.4rem;
}

[data-testid="stMetricLabel"] {
  font-weight: 600;
  color: var(--bs-secondary-color) !important;
  font-size: 0.88rem !important;
}

[data-testid="stMetricValue"] {
  color: var(--bs-primary-dark) !important;
  font-weight: 750 !important;
  letter-spacing: -0.02em;
}

.kpi {
  font-size: 2.15rem;
  font-weight: 750;
  color: var(--bs-primary-dark) !important;
  margin: 0.35rem 0;
  line-height: 1.2;
  overflow-wrap: anywhere;
  letter-spacing: -0.02em;
}

.stApp [data-testid="stMarkdownContainer"] .kpi {
  font-size: 2.15rem;
  line-height: 1.2;
}

.muted {
  color: var(--bs-secondary-color) !important;
  font-size: 0.88rem;
  line-height: 1.5;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: #87621B !important;
  background: var(--bs-accent-light);
  border: 1px solid rgba(196, 147, 57, 0.28);
  padding: 0.22rem 0.55rem;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  font-weight: 700;
  border-radius: 6px;
  text-transform: uppercase;
}

.badge-primary {
  background-color: var(--bs-primary-subtle);
  color: var(--bs-primary) !important;
  border: 1px solid rgba(27, 73, 88, 0.16);
}

.badge-neutral {
  background-color: var(--bs-surface-alt);
  color: var(--bs-secondary-color) !important;
  border: 1px solid var(--bs-border-color);
}

.badge-success {
  background-color: #ECFDF5;
  color: #047857 !important;
  border: 1px solid #A7F3D0;
}

.badge-warning {
  background-color: #FFFBEB;
  color: #B45309 !important;
  border: 1px solid #FDE68A;
}

.badge-danger {
  background-color: #FEF2F2;
  color: #B91C1C !important;
  border: 1px solid #FECACA;
}

.badge-accent {
  background-color: var(--bs-accent-light);
  color: #87621B !important;
  border: 1px solid rgba(196, 147, 57, 0.35);
}

/* Animated Live Status Dot */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #10B981;
  display: inline-block;
  animation: pulse-dot 2s infinite ease-in-out;
  flex-shrink: 0;
}

.status-dot.amber {
  background-color: #F59E0B;
}

.status-dot.red {
  background-color: #EF4444;
}

@keyframes pulse-dot {
  0% { transform: scale(0.95); opacity: 0.85; }
  50% { transform: scale(1.35); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.85; }
}

/* Card Header Icon Box (Inspirado en la Suite) */
.card-header-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background-color: var(--bs-primary-subtle);
  color: var(--bs-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.35rem;
  flex-shrink: 0;
  border: 1px solid rgba(27, 73, 88, 0.12);
  margin-bottom: 0.75rem;
}

.card-header-icon.gold {
  background-color: var(--bs-accent-light);
  color: #87621B;
  border-color: rgba(196, 147, 57, 0.28);
}

.card-header-icon.emerald {
  background-color: #ECFDF5;
  color: #047857;
  border-color: #A7F3D0;
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
  background-color: var(--bs-primary-subtle);
  border-left-color: var(--bs-primary);
}

.action-directive-box.teal strong {
  color: var(--bs-primary-dark);
}

.action-directive-box.emerald {
  background-color: #ECFDF5;
  border-left-color: #10B981;
}

.action-directive-box.emerald strong {
  color: #047857;
}

.action-directive-box.amber {
  background-color: #FFFBEB;
  border-left-color: #F59E0B;
}

.action-directive-box.amber strong {
  color: #B45309;
}

.action-directive-box .action-icon {
  font-size: 1.5rem;
  line-height: 1;
}

/* Continuous Progress Bar */
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
  background: linear-gradient(90deg, var(--bs-primary) 0%, var(--bs-accent) 100%);
  border-radius: 9999px;
  transition: width 0.4s ease;
}

.section-title {
  font-size: 1.22rem;
  font-weight: 700;
  color: var(--bs-primary-dark);
  margin: 1.2rem 0 0.7rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Forms, Inputs, Textareas, Selects */
.stApp [data-baseweb="input"] > div,
.stApp [data-baseweb="textarea"] > div,
.stApp [data-baseweb="select"] > div,
.stApp input,
.stApp textarea {
  background: #FFFFFF !important;
  color: var(--bs-body-color) !important;
  -webkit-text-fill-color: var(--bs-body-color) !important;
  border-color: #D1DCE0 !important;
  border-radius: 10px !important;
  opacity: 1 !important;
  box-shadow: var(--shadow-xs);
  transition: all 0.2s ease;
}

.stApp [data-baseweb="input"]:focus-within > div,
.stApp [data-baseweb="textarea"]:focus-within > div,
.stApp [data-baseweb="select"]:focus-within > div {
  border-color: var(--bs-primary) !important;
  box-shadow: 0 0 0 3px var(--bs-focus-ring) !important;
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
  color: #8A9CA3 !important;
  -webkit-text-fill-color: #8A9CA3 !important;
}

.stApp input:disabled,
.stApp textarea:disabled {
  background: #EEF3F5 !important;
  color: #798D94 !important;
  -webkit-text-fill-color: #798D94 !important;
  border-color: #DEE5E8 !important;
}

.stApp [data-baseweb="select"] svg {
  fill: var(--bs-primary) !important;
}

/* Buttons and Interactive Elements */
div.stButton > button,
div.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button {
  border: 1px solid #D1DCE0;
  background: #FFFFFF;
  color: var(--bs-primary-dark);
  border-radius: 10px;
  min-height: 44px;
  padding: 0.6rem 1.2rem;
  font-size: 0.92rem;
  font-weight: 600;
  font-family: inherit;
  box-shadow: var(--shadow-xs);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

div.stButton > button p,
div.stDownloadButton > button p,
[data-testid="stFormSubmitButton"] button p {
  color: inherit !important;
  font-weight: inherit !important;
}

.stApp [data-testid="stSidebar"] button [data-testid="stMarkdownContainer"],
.stApp [data-testid="stSidebar"] button p,
.stApp button [data-testid="stMarkdownContainer"],
.stApp button [data-testid="stMarkdownContainer"] p {
  color: inherit !important;
}

div.stButton > button:hover,
div.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
  background: #F4F8FA;
  border-color: #BAC7CB;
  color: var(--bs-primary-dark);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

div.stButton > button:active,
div.stDownloadButton > button:active,
[data-testid="stFormSubmitButton"] button:active {
  transform: translateY(0);
}

/* Primary Buttons */
div.stButton > button[kind="primary"],
div.stDownloadButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg, #1B4958 0%, #12333E 100%) !important;
  color: #FFFFFF !important;
  border: 1px solid #1B4958 !important;
  box-shadow: 0 2px 5px rgba(27, 73, 88, 0.2);
}

div.stButton > button[kind="primary"]:hover,
div.stDownloadButton > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover {
  background: linear-gradient(135deg, #245A6D 0%, #173E4B 100%) !important;
  border-color: #245A6D !important;
  box-shadow: 0 4px 10px rgba(27, 73, 88, 0.28);
  transform: translateY(-1px);
  color: #FFFFFF !important;
}

.stApp button:focus-visible,
.stApp input:focus-visible,
.stApp textarea:focus-visible {
  outline: 3px solid var(--bs-accent) !important;
  outline-offset: 2px;
}

.stApp a {
  color: var(--bs-primary);
  text-underline-offset: 3px;
  font-weight: 500;
  transition: color 0.15s ease;
}

.stApp a:hover {
  color: var(--bs-primary-dark);
}

/* Alerts, DataFrames, Forms, Tabs */
.stApp [data-testid="stAlert"] {
  border-radius: 12px;
  box-shadow: var(--shadow-xs);
  border: 1px solid rgba(0, 0, 0, 0.06);
  padding: 0.9rem 1.15rem;
}

.stApp [data-testid="stDataFrame"] {
  border: 1px solid var(--bs-border-color);
  border-radius: 12px;
  box-shadow: var(--shadow-xs);
  overflow: hidden;
  background: #FFFFFF;
}

.stApp [data-testid="stExpander"] {
  background: #FFFFFF;
  border: 1px solid var(--bs-border-color);
  border-radius: 12px;
  box-shadow: var(--shadow-xs);
  overflow: hidden;
  transition: border-color 0.2s ease;
}

.stApp [data-testid="stExpander"]:hover {
  border-color: #CBD7DC;
}

/* Sidebar Expanders: High Contrast White Container with Dark Legible Text */
[data-testid="stSidebar"] [data-testid="stExpander"] {
  background: #FFFFFF !important;
  border: 1px solid rgba(255, 255, 255, 0.25) !important;
  border-radius: 12px !important;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.14) !important;
  margin: 0.5rem 0 !important;
  overflow: hidden !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] summary {
  padding: 0.75rem 1rem !important;
  border-radius: 12px !important;
  background: #FFFFFF !important;
  cursor: pointer !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
  background: #F4F8FA !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary *,
[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary span,
[data-testid="stSidebar"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p {
  color: #12333E !important;
  -webkit-text-fill-color: #12333E !important;
  font-weight: 700 !important;
  font-size: 0.92rem !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
  fill: #1B4958 !important;
  stroke: #1B4958 !important;
  color: #1B4958 !important;
  width: 1.15rem !important;
  height: 1.15rem !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"],
[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] * {
  color: #1E333C !important;
  -webkit-text-fill-color: #1E333C !important;
  font-size: 0.89rem !important;
  line-height: 1.5 !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] strong {
  color: #12333E !important;
  -webkit-text-fill-color: #12333E !important;
  font-weight: 750 !important;
}

/* Sidebar Buttons & Triggers: Crisp White Cards with High-Contrast Dark Teal Text */
[data-testid="stSidebar"] div.stButton > button,
[data-testid="stSidebar"] div.stDownloadButton > button,
[data-testid="stSidebar"] div.stLinkButton > a,
[data-testid="stSidebar"] [data-testid="stPopover"] > button {
  background: #FFFFFF !important;
  color: #12333E !important;
  -webkit-text-fill-color: #12333E !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  font-weight: 700 !important;
  font-size: 0.92rem !important;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.14) !important;
  border-radius: 10px !important;
  min-height: 44px !important;
  transition: all 0.2s ease !important;
  width: 100% !important;
}

[data-testid="stSidebar"] div.stButton > button:hover,
[data-testid="stSidebar"] div.stDownloadButton > button:hover,
[data-testid="stSidebar"] div.stLinkButton > a:hover,
[data-testid="stSidebar"] [data-testid="stPopover"] > button:hover {
  background: #F4F8FA !important;
  color: #1B4958 !important;
  -webkit-text-fill-color: #1B4958 !important;
  border-color: #FFFFFF !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.22) !important;
}

[data-testid="stSidebar"] div.stButton > button p,
[data-testid="stSidebar"] div.stDownloadButton > button p,
[data-testid="stSidebar"] div.stLinkButton > a p,
[data-testid="stSidebar"] [data-testid="stPopover"] > button p {
  color: #12333E !important;
  -webkit-text-fill-color: #12333E !important;
  font-weight: 700 !important;
}

/* Popover Content */
[data-baseweb="popover"] {
  background: #FFFFFF !important;
  border: 1px solid var(--bs-border-color) !important;
  box-shadow: var(--shadow-lg) !important;
  border-radius: 14px !important;
  padding: 0.85rem !important;
}

[data-baseweb="popover"] *,
[data-baseweb="popover"] p,
[data-baseweb="popover"] li,
[data-baseweb="popover"] [data-testid="stMarkdownContainer"] * {
  color: #1E333C !important;
  -webkit-text-fill-color: #1E333C !important;
  font-size: 0.9rem !important;
}

[data-baseweb="popover"] strong {
  color: #12333E !important;
  -webkit-text-fill-color: #12333E !important;
  font-weight: 750 !important;
}

[data-baseweb="popover"] [data-testid="stCaptionContainer"] p {
  color: #5D727B !important;
  -webkit-text-fill-color: #5D727B !important;
}


.stApp [data-baseweb="tab-list"] {
  gap: 0.5rem;
  border-bottom: 2px solid var(--bs-border-color);
  padding-bottom: 2px;
}

.stApp [data-baseweb="tab"] {
  font-weight: 600;
  font-size: 0.93rem;
  color: var(--bs-secondary-color);
  padding: 0.65rem 1.1rem;
  border-radius: 8px 8px 0 0;
  transition: all 0.2s ease;
}

.stApp [data-baseweb="tab"]:hover {
  color: var(--bs-primary);
  background: rgba(27, 73, 88, 0.04);
}

.stApp [data-baseweb="tab"][aria-selected="true"] {
  color: var(--bs-primary) !important;
  border-bottom: 2px solid var(--bs-primary) !important;
  font-weight: 700;
}

.stApp [data-testid="stForm"] {
  background: #FFFFFF;
  border: 1px solid var(--bs-border-color);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  padding: 1.6rem;
}

.stApp [data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, var(--bs-primary) 0%, var(--bs-accent) 100%);
  border-radius: 4px;
}

/* Institutional Login Page Card */
.st-key-institutional_login {
  max-width: 520px;
  margin: 3.5rem auto 2rem;
  padding: 2.2rem 2.4rem;
  background: #FFFFFF;
  border: 1px solid var(--bs-border-color);
  border-radius: 18px;
  box-shadow: var(--shadow-lg);
  position: relative;
}

.st-key-institutional_login::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--bs-primary) 0%, var(--bs-accent) 100%);
  border-radius: 18px 18px 0 0;
}

.institution-footnote {
  border-top: 1px solid var(--bs-border-color);
  padding-top: 1.1rem;
  margin-top: 2rem;
  color: var(--bs-secondary-color) !important;
  font-size: 0.8rem;
  line-height: 1.5;
}

/* Top user bar styling */
.topbar-user {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 0.35rem 0.5rem;
}

.user-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  background: #FFFFFF;
  border: 1px solid var(--bs-border-color);
  padding: 0.4rem 0.85rem;
  border-radius: 20px;
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--bs-primary-dark);
  box-shadow: var(--shadow-xs);
}

.user-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10B981;
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

/* Form Controls & Checkboxes */
.stApp [data-baseweb="checkbox"] input:checked + div {
  background-color: var(--bs-primary) !important;
  border-color: var(--bs-primary) !important;
}

.stApp [data-baseweb="radio"] input:checked + div {
  border-color: var(--bs-primary) !important;
}

.stApp [data-baseweb="radio"] input:checked + div > div {
  background-color: var(--bs-primary) !important;
}

/* Popover & Dropdowns */
[data-baseweb="popover"] {
  border-radius: 12px !important;
  box-shadow: var(--shadow-lg) !important;
}

[data-baseweb="menu"] {
  border-radius: 10px !important;
  padding: 4px !important;
}

.card h4 {
  margin: 0.5rem 0 0.25rem;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--bs-primary-dark);
}

/* Alert Callouts with Accent Borders */
div[data-testid="stAlert"] {
  border-left-width: 4px !important;
  border-left-style: solid !important;
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
  border-left-color: var(--bs-primary) !important;
  background-color: #F0F6F8 !important;
}

/* Multiselect Tags */
[data-baseweb="tag"] {
  background: var(--bs-primary-subtle) !important;
  color: var(--bs-primary-dark) !important;
  border-radius: 6px !important;
  font-weight: 600 !important;
  border: 1px solid rgba(27, 73, 88, 0.16) !important;
}

[data-baseweb="tag"] span {
  color: var(--bs-primary-dark) !important;
}

/* File Uploader Modern Box */
[data-testid="stFileUploader"] section {
  border: 2px dashed #CBD7DC !important;
  border-radius: 14px !important;
  background: #FAFDFE !important;
  padding: 1.3rem !important;
  transition: all 0.2s ease;
}

[data-testid="stFileUploader"] section:hover {
  border-color: var(--bs-primary) !important;
  background: #F1F7F9 !important;
}

/* Micro-transitions */
.card, [data-testid="stMetric"], div.stButton > button {
  will-change: transform, box-shadow;
}

/* Responsive Mobile & Tablet Rules */
@media(max-width: 768px) {
  /* Prevent horizontal overflow & set comfortable mobile gutters */
  .block-container {
    padding-top: 0.85rem !important;
    padding-bottom: 3.5rem !important;
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
    max-width: 100vw !important;
  }

  /* Mobile Hamburger Menu button */
  [data-testid="collapsedControl"] {
    background: #FFFFFF !important;
    border: 1px solid #D1DCE0 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 8px rgba(15, 34, 42, 0.12) !important;
    color: #1B4958 !important;
    top: 0.5rem !important;
    left: 0.5rem !important;
    z-index: 99999 !important;
    padding: 6px !important;
  }
  [data-testid="collapsedControl"] svg {
    fill: #1B4958 !important;
    stroke: #1B4958 !important;
  }

  /* Sidebar responsive width on mobile */
  [data-testid="stSidebar"] {
    width: 86vw !important;
    max-width: 360px !important;
  }

  /* Header and User Bar on Mobile */
  .topbar-user {
    justify-content: space-between !important;
    flex-wrap: wrap !important;
    gap: 0.5rem !important;
    padding: 0.25rem 0 !important;
    margin-bottom: 0.75rem !important;
  }

  .user-badge {
    font-size: 0.8rem !important;
    padding: 0.35rem 0.7rem !important;
  }

  /* Hero Banner on Phones */
  .hero {
    padding: 1.15rem 1.25rem !important;
    margin-bottom: 1.15rem !important;
    border-radius: 12px !important;
  }
  .hero h1 {
    font-size: 1.45rem !important;
    line-height: 1.25 !important;
  }
  .hero p {
    font-size: 0.88rem !important;
    line-height: 1.45 !important;
  }

  /* Typography scale on mobile */
  .stApp h1 { font-size: 1.6rem !important; }
  .stApp h2 { font-size: 1.35rem !important; }
  .stApp h3 { font-size: 1.15rem !important; }
  .stApp h4 { font-size: 1.0rem !important; }

  /* Columns stack gracefully on mobile */
  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 0.75rem !important;
  }
  [data-testid="stHorizontalBlock"] > [data-testid="column"],
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 100% !important;
    min-width: 100% !important;
  }

  /* KPI Cards compact on mobile */
  .card {
    padding: 1.1rem 1.15rem !important;
    border-radius: 12px !important;
  }
  .kpi, .stApp [data-testid="stMarkdownContainer"] .kpi {
    font-size: 1.75rem !important;
  }
  [data-testid="stMetric"] {
    padding: 1rem 1.15rem !important;
  }

  /* Tabs with horizontal touch scroll without wrapping */
  [data-baseweb="tab-list"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
    padding-bottom: 4px !important;
    gap: 0.35rem !important;
  }
  [data-baseweb="tab-list"]::-webkit-scrollbar {
    display: none !important;
  }
  [data-baseweb="tab"] {
    white-space: nowrap !important;
    flex-shrink: 0 !important;
    padding: 0.55rem 0.9rem !important;
    font-size: 0.88rem !important;
  }

  /* Form inputs: min 16px font to prevent unwanted iOS Safari auto-zoom */
  .stApp input,
  .stApp textarea,
  .stApp select,
  .stApp [data-baseweb="input"] input,
  .stApp [data-baseweb="textarea"] textarea {
    font-size: 16px !important;
    min-height: 44px !important;
  }

  /* Touch-friendly buttons (Apple HIG minimum 44px) */
  div.stButton > button,
  div.stDownloadButton > button,
  [data-testid="stFormSubmitButton"] button,
  div.stLinkButton > a {
    width: 100% !important;
    min-height: 48px !important;
    font-size: 0.95rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
  }

  /* Dataframes & Tables responsive touch scroll */
  [data-testid="stDataFrame"], .stTable {
    max-width: 100% !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
  }

  /* Action Directive Callouts */
  .action-directive-box {
    padding: 0.9rem 1rem !important;
    font-size: 0.88rem !important;
    gap: 0.75rem !important;
    border-radius: 10px !important;
  }

  /* Institutional login card on mobile */
  .st-key-institutional_login {
    margin: 1.25rem auto 1.5rem !important;
    padding: 1.4rem 1.25rem !important;
    border-radius: 14px !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }
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

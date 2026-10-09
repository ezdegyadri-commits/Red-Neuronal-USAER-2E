"""
Script to apply USAER 02-E design tokens, aesthetics and branding
to the Psychological Assessment Suite (M-CHAT-R & USAER Protocol)
without altering any business logic, databases, or algorithms.
"""

import os
import re

PRUEBAS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Pruebas psicológicas"))
CSS_PATH = os.path.join(PRUEBAS_DIR, "static", "css", "style.css")
HTML_PATH = os.path.join(PRUEBAS_DIR, "templates", "index.html")
JS_PATH = os.path.join(PRUEBAS_DIR, "static", "js", "app.js")

def update_css():
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    # 1. Update Root Tokens
    root_old_pattern = r":root\s*\{[^}]*--hue-primary:[^}]*\}"
    root_new = """:root {
  /* ==========================================================================
     Identidad Institucional USAER 02-E (Zona 001 · Yucatán)
     ========================================================================== */
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

  /* App Theme Tokens */
  --bg-app: #F8FAFB;
  --bg-surface: #FFFFFF;
  --bg-surface-elevated: #FFFFFF;
  --bg-surface-subtle: #F1F5F7;
  --bg-card: #FFFFFF;
  --border-subtle: #E2E8EB;
  --border-focus: #1B4958;

  --text-main: #1E333C;
  --text-secondary: #5D727B;
  --text-muted: #8A9CA3;
  --text-inverse: #FFFFFF;

  --primary: #1B4958;
  --primary-hover: #12333E;
  --primary-light: #E8F2F5;
  --primary-border: #BAC7CB;
  --primary-subtle: #EDF4F6;

  --accent: #C49339;
  --accent-light: #FBF4E8;
  --accent-hover: #AF7F2B;
  --accent-border: rgba(196, 147, 57, 0.35);

  --teal: #1B4958;
  --teal-light: #E8F2F5;

  --success: #10B981;
  --success-light: #ECFDF5;
  --success-border: #A7F3D0;

  --warning: #F59E0B;
  --warning-light: #FFFBEB;
  --warning-border: #FDE68A;

  --danger: #EF4444;
  --danger-light: #FEF2F2;
  --danger-border: #FECACA;

  /* Elevations & Shadows identical to USAER 2E */
  --shadow-xs: 0 1px 2px rgba(15, 34, 42, 0.04);
  --shadow-sm: 0 1px 3px rgba(15, 34, 42, 0.06), 0 1px 2px rgba(15, 34, 42, 0.04);
  --shadow-md: 0 4px 10px -2px rgba(15, 34, 42, 0.06), 0 2px 4px -2px rgba(15, 34, 42, 0.03);
  --shadow-lg: 0 12px 24px -4px rgba(15, 34, 42, 0.08), 0 4px 8px -4px rgba(15, 34, 42, 0.03);
  --shadow-hover: 0 8px 20px -3px rgba(15, 34, 42, 0.09), 0 3px 6px -2px rgba(15, 34, 42, 0.04);

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 18px;
  --radius-full: 9999px;

  --transition-fast: 0.15s ease;
  --transition-normal: 0.22s cubic-bezier(0.4, 0, 0.2, 1);

  --font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}"""

    css = re.sub(root_old_pattern, root_new, css, flags=re.DOTALL)

    # 2. Update Dark Theme Tokens
    dark_old_pattern = r"body\.theme-dark\s*\{[^}]*--bg-app:[^}]*\}"
    dark_new = """body.theme-dark {
  /* Identidad Modo Oscuro basada en la Barra Lateral de USAER 02-E */
  --bg-app: #0B222A;
  --bg-surface: #13333F;
  --bg-surface-elevated: #1E414E;
  --bg-surface-subtle: #0F2A34;
  --bg-card: rgba(19, 51, 63, 0.95);
  --border-subtle: rgba(255, 255, 255, 0.1);
  --border-focus: #C49339;

  --text-main: #FFFFFF;
  --text-secondary: #CFE0E5;
  --text-muted: #ADC4CC;
  --text-inverse: #0B222A;

  --primary: #3A879E;
  --primary-hover: #529CB2;
  --primary-light: rgba(58, 135, 158, 0.22);
  --primary-border: rgba(58, 135, 158, 0.45);

  --accent: #E7C37A;
  --accent-light: rgba(196, 147, 57, 0.22);
  --accent-border: rgba(231, 195, 122, 0.35);

  --teal: #3A879E;
  --teal-light: rgba(58, 135, 158, 0.22);

  --success: #34D399;
  --success-light: rgba(52, 211, 153, 0.15);
  --success-border: #059669;

  --warning: #FBBF24;
  --warning-light: rgba(251, 191, 36, 0.15);
  --warning-border: #D97706;

  --danger: #F87171;
  --danger-light: rgba(248, 113, 113, 0.15);
  --danger-border: #DC2626;

  --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 10px -2px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 12px 24px -4px rgba(0, 0, 0, 0.6);
  --shadow-xl: 0 20px 30px -5px rgba(0, 0, 0, 0.7);
}"""
    css = re.sub(dark_old_pattern, dark_new, css, flags=re.DOTALL)

    # 3. Header Accent Stripe
    if ".app-header::before" not in css:
        header_needle = ".app-header {"
        header_replacement = """.app-header {
  position: relative;"""
        css = css.replace(header_needle, header_replacement, 1)

        css = css.replace(
            ".header-container {",
            """.app-header::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3.5px;
  background: linear-gradient(90deg, #1B4958 0%, #C49339 100%);
  z-index: 101;
}

.header-container {""",
            1
        )

    # 4. Brand Logo styling
    brand_logo_old = r"\.brand-logo\s*\{[^}]*\}"
    brand_logo_new = """.brand-logo {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #1B4958 0%, #12333E 100%);
  color: #C49339;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 8px rgba(27, 73, 88, 0.25);
  border: 1px solid rgba(196, 147, 57, 0.4);
  font-size: 1.35rem;
  font-weight: 800;
  flex-shrink: 0;
}

.brand-overline {
  display: inline-block;
  background: rgba(196, 147, 57, 0.16);
  color: #87621B;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 0.25rem;
  border: 1px solid rgba(196, 147, 57, 0.35);
}

body.theme-dark .brand-overline {
  background: rgba(196, 147, 57, 0.22);
  color: #E7C37A;
}"""
    css = re.sub(brand_logo_old, brand_logo_new, css, flags=re.DOTALL)

    # 5. Buttons Styling
    btn_primary_old = r"\.btn-primary\s*\{[^}]*\}\s*\.btn-primary:hover\s*\{[^}]*\}"
    btn_primary_new = """.btn-primary {
  background: linear-gradient(135deg, #1B4958 0%, #12333E 100%);
  color: #ffffff !important;
  border: 1px solid #1B4958;
  box-shadow: 0 2px 5px rgba(27, 73, 88, 0.2);
}

.btn-primary:hover {
  background: linear-gradient(135deg, #245A6D 0%, #173E4B 100%);
  border-color: #245A6D;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(27, 73, 88, 0.28);
  color: #ffffff !important;
}"""
    css = re.sub(btn_primary_old, btn_primary_new, css, flags=re.DOTALL)

    btn_secondary_old = r"\.btn-secondary\s*\{[^}]*\}\s*\.btn-secondary:hover\s*\{[^}]*\}"
    btn_secondary_new = """.btn-secondary {
  background: linear-gradient(135deg, #C49339 0%, #AF7F2B 100%);
  color: #ffffff !important;
  border: 1px solid #C49339;
  box-shadow: 0 2px 5px rgba(196, 147, 57, 0.2);
}

.btn-secondary:hover {
  background: linear-gradient(135deg, #D4A348 0%, #BE8C34 100%);
  border-color: #D4A348;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(196, 147, 57, 0.28);
}"""
    css = re.sub(btn_secondary_old, btn_secondary_new, css, flags=re.DOTALL)

    # 6. Instrument Switcher Button
    switch_old = r"\.btn-instrument-switch\.active\s*\{[^}]*\}"
    switch_new = """.btn-instrument-switch.active {
  border-color: var(--primary);
  background-color: var(--bg-surface);
  box-shadow: inset 3.5px 0 0 #C49339, 0 2px 8px rgba(27, 73, 88, 0.15);
}

.btn-instrument-switch.active strong {
  color: var(--primary);
}

body.theme-dark .btn-instrument-switch.active {
  border-color: var(--accent);
  box-shadow: inset 3.5px 0 0 var(--accent), 0 2px 8px rgba(0, 0, 0, 0.35);
}

body.theme-dark .btn-instrument-switch.active strong {
  color: var(--accent);
}"""
    css = re.sub(switch_old, switch_new, css, flags=re.DOTALL)

    # 7. Navigation Tabs
    nav_tab_old = r"\.nav-tab:hover\s*\{[^}]*\}\s*\.nav-tab\.active\s*\{[^}]*\}"
    nav_tab_new = """.nav-tab:hover {
  color: var(--primary);
  background-color: rgba(27, 73, 88, 0.04);
  border-top-left-radius: var(--radius-sm);
  border-top-right-radius: var(--radius-sm);
}

.nav-tab.active {
  color: var(--primary) !important;
  border-bottom: 2.5px solid var(--primary) !important;
  font-weight: 700;
}

body.theme-dark .nav-tab.active {
  color: var(--accent) !important;
  border-bottom-color: var(--accent) !important;
}"""
    css = re.sub(nav_tab_old, nav_tab_new, css, flags=re.DOTALL)

    # 8. Choice Buttons
    choice_old = r"\.btn-choice\.selected-si\s*\{[^}]*\}\s*\.btn-choice\.selected-no\s*\{[^}]*\}"
    choice_new = """.btn-choice.selected-si {
  background: linear-gradient(135deg, #1B4958 0%, #12333E 100%);
  border-color: #1B4958;
  color: #ffffff;
  box-shadow: 0 3px 8px rgba(27, 73, 88, 0.25);
}

.btn-choice.selected-no {
  background-color: #5D727B;
  border-color: #5D727B;
  color: #ffffff;
  box-shadow: 0 3px 8px rgba(93, 114, 123, 0.25);
}"""
    css = re.sub(choice_old, choice_new, css, flags=re.DOTALL)

    # 9. Question Cards Risk
    card_risk_old = r"\.question-card\.is-risk\s*\{[^}]*\}"
    card_risk_new = """.question-card.is-risk {
  border-left: 4px solid var(--accent);
  background-color: rgba(196, 147, 57, 0.035);
}"""
    css = re.sub(card_risk_old, card_risk_new, css, flags=re.DOTALL)

    # 10. Progress Bar
    css = css.replace(
        "background: linear-gradient(90deg, var(--teal), var(--primary));",
        "background: linear-gradient(90deg, #1B4958 0%, #C49339 100%);"
    )

    # 11. Report Header Banner
    banner_old = r"\.report-header-banner\s*\{[^}]*\}"
    banner_new = """.report-header-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #12333E 0%, #1B4958 100%);
  color: #ffffff;
  border-radius: var(--radius-lg);
  padding: 1.75rem 2rem;
  margin-bottom: 1.5rem;
  border-bottom: 4px solid #C49339;
  box-shadow: var(--shadow-md);
}"""
    css = re.sub(banner_old, banner_new, css, flags=re.DOTALL)

    # 12. Action Directive Box
    action_old = r"\.action-directive-box\s*\{[^}]*\}"
    action_new = """.action-directive-box {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  background-color: var(--accent-light);
  border-left: 4px solid var(--accent);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
  font-size: 0.9rem;
  color: var(--text-main);
}

.action-directive-box strong {
  display: block;
  margin-bottom: 0.2rem;
  color: #87621B;
}

body.theme-dark .action-directive-box {
  background-color: rgba(196, 147, 57, 0.12);
}

body.theme-dark .action-directive-box strong {
  color: #E7C37A;
}"""
    css = re.sub(action_old, action_new, css, flags=re.DOTALL)

    # 13. Replace lingering sky-blue colors
    css = css.replace("rgba(2, 132, 199, 0.28)", "rgba(27, 73, 88, 0.2)")
    css = css.replace("rgba(2, 132, 199, 0.35)", "rgba(27, 73, 88, 0.28)")
    css = css.replace("rgba(2, 132, 199, 0.25)", "rgba(27, 73, 88, 0.18)")
    css = css.replace("rgba(2, 132, 199, 0.15)", "rgba(27, 73, 88, 0.15)")
    css = css.replace("rgba(2, 132, 199, 0.2)", "rgba(27, 73, 88, 0.18)")
    css = css.replace("rgba(2, 132, 199, 0.08)", "rgba(27, 73, 88, 0.1)")

    with open(CSS_PATH, "w", encoding="utf-8") as f:
        f.write(css)
    print("CSS updated with USAER 02-E design system.")


def update_html():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Update Title and Meta
    html = re.sub(
        r"<title>.*?</title>",
        "<title>USAER 02-E | Suite Psicométrica y Psicopedagógica de Evaluación de TEA</title>",
        html
    )

    # 2. Update Header Brand Section
    brand_section_old = r'<div class="brand-section">.*?</div>\s*</div>\s*<div class="header-actions">'
    brand_section_new = '''<div class="brand-section">
                <div class="brand-logo" id="brand-logo-icon">◈</div>
                <div class="brand-titles">
                    <span class="brand-overline">Educación Especial · Zona 001 · Yucatán</span>
                    <h1 class="brand-title">USAER 02-E · Suite Psicométrica TEA</h1>
                    <div class="brand-badge-row">
                        <span class="badge badge-primary" id="header-active-tool-badge">M-CHAT-R/F™ & Protocolo USAER</span>
                        <span class="badge badge-neutral" id="header-age-range-badge">Atención Temprana y Escolar</span>
                        <span class="badge badge-success" id="server-status-pill">
                            <span class="status-dot"></span> Sincronizado
                        </span>
                    </div>
                </div>
            </div>

            <div class="header-actions">'''
    html = re.sub(brand_section_old, brand_section_new, html, flags=re.DOTALL)

    # 3. Report Header Banner Title & Subtitle
    html = html.replace(
        '<div class="clinic-logo" id="report-logo-icon">🧠</div>',
        '<div class="clinic-logo" id="report-logo-icon">◈</div>'
    )
    html = html.replace(
        '<p id="report-doc-subtitle">Cuestionario Revisado de Detección del Autismo en Niños Pequeños</p>',
        '<p id="report-doc-subtitle">USAER 02-E · Zona 001 · Educación Especial Yucatán</p>'
    )

    # 4. Evaluator Signature Subtitle
    html = html.replace(
        '<span class="sig-sub" id="sig-evaluator-sub">Psicología Clínica / Educación Especial USAER</span>',
        '<span class="sig-sub" id="sig-evaluator-sub">Área de Psicología / Educación Especial · USAER 02-E · Zona 001</span>'
    )

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML updated with USAER 02-E institutional branding.")


def update_js():
    with open(JS_PATH, "r", encoding="utf-8") as f:
        js = f.read()

    # Replace radar baseline color in app.js (M-CHAT radar)
    js = js.replace(
        'backgroundColor: "rgba(2, 132, 199, 0.08)",\n                            borderColor: "#0284c7",',
        'backgroundColor: "rgba(27, 73, 88, 0.12)",\n                            borderColor: "#1B4958",'
    )
    js = js.replace(
        'backgroundColor: "rgba(2, 132, 199, 0.08)",\r\n                            borderColor: "#0284c7",',
        'backgroundColor: "rgba(27, 73, 88, 0.12)",\r\n                            borderColor: "#1B4958",'
    )

    with open(JS_PATH, "w", encoding="utf-8") as f:
        f.write(js)
    print("JavaScript chart styling updated with USAER 02-E palette.")


def build_dist():
    import shutil
    dist_dir = os.path.join(PRUEBAS_DIR, "dist_public")
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)

    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(os.path.join(dist_dir, "static", "css"), exist_ok=True)
    os.makedirs(os.path.join(dist_dir, "static", "js"), exist_ok=True)

    shutil.copy(os.path.join(PRUEBAS_DIR, "static", "css", "style.css"), os.path.join(dist_dir, "static", "css", "style.css"))
    shutil.copy(os.path.join(PRUEBAS_DIR, "static", "js", "chart.min.js"), os.path.join(dist_dir, "static", "js", "chart.min.js"))
    shutil.copy(os.path.join(PRUEBAS_DIR, "static", "js", "app.js"), os.path.join(dist_dir, "static", "js", "app.js"))

    with open(os.path.join(PRUEBAS_DIR, "templates", "index.html"), "r", encoding="utf-8") as f:
        html_content = f.read()

    html_content = html_content.replace('href="/static/', 'href="./static/')
    html_content = html_content.replace('src="/static/', 'src="./static/')

    with open(os.path.join(dist_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Bundle dist_public prepared successfully!")


def update_usaer_platform():
    pages_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui", "pages.py"))
    with open(pages_path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    # 1. Update cards in inicio
    old_cards = """    c1,c2,c3,c4=st.columns(4)\r
    with c1: card("Alumnos visibles",len(df))\r
    with c2: card("Anexos 3",len(repo.anexo3()))\r
    with c3: card("Sugerencias",len(repo.anexo4()))\r
    with c4: card("Eventos",len(repo.anexo5()))"""

    new_cards = """    c1,c2,c3,c4=st.columns(4)\r
    with c1: card("Alumnos visibles",len(df), icon="👥", badge="Padrón")\r
    with c2: card("Anexos 3",len(repo.anexo3()), icon="📋", badge="BAP")\r
    with c3: card("Sugerencias",len(repo.anexo4()), icon="💡", badge="Anexo IV")\r
    with c4: card("Eventos",len(repo.anexo5()), icon="📌", badge="Anexo V")"""

    if old_cards in content:
        content = content.replace(old_cards, new_cards, 1)

    # 2. Update process route and add Suite TEA card
    old_route = """    for c,t in zip(cols,["1. Expediente","2. BAP","3. IA + revisión","4. Seguimiento","5. Evidencia"]):\r
        with c: st.markdown(f"<div class='card'><span class='badge'>PROCESO</span><h4>{t}</h4><div class='muted'>La información permanece conectada.</div></div>",unsafe_allow_html=True)"""

    new_route = """    for c,t,icon in zip(cols,["1. Expediente","2. BAP","3. IA + revisión","4. Seguimiento","5. Evidencia"], ["📁","📊","🧠","🩺","📝"]):\r
        with c: st.markdown(f"<div class='card'><div class='card-header-icon gold' style='width:36px;height:36px;font-size:1.1rem;margin-bottom:0.5rem;'>{icon}</div><span class='badge'>PROCESO</span><h4>{t}</h4><div class='muted'>La información permanece conectada.</div></div>",unsafe_allow_html=True)\r
    st.markdown("### Instrumentos Clínicos y Psicométricos")\r
    c_tea1, c_tea2 = st.columns([3.8, 1.2])\r
    with c_tea1:\r
        st.markdown(\r
            "<div class='card' style='padding:1.1rem 1.3rem;'>"\r
            "<span class='badge' style='margin-bottom:0.35rem;'>Área de Psicología y Educación Especial</span>"\r
            "<h4 style='margin:0 0 0.25rem 0;'>Suite Psicométrica TEA (M-CHAT-R/F™ & Protocolo USAER)</h4>"\r
            "<p class='muted' style='margin:0;font-size:0.88rem;'>Herramienta digital de cribado temprano y observación en edad escolar con baremación automática e informe oficial.</p>"\r
            "</div>",\r
            unsafe_allow_html=True,\r
        )\r
    with c_tea2:\r
        st.write("")\r
        st.link_button("Abrir Suite TEA ◈", "https://deeply-howler-8m5y7.ship.place/", type="primary", use_container_width=True)"""

    if old_route in content:
        content = content.replace(old_route, new_route, 1)

    # 3. Update expedientes metrics cards
    old_exp = """    c=st.columns(4)\r
    with c[0]: card("Expediente",exp["id_expediente"])\r
    with c[1]: card("Grado / grupo",f"{a.get('Grado','')} {a.get('Grupo','')}")\r
    with c[2]: card("Condición",a.get("Condicion_Discapacidad",""))\r
    with c[3]: card("Estatus",a.get("Estatus",""))"""

    new_exp = """    c=st.columns(4)\r
    with c[0]: card("Expediente",exp["id_expediente"], icon="🗂️", badge="ID")\r
    with c[1]: card("Grado / grupo",f"{a.get('Grado','')} {a.get('Grupo','')}", icon="🏫")\r
    with c[2]: card("Condición",a.get("Condicion_Discapacidad",""), icon="👤")\r
    with c[3]: card("Estatus",a.get("Estatus",""), icon="📌")"""

    if old_exp in content:
        content = content.replace(old_exp, new_exp, 1)

    with open(pages_path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

    print("USAER 2E pages.py updated cleanly with CRLF preservation!")


if __name__ == "__main__":
    update_usaer_platform()



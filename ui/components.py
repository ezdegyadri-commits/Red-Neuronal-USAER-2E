import streamlit as st
from html import escape
import pandas as pd


def hero(title, subtitle="", badge="USAER 02-E · Gestión educativa"):
    """Encabezado de página contemporáneo con jerarquía clara y etiqueta institucional."""
    eyebrow_html = f"<div class='eyebrow'>{escape(str(badge))}</div>" if badge else ""
    subtitle_html = f"<p>{escape(str(subtitle))}</p>" if subtitle else ""
    st.markdown(
        f"<div class='hero'>{eyebrow_html}<h1>{escape(str(title))}</h1>{subtitle_html}</div>",
        unsafe_allow_html=True,
    )


def card(title, value, caption="", badge="", icon=""):
    """Tarjeta de métrica o resumen con sombra suave, tipografía KPI, contenedor elevado e icono opcional."""
    icon_html = f"<div class='card-header-icon'>{escape(str(icon))}</div>" if icon else ""
    badge_html = f"<div style='margin-bottom:0.4rem'><span class='badge'>{escape(str(badge))}</span></div>" if badge else ""
    caption_html = f"<div class='muted'>{escape(str(caption))}</div>" if caption else ""
    st.markdown(
        f"<div class='card'>{icon_html}{badge_html}<div class='muted'>{escape(str(title))}</div><p class='kpi'>{escape(str(value))}</p>{caption_html}</div>",
        unsafe_allow_html=True,
    )


def directive_box(title, text, icon="💡", variant="gold"):
    """Caja de recomendación o directiva con borde de acento institucional."""
    variant_class = f" {escape(str(variant))}" if variant else ""
    st.markdown(
        f"<div class='action-directive-box{variant_class}'><div class='action-icon'>{escape(str(icon))}</div><div><strong>{escape(str(title))}</strong><p style='margin:0;font-size:0.9rem;line-height:1.5;'>{escape(str(text))}</p></div></div>",
        unsafe_allow_html=True,
    )


def status_badge(text, variant="success", pulse=False):
    """Badge de estado con soporte para punto pulsante en vivo."""
    dot_html = "<span class='status-dot'></span> " if pulse else ""
    return f"<span class='badge badge-{escape(str(variant))}'>{dot_html}{escape(str(text))}</span>"


def progress_bar(value, total, label=""):
    """Barra de progreso visual con degradado institucional continuo."""
    pct = min(100, max(0, int((value / total) * 100))) if total else 0
    label_html = f"<div style='display:flex;justify-content:space-between;font-size:0.82rem;font-weight:600;margin-bottom:0.25rem;'><span class='muted'>{escape(str(label))}</span><span style='color:var(--bs-primary);font-weight:700;'>{value}/{total} ({pct}%)</span></div>" if label else ""
    st.markdown(
        f"<div style='margin:0.5rem 0;'>{label_html}<div class='progress-bar-container'><div class='progress-bar-fill' style='width:{pct}%;'></div></div></div>",
        unsafe_allow_html=True,
    )


def data_table(df, title="", max_rows=15):
    """Data table moderna con bordes redondeados, encabezados de contraste y filas interactivas."""
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        st.info("No hay registros para mostrar en la tabla.")
        return
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
    
    header_html = "".join(f"<th>{escape(str(c))}</th>" for c in df.columns)
    rows_html = []
    for _, row in df.head(max_rows).iterrows():
        cells = "".join(f"<td>{escape(str(val))}</td>" for val in row.values)
        rows_html.append(f"<tr>{cells}</tr>")
    
    title_html = f"<div style='padding:0.85rem 1.15rem;border-bottom:1px solid #E2E8F0;font-weight:700;color:var(--bs-primary-dark);font-size:1.02rem;'>{escape(title)}</div>" if title else ""
    footer_html = f"<div style='padding:0.65rem 1.15rem;background:#F8FAFC;border-top:1px solid #E2E8F0;font-size:0.82rem;color:#64748B;'>Mostrando {min(len(df), max_rows)} de {len(df)} registros</div>" if len(df) > max_rows else ""
    
    table_markup = f"""
    <div class='saas-data-table-container'>
      {title_html}
      <div style='overflow-x:auto;'>
        <table class='saas-data-table'>
          <thead><tr>{header_html}</tr></thead>
          <tbody>{''.join(rows_html)}</tbody>
        </table>
      </div>
      {footer_html}
    </div>
    """
    st.markdown(table_markup, unsafe_allow_html=True)

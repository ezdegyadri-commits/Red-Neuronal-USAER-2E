import streamlit as st
from html import escape


def hero(title, subtitle="", badge="USAER 02-E · Gestión educativa"):
    """Encabezado de página contemporáneo con jerarquía clara y etiqueta institucional."""
    eyebrow_html = f"<div class='eyebrow'>{escape(str(badge))}</div>" if badge else ""
    subtitle_html = f"<p>{escape(str(subtitle))}</p>" if subtitle else ""
    st.markdown(
        f"<div class='hero'>{eyebrow_html}<h1>{escape(str(title))}</h1>{subtitle_html}</div>",
        unsafe_allow_html=True,
    )


def card(title, value, caption="", badge=""):
    """Tarjeta de métrica o resumen con sombra suave, tipografía KPI y contenedor elevado."""
    badge_html = f"<div style='margin-bottom:0.4rem'><span class='badge'>{escape(str(badge))}</span></div>" if badge else ""
    caption_html = f"<div class='muted'>{escape(str(caption))}</div>" if caption else ""
    st.markdown(
        f"<div class='card'>{badge_html}<div class='muted'>{escape(str(title))}</div><p class='kpi'>{escape(str(value))}</p>{caption_html}</div>",
        unsafe_allow_html=True,
    )

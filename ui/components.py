import streamlit as st
from html import escape


def hero(title, subtitle=""):
    st.markdown(f"<div class='hero'><div class='eyebrow'>USAER 02-E · Gestión educativa</div><h1>{escape(str(title))}</h1><p>{escape(str(subtitle))}</p></div>", unsafe_allow_html=True)


def card(title, value, caption=""):
    st.markdown(f"<div class='card'><div class='muted'>{escape(str(title))}</div><p class='kpi'>{escape(str(value))}</p><div class='muted'>{escape(str(caption))}</div></div>", unsafe_allow_html=True)

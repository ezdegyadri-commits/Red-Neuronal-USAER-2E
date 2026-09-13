import streamlit as st


def hero(title, subtitle=""):
    st.markdown(f"<div class='hero'><h1>{title}</h1><p>{subtitle}</p></div>", unsafe_allow_html=True)


def card(title, value, caption=""):
    st.markdown(f"<div class='card'><div class='muted'>{title}</div><p class='kpi'>{value}</p><div class='muted'>{caption}</div></div>", unsafe_allow_html=True)

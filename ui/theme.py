import streamlit as st


def inject():
    st.markdown("""
    <style>
    :root{--u-blue:#123B5D;--u-blue2:#1B5E86;--u-gold:#D8A72E;--u-cream:#F6F4EF;--u-ink:#183042;--u-muted:#667784;--u-line:#E1E7EB;}
    .stApp{background:linear-gradient(180deg,#F7F9FA 0%,#F4F6F5 100%);color:var(--u-ink)}
    [data-testid='stSidebar']{background:linear-gradient(180deg,#123B5D,#0D304A);}
    [data-testid='stSidebar'] *{color:#fff!important}
    .brand{padding:8px 0 18px}.brand h1{font-size:1.7rem;margin:0;color:white}.brand p{margin:3px 0 0;color:#DDEAF2;font-size:.85rem}
    .hero{background:linear-gradient(135deg,#123B5D,#1B5E86);padding:28px;border-radius:22px;color:#fff;box-shadow:0 14px 35px rgba(18,59,93,.18);margin-bottom:22px}
    .hero h1{margin:0;font-size:2.1rem}.hero p{margin:.5rem 0 0;color:#DDEAF2}
    .card{background:#fff;border:1px solid var(--u-line);border-radius:18px;padding:18px;box-shadow:0 6px 20px rgba(25,50,65,.06);height:100%}
    .kpi{font-size:1.9rem;font-weight:800;color:var(--u-blue);margin:0}.muted{color:var(--u-muted);font-size:.86rem}.badge{display:inline-block;padding:4px 9px;border-radius:999px;background:#EAF2F7;color:var(--u-blue);font-size:.75rem;font-weight:700}
    div.stButton>button{border-radius:11px;border:1px solid #D7E0E6;font-weight:600}
    div.stButton>button[kind='primary']{background:var(--u-blue);color:#fff;border-color:var(--u-blue)}
    [data-testid='stMetric']{background:#fff;border:1px solid var(--u-line);padding:14px;border-radius:16px}
    .section-title{font-size:1.2rem;font-weight:800;color:var(--u-blue);margin:12px 0}
    </style>
    """, unsafe_allow_html=True)

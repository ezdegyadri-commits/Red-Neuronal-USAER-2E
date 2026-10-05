"""Identidad institucional, sin fuentes externas ni acceso a datos."""
import streamlit as st

CSS = """
<style>
:root {
 --bs-primary:#254F60; --bs-primary-dark:#173B49; --bs-body-bg:#F6F5F1;
 --bs-surface:#FFFFFF; --bs-body-color:#243A43; --bs-secondary-color:#5B6C73;
 --bs-border-color:#D8DFDF; --usaer-accent:#A77C38; --bs-focus-ring:rgba(37,79,96,.24);
}
.stApp,[data-testid="stAppViewContainer"] {background:var(--bs-body-bg); color:var(--bs-body-color); font-family:"Segoe UI",system-ui,-apple-system,Arial,sans-serif;}
.stApp,.stApp * {color-scheme:light;}
.stApp p,.stApp label,.stApp li,[data-testid="stMarkdownContainer"] {color:var(--bs-body-color);}
[data-testid="stCaptionContainer"] {color:var(--bs-secondary-color);}
.stApp h1,.stApp h2,.stApp h3 {letter-spacing:-.025em; color:#173B49;}
.stApp h1 {font-size:2.25rem; font-weight:650;}
.stApp h2 {font-size:1.65rem; font-weight:650;}
.stApp h3 {font-size:1.2rem; font-weight:650;}
.block-container {max-width:1440px; padding-top:2.5rem; padding-bottom:4rem;}
[data-testid="stHeader"] {background:var(--bs-body-bg);}
[data-testid="stSidebar"] {background:#183B49; border-right:1px solid #294E5B;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] p,[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color:#E8EFF0;}
[data-testid="stSidebar"] a {color:#E8EFF0;}
[data-testid="stSidebar"] .stRadio label {padding:.48rem .6rem; border-radius:4px;}
[data-testid="stSidebar"] .stRadio label:hover {background:#294E5B;}
[data-testid="stSidebar"] .stRadio label:has(input:checked) {background:#315A69; box-shadow:inset 3px 0 #D8B979;}
[data-testid="stSidebar"] button[kind="headerNoPadding"] {color:white;}
.brand {padding:.7rem 0 1.5rem; margin-bottom:1rem; border-bottom:1px solid #45616B;}
.brand h1 {font-size:1.6rem; letter-spacing:.06em; color:#FFF; margin:0;}
.brand p {font-size:.83rem; line-height:1.6; margin:.6rem 0 0; color:#D5E2E6!important;}
.brand .brand-overline {color:#D8B979!important; font-size:.7rem; letter-spacing:.16em; text-transform:uppercase; margin:0 0 .6rem;}
.hero {background:#FFF; border:1px solid var(--bs-border-color); border-top:3px solid var(--usaer-accent); border-radius:5px; padding:1.8rem 2rem; margin:0 0 1.5rem;}
.hero .eyebrow {font-size:.72rem; letter-spacing:.16em; font-weight:650; text-transform:uppercase; color:#68777A; margin:0 0 .65rem;}
.hero h1 {font-size:clamp(1.65rem,2.8vw,2.35rem); line-height:1.2; margin:0; font-weight:650; color:#173B49!important;}
.hero p {color:#5B6C73!important; max-width:58rem; margin:.7rem 0 0; line-height:1.6;}
.card,[data-testid="stMetric"] {background:#FFF; border:1px solid var(--bs-border-color); border-radius:5px;}
.card {padding:1.3rem; height:100%;}
[data-testid="stMetric"] {padding:1rem 1.3rem;}
.kpi {font-size:2rem; font-weight:650; color:#173B49!important; margin:.3rem 0; line-height:1.25; overflow-wrap:anywhere;}
.stApp [data-testid="stMarkdownContainer"] .kpi {font-size:2rem; line-height:1.25;}
.muted {color:#5B6C73!important; font-size:.88rem; line-height:1.5;}
.badge {display:inline-block; color:#5E512F!important; background:#F3EFE5; padding:.22rem .5rem; font-size:.68rem; letter-spacing:.08em; font-weight:650; border-radius:3px;}
.section-title {font-size:1.2rem; font-weight:650; color:#173B49; margin:1rem 0 .6rem;}
.stApp [data-baseweb="input"] > div,.stApp [data-baseweb="textarea"] > div,
.stApp [data-baseweb="select"] > div,.stApp input,.stApp textarea {
 background:#FFF!important; color:#243A43!important; -webkit-text-fill-color:#243A43!important; border-color:#B4C1C4!important; opacity:1!important;
}
.stApp [data-baseweb="select"] *,.stApp [data-baseweb="input"] input,
.stApp [data-baseweb="textarea"] textarea {color:#243A43!important; -webkit-text-fill-color:#243A43!important;}
.stApp input::placeholder,.stApp textarea::placeholder {color:#63747A!important; -webkit-text-fill-color:#63747A!important;}
.stApp input:disabled,.stApp textarea:disabled {background:#ECEFED!important; color:#64747A!important;}
.stApp [data-baseweb="select"] svg {fill:#254F60!important;}
div.stButton > button,div.stDownloadButton > button,[data-testid="stFormSubmitButton"] button {
 border:1px solid #AABBBF; background:#FFF; color:#173B49; border-radius:5px; min-height:44px; padding:.55rem 1rem; font-size:.92rem; font-weight:600;
}
div.stButton > button p,div.stDownloadButton > button p,[data-testid="stFormSubmitButton"] button p {color:inherit!important;}
.stApp [data-testid="stSidebar"] button [data-testid="stMarkdownContainer"],
.stApp [data-testid="stSidebar"] button p,
.stApp button [data-testid="stMarkdownContainer"],.stApp button [data-testid="stMarkdownContainer"] p {color:inherit!important;}
div.stButton > button[kind="primary"],div.stDownloadButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] {background:#254F60!important; color:#FFF!important; border-color:#254F60!important;}
div.stButton > button:hover,div.stDownloadButton > button:hover,[data-testid="stFormSubmitButton"] button:hover {background:#EAF0F1; border-color:#254F60; color:#173B49;}
div.stButton > button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {background:#173B49!important;}
.stApp button:focus-visible,.stApp input:focus-visible,.stApp textarea:focus-visible {outline:3px solid #A77C38!important; outline-offset:2px;}
.stApp a {color:#254F60; text-underline-offset:3px;}
.stApp [data-testid="stAlert"] {border-radius:5px; box-shadow:none;}
.stApp [data-testid="stDataFrame"] {border:1px solid var(--bs-border-color); border-radius:5px; overflow:hidden;}
.stApp [data-testid="stExpander"] {background:#FFF; border-radius:5px;}
.stApp [data-baseweb="tab-list"] {gap:1.5rem; border-bottom:1px solid #D8DFDF;}
.stApp [data-baseweb="tab"] {font-weight:600;}
.stApp [data-testid="stForm"] {background:#FFF; border-color:#D8DFDF; border-radius:5px;}
.stApp [data-testid="stProgress"] > div > div {background:#254F60;}
.institution-footnote {border-top:1px solid #D8DFDF; padding-top:1rem; margin-top:2rem; color:#5B6C73!important; font-size:.78rem;}
.st-key-institutional_login {max-width:540px; margin:2rem auto;}
@media(max-width:768px) {
 .block-container {padding:1rem .85rem 3rem!important;}
 .hero {padding:1.25rem; margin-bottom:1rem;}
 .hero h1 {font-size:1.7rem;}
 [data-testid="stHorizontalBlock"] {flex-wrap:wrap!important; gap:.75rem!important;}
 [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {flex:1 1 100%!important; min-width:100%!important;}
 div.stButton > button,div.stDownloadButton > button {width:100%; min-height:48px;}
}
@media(prefers-reduced-motion:reduce) {*,*::before,*::after {transition:none!important; animation:none!important;}}
</style>
"""

def inject():
    st.markdown(CSS, unsafe_allow_html=True)

import streamlit as st


def inject():
    st.markdown("""
    <style>
    :root {
        --bs-primary: #0B5ED7;
        --bs-primary-dark: #084298;
        --bs-info: #0AA2C0;
        --bs-success: #198754;
        --bs-body-bg: #F4F7FB;
        --bs-surface: #FFFFFF;
        --bs-body-color: #1F2937;
        --bs-secondary-color: #52606D;
        --bs-border-color: #D9E2EC;
        --bs-focus-ring: rgba(13, 110, 253, .25);
    }

    .stApp, [data-testid="stAppViewContainer"] {
        background: var(--bs-body-bg);
        color: var(--bs-body-color);
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    }
    .stApp, .stApp * { color-scheme: light; }
    .stApp p, .stApp label, .stApp li,
    .stApp [data-testid="stMarkdownContainer"] {
        color: var(--bs-body-color);
    }
    .stApp [data-testid="stCaptionContainer"] {
        color: var(--bs-secondary-color);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #123B5D 0%, #082F49 100%);
        border-right: 1px solid rgba(255,255,255,.12);
    }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,.12);
        border-radius: .375rem;
    }
    .brand {
        padding: 1rem .25rem 1.25rem;
        border-bottom: 1px solid rgba(255,255,255,.16);
        margin-bottom: .75rem;
    }
    .brand h1 {
        font-size: 1.45rem;
        letter-spacing: .02em;
        margin: 0;
        color: #FFFFFF;
        font-weight: 750;
    }
    .brand p {
        color: #D9EAF7 !important;
        font-size: .88rem;
        margin: .35rem 0 0;
    }

    .hero {
        background: linear-gradient(135deg, #123B5D 0%, #0B5ED7 100%);
        border-radius: .75rem;
        color: #FFFFFF;
        padding: 1.75rem 2rem;
        margin: 0 0 1.5rem;
        box-shadow: 0 .5rem 1rem rgba(8, 47, 73, .15);
    }
    .hero h1 {
        color: #FFFFFF !important;
        font-size: clamp(1.5rem, 3vw, 2rem);
        line-height: 1.2;
        margin: 0;
        font-weight: 750;
    }
    .hero p {
        color: #E9F2FF !important;
        margin: .55rem 0 0;
        max-width: 52rem;
    }

    .card, [data-testid="stMetric"] {
        background: var(--bs-surface);
        border: 1px solid var(--bs-border-color);
        border-radius: .5rem;
        box-shadow: 0 .125rem .25rem rgba(31, 41, 55, .075);
    }
    .card { padding: 1.1rem; height: 100%; }
    .card * { color: var(--bs-body-color); }
    .kpi {
        color: var(--bs-primary-dark);
        font-size: 1.8rem;
        font-weight: 750;
        margin: 0;
    }
    .muted { color: var(--bs-secondary-color) !important; font-size: .92rem; }
    .badge {
        background: #DCEBFF;
        border-radius: 50rem;
        color: #084298 !important;
        display: inline-block;
        font-size: .75rem;
        font-weight: 700;
        padding: .3rem .55rem;
    }
    .section-title {
        color: #123B5D;
        font-size: 1.2rem;
        font-weight: 750;
        margin: 1rem 0 .65rem;
    }

    /* Campos legibles en Android, incluido cuando el teléfono está en modo oscuro. */
    .stApp [data-baseweb="input"] > div,
    .stApp [data-baseweb="textarea"] > div,
    .stApp [data-baseweb="select"] > div,
    .stApp [data-testid="stDateInput"] [data-baseweb="input"] > div,
    .stApp [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    .stApp input,
    .stApp textarea {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        border-color: #9FB3C8 !important;
        color: #1F2937 !important;
        -webkit-text-fill-color: #1F2937 !important;
        opacity: 1 !important;
    }
    .stApp [data-baseweb="select"] *,
    .stApp [data-baseweb="input"] input,
    .stApp [data-baseweb="textarea"] textarea,
    .stApp [data-testid="stDateInput"] input {
        color: #1F2937 !important;
        -webkit-text-fill-color: #1F2937 !important;
        opacity: 1 !important;
    }
    .stApp [data-baseweb="select"] svg,
    .stApp [data-testid="stDateInput"] svg {
        color: #1F2937 !important;
        fill: #1F2937 !important;
    }
    .stApp input::placeholder, .stApp textarea::placeholder {
        color: #52606D !important;
        -webkit-text-fill-color: #52606D !important;
        opacity: 1 !important;
    }

    div.stButton > button, div.stDownloadButton > button {
        background: #FFFFFF;
        border: 1px solid #0B5ED7;
        border-radius: .375rem;
        color: #0B5ED7;
        font-weight: 650;
        min-height: 42px;
        padding: .45rem .85rem;
    }
    div.stButton > button[kind="primary"],
    div.stDownloadButton > button[kind="primary"] {
        background: #0B5ED7 !important;
        border-color: #0B5ED7 !important;
        color: #FFFFFF !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background: #084298 !important;
        border-color: #084298 !important;
        color: #FFFFFF !important;
    }
    div.stButton > button:focus, div.stDownloadButton > button:focus {
        box-shadow: 0 0 0 .25rem var(--bs-focus-ring) !important;
    }
    .stApp a { color: #0B5ED7; font-weight: 600; }
    .stApp [data-testid="stDataFrame"] {
        border: 1px solid var(--bs-border-color);
        border-radius: .5rem;
        overflow: hidden;
    }

    @media (max-width: 768px) {
        .block-container { padding: 1rem .8rem 4rem !important; }
        .hero { border-radius: .65rem; padding: 1.35rem 1rem; margin-bottom: 1rem; }
        .hero h1 { font-size: 1.45rem; }
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: .75rem !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        div.stButton > button, div.stDownloadButton > button {
            font-size: 1rem;
            min-height: 48px;
            width: 100%;
        }
        .stApp label, .stApp p, .stApp li { font-size: 1rem; }
        [data-testid="stSidebar"] { min-width: 17rem; }
    }
    </style>
    """, unsafe_allow_html=True)

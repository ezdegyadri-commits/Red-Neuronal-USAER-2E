import streamlit as st


def inject():
    st.markdown("""
    <style>
    :root {
        --bs-primary: #087E8B;
        --bs-primary-dark: #07545D;
        --bs-info: #247BA0;
        --bs-success: #16866A;
        --bs-body-bg: #F3F7F8;
        --bs-surface: #FFFFFF;
        --bs-body-color: #18313A;
        --bs-secondary-color: #526A72;
        --bs-border-color: #D5E2E4;
        --bs-focus-ring: rgba(8, 126, 139, .28);
        --usaer-accent: #E7A83E;
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
        background: linear-gradient(118deg, #123B4A 0%, #087E8B 72%, #159E9A 100%);
        border: 1px solid rgba(255,255,255,.18);
        border-left: 6px solid var(--usaer-accent);
        border-radius: 1rem;
        color: #FFFFFF;
        padding: 1.8rem 2rem;
        margin: 0 0 1.5rem;
        box-shadow: 0 .75rem 1.7rem rgba(18, 59, 74, .16);
        animation: usaer-arrive .42s ease-out both;
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
        border-radius: .85rem;
        box-shadow: 0 .2rem .55rem rgba(24, 49, 58, .07);
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }
    .card { padding: 1.15rem; height: 100%; border-top: 3px solid #159E9A; }
    .card:hover, [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #9CCDCF;
        box-shadow: 0 .55rem 1.1rem rgba(24, 49, 58, .11);
    }
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
        border: 1px solid #087E8B;
        border-radius: .7rem;
        color: #07545D;
        font-size: 1rem;
        font-weight: 700;
        min-height: 50px;
        padding: .65rem 1.05rem;
        box-shadow: 0 .15rem .35rem rgba(18, 59, 74, .08);
        transition: transform .16s ease, box-shadow .16s ease, background-color .16s ease;
    }
    div.stButton > button[kind="primary"],
    div.stDownloadButton > button[kind="primary"] {
        background: #087E8B !important;
        border-color: #087E8B !important;
        color: #FFFFFF !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background: #07545D !important;
        border-color: #07545D !important;
        color: #FFFFFF !important;
        transform: translateY(-1px);
        box-shadow: 0 .35rem .75rem rgba(7, 84, 93, .2);
    }
    div.stButton > button:focus, div.stDownloadButton > button:focus {
        box-shadow: 0 0 0 .25rem var(--bs-focus-ring) !important;
    }
    .stApp a { color: #07545D; font-weight: 700; }
    .stApp [data-testid="stAlert"] {
        border-radius: .75rem;
        border-left-width: 5px;
        box-shadow: 0 .18rem .45rem rgba(24, 49, 58, .05);
        animation: usaer-arrive .24s ease-out both;
    }
    .stApp [data-testid="stSpinner"] p { color: #07545D; font-weight: 650; }
    .stApp [data-testid="stProgress"] > div > div {
        background: linear-gradient(90deg, #087E8B, #38B2AC, #E7A83E);
        background-size: 180% 100%;
        animation: usaer-progress 1.6s linear infinite;
    }
    @keyframes usaer-arrive {
        from { opacity: 0; transform: translateY(5px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes usaer-progress {
        from { background-position: 100% 0; }
        to { background-position: -80% 0; }
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: .01ms !important;
            animation-iteration-count: 1 !important;
            scroll-behavior: auto !important;
            transition-duration: .01ms !important;
        }
    }
    .stApp [data-testid="stDataFrame"] {
        border: 1px solid var(--bs-border-color);
        border-radius: .5rem;
        overflow: hidden;
    }

    @media (max-width: 768px) {
        .block-container { padding: 1rem .8rem 4rem !important; }
        .hero { border-radius: .8rem; padding: 1.35rem 1rem; margin-bottom: 1rem; }
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
            min-height: 54px;
            width: 100%;
        }
        .stApp label, .stApp p, .stApp li { font-size: 1rem; }
        [data-testid="stSidebar"] { min-width: 17rem; }
    }
    </style>
    """, unsafe_allow_html=True)

import streamlit as st


def inject():
    st.markdown("""
    <style>
    :root {
        --u-blue: #0B3A5B;
        --u-blue2: #075985;
        --u-gold: #9A6700;
        --u-bg: #F5F7FA;
        --u-surface: #FFFFFF;
        --u-ink: #102A43;
        --u-muted: #486581;
        --u-line: #BCCCDC;
        --u-focus: #005FCC;
    }

    .stApp, [data-testid="stAppViewContainer"] {
        background: var(--u-bg);
        color: var(--u-ink);
    }
    .stApp p, .stApp label, .stApp li,
    .stApp [data-testid="stMarkdownContainer"],
    .stApp [data-testid="stCaptionContainer"] {
        color: var(--u-ink);
    }
    .stApp [data-testid="stCaptionContainer"] {
        color: var(--u-muted);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0B3A5B, #062B45);
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] input {
        background: #FFFFFF !important;
        color: #102A43 !important;
    }

    .brand { padding: 8px 0 18px; }
    .brand h1 { font-size: 1.7rem; margin: 0; color: #FFFFFF; }
    .brand p { margin: 3px 0 0; color: #E6F1F8 !important; font-size: .9rem; }

    .hero {
        background: linear-gradient(135deg, #0B3A5B, #075985);
        padding: 28px;
        border-radius: 20px;
        color: #FFFFFF;
        box-shadow: 0 10px 25px rgba(11,58,91,.20);
        margin-bottom: 22px;
    }
    .hero h1, .hero p { color: #FFFFFF !important; }
    .hero h1 { margin: 0; font-size: 2rem; line-height: 1.2; }
    .hero p { margin: .55rem 0 0; color: #E6F1F8 !important; }

    .card, [data-testid="stMetric"] {
        background: var(--u-surface);
        border: 1px solid var(--u-line);
        border-radius: 16px;
        box-shadow: 0 4px 14px rgba(16,42,67,.08);
    }
    .card { padding: 18px; height: 100%; }
    .card *, [data-testid="stMetric"] * { color: var(--u-ink); }
    .kpi { font-size: 1.9rem; font-weight: 800; color: var(--u-blue); margin: 0; }
    .muted { color: var(--u-muted) !important; font-size: .92rem; }
    .badge {
        display: inline-block;
        padding: 4px 9px;
        border-radius: 999px;
        background: #D9EAF7;
        color: #073B5C !important;
        font-size: .78rem;
        font-weight: 800;
    }
    .section-title { font-size: 1.2rem; font-weight: 800; color: var(--u-blue); margin: 12px 0; }

    .stApp [data-baseweb="input"] > div,
    .stApp [data-baseweb="textarea"] > div,
    .stApp [data-baseweb="select"] > div {
        background: #FFFFFF !important;
        color: var(--u-ink) !important;
        border-color: #829AB1 !important;
    }
    .stApp input, .stApp textarea,
    .stApp [data-baseweb="select"] span {
        color: var(--u-ink) !important;
        -webkit-text-fill-color: var(--u-ink) !important;
        opacity: 1 !important;
    }
    .stApp input::placeholder, .stApp textarea::placeholder {
        color: #627D98 !important;
        -webkit-text-fill-color: #627D98 !important;
        opacity: 1 !important;
    }
    .stApp [data-baseweb="radio"] label,
    .stApp [data-baseweb="checkbox"] label {
        color: var(--u-ink) !important;
    }

    div.stButton > button, div.stDownloadButton > button {
        border-radius: 10px;
        border: 2px solid #486581;
        background: #FFFFFF;
        color: #102A43;
        font-weight: 700;
        min-height: 44px;
    }
    div.stButton > button[kind="primary"],
    div.stDownloadButton > button[kind="primary"] {
        background: var(--u-blue) !important;
        color: #FFFFFF !important;
        border-color: var(--u-blue) !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        border-color: var(--u-focus) !important;
        box-shadow: 0 0 0 3px rgba(0,95,204,.18);
    }
    .stApp a { color: #005FCC; font-weight: 600; }
    .stApp [data-testid="stDataFrame"] { border: 1px solid var(--u-line); border-radius: 10px; }

    @media (max-width: 768px) {
        .block-container { padding: 1rem .8rem 5rem !important; }
        .hero { padding: 20px 16px; border-radius: 14px; margin-bottom: 16px; }
        .hero h1 { font-size: 1.55rem; }
        .hero p { font-size: .98rem; }
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: .75rem !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        div.stButton > button, div.stDownloadButton > button {
            width: 100%;
            min-height: 48px;
            font-size: 1rem;
        }
        .stApp label, .stApp p, .stApp li { font-size: 1rem; }
        [data-testid="stSidebar"] { min-width: 17rem; }
    }
    </style>
    """, unsafe_allow_html=True)

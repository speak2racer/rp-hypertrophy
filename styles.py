import streamlit as st

def inject_css():
    st.markdown("""
<style>
/* ── Typography ── */
h1 { font-size: 1.6rem !important; font-weight: 700 !important; letter-spacing: -0.02em; }
h2 { font-size: 1.2rem !important; font-weight: 600 !important; }
h3 { font-size: 1rem !important; font-weight: 600 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0f0f0f !important;
    border-right: 1px solid #1e1e1e !important;
}
[data-testid="stSidebarNav"] a {
    color: #999 !important;
    font-size: 0.9rem;
    padding: 6px 12px;
    border-radius: 6px;
    transition: all 0.15s;
}
[data-testid="stSidebarNav"] a:hover { color: #fff !important; background: #1e1e1e; }
[data-testid="stSidebarNav"] a[aria-current="page"] {
    color: #fff !important;
    background: #1e1e1e;
    font-weight: 600;
}

/* ── Cards / Containers ── */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 10px !important;
    border: 1px solid #1e1e1e !important;
    background: #111 !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #111;
    border: 1px solid #1e1e1e;
    border-radius: 10px;
    padding: 14px 16px;
}
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #666 !important; text-transform: uppercase; letter-spacing: .05em; }
[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700 !important; color: #f0f0f0 !important; }

/* ── Buttons ── */
[data-testid="stButton"] > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: all 0.15s !important;
}
[data-testid="stButton"] > button[kind="primary"] {
    background: #e05c2a !important;
    border: none !important;
    color: #fff !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #c94d20 !important;
}
[data-testid="stButton"] > button[kind="secondary"] {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    color: #ccc !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color: #444 !important;
    color: #fff !important;
}

/* ── Inputs ── */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
textarea {
    background: #161616 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 6px !important;
    color: #e8e8e8 !important;
    font-size: 0.9rem !important;
}
[data-testid="stNumberInput"] input { text-align: center; }
[data-testid="stSelectbox"] > div > div {
    background: #161616 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 6px !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid #1e1e1e !important;
    gap: 4px;
}
[data-testid="stTabs"] button[role="tab"] {
    color: #666 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    border-radius: 6px 6px 0 0 !important;
    border: none !important;
    background: transparent !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #f0f0f0 !important;
    font-weight: 700 !important;
    border-bottom: 2px solid #e05c2a !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    border: 1px solid #1e1e1e !important;
    border-radius: 8px !important;
    background: #0f0f0f !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    font-size: 0.9rem !important;
}

/* ── Divider ── */
hr { border-color: #1e1e1e !important; margin: 16px 0 !important; }

/* ── Info / Warning / Error / Success boxes ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    border: 1px solid !important;
    font-size: 0.85rem !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border-radius: 8px !important; overflow: hidden; }

/* ── Sliders ── */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background: #e05c2a !important;
}

/* ── Custom utility classes ── */
.page-header {
    padding: 0 0 20px 0;
    border-bottom: 1px solid #1e1e1e;
    margin-bottom: 24px;
}
.page-title { font-size: 1.5rem; font-weight: 700; color: #f0f0f0; margin: 0; }
.page-sub   { font-size: 0.85rem; color: #555; margin-top: 4px; }

.stat-card {
    background: #111; border: 1px solid #1e1e1e; border-radius: 10px;
    padding: 16px 20px;
}
.stat-label { font-size: 0.72rem; color: #555; text-transform: uppercase; letter-spacing: .06em; }
.stat-value { font-size: 1.5rem; font-weight: 700; color: #f0f0f0; margin-top: 4px; }
.stat-sub   { font-size: 0.78rem; color: #444; margin-top: 2px; }

.mg-card {
    background: #111; border: 1px solid #1e1e1e; border-radius: 8px;
    padding: 12px 14px; margin-bottom: 12px;
}
.mg-card-header {
    display: flex; align-items: center; gap: 10px;
    border-bottom: 1px solid #1a1a1a; padding-bottom: 8px; margin-bottom: 8px;
}
.mg-card-title { font-size: 1rem; font-weight: 700; color: #f0f0f0; }
.mg-card-meta  { font-size: 0.78rem; color: #555; margin-left: auto; }

.badge {
    display: inline-block; padding: 2px 8px; border-radius: 12px;
    font-size: 0.72rem; font-weight: 600; letter-spacing: .03em;
}
.badge-orange { background: #2a1500; color: #e05c2a; border: 1px solid #3a2000; }
.badge-blue   { background: #0d1a2a; color: #6b9fd4; border: 1px solid #1a2d40; }
.badge-amber  { background: #1f1600; color: #c89020; border: 1px solid #2d2000; }
.badge-red    { background: #1f0a08; color: #c0392b; border: 1px solid #2d1008; }
.badge-gray   { background: #1a1a1a; color: #666; border: 1px solid #222; }

.weight-hint {
    background: #111; border: 1px solid #1e1e1e; border-radius: 6px;
    padding: 8px 12px; font-size: 0.85rem; color: #888; margin: 6px 0;
}
.weight-hint b { color: #f0f0f0; font-size: 1rem; }

.set-grid-header {
    display: grid; grid-template-columns: 28px 1fr 1fr 1fr;
    gap: 4px; padding: 6px 0 4px;
    font-size: 0.7rem; font-weight: 600; color: #444;
    text-transform: uppercase; letter-spacing: .06em;
}
</style>
""", unsafe_allow_html=True)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from datetime import date
from database import get_mesocycles, update_mesocycle_status, delete_mesocycle
from data.rp_volumes import RP_VOLUMES
from styles import inject_css
from auth import login_user, register_user, get_current_user, render_sidebar_user

st.set_page_config(
    page_title="RP Hypertrophy",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
if not get_current_user():
    st.markdown("""
    <div style='max-width:400px;margin:60px auto'>
        <div style='text-align:center;margin-bottom:32px'>
            <div style='font-size:3rem'>🏋️</div>
            <div style='font-size:1.6rem;font-weight:700;color:#f0f0f0;margin-top:8px'>RP Hypertrophy</div>
            <div style='font-size:0.85rem;color:#555;margin-top:4px'>Renaissance Periodization Training</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Anmelden", "Registrieren"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Benutzername")
            password = st.text_input("Passwort", type="password")
            submitted = st.form_submit_button("Anmelden", type="primary", use_container_width=True)
        if submitted:
            ok, msg, user = login_user(username, password)
            if ok:
                st.session_state["auth_user"] = user
                st.rerun()
            else:
                st.error(msg)

    with tab_register:
        with st.form("register_form"):
            new_user = st.text_input("Benutzername wählen")
            new_pw = st.text_input("Passwort wählen", type="password")
            new_pw2 = st.text_input("Passwort wiederholen", type="password")
            submitted2 = st.form_submit_button("Registrieren", type="primary", use_container_width=True)
        if submitted2:
            if new_pw != new_pw2:
                st.error("Passwörter stimmen nicht überein.")
            else:
                ok, msg = register_user(new_user, new_pw)
                if ok:
                    st.success(msg + " Du kannst dich jetzt anmelden.")
                else:
                    st.error(msg)
    st.stop()

# ── Logged in ─────────────────────────────────────────────────────────────────
user = get_current_user()
render_sidebar_user()

mesocycles = get_mesocycles(user_id=user["id"])
active = [m for m in mesocycles if m["status"] == "active"]
deload = [m for m in mesocycles if m["status"] == "deload"]
completed = [m for m in mesocycles if m["status"] == "completed"]

st.markdown("""
<div class='page-header'>
    <p class='page-title'>RP Hypertrophy</p>
    <p class='page-sub'>Renaissance Periodization — Mesozyklus-basiertes Hypertrophie-Training</p>
</div>
""", unsafe_allow_html=True)

if active or deload:
    meso = (active or deload)[0]
    start = date.fromisoformat(meso["start_date"])
    days_in = (date.today() - start).days
    current_week = min(days_in // 7 + 1, meso["weeks"])
    is_deload = meso["status"] == "deload"

    status_badge = (
        "<span class='badge badge-blue'>Deload</span>"
        if is_deload else
        "<span class='badge badge-orange'>Aktiv</span>"
    )
    st.markdown(f"""
    <div class='mg-card'>
        <div class='mg-card-header'>
            <span class='mg-card-title'>{meso['name']}</span>
            {status_badge}
            <span class='mg-card-meta'>{meso.get('split_template', '')} · Start {start.strftime('%d.%m.%Y')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aktuelle Woche", f"{current_week} / {meso['weeks']}")
    c2.metric("Trainingstage", len(meso.get("split_days") or {}))
    c3.metric("Muskelgruppen", len(meso["muscle_groups"]))
    days_left = meso["weeks"] * 7 - days_in
    c4.metric("Verbleibend", f"{max(days_left, 0)} Tage")

    st.markdown("**Muskelgruppen in diesem Zyklus:**")
    mg_cols = st.columns(min(len(meso["muscle_groups"]), 6))
    for i, mg in enumerate(meso["muscle_groups"]):
        icon = RP_VOLUMES.get(mg, {}).get("icon", "💪")
        mg_cols[i % 6].markdown(
            f"<div style='background:#111;border:1px solid #1e1e1e;border-radius:8px;"
            f"padding:8px 10px;text-align:center;font-size:0.82rem'>"
            f"<div style='font-size:1.2rem'>{icon}</div>{mg}</div>",
            unsafe_allow_html=True
        )

    st.markdown("")
    btn1, btn2, _ = st.columns([1, 1, 4])
    if btn1.button("▶ Training", type="primary", use_container_width=True):
        st.switch_page("pages/2_Training.py")
    if btn2.button("📊 Fortschritt", use_container_width=True):
        st.switch_page("pages/3_Fortschritt.py")

    if is_deload:
        st.divider()
        if st.button("✅ Deload abschließen & Zyklus beenden"):
            update_mesocycle_status(meso["id"], "completed")
            st.rerun()
else:
    st.markdown("""
    <div style='background:#111;border:1px solid #1e1e1e;border-radius:10px;
    padding:40px;text-align:center;margin:20px 0'>
        <div style='font-size:2.5rem'>🏋️</div>
        <div style='font-size:1.1rem;font-weight:600;color:#f0f0f0;margin:12px 0 6px'>
            Kein aktiver Mesozyklus
        </div>
        <div style='font-size:0.85rem;color:#555'>
            Erstelle einen neuen Zyklus um mit dem Training zu beginnen
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("➕ Mesozyklus erstellen", type="primary"):
        st.switch_page("pages/1_Mesozyklus.py")

if completed:
    st.divider()
    st.markdown("**Abgeschlossene Zyklen**")
    for m in completed:
        with st.expander(f"✅ {m['name']} — {m['start_date']}  ({m['weeks']} Wochen)"):
            st.caption(f"Muskelgruppen: {', '.join(m['muscle_groups'])}")
            col1, col2, _ = st.columns([1, 1, 4])
            if col1.button("Reaktivieren", key=f"act_{m['id']}"):
                for a in active:
                    update_mesocycle_status(a["id"], "completed")
                update_mesocycle_status(m["id"], "active")
                st.rerun()
            if col2.button("🗑️ Löschen", key=f"del_{m['id']}"):
                delete_mesocycle(m["id"])
                st.rerun()

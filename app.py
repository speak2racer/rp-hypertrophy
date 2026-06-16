import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from datetime import date
from database import (get_mesocycles, update_mesocycle_status, delete_mesocycle,
                       clone_mesocycle, get_muscle_configs, get_last_workout_per_day)
from data.rp_volumes import RP_VOLUMES
from styles import inject_css
from auth import login_user, register_user, get_current_user, render_sidebar_user, set_auth_token, init_auth, get_effective_user_id

st.set_page_config(
    page_title="Spischeks Hypertrophie Coaching",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Auth Gate ─────────────────────────────────────────────────────────────────
# init_auth() handles the cookie component timing (2 render cycles needed).
# On first render it shows "Laden…" and stops; on second render cookies are available.
if not init_auth():
    st.markdown("""
    <div style='max-width:400px;margin:60px auto'>
        <div style='text-align:center;margin-bottom:32px'>
            <div style='font-size:3rem'>🏋️</div>
            <div style='font-size:1.6rem;font-weight:700;color:#f0f0f0;margin-top:8px'>Spischeks Hypertrophie Coaching</div>
            <div style='font-size:0.85rem;color:#555;margin-top:4px'>Mesozyklus-basiertes Hypertrophie-Training</div>
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
            ok, msg, user, token = login_user(username, password)
            if ok:
                st.session_state["auth_user"] = user
                st.session_state["auth_token"] = token
                set_auth_token(token)
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

try:
    mesocycles = get_mesocycles(user_id=get_effective_user_id())
except Exception as e:
    st.error(f"⚠️ Datenbankfehler: {e}\n\nBitte Seite neu laden. Falls das Problem bleibt, kurz warten — die Verbindung wird automatisch wiederhergestellt.")
    st.stop()
active = [m for m in mesocycles if m["status"] == "active"]
deload = [m for m in mesocycles if m["status"] == "deload"]
completed = [m for m in mesocycles if m["status"] == "completed"]

st.markdown("""
<div class='page-header'>
    <p class='page-title'>Spischeks Hypertrophie Coaching</p>
    <p class='page-sub'>Mesozyklus-basiertes Hypertrophie-Training</p>
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

    # ── "Was steht heute an?" ─────────────────────────────────────────────────
    split_order = meso.get("split_order") or []
    split_days  = meso.get("split_days") or {}
    if split_order and split_days:
        last_per_day = get_last_workout_per_day(meso["id"])
        # Find the last-trained day by most recent date
        if last_per_day:
            last_day_name = max(last_per_day, key=lambda d: last_per_day[d])
            if last_day_name in split_order:
                next_idx = (split_order.index(last_day_name) + 1) % len(split_order)
            else:
                next_idx = 0
        else:
            next_idx = 0
        next_day = split_order[next_idx]
        next_muscles = split_days.get(next_day, [])
        next_icons = " ".join(RP_VOLUMES.get(mg, {}).get("icon", "💪") for mg in next_muscles)
        st.markdown("")
        with st.container(border=True):
            col_l, col_r = st.columns([3, 1])
            with col_l:
                st.markdown(f"**Nächste Einheit: {next_day}** {next_icons}")
                st.caption("  ·  ".join(next_muscles) if next_muscles else "")
            with col_r:
                if st.button("▶ Jetzt trainieren", type="primary", use_container_width=True):
                    st.session_state["selected_training_day"] = next_day
                    st.switch_page("pages/2_Training.py")

    st.markdown("")
    btn1, btn2, _ = st.columns([1, 1, 4])
    if btn1.button("▶ Training", use_container_width=True):
        st.switch_page("pages/2_Training.py")
    if btn2.button("📊 Fortschritt", use_container_width=True):
        st.switch_page("pages/3_Fortschritt.py")

    if is_deload:
        st.divider()
        if st.button("✅ Deload abschließen & Zyklus beenden"):
            update_mesocycle_status(meso["id"], "completed")
            st.rerun()
else:
    if not completed:
        # First-time user onboarding
        st.markdown("""
        <div style='background:#111;border:1px solid #222;border-radius:12px;
        padding:32px 40px;text-align:center;margin:20px 0 28px'>
            <div style='font-size:2.8rem'>👋</div>
            <div style='font-size:1.3rem;font-weight:700;color:#f0f0f0;margin:12px 0 8px'>
                Willkommen bei Spischeks Hypertrophie Coaching!
            </div>
            <div style='font-size:0.9rem;color:#888;max-width:520px;margin:0 auto'>
                Diese App hilft dir systematisch Muskeln aufzubauen — mit einem klaren Plan,
                automatischer Gewichtssteuerung und Volumen das sich an deine Erholung anpasst.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### In 4 Schritten loslegen:")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            with st.container(border=True):
                st.markdown("**1️⃣ Mesozyklus planen**")
                st.caption(
                    "Wähle ein Split-Template (z.B. Push/Pull/Legs), "
                    "such dir Übungen aus und lege fest wie viele Wochen der Zyklus dauert. "
                    "Die App schlägt das Startvolumen automatisch vor."
                )
        with c2:
            with st.container(border=True):
                st.markdown("**2️⃣ Training tracken**")
                st.caption(
                    "Trag nach jedem Satz Gewicht, Wiederholungen und RIR ein. "
                    "**RIR** (Reps in Reserve) = wie viele Wdh. du noch könntest. "
                    "Die App berechnet daraus automatisch dein 10RM und schlägt Gewichte vor."
                )
        with c3:
            with st.container(border=True):
                st.markdown("**3️⃣ Feedback geben**")
                st.caption(
                    "Nach jeder Session kurz bewerten: "
                    "**Pump** = wie stark der Muskel während dem Training gepumpt war. "
                    "**Soreness** = Muskelkater am nächsten Tag. "
                    "Daraus passt die App die Satzanzahl in der nächsten Session an."
                )
        with c4:
            with st.container(border=True):
                st.markdown("**4️⃣ Kalibrierung**")
                st.caption(
                    "Nach mehreren Sessions lernt die App dein optimales Volumen kennen: "
                    "**MEV** = Minimum für Fortschritt, "
                    "**MAV** = optimaler Bereich, "
                    "**MRV** = Maximum das du noch erholen kannst."
                )

        st.markdown("")
        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button("➕ Ersten Mesozyklus erstellen", type="primary", use_container_width=True):
                st.switch_page("pages/1_Mesozyklus.py")
        st.caption("👆 Klicke hier um deinen ersten Trainingsplan zu erstellen — dauert ca. 2 Minuten.")
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
            col1, col2, col3, _ = st.columns([1, 1, 1, 3])
            if col1.button("Reaktivieren", key=f"act_{m['id']}"):
                for a in active:
                    update_mesocycle_status(a["id"], "completed")
                update_mesocycle_status(m["id"], "active")
                st.rerun()
            if col2.button("📋 Kopieren", key=f"copy_{m['id']}"):
                st.session_state[f"clone_{m['id']}"] = True
            if col3.button("🗑️ Löschen", key=f"del_{m['id']}"):
                delete_mesocycle(m["id"])
                st.rerun()

            if st.session_state.get(f"clone_{m['id']}"):
                from calibration import get_calibrated_volumes
                st.markdown("---")
                new_name = st.text_input(
                    "Name des neuen Mesozyklus",
                    value=f"{m['name']} (Kopie)",
                    key=f"clone_name_{m['id']}"
                )
                new_start = st.date_input("Startdatum", value=date.today(),
                                          key=f"clone_start_{m['id']}")

                # Preview calibrated volumes
                old_configs = get_muscle_configs(m["id"])
                st.markdown("**Volumen-Anpassung (kalibriert vs. alter Zyklus):**")
                preview_cols = st.columns(3)
                new_configs = {}
                for i, mg in enumerate(m["muscle_groups"]):
                    cal = get_calibrated_volumes(mg)
                    old_cfg = old_configs.get(mg, {})
                    old_sets = old_cfg.get("start_sets", "–")
                    exercises = old_cfg.get("exercises", [])
                    new_start_sets = cal["recommended_start"]
                    new_configs[mg] = {"start_sets": new_start_sets, "exercises": exercises}
                    icon = RP_VOLUMES.get(mg, {}).get("icon", "💪")
                    with preview_cols[i % 3]:
                        delta = new_start_sets - old_sets if isinstance(old_sets, int) else 0
                        delta_str = f"{delta:+d} Sets" if delta != 0 else "gleich"
                        st.metric(f"{icon} {mg}", f"{new_start_sets} Sets/Wo.",
                                  delta=delta_str)

                c_ok, c_cancel = st.columns([1, 1])
                if c_ok.button("✅ Neuen Zyklus erstellen", type="primary",
                               key=f"clone_ok_{m['id']}"):
                    for a in active:
                        update_mesocycle_status(a["id"], "completed")
                    clone_mesocycle(m["id"], new_name, new_start, new_configs,
                                    user_id=get_effective_user_id())
                    del st.session_state[f"clone_{m['id']}"]
                    st.success(f"✅ **{new_name}** erstellt!")
                    st.rerun()
                if c_cancel.button("Abbrechen", key=f"clone_cancel_{m['id']}"):
                    del st.session_state[f"clone_{m['id']}"]
                    st.rerun()

import streamlit as st
from database import get_mesocycles, update_mesocycle_status, delete_mesocycle
from data.rp_volumes import RP_VOLUMES
from datetime import date

st.set_page_config(
    page_title="RP Hypertrophy",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏋️ RP Hypertrophy")
st.caption("Renaissance Periodization — Mesozyklus-basiertes Hypertrophie-Training")

st.divider()

# ── Active Mesocycle Dashboard ────────────────────────────────────────────────
mesocycles = get_mesocycles()
active = [m for m in mesocycles if m["status"] == "active"]
deload = [m for m in mesocycles if m["status"] == "deload"]

if active:
    meso = active[0]
    start = date.fromisoformat(meso["start_date"])
    days_in = (date.today() - start).days
    current_week = min(days_in // 7 + 1, meso["weeks"])

    st.subheader(f"Aktiver Mesozyklus: {meso['name']}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Woche", f"{current_week} / {meso['weeks']}")
    col2.metric("Start", start.strftime("%d.%m.%Y"))
    col3.metric("Muskelgruppen", len(meso["muscle_groups"]))
    col4.metric("Status", "🟢 Aktiv" if meso["status"] == "active" else "🔵 Deload")

    st.markdown("**Trainierte Muskelgruppen:**")
    cols = st.columns(5)
    for i, mg in enumerate(meso["muscle_groups"]):
        icon = RP_VOLUMES.get(mg, {}).get("icon", "💪")
        cols[i % 5].info(f"{icon} {mg}")

    col_a, col_b, col_c = st.columns([1, 1, 4])
    if col_a.button("▶ Training starten", type="primary"):
        st.switch_page("pages/2_Training.py")
    if col_b.button("📊 Fortschritt"):
        st.switch_page("pages/3_Fortschritt.py")

elif deload:
    meso = deload[0]
    st.info(f"🔵 Deload-Woche aktiv: **{meso['name']}**")
    if st.button("Deload abschließen & Zyklus beenden"):
        update_mesocycle_status(meso["id"], "completed")
        st.rerun()
else:
    st.info("Kein aktiver Mesozyklus. Starte einen neuen Zyklus im Mesozyklus-Planer.")
    if st.button("➕ Neuen Mesozyklus erstellen", type="primary"):
        st.switch_page("pages/1_Mesozyklus.py")

st.divider()

# ── All Mesocycles ────────────────────────────────────────────────────────────
if mesocycles:
    st.subheader("Alle Mesozyklen")
    for m in mesocycles:
        status_icon = {"active": "🟢", "deload": "🔵", "completed": "✅"}.get(m["status"], "⚪")
        with st.expander(f"{status_icon} {m['name']} — {m['start_date']}  ({m['weeks']} Wochen)"):
            st.write(f"**Muskelgruppen:** {', '.join(m['muscle_groups'])}")
            col1, col2, col3 = st.columns([1, 1, 4])
            if m["status"] != "active" and col1.button("Als aktiv setzen", key=f"act_{m['id']}"):
                for a in active:
                    update_mesocycle_status(a["id"], "completed")
                update_mesocycle_status(m["id"], "active")
                st.rerun()
            if col2.button("🗑️ Löschen", key=f"del_{m['id']}"):
                delete_mesocycle(m["id"])
                st.rerun()

st.divider()
st.markdown(
    "<small>Basiert auf den RP-Hypertrophie-Prinzipien von Renaissance Periodization</small>",
    unsafe_allow_html=True
)

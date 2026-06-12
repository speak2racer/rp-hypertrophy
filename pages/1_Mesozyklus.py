import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from datetime import date
from data.rp_volumes import RP_VOLUMES, MUSCLE_GROUPS
from styles import inject_css
from auth import require_auth, render_sidebar_user, init_auth
from data.exercises import EXERCISES
from data.templates import TEMPLATES, TEMPLATE_NAMES
from database import create_mesocycle, save_muscle_config, get_mesocycles, update_mesocycle_status
from calibration import get_calibrated_volumes

st.set_page_config(page_title="Mesozyklus-Planer", page_icon="📅", layout="wide")
inject_css()
init_auth()
user = require_auth()
render_sidebar_user()
st.markdown("""
<div class='page-header'>
    <p class='page-title'>📅 Mesozyklus-Planer</p>
    <p class='page-sub'>Plane deinen nächsten Hypertrophie-Zyklus nach RP-Prinzipien</p>
</div>
""", unsafe_allow_html=True)

# ── Step 1: Basic Settings ────────────────────────────────────────────────────
st.subheader("1. Grundeinstellungen")
col1, col2, col3 = st.columns(3)
with col1:
    meso_name = st.text_input("Name des Mesozyklus", value=f"Meso {date.today().strftime('%b %Y')}")
with col2:
    start_date = st.date_input("Startdatum", value=date.today())
with col3:
    weeks = st.slider("Wochen (excl. Deload)", min_value=3, max_value=8, value=5)

st.caption(f"Deload-Woche: Woche {weeks + 1} | Gesamtdauer: {weeks + 1} Wochen")

st.divider()

# ── Step 2: Split Template ────────────────────────────────────────────────────
st.subheader("2. Split-Template wählen")

_template_options = [n for n in TEMPLATE_NAMES if n != "Custom"] + ["✏️ Eigenes Template"]

def _template_label(name: str) -> str:
    if name == "✏️ Eigenes Template":
        return "✏️ Eigenes Template"
    tmpl = TEMPLATES[name]
    all_muscles = list(dict.fromkeys(mg for mgs in tmpl["days"].values() for mg in mgs))
    icons = " ".join(RP_VOLUMES.get(mg, {}).get("icon", "💪") for mg in all_muscles)
    num_days = len(tmpl["days"])
    return f"{name} — {num_days} Tage · {icons} · {tmpl['description']}"

_current = st.session_state.get("selected_template", None)
_default_idx = (
    _template_options.index(_current)
    if _current and _current in _template_options
    else (0 if _current != "Custom" else len(_template_options) - 1)
)

_chosen = st.selectbox(
    "Template",
    options=_template_options,
    index=_default_idx,
    format_func=_template_label,
)
_new_selection = "Custom" if _chosen == "✏️ Eigenes Template" else _chosen

if st.session_state.get("selected_template") != _new_selection:
    st.session_state["selected_template"] = _new_selection
    st.rerun()

selected_template_name = _new_selection

# ── Step 2b: Custom template builder ─────────────────────────────────────────
if selected_template_name == "Custom":
    st.markdown("**Eigenes Template definieren:**")

    if "custom_days" not in st.session_state:
        st.session_state["custom_days"] = {"Tag A": []}

    # Add / remove days
    col_add, col_remove = st.columns([1, 5])
    if col_add.button("➕ Tag hinzufügen"):
        existing = list(st.session_state["custom_days"].keys())
        new_key = f"Tag {chr(65 + len(existing))}"
        st.session_state["custom_days"][new_key] = []
        st.rerun()

    custom_days = {}
    days_to_delete = []
    for day_name, day_muscles in list(st.session_state["custom_days"].items()):
        c1, c2, c3 = st.columns([2, 5, 1])
        new_name = c1.text_input("Tag-Name", value=day_name, key=f"dn_{day_name}")
        chosen_mg = c2.multiselect(
            "Muskelgruppen",
            options=MUSCLE_GROUPS,
            default=day_muscles,
            key=f"dm_{day_name}",
        )
        if c3.button("🗑️", key=f"del_{day_name}"):
            days_to_delete.append(day_name)
        custom_days[new_name] = chosen_mg

    for d in days_to_delete:
        if d in st.session_state["custom_days"]:
            del st.session_state["custom_days"][d]
        st.rerun()

    st.session_state["custom_days"] = custom_days
    split_days = custom_days
    split_order = list(custom_days.keys())

else:
    tmpl = TEMPLATES[selected_template_name]
    split_days = dict(tmpl["days"])
    split_order = list(tmpl["suggested_order"])

    # Clear cached edit-keys when template changes to avoid stale session_state
    if st.session_state.get("_last_template") != selected_template_name:
        for k in list(st.session_state.keys()):
            if k.startswith("edit_"):
                del st.session_state[k]
        st.session_state["_last_template"] = selected_template_name

    # Allow reordering/editing the template days
    with st.expander("🔧 Template anpassen (optional)", expanded=False):
        st.caption("Du kannst Muskelgruppen pro Tag anpassen.")
        edited_days = {}
        for day_name in split_order:
            day_muscles = split_days.get(day_name, [])
            chosen = st.multiselect(
                day_name,
                options=MUSCLE_GROUPS,
                default=day_muscles,
                key=f"edit_{day_name}",
            )
            edited_days[day_name] = chosen
        split_days = edited_days

# Show template preview
st.markdown("**Split-Übersicht:**")
preview_cols = st.columns(min(len(split_days), 4))
for i, (day_name, muscles) in enumerate(split_days.items()):
    with preview_cols[i % len(preview_cols)]:
        icons = " ".join(RP_VOLUMES.get(mg, {}).get("icon", "💪") for mg in muscles)
        st.info(f"**{day_name}**\n\n{icons}\n\n" + "\n".join(f"• {mg}" for mg in muscles))

# Derive all unique muscle groups from the split
selected_muscles = list(dict.fromkeys(
    mg for muscles in split_days.values() for mg in muscles
))

if not selected_muscles:
    st.warning("Das Template hat keine Muskelgruppen definiert.")
    st.stop()

st.divider()

# ── Step 3: Exercise Selection ────────────────────────────────────────────────
st.subheader("3. Übungen wählen")

calibrated = {mg: get_calibrated_volumes(mg) for mg in selected_muscles}
muscle_configs = {}

cols = st.columns(2)
for i, mg in enumerate(selected_muscles):
    cal = calibrated[mg]
    vol_base = RP_VOLUMES.get(mg, {})
    available = [e["name"] for e in EXERCISES.get(mg, [])]
    sfr_map = {e["name"]: e["sfr"] for e in EXERCISES.get(mg, [])}
    trains_on = [d for d, mgs in split_days.items() if mg in mgs]
    freq = len(trains_on) if trains_on else 1
    start_sets = cal["recommended_start"]
    sets_per_session = max(1, round(start_sets / freq))

    # Recommend exercises: ≥1 per training day (rotation) AND enough for session volume
    if sets_per_session <= 6:
        per_session_rec = 1
    elif sets_per_session <= 12:
        per_session_rec = 2
    else:
        per_session_rec = 3
    rec_ex = max(freq, per_session_rec)

    with cols[i % 2]:
        icon = vol_base.get("icon", "💪")
        days_str = ", ".join(trains_on) if trains_on else "–"
        st.markdown(f"**{icon} {mg}**")
        st.caption(
            f"Empfehlung: **{rec_ex} Übung{'en' if rec_ex != 1 else ''}** "
            f"· {freq}× pro Woche · {sets_per_session} Sets/Session"
        )
        chosen = st.multiselect(
            f"ex_{mg}",
            options=available,
            default=available[:rec_ex] if len(available) >= rec_ex else available,
            key=f"ex_{mg}",
            label_visibility="collapsed",
        )
        sfr_badges = " · ".join(
            f"{'🟢' if sfr_map.get(e) == 'high' else '🟡'} {e}"
            for e in chosen
        )
        if sfr_badges:
            st.caption(sfr_badges)

    progression = [min(start_sets + (w - 1) * 2, cal["MRV"]) for w in range(1, weeks + 1)]
    muscle_configs[mg] = {
        "start_sets": start_sets,
        "exercises": chosen,
        "cal": cal,
        "progression": progression,
    }

st.divider()

# ── Step 4: Summary ───────────────────────────────────────────────────────────
st.subheader("4. Zusammenfassung")

total_w1 = sum(c["start_sets"] for c in muscle_configs.values())
total_peak = sum(c["progression"][-1] for c in muscle_configs.values())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Template", selected_template_name)
col2.metric("Trainingstage", len(split_days))
col3.metric("Startvolumen", f"{total_w1} Sets/Wo.")
col4.metric("Peakvolumen", f"{total_peak} Sets/Wo.")

st.divider()

if st.button("✅ Mesozyklus erstellen", type="primary", disabled=not meso_name):
    for m in get_mesocycles(user_id=user["id"]):
        if m["status"] == "active":
            update_mesocycle_status(m["id"], "completed")

    meso_id = create_mesocycle(
        meso_name, start_date, weeks, weeks + 1, selected_muscles,
        split_template=selected_template_name,
        split_days=split_days,
        split_order=split_order,
        user_id=user["id"],
    )

    for mg, cfg in muscle_configs.items():
        save_muscle_config(meso_id, mg, cfg["start_sets"], cfg["exercises"])

    st.success(f"✅ Mesozyklus **{meso_name}** erfolgreich erstellt!")
    st.balloons()
    if st.button("▶ Zum Training"):
        st.switch_page("pages/2_Training.py")

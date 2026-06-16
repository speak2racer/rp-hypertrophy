import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from datetime import date
from data.rp_volumes import RP_VOLUMES, MUSCLE_GROUPS
from styles import inject_css
from auth import require_auth, render_sidebar_user, init_auth, get_effective_user_id
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
    <p class='page-sub'>Plane deinen nächsten Hypertrophie-Zyklus</p>
</div>
""", unsafe_allow_html=True)

# ── Makrozyklus-Empfehlung ────────────────────────────────────────────────────
def _macro_recommendation(mesocycles: list) -> tuple[str, str, str]:
    """
    Analysiert abgeschlossene Mesos und empfiehlt den nächsten Typ.
    Returns (recommended_type, title, explanation).
    """
    done = [m for m in mesocycles if m["status"] in ("completed", "active", "deload")]
    done_sorted = sorted(done, key=lambda m: m.get("created_at", ""), reverse=True)

    if not done_sorted:
        return "hypertrophy", "💪 Empfehlung: Hypertrophie-Meso", \
               "Starte mit einem Hypertrophie-Meso um Muskelvolumen aufzubauen und dein MEV/MRV zu kalibrieren."

    # Zähle aufeinanderfolgende Hypertrophie-Mesos seit letztem Kraft-Meso
    hyp_streak = 0
    last_strength_idx = None
    for i, m in enumerate(done_sorted):
        t = m.get("meso_type") or "hypertrophy"
        if t == "strength":
            last_strength_idx = i
            break
        hyp_streak += 1

    total = len(done_sorted)
    last_type = done_sorted[0].get("meso_type") or "hypertrophy"

    if last_type == "strength":
        return "hypertrophy", "💪 Empfehlung: Hypertrophie-Meso", \
               "Du hast gerade einen Kraft-Meso abgeschlossen. Jetzt ist der ideale Zeitpunkt für " \
               "Hypertrophie — dein 1RM ist verbessert, nutze das für höhere Gewichte bei mehr Volumen."
    elif hyp_streak >= 3:
        return "strength", "🏋️ Empfehlung: Kraft-Meso", \
               f"Du hast {hyp_streak} Hypertrophie-Mesos in Folge absolviert. " \
               "Zeit für einen Kraft-Meso um das 1RM zu steigern und die Basis für den nächsten Aufbaublock zu legen."
    elif hyp_streak == 2:
        return "strength", "🏋️ Empfehlung: Kraft-Meso (optional)", \
               "Nach 2 Hypertrophie-Mesos wäre ein Kraft-Meso sinnvoll. " \
               "Du kannst noch einen dritten Hypertrophie-Meso machen, spätestens danach solltest du jedoch Kraft trainieren."
    else:
        return "hypertrophy", "💪 Empfehlung: Hypertrophie-Meso", \
               f"Du bist bei {hyp_streak} Hypertrophie-Meso{'s' if hyp_streak != 1 else ''} seit dem letzten Kraft-Block. " \
               "Noch 1–2 weitere Hypertrophie-Mesos sind sinnvoll bevor du wieder Kraft trainierst."

all_mesos = get_mesocycles(user_id=get_effective_user_id())
rec_type, rec_title, rec_text = _macro_recommendation(all_mesos)

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

# Makrozyklus-Empfehlung anzeigen
with st.container(border=True):
    st.markdown(f"**{rec_title}**")
    st.caption(rec_text)
    # Timeline der letzten Mesos
    done_mesos = [m for m in all_mesos if m["status"] in ("completed", "active", "deload")]
    if done_mesos:
        timeline = []
        for m in sorted(done_mesos, key=lambda x: x.get("created_at", ""))[-6:]:
            t = m.get("meso_type") or "hypertrophy"
            icon = "💪" if t == "hypertrophy" else "🏋️"
            timeline.append(f"{icon} {m['name']}")
        timeline.append(f"**→ Neu**")
        st.caption("  ›  ".join(timeline))

st.caption("**RIR** (Reps in Reserve) = Wdh. die du am Ende eines Satzes noch könntest. 3 RIR = du hörst auf, könntest aber noch 3 weitere Wdh. schaffen.")

_default_type_idx = 0 if rec_type == "hypertrophy" else 1
meso_type = st.radio(
    "Mesozyklus-Typ",
    options=["hypertrophy", "strength"],
    format_func=lambda x: "💪 Hypertrophie  —  hohes Volumen, 8–12 Wdh., MEV→MRV" if x == "hypertrophy"
                          else "🏋️ Kraft  —  schwere Gewichte, 3–6 Wdh., Volumen bei MEV",
    horizontal=True,
    index=_default_type_idx,
    key="meso_type_select",
)
if meso_type == "strength":
    st.info("**Kraft-Meso:** Weniger Sätze (nahe MEV), höhere Intensität (80–95% 1RM), 3–6 Wiederholungen. "
            "Verbessert das 1RM → automatisch höhere Gewichtsvorschläge im nächsten Hypertrophie-Meso.")

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

with st.expander("ℹ️ Was bedeuten MEV, MAV, MRV?", expanded=False):
    st.markdown("""
| Begriff | Bedeutung | Praxis |
|---------|-----------|--------|
| **MEV** — Minimum Effective Volume | Mindestanzahl Sätze pro Woche damit der Muskel wächst | Startpunkt nach Deload |
| **MAV** — Maximum Adaptive Volume | Optimaler Bereich für maximales Wachstum | Ziel-Bereich im Meso |
| **MRV** — Maximum Recoverable Volume | Maximale Sätze die du noch erholen kannst | Nie dauerhaft überschreiten |

Die App startet nahe MEV und steigert das Volumen jede Woche Richtung MAV/MRV.
Nach dem Deload startet der nächste Zyklus wieder bei MEV — aber auf höherem Niveau.
""")


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

    # Kraft-Meso: Volumen bleibt bei MEV, kein Anstieg über Wochen
    if meso_type == "strength":
        start_sets = max(cal["MEV"], 3)
        sets_per_session = max(1, round(start_sets / freq))
        rec_ex = 1  # Kraft: 1 Hauptübung pro Muskel
        intensity_hint = "3–6 Wdh. · 80–95% 1RM · Volumen konstant bei MEV"
    else:
        start_sets = cal["recommended_start"]
        sets_per_session = max(1, round(start_sets / freq))
        if sets_per_session <= 6:
            per_session_rec = 1
        elif sets_per_session <= 12:
            per_session_rec = 2
        else:
            per_session_rec = 3
        rec_ex = max(freq, per_session_rec)
        intensity_hint = f"{sets_per_session} Sets/Session · 8–12 Wdh."

    with cols[i % 2]:
        icon = vol_base.get("icon", "💪")
        mev = cal.get("MEV", vol_base.get("MEV", "?"))
        mav_l = cal.get("MAV_low", vol_base.get("MAV_low", "?"))
        mav_h = cal.get("MAV_high", vol_base.get("MAV_high", "?"))
        mrv = cal.get("MRV", vol_base.get("MRV", "?"))
        st.markdown(f"**{icon} {mg}**")
        st.caption(
            f"Empfehlung: **{rec_ex} Übung{'en' if rec_ex != 1 else ''}** "
            f"· {freq}× pro Woche · {intensity_hint} "
            f"· MEV {mev} / MAV {mav_l}–{mav_h} / MRV {mrv} Sets/Wo."
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

    # Progression: Hypertrophie steigt wöchentlich, Kraft bleibt konstant bei MEV
    if meso_type == "strength":
        progression = [start_sets] * weeks
    else:
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
    for m in all_mesos:
        if m["status"] == "active":
            update_mesocycle_status(m["id"], "completed")

    meso_id = create_mesocycle(
        meso_name, start_date, weeks, weeks + 1, selected_muscles,
        split_template=selected_template_name,
        split_days=split_days,
        split_order=split_order,
        user_id=get_effective_user_id(),
        meso_type=meso_type,
    )

    for mg, cfg in muscle_configs.items():
        save_muscle_config(meso_id, mg, cfg["start_sets"], cfg["exercises"])

    st.success(f"✅ Mesozyklus **{meso_name}** erfolgreich erstellt!")
    st.balloons()
    if st.button("▶ Zum Training"):
        st.switch_page("pages/2_Training.py")

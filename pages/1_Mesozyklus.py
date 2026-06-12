import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import date
from data.rp_volumes import RP_VOLUMES, MUSCLE_GROUPS
from styles import inject_css
from data.exercises import EXERCISES
from data.templates import TEMPLATES, TEMPLATE_NAMES
from database import create_mesocycle, save_muscle_config, get_mesocycles, update_mesocycle_status
from calibration import get_calibrated_volumes

st.set_page_config(page_title="Mesozyklus-Planer", page_icon="📅", layout="wide")
inject_css()
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

# Template cards
template_cols = st.columns(4)
for i, name in enumerate([n for n in TEMPLATE_NAMES if n != "Custom"]):
    tmpl = TEMPLATES[name]
    with template_cols[i % 4]:
        num_days = len(tmpl["days"])
        if st.button(
            f"**{name}**\n{tmpl['description']}\n_{num_days} Trainingstage_",
            key=f"tmpl_{name}",
            use_container_width=True,
        ):
            st.session_state["selected_template"] = name

if st.button("✏️ Eigenes Template erstellen", use_container_width=False):
    st.session_state["selected_template"] = "Custom"

selected_template_name = st.session_state.get("selected_template", None)

if not selected_template_name:
    st.info("Wähle ein Template um fortzufahren.")
    st.stop()

st.success(f"✅ Template gewählt: **{selected_template_name}**")

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

# ── Step 3: Volume & Exercise Config per Muscle ───────────────────────────────
st.subheader("3. Volumen & Übungen konfigurieren")

calibrated = {mg: get_calibrated_volumes(mg) for mg in selected_muscles}
has_history = any(c["source"] == "calibrated" for c in calibrated.values())

if has_history:
    st.success("✅ Kalibrierte Werte aus vorherigen Zyklen werden verwendet.")
else:
    st.info("ℹ️ Noch kein vorheriger Zyklus — RP-Literaturwerte als Ausgangspunkt.")

muscle_configs = {}

for mg in selected_muscles:
    cal = calibrated[mg]
    vol_base = RP_VOLUMES.get(mg, {})

    source_label = (
        f"📊 kalibriert aus **{cal.get('source_meso', '')}**"
        if cal["source"] == "calibrated"
        else "📖 Literaturwert"
    )
    confidence_badge = {"high": "🟢", "medium": "🟡", "low": "⚪"}.get(cal.get("confidence", "low"), "⚪")

    # Which days trains this muscle?
    trains_on = [d for d, mgs in split_days.items() if mg in mgs]
    freq_label = f"trainiert an: {', '.join(trains_on)}"

    with st.expander(
        f"{vol_base.get('icon','💪')} **{mg}** — "
        f"MEV: {cal['MEV']} | MAV: {cal['MAV_low']}–{cal['MAV_high']} | MRV: {cal['MRV']}  "
        f"{confidence_badge} {source_label}",
        expanded=False
    ):
        freq = len(trains_on) if trains_on else 1
        st.caption(f"{freq_label} · **{freq}× pro Woche** → je Session: MEV {max(1,round(cal['MEV']/freq))}–MRV {max(1,round(cal['MRV']/freq))} Sets")

        if cal["source"] == "calibrated":
            with st.container(border=True):
                st.caption("**Kalibrierungs-Begründung:** (Wochenwerte)")
                col_e1, col_e2, col_e3 = st.columns(3)
                col_e1.info(f"**MEV {cal['MEV']} Sets/Wo.**\n\n{cal['explanations']['MEV']}")
                col_e2.success(f"**MAV {cal['MAV_low']}–{cal['MAV_high']} Sets/Wo.**\n\n{cal['explanations']['MAV']}")
                col_e3.warning(f"**MRV {cal['MRV']} Sets/Wo.**\n\n{cal['explanations']['MRV']}")

        c1, c2 = st.columns([1, 2])

        with c1:
            st.markdown("**Startvolumen (Sets / Woche gesamt)**")
            start_sets = st.slider(
                "Sets in Woche 1",
                min_value=max(cal["MEV"] - 2, 1),
                max_value=cal["MRV"],
                value=cal["recommended_start"],
                key=f"sets_{mg}"
            )

            if start_sets <= cal["MEV"]:
                st.info("⚪ unter MEV")
            elif start_sets <= cal["MAV_high"]:
                st.success("🟢 MAV (optimal)")
            elif start_sets < cal["MRV"]:
                st.warning("🟡 über MAV")
            else:
                st.error("🔴 MRV (Maximum)")

            progression = [min(start_sets + (w - 1) * 2, cal["MRV"]) for w in range(1, weeks + 1)]
            deload_sets = max(cal["MEV"] - 2, 2)
            st.caption(f"Progression: {' → '.join(map(str, progression))} → Deload: {deload_sets}")

            mrv_week = next((i + 1 for i, s in enumerate(progression) if s >= cal["MRV"]), None)
            if mrv_week and mrv_week <= weeks - 1:
                st.warning(f"⚠️ MRV in Woche {mrv_week} erreicht. Erwäge tieferen Start.")

        with c2:
            st.markdown("**Übungsauswahl**")
            available = [e["name"] for e in EXERCISES.get(mg, [])]
            chosen = st.multiselect(
                "Übungen für diesen Zyklus",
                options=available,
                default=available[:2] if len(available) >= 2 else available,
                key=f"ex_{mg}"
            )
            sfr_map = {e["name"]: e["sfr"] for e in EXERCISES.get(mg, [])}
            for ex in chosen:
                badge = {"high": "🟢 High SFR", "medium": "🟡 Medium SFR"}.get(sfr_map.get(ex), "")
                st.caption(f"  {ex}: {badge}")

        muscle_configs[mg] = {
            "start_sets": start_sets,
            "exercises": chosen,
            "progression": progression,
            "cal": cal,
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

summary_rows = []
for mg, cfg in muscle_configs.items():
    cal = cfg["cal"]
    row = {
        "Muskelgruppe": mg,
        "Trainingstage": ", ".join(d for d, mgs in split_days.items() if mg in mgs),
        "Quelle": "📊 Kalibriert" if cal["source"] == "calibrated" else "📖 Literatur",
        "MEV": cal["MEV"], "MAV": f"{cal['MAV_low']}–{cal['MAV_high']}", "MRV": cal["MRV"],
        "Start": cfg["start_sets"],
    }
    for i, s in enumerate(cfg["progression"]):
        row[f"W{i+1}"] = s
    row["Deload"] = max(cal["MEV"] - 2, 2)
    summary_rows.append(row)

st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

st.divider()

if st.button("✅ Mesozyklus erstellen", type="primary", disabled=not meso_name):
    for m in get_mesocycles():
        if m["status"] == "active":
            update_mesocycle_status(m["id"], "completed")

    meso_id = create_mesocycle(
        meso_name, start_date, weeks, weeks + 1, selected_muscles,
        split_template=selected_template_name,
        split_days=split_days,
        split_order=split_order,
    )

    for mg, cfg in muscle_configs.items():
        save_muscle_config(meso_id, mg, cfg["start_sets"], cfg["exercises"])

    st.success(f"✅ Mesozyklus **{meso_name}** erfolgreich erstellt!")
    st.balloons()
    if st.button("▶ Zum Training"):
        st.switch_page("pages/2_Training.py")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from styles import inject_css
from auth import require_auth, render_sidebar_user
from database import get_ten_rm, save_ten_rm, get_all_ten_rms
from data.exercises import EXERCISES
from data.rp_volumes import RP_VOLUMES

st.set_page_config(page_title="10RM", page_icon="⚖️", layout="wide")
inject_css()
user = require_auth()
render_sidebar_user()
st.markdown("""
<div class='page-header'>
    <p class='page-title'>⚖️ 10RM-Werte</p>
    <p class='page-sub'>Maximales Gewicht für 10 saubere Wiederholungen — Basis für alle Gewichtsvorschläge im Training</p>
</div>
""", unsafe_allow_html=True)

all_exercises = []
for mg, ex_list in EXERCISES.items():
    for ex in ex_list:
        all_exercises.append({"muscle_group": mg, "name": ex["name"], "sfr": ex.get("sfr", "")})

existing_rms = get_all_ten_rms(user_id=user["id"])
mg_order = list(dict.fromkeys(e["muscle_group"] for e in all_exercises))
updated = {}

for mg in mg_order:
    exercises_in_mg = [e for e in all_exercises if e["muscle_group"] == mg]
    icon = RP_VOLUMES.get(mg, {}).get("icon", "💪")

    with st.expander(f"{icon} **{mg}**", expanded=False):
        cols = st.columns(2)
        for i, ex in enumerate(exercises_in_mg):
            current = existing_rms.get(ex["name"], 0.0)
            sfr_badge = {"high": "🟢", "medium": "🟡"}.get(ex["sfr"], "")
            val = cols[i % 2].number_input(
                f"{sfr_badge} {ex['name']}",
                min_value=0.0,
                step=2.5,
                value=float(current),
                key=f"rm_{mg}_{ex['name']}",
                help="0 = noch nicht eingetragen"
            )
            if val != current:
                updated[ex["name"]] = val

if updated:
    if st.button("💾 Speichern", type="primary"):
        for ex_name, weight in updated.items():
            save_ten_rm(ex_name, weight, user_id=user["id"])
        st.success(f"✅ {len(updated)} Wert(e) gespeichert.")
        st.rerun()

st.divider()
st.subheader("Übersicht")

existing_rms = get_all_ten_rms(user_id=user["id"])
rm_rows = []
for ex in all_exercises:
    w = existing_rms.get(ex["name"])
    if w and w > 0:
        rm_rows.append({
            "Muskelgruppe": ex["muscle_group"],
            "Übung": ex["name"],
            "10RM (kg)": w,
            "3 RIR → 87.5%": round(w * 0.875 / 2.5) * 2.5,
            "2 RIR → 92.5%": round(w * 0.925 / 2.5) * 2.5,
            "1 RIR → 97.5%": round(w * 0.975 / 2.5) * 2.5,
        })

if rm_rows:
    st.dataframe(pd.DataFrame(rm_rows), use_container_width=True, hide_index=True)
else:
    st.info("Noch keine 10RM-Werte hinterlegt. Trage oben deine Werte ein.")

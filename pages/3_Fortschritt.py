import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from styles import inject_css
from auth import require_auth, render_sidebar_user, init_auth, get_effective_user_id
from database import (
    get_mesocycles, get_sets_per_muscle_per_week, get_all_sets_for_exercise,
    get_all_feedback_for_meso, get_workouts, get_sets
)
from data.rp_volumes import RP_VOLUMES
from data.exercises import EXERCISES
from calibration import calibrate_muscle, get_calibrated_volumes

st.set_page_config(page_title="Fortschritt", page_icon="📊", layout="wide")
inject_css()
init_auth()
user = require_auth()
render_sidebar_user()
st.markdown("""
<div class='page-header'>
    <p class='page-title'>📊 Fortschritt & Analyse</p>
    <p class='page-sub'>Volumen, Stärke, Feedback und Kalibrierung im Überblick</p>
</div>
""", unsafe_allow_html=True)

mesocycles = get_mesocycles(user_id=get_effective_user_id())

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📈 Volumen", "💪 Stärke", "🎯 Feedback", "🔍 Deload-Analyse", "🧠 Kalibrierung"]
)

# ── Tabs 1–4: need a mesocycle ────────────────────────────────────────────────
_NO_MESO = not mesocycles

if not _NO_MESO:
    meso_options = {f"{m['name']} ({m['start_date']})": m for m in mesocycles}
    selected_label = st.selectbox("Mesozyklus auswählen", list(meso_options.keys()))
    meso = meso_options[selected_label]

# ── Tab 1: Volume per Muscle per Week ────────────────────────────────────────
with tab1:
    if _NO_MESO:
        st.info("Noch keine Mesozyklen vorhanden.")
    else:
        st.subheader("Trainingsvolumen pro Muskelgruppe")
        vol_data = get_sets_per_muscle_per_week(meso["id"])
        if not vol_data:
            st.info("Noch keine Trainingsdaten.")
        else:
            df = pd.DataFrame(vol_data)
            pivot = df.pivot(index="muscle_group", columns="week_number", values="set_count").fillna(0)
            pivot.columns = [f"Woche {c}" for c in pivot.columns]
            pivot = pivot.astype(int)

            # ── Per-muscle charts with MEV/MAV/MRV bands ──────────────────────
            for mg in pivot.index:
                if pivot.loc[mg].sum() == 0:
                    continue
                vol = RP_VOLUMES.get(mg, {})
                icon = vol.get("icon", "💪")
                weeks_data = pivot.loc[mg]
                last_sets = int(weeks_data.iloc[-1])
                zone = (
                    "🟢 im MEV-Bereich" if last_sets <= vol.get("MEV", 99)
                    else "🟡 im MAV-Bereich" if last_sets <= vol.get("MAV_high", 99)
                    else "🔴 über MRV"
                )
                with st.expander(f"{icon} **{mg}** — Woche {len(weeks_data)}: {last_sets} Sets  {zone}", expanded=True):
                    chart_df = pd.DataFrame({
                        "Trainingsvolumen": weeks_data.values,
                        "MEV": [vol.get("MEV", None)] * len(weeks_data),
                        "MAV-low": [vol.get("MAV_low", None)] * len(weeks_data),
                        "MAV-high": [vol.get("MAV_high", None)] * len(weeks_data),
                        "MRV": [vol.get("MRV", None)] * len(weeks_data),
                    }, index=weeks_data.index)
                    st.line_chart(chart_df, use_container_width=True)

# ── Tab 2: Strength Progress ──────────────────────────────────────────────────
with tab2:
    if _NO_MESO:
        st.info("Noch keine Mesozyklen vorhanden.")
    else:
        st.subheader("Stärkeentwicklung")
        all_muscles = meso.get("muscle_groups", list(RP_VOLUMES.keys()))
        selected_mg = st.selectbox("Muskelgruppe", all_muscles)
        exercises_for_mg = [e["name"] for e in EXERCISES.get(selected_mg, [])]
        if not exercises_for_mg:
            st.info("Keine Übungen für diese Muskelgruppe.")
        else:
            selected_ex = st.selectbox("Übung", exercises_for_mg)
            sets = get_all_sets_for_exercise(selected_ex)
            if not sets:
                st.info(f"Noch keine Daten für **{selected_ex}**.")
            else:
                df = pd.DataFrame(sets)
                df["date"] = pd.to_datetime(df["date"])
                df["1RM"] = df["weight"] * (1 + df["reps"] / 30)
                df["volume"] = df["weight"] * df["reps"]
                df_best = df.groupby("date").agg(
                    best_weight=("weight", "max"),
                    max_reps=("reps", "max"),
                    estimated_1rm=("1RM", "max"),
                    total_volume=("volume", "sum")
                ).reset_index()
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Maximales Gewicht (kg)**")
                    st.line_chart(df_best.set_index("date")["best_weight"])
                with c2:
                    st.markdown("**Geschätztes 1RM (Epley)**")
                    st.line_chart(df_best.set_index("date")["estimated_1rm"])
                st.markdown("**Trainingsvolumen (kg × Wdh.)**")
                st.bar_chart(df_best.set_index("date")["total_volume"])
                st.dataframe(
                    df[["date", "week_number", "set_number", "weight", "reps", "rpe"]].rename(columns={
                        "date": "Datum", "week_number": "Woche", "set_number": "Set",
                        "weight": "Gewicht", "reps": "Wdh.", "rpe": "RPE"
                    }),
                    use_container_width=True, hide_index=True
                )

# ── Tab 3: Session Feedback ───────────────────────────────────────────────────
with tab3:
    if _NO_MESO:
        st.info("Noch keine Mesozyklen vorhanden.")
    else:
        st.subheader("Session-Feedback Analyse")
        feedback_data = get_all_feedback_for_meso(meso["id"])
        if not feedback_data:
            st.info("Noch kein Feedback erfasst.")
        else:
            df_fb = pd.DataFrame(feedback_data)
            df_fb["date"] = pd.to_datetime(df_fb["date"])
            perf_labels = {1: "Viel schlechter", 2: "Schlechter", 3: "Gleich", 4: "Besser", 5: "Viel besser"}
            df_fb["performance_label"] = df_fb["performance"].map(perf_labels)
            muscles = df_fb["muscle_group"].unique()
            selected_fb_mg = st.selectbox("Muskelgruppe", muscles, key="fb_mg")
            df_mg = df_fb[df_fb["muscle_group"] == selected_fb_mg].sort_values("date")
            if not df_mg.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("Ø Pump", f"{df_mg['pump'].mean():.1f}/5")
                c2.metric("Ø Soreness", f"{df_mg['soreness'].mean():.1f}/5")
                c3.metric("Ø Performance", f"{df_mg['performance'].mean():.1f}/5")
                st.line_chart(df_mg.set_index("date")[["pump", "soreness", "performance"]])
                st.dataframe(
                    df_mg[["date", "week_number", "pump", "soreness", "performance_label"]].rename(columns={
                        "date": "Datum", "week_number": "Woche", "pump": "Pump",
                        "soreness": "Soreness", "performance_label": "Performance"
                    }),
                    use_container_width=True, hide_index=True
                )

# ── Tab 4: Deload Analysis ────────────────────────────────────────────────────
with tab4:
    if _NO_MESO:
        st.info("Noch keine Mesozyklen vorhanden.")
    else:
        st.subheader("Deload-Empfehlung")
        feedback_data = get_all_feedback_for_meso(meso["id"])
        if not feedback_data:
            st.info("Noch nicht genug Daten für eine Analyse.")
        else:
            df_fb = pd.DataFrame(feedback_data)
            deload_needed = []
            for mg in meso["muscle_groups"]:
                df_mg = df_fb[df_fb["muscle_group"] == mg]
                if df_mg.empty:
                    continue
                last_3 = df_mg.tail(3)
                avg_soreness = last_3["soreness"].mean()
                avg_performance = last_3["performance"].mean()
                avg_pump = last_3["pump"].mean()
                score = 0
                reasons = []
                if avg_soreness > 3.5:
                    score += 1; reasons.append(f"Hohe Soreness ({avg_soreness:.1f}/5)")
                if avg_performance < 2.5:
                    score += 1; reasons.append(f"Sinkende Performance ({avg_performance:.1f}/5)")
                if avg_pump < 2.5:
                    score += 1; reasons.append(f"Niedriger Pump ({avg_pump:.1f}/5)")
                icon = RP_VOLUMES.get(mg, {}).get("icon", "💪")
                status = "🔴 Deload empfohlen" if score >= 2 else ("🟡 Beobachten" if score == 1 else "🟢 Weiter trainieren")
                col1, col2 = st.columns([1, 3])
                col1.metric(f"{icon} {mg}", status)
                if reasons:
                    col2.warning(f"Indikatoren: {' | '.join(reasons)}")
                else:
                    col2.success("Keine Warnsignale")
                if score >= 2:
                    deload_needed.append(mg)
            if deload_needed:
                st.divider()
                st.error(f"**Deload-Empfehlung:** {', '.join(deload_needed)} zeigen Erholungsdefizite.")
                if st.button("🔵 Deload-Woche starten"):
                    from database import update_mesocycle_status
                    update_mesocycle_status(meso["id"], "deload")
                    st.rerun()

# ── Tab 5: Calibration — always visible ──────────────────────────────────────
with tab5:
    st.subheader("🧠 Kalibrierungs-Bericht")
    st.markdown(
        "MEV, MAV und MRV aus deinen Feedback-Daten — oder Literaturwerte als Ausgangspunkt."
    )
    st.markdown("""
| Kürzel | Bedeutung | Beschreibung |
|--------|-----------|--------------|
| **MEV** | Minimum Effective Volume | Minimale Sätze/Woche für Wachstumsreiz |
| **MAV** | Maximum Adaptive Volume | Optimaler Bereich — bester Pump, moderate Soreness |
| **MRV** | Maximum Recoverable Volume | Obergrenze — darüber keine volle Erholung mehr |

Du startest bei MEV und steigerst wöchentlich bis zum MRV. Die Deload-Woche danach stellt die Regeneration sicher.
    """)
    st.divider()

    # Use current meso if available, else show literature for all muscle groups
    if not _NO_MESO:
        display_muscles = meso.get("muscle_groups", list(RP_VOLUMES.keys()))
        for mg in display_muscles:
            cal = calibrate_muscle(meso["id"], mg)
            _source = f"aus **{meso['name']}**" if cal["source"] == "calibrated" else "Literaturwert"
            _conf = {"high": "🟢", "medium": "🟡", "low": "⚪"}.get(cal.get("confidence", "low"), "⚪")
            icon = RP_VOLUMES.get(mg, {}).get("icon", "💪")
            with st.expander(f"{icon} **{mg}** — {_conf} {_source}", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("MEV", f"{cal['MEV']} Sets/Wo.")
                c2.metric("MAV", f"{cal['MAV_low']}–{cal['MAV_high']} Sets/Wo.")
                c3.metric("MRV", f"{cal['MRV']} Sets/Wo.")
                c4.metric("Empf. Start", f"{cal['recommended_start']} Sets/Wo.")
    else:
        st.info("Noch kein Mesozyklus — Literaturwerte als Referenz.")
        for mg, vol in RP_VOLUMES.items():
            icon = vol.get("icon", "💪")
            with st.expander(f"{icon} **{mg}** — ⚪ Literaturwert", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("MEV", f"{vol['MEV']} Sets/Wo.")
                c2.metric("MAV", f"{vol['MAV_low']}–{vol['MAV_high']} Sets/Wo.")
                c3.metric("MRV", f"{vol['MRV']} Sets/Wo.")
                c4.metric("Empf. Start", f"{vol['MEV']} Sets/Wo.")

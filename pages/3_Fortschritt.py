import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from database import (
    get_mesocycles, get_sets_per_muscle_per_week, get_all_sets_for_exercise,
    get_all_feedback_for_meso, get_workouts, get_sets,
    get_ten_rm, save_ten_rm, get_all_ten_rms
)
from data.rp_volumes import RP_VOLUMES
from data.exercises import EXERCISES
from calibration import calibrate_muscle

st.set_page_config(page_title="Fortschritt", page_icon="📊", layout="wide")
st.title("📊 Fortschritt & Analyse")

mesocycles = get_mesocycles()
if not mesocycles:
    st.info("Noch keine Mesozyklen vorhanden.")
    st.stop()

# Meso selector
meso_options = {f"{m['name']} ({m['start_date']})": m for m in mesocycles}
selected_label = st.selectbox("Mesozyklus auswählen", list(meso_options.keys()))
meso = meso_options[selected_label]

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Volumen", "💪 Stärke", "🎯 Feedback", "🔍 Deload-Analyse", "🧠 Kalibrierung", "⚖️ 10RM"])

# ── Tab 1: Volume per Muscle per Week ─────────────────────────────────────────
with tab1:
    st.subheader("Trainingsvolumen pro Muskelgruppe")
    vol_data = get_sets_per_muscle_per_week(meso["id"])

    if not vol_data:
        st.info("Noch keine Trainingsdaten.")
    else:
        df = pd.DataFrame(vol_data)
        pivot = df.pivot(index="muscle_group", columns="week_number", values="set_count").fillna(0)
        pivot.columns = [f"Woche {c}" for c in pivot.columns]
        pivot = pivot.astype(int)

        # Add RP landmarks
        pivot_display = pivot.copy()
        for mg in pivot.index:
            if mg in RP_VOLUMES:
                vol = RP_VOLUMES[mg]
                pivot_display.loc[mg, "MEV"] = vol["MEV"]
                pivot_display.loc[mg, "MRV"] = vol["MRV"]

        st.dataframe(pivot_display, use_container_width=True)

        # Line chart per muscle
        st.markdown("**Volumen-Verlauf:**")
        chart_data = pivot.T
        st.line_chart(chart_data)

        # Per-muscle volume vs landmarks
        st.markdown("**Volumen vs. RP-Landmarks:**")
        for mg in pivot.index:
            if mg not in RP_VOLUMES:
                continue
            vol = RP_VOLUMES[mg]
            weeks_done = pivot.loc[mg]
            if weeks_done.sum() == 0:
                continue

            cols = st.columns([2, 5])
            with cols[0]:
                last_week_sets = int(weeks_done.iloc[-1])
                zone = (
                    "🟢 MEV" if last_week_sets <= vol["MEV"]
                    else "🟡 MAV" if last_week_sets <= vol["MAV_high"]
                    else "🔴 über MRV"
                )
                st.metric(mg, f"{last_week_sets} Sets", delta=zone)

# ── Tab 2: Strength Progress ──────────────────────────────────────────────────
with tab2:
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
            df["1RM"] = df["weight"] * (1 + df["reps"] / 30)  # Epley formula
            df["volume"] = df["weight"] * df["reps"]

            # Best set per day
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

            st.markdown("**Alle Sets:**")
            st.dataframe(
                df[["date", "week_number", "set_number", "weight", "reps", "rpe"]].rename(columns={
                    "date": "Datum", "week_number": "Woche", "set_number": "Set",
                    "weight": "Gewicht", "reps": "Wdh.", "rpe": "RPE"
                }),
                use_container_width=True, hide_index=True
            )

# ── Tab 3: Session Feedback ───────────────────────────────────────────────────
with tab3:
    st.subheader("Session-Feedback Analyse")

    feedback_data = get_all_feedback_for_meso(meso["id"])
    if not feedback_data:
        st.info("Noch kein Feedback erfasst.")
    else:
        df_fb = pd.DataFrame(feedback_data)
        df_fb["date"] = pd.to_datetime(df_fb["date"])

        perf_labels = {1: "Viel schlechter", 2: "Schlechter", 3: "Gleich", 4: "Besser", 5: "Viel besser"}
        df_fb["performance_label"] = df_fb["performance"].map(perf_labels)

        # Per muscle feedback over time
        muscles = df_fb["muscle_group"].unique()
        selected_fb_mg = st.selectbox("Muskelgruppe", muscles, key="fb_mg")

        df_mg = df_fb[df_fb["muscle_group"] == selected_fb_mg].sort_values("date")

        if not df_mg.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Ø Pump", f"{df_mg['pump'].mean():.1f}/5")
            c2.metric("Ø Soreness", f"{df_mg['soreness'].mean():.1f}/5")
            c3.metric("Ø Performance", f"{df_mg['performance'].mean():.1f}/5")

            chart_df = df_mg.set_index("date")[["pump", "soreness", "performance"]]
            st.line_chart(chart_df)

            st.markdown("**Details:**")
            st.dataframe(
                df_mg[["date", "week_number", "pump", "soreness", "performance_label"]].rename(columns={
                    "date": "Datum", "week_number": "Woche", "pump": "Pump",
                    "soreness": "Soreness", "performance_label": "Performance"
                }),
                use_container_width=True, hide_index=True
            )

# ── Tab 4: Deload Analysis ────────────────────────────────────────────────────
with tab4:
    st.subheader("Deload-Empfehlung")
    st.caption("Basiert auf Feedback-Daten und Volumen-Progression")

    feedback_data = get_all_feedback_for_meso(meso["id"])

    if not feedback_data:
        st.info("Noch nicht genug Daten für eine Analyse.")
    else:
        df_fb = pd.DataFrame(feedback_data)

        st.markdown("**Deload-Indikatoren pro Muskelgruppe:**")

        deload_needed = []
        for mg in meso["muscle_groups"]:
            df_mg = df_fb[df_fb["muscle_group"] == mg]
            if df_mg.empty:
                continue

            last_3 = df_mg.tail(3)
            avg_soreness = last_3["soreness"].mean()
            avg_performance = last_3["performance"].mean()
            avg_pump = last_3["pump"].mean()

            # RP Deload rules:
            # - Soreness consistently high (>3.5) = needs rest
            # - Performance declining (<2.5) = needs rest
            # - Pump low (<2.5) = diminishing returns
            score = 0
            reasons = []
            if avg_soreness > 3.5:
                score += 1
                reasons.append(f"Hohe Soreness ({avg_soreness:.1f}/5)")
            if avg_performance < 2.5:
                score += 1
                reasons.append(f"Sinkende Performance ({avg_performance:.1f}/5)")
            if avg_pump < 2.5:
                score += 1
                reasons.append(f"Niedriger Pump ({avg_pump:.1f}/5)")

            icon = RP_VOLUMES.get(mg, {}).get("icon", "💪")
            status = "🔴 Deload empfohlen" if score >= 2 else ("🟡 Beobachten" if score == 1 else "🟢 Weiter trainieren")

            with st.container():
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
            st.error(
                f"**Deload-Empfehlung:** {', '.join(deload_needed)} zeigen Erholungsdefizite. "
                f"Erwäge eine Deload-Woche mit 50% Volumen und ~70% Intensität."
            )
            if st.button("🔵 Deload-Woche starten"):
                from database import update_mesocycle_status
                update_mesocycle_status(meso["id"], "deload")
                st.success("Deload-Modus aktiviert.")
                st.rerun()

# ── Tab 5: Calibration Report ─────────────────────────────────────────────────
with tab5:
    st.subheader("🧠 Kalibrierungs-Bericht")
    st.caption(
        "Aus deinen Feedback-Daten werden MEV, MAV und MRV für den nächsten Zyklus abgeleitet. "
        "Diese Werte werden im Mesozyklus-Planer automatisch als Startpunkt verwendet."
    )

    muscles_in_meso = meso.get("muscle_groups", [])
    if not muscles_in_meso:
        st.info("Keine Muskelgruppen im Mesozyklus.")
        st.stop()

    cal_rows = []
    for mg in muscles_in_meso:
        cal = calibrate_muscle(meso["id"], mg)
        icon = RP_VOLUMES.get(mg, {}).get("icon", "💪")
        base = RP_VOLUMES.get(mg, {})

        confidence_label = {"high": "🟢 Hoch", "medium": "🟡 Mittel", "low": "⚪ Niedrig"}.get(
            cal.get("confidence", "low"), "⚪"
        )

        with st.expander(f"{icon} **{mg}** — Konfidenz: {confidence_label}", expanded=True):
            col1, col2, col3, col4 = st.columns(4)

            # Show delta vs literature
            base_mev = base.get("MEV", "–")
            base_mrv = base.get("MRV", "–")
            col1.metric(
                "MEV (nächster Meso)",
                f"{cal['MEV']} Sets",
                delta=f"{cal['MEV'] - base_mev:+d} vs. Literatur" if isinstance(base_mev, int) else None
            )
            col2.metric(
                "MAV-Fenster",
                f"{cal['MAV_low']}–{cal['MAV_high']} Sets"
            )
            col3.metric(
                "MRV (nächster Meso)",
                f"{cal['MRV']} Sets",
                delta=f"{cal['MRV'] - base_mrv:+d} vs. Literatur" if isinstance(base_mrv, int) else None
            )
            col4.metric(
                "Empfohlener Start",
                f"{cal['recommended_start']} Sets",
                delta="im MAV" if cal['MAV_low'] <= cal['recommended_start'] <= cal['MAV_high'] else "unter MAV"
            )

            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.info(f"**MEV-Begründung**\n\n{cal['explanations']['MEV']}")
            c2.success(f"**MAV-Begründung**\n\n{cal['explanations']['MAV']}")
            c3.warning(f"**MRV-Begründung**\n\n{cal['explanations']['MRV']}")

            cal_rows.append({
                "Muskelgruppe": mg,
                "MEV (kalibriert)": cal["MEV"],
                "MEV (Literatur)": base.get("MEV", "–"),
                "MAV": f"{cal['MAV_low']}–{cal['MAV_high']}",
                "MRV (kalibriert)": cal["MRV"],
                "MRV (Literatur)": base.get("MRV", "–"),
                "Empf. Start": cal["recommended_start"],
                "Konfidenz": confidence_label,
                "Datenpunkte": cal.get("weeks_with_data", 0),
            })

    if cal_rows:
        st.divider()
        st.markdown("**Gesamtübersicht:**")
        st.dataframe(pd.DataFrame(cal_rows), use_container_width=True, hide_index=True)

        st.info(
            "Diese kalibrierten Werte werden automatisch im **Mesozyklus-Planer** "
            "für deinen nächsten Zyklus verwendet."
        )

# ── Tab 6: 10RM Management ────────────────────────────────────────────────────
with tab6:
    st.subheader("⚖️ 10RM-Werte verwalten")
    st.caption(
        "Das 10RM (maximales Gewicht für 10 saubere Wiederholungen) dient als Basis für alle "
        "Gewichtsvorschläge im Training. Trage hier deine aktuellen Werte ein."
    )

    # Collect all exercises from all muscle groups
    all_exercises = []
    for mg, ex_list in EXERCISES.items():
        for ex in ex_list:
            all_exercises.append({"muscle_group": mg, "name": ex["name"], "sfr": ex.get("sfr", "")})

    # Load existing 10RMs
    existing_rms = get_all_ten_rms()  # dict: exercise_name → weight

    st.markdown("### Gewichte eintragen")

    # Group by muscle group
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
                save_ten_rm(ex_name, weight)
            st.success(f"✅ {len(updated)} Wert(e) gespeichert.")
            st.rerun()

    st.divider()
    st.markdown("### Aktuelle 10RM-Übersicht")
    existing_rms = get_all_ten_rms()
    if existing_rms:
        rm_rows = []
        for ex in all_exercises:
            w = existing_rms.get(ex["name"])
            if w and w > 0:
                from data.rp_volumes import RP_VOLUMES as _RV
                rm_rows.append({
                    "Muskelgruppe": ex["muscle_group"],
                    "Übung": ex["name"],
                    "10RM (kg)": w,
                    "3 RIR (87.5%)": round(w * 0.875 / 2.5) * 2.5,
                    "2 RIR (92.5%)": round(w * 0.925 / 2.5) * 2.5,
                    "1 RIR (97.5%)": round(w * 0.975 / 2.5) * 2.5,
                })
        if rm_rows:
            st.dataframe(pd.DataFrame(rm_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Noch keine 10RM-Werte hinterlegt.")
    else:
        st.info("Noch keine 10RM-Werte hinterlegt.")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from datetime import date
from database import (
    get_mesocycles, get_muscle_configs, create_workout, get_workouts,
    save_set, get_sets, save_feedback, get_feedback, get_sets_per_muscle_per_week,
    update_mesocycle_status
)
from data.rp_volumes import RP_VOLUMES
from data.exercises import EXERCISES

st.set_page_config(page_title="Training", page_icon="🏋️", layout="wide")
st.title("🏋️ Training")

# ── Active mesocycle ──────────────────────────────────────────────────────────
mesocycles = get_mesocycles()
active = [m for m in mesocycles if m["status"] in ("active", "deload")]

if not active:
    st.warning("Kein aktiver Mesozyklus. Bitte zuerst einen Mesozyklus erstellen.")
    if st.button("➕ Mesozyklus erstellen"):
        st.switch_page("pages/1_Mesozyklus.py")
    st.stop()

meso = active[0]
start = date.fromisoformat(meso["start_date"])
days_in = (date.today() - start).days
current_week = min(days_in // 7 + 1, meso["weeks"])
muscle_configs = get_muscle_configs(meso["id"])
split_days: dict = meso.get("split_days") or {}
split_order: list = meso.get("split_order") or list(split_days.keys())

if current_week > meso["weeks"]:
    st.info("🔵 **Deload-Woche** — Reduziere Volumen und Intensität um ~50%")
    if st.button("Deload abschließen & Zyklus beenden"):
        update_mesocycle_status(meso["id"], "completed")
        st.rerun()

st.caption(f"Mesozyklus: **{meso['name']}** | Woche **{current_week}** / **{meso['weeks']}** | Split: **{meso.get('split_template') or 'Manuell'}**")

st.divider()

tab1, tab2 = st.tabs(["▶ Neue Session", "📋 Session-Verlauf"])

with tab1:
    st.subheader("Neue Trainingseinheit")

    col1, col2 = st.columns(2)
    with col1:
        workout_date = st.date_input("Datum", value=date.today())
    with col2:
        week_num = st.number_input(
            "Woche", min_value=1, max_value=meso["weeks"] + 1, value=current_week
        )

    # ── Day selector ──────────────────────────────────────────────────────────
    if split_days:
        st.markdown("**Welcher Trainingstag?**")

        day_cols = st.columns(min(len(split_days), 4))
        selected_day = st.session_state.get("selected_training_day")

        for i, day_name in enumerate(split_order):
            muscles_in_day = split_days.get(day_name, [])
            icons = " ".join(RP_VOLUMES.get(mg, {}).get("icon", "💪") for mg in muscles_in_day)
            is_selected = selected_day == day_name
            label = f"{'✅ ' if is_selected else ''}{day_name}\n{icons}"
            with day_cols[i % len(day_cols)]:
                if st.button(label, key=f"day_{day_name}", use_container_width=True,
                             type="primary" if is_selected else "secondary"):
                    st.session_state["selected_training_day"] = day_name
                    st.rerun()

        selected_day = st.session_state.get("selected_training_day")
        if not selected_day or selected_day not in split_days:
            st.info("Wähle einen Trainingstag um fortzufahren.")
            st.stop()

        session_muscles = split_days[selected_day]
        st.success(f"**{selected_day}**: {', '.join(session_muscles)}")

    else:
        # Fallback: manual muscle selection (no template)
        st.markdown("**Welche Muskelgruppen trainierst du heute?**")
        session_muscles = []
        cols = st.columns(5)
        for i, mg in enumerate(meso["muscle_groups"]):
            icon = RP_VOLUMES.get(mg, {}).get("icon", "💪")
            if cols[i % 5].checkbox(f"{icon} {mg}", key=f"sess_{mg}"):
                session_muscles.append(mg)

        if not session_muscles:
            st.info("Wähle die Muskelgruppen für die heutige Einheit.")
            st.stop()

    st.divider()

    # ── Set logging per muscle ────────────────────────────────────────────────
    session_sets = {}

    for mg in session_muscles:
        vol = RP_VOLUMES.get(mg, {})
        cfg = muscle_configs.get(mg, {})
        exercises = cfg.get("exercises", [e["name"] for e in EXERCISES.get(mg, [])][:2])

        start_sets = cfg.get("start_sets", vol.get("MEV", 8))
        if current_week > meso["weeks"]:
            target_sets = max(vol.get("MEV", 6) - 2, 2)
        else:
            target_sets = min(start_sets + (week_num - 1) * 2, vol.get("MRV", 20))

        with st.expander(
            f"{vol.get('icon', '💪')} {mg} — Ziel: {target_sets} Sets",
            expanded=True
        ):
            all_options = [e["name"] for e in EXERCISES.get(mg, [])]
            chosen_ex = st.selectbox(
                "Übung",
                options=all_options,
                index=all_options.index(exercises[0]) if exercises and exercises[0] in all_options else 0,
                key=f"ex_sel_{mg}"
            )

            num_sets = st.number_input(
                "Anzahl Sets",
                min_value=1, max_value=target_sets + 4,
                value=min(target_sets, 6),
                key=f"nsets_{mg}"
            )

            set_cols_header = st.columns([1, 2, 2, 2])
            set_cols_header[0].caption("Set")
            set_cols_header[1].caption("Gewicht (kg)")
            set_cols_header[2].caption("Wdh.")
            set_cols_header[3].caption("RPE")

            mg_sets = []
            for s in range(1, int(num_sets) + 1):
                sc = st.columns([1, 2, 2, 2])
                sc[0].markdown(f"**{s}**")
                weight = sc[1].number_input("", min_value=0.0, step=2.5,
                                            key=f"w_{mg}_{s}", label_visibility="collapsed")
                reps = sc[2].number_input("", min_value=1, max_value=50, value=10,
                                          key=f"r_{mg}_{s}", label_visibility="collapsed")
                rpe = sc[3].select_slider(
                    "", options=[6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0],
                    value=8.0, key=f"rpe_{mg}_{s}", label_visibility="collapsed"
                )
                mg_sets.append({"exercise": chosen_ex, "set": s, "weight": weight,
                                 "reps": reps, "rpe": rpe})
            session_sets[mg] = mg_sets

            st.markdown("**Session-Feedback**")
            fc = st.columns(3)
            pump = fc[0].slider("Pump 💉", 1, 5, 3, key=f"pump_{mg}")
            soreness = fc[1].slider("Soreness 😣", 1, 5, 3, key=f"sor_{mg}")
            performance = fc[2].select_slider(
                "Performance",
                options=["Viel schlechter", "Schlechter", "Gleich", "Besser", "Viel besser"],
                value="Gleich", key=f"perf_{mg}"
            )
            session_sets[mg + "__feedback"] = {
                "pump": pump, "soreness": soreness, "performance": performance
            }

    st.divider()
    notes = st.text_area("Session-Notizen", placeholder="Wie war das Training insgesamt?")

    if st.button("💾 Session speichern", type="primary"):
        workout_id = create_workout(meso["id"], workout_date, week_num, notes)
        perf_map = {"Viel schlechter": 1, "Schlechter": 2, "Gleich": 3, "Besser": 4, "Viel besser": 5}

        for mg in session_muscles:
            for s_data in session_sets.get(mg, []):
                save_set(workout_id, mg, s_data["exercise"], s_data["set"],
                         s_data["weight"], s_data["reps"], s_data["rpe"])
            fb = session_sets.get(mg + "__feedback", {})
            if fb:
                save_feedback(workout_id, mg, fb["pump"], fb["soreness"],
                              perf_map.get(fb["performance"], 3), notes)

        # Clear day selection after saving
        if "selected_training_day" in st.session_state:
            del st.session_state["selected_training_day"]

        st.success("✅ Session gespeichert!")
        st.rerun()

# ── Workout History ───────────────────────────────────────────────────────────
with tab2:
    st.subheader("Bisherige Sessions")
    workouts = get_workouts(meso["id"])

    if not workouts:
        st.info("Noch keine Sessions für diesen Mesozyklus.")
    else:
        for w in workouts:
            with st.expander(f"📅 {w['date']} — Woche {w['week_number']}"):
                sets = get_sets(w["id"])
                if sets:
                    import pandas as pd
                    df = pd.DataFrame(sets)[["muscle_group", "exercise", "set_number", "weight", "reps", "rpe"]]
                    df.columns = ["Muskelgruppe", "Übung", "Set", "Gewicht", "Wdh.", "RPE"]
                    st.dataframe(df, use_container_width=True, hide_index=True)

                for fb in get_feedback(w["id"]):
                    perf_labels = {1: "Viel schlechter", 2: "Schlechter", 3: "Gleich",
                                   4: "Besser", 5: "Viel besser"}
                    st.caption(
                        f"**{fb['muscle_group']}**: Pump {fb['pump']}/5 | "
                        f"Soreness {fb['soreness']}/5 | Performance: {perf_labels.get(fb['performance'], '?')}"
                    )
                if w.get("notes"):
                    st.caption(f"📝 {w['notes']}")

    st.divider()
    st.subheader("Volumen-Übersicht")
    vol_data = get_sets_per_muscle_per_week(meso["id"])
    if vol_data:
        import pandas as pd
        df_vol = pd.DataFrame(vol_data)
        pivot = df_vol.pivot(index="muscle_group", columns="week_number",
                             values="set_count").fillna(0)
        pivot.columns = [f"Woche {c}" for c in pivot.columns]
        st.dataframe(pivot.astype(int), use_container_width=True)

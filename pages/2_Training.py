import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import date
from database import (
    get_mesocycles, get_muscle_configs, create_workout, get_workouts,
    save_set, get_sets, save_feedback, get_feedback, get_sets_per_muscle_per_week,
    update_mesocycle_status, get_ten_rm, save_ten_rm, get_all_ten_rms
)
from data.rp_volumes import RP_VOLUMES
from data.exercises import EXERCISES

st.set_page_config(page_title="Training", page_icon="🏋️", layout="wide")
st.title("🏋️ Training")

# ── RIR target per week (RP methodology) ─────────────────────────────────────
# Week 1 → easiest (body adapting to exercises), last week → hardest

def get_rir_target(week: int, total_weeks: int, is_deload: bool) -> dict:
    """Returns target RIR range and description for a given week."""
    if is_deload:
        return {"low": 4, "high": 5, "label": "4–5 RIR", "desc": "Deload — sehr leicht", "color": "info"}

    # Linearly progress from 3-4 RIR (week 1) down to 0-1 RIR (last week)
    # Normalised position in the meso (0.0 = first week, 1.0 = last week)
    pos = (week - 1) / max(total_weeks - 1, 1)

    if pos <= 0.25:
        return {"low": 3, "high": 4, "label": "3–4 RIR", "desc": "Eingewöhnung — leichter Einstieg", "color": "info"}
    elif pos <= 0.5:
        return {"low": 2, "high": 3, "label": "2–3 RIR", "desc": "Aufbauend — moderate Intensität", "color": "success"}
    elif pos <= 0.75:
        return {"low": 1, "high": 2, "label": "1–2 RIR", "desc": "Fordernd — nah ans Versagen", "color": "warning"}
    else:
        return {"low": 0, "high": 1, "label": "0–1 RIR", "desc": "Maximale Anstrengung — letzter Zyklusteil", "color": "error"}


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
is_deload = current_week > meso["weeks"] or meso["status"] == "deload"
muscle_configs = get_muscle_configs(meso["id"])
split_days: dict = meso.get("split_days") or {}
split_order: list = meso.get("split_order") or list(split_days.keys())

# ── Week banner ───────────────────────────────────────────────────────────────
if is_deload:
    st.info("🔵 **Deload-Woche** — Reduziere Volumen um ~50%, Gewicht um ~30%")
    if st.button("Deload abschließen & Zyklus beenden"):
        update_mesocycle_status(meso["id"], "completed")
        st.rerun()
    rir = get_rir_target(current_week, meso["weeks"], is_deload=True)
else:
    rir = get_rir_target(current_week, meso["weeks"], is_deload=False)

# ── RIR week overview strip ───────────────────────────────────────────────────
st.markdown(f"**{meso['name']}** · Split: {meso.get('split_template') or 'Manuell'}")

week_cols = st.columns(meso["weeks"] + 1)
for w in range(1, meso["weeks"] + 1):
    r = get_rir_target(w, meso["weeks"], is_deload=False)
    is_now = (w == current_week and not is_deload)
    label = f"**W{w}**\n{r['label']}" if is_now else f"W{w}\n{r['label']}"
    week_cols[w - 1].markdown(
        f"<div style='text-align:center; padding:6px 2px; border-radius:6px; "
        f"background:{'#1f4e79' if is_now else 'transparent'}; "
        f"color:{'white' if is_now else 'inherit'}; font-size:0.8em'>{label}</div>",
        unsafe_allow_html=True
    )
# Deload column
dl_r = get_rir_target(0, meso["weeks"], is_deload=True)
week_cols[meso["weeks"]].markdown(
    f"<div style='text-align:center; padding:6px 2px; border-radius:6px; "
    f"background:{'#1f4e79' if is_deload else 'transparent'}; "
    f"color:{'white' if is_deload else 'inherit'}; font-size:0.8em'>"
    f"{'**' if is_deload else ''}Deload\n{dl_r['label']}{'**' if is_deload else ''}</div>",
    unsafe_allow_html=True
)

# Current week RIR callout
getattr(st, rir["color"])(
    f"**Ziel diese Woche (Woche {current_week if not is_deload else 'Deload'}): "
    f"{rir['label']}** — {rir['desc']}"
)

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
        # Recalculate RIR if user manually changes week
        rir = get_rir_target(week_num, meso["weeks"], is_deload=(week_num > meso["weeks"]))

    # ── Day selector ──────────────────────────────────────────────────────────
    if split_days:
        st.markdown("**Welcher Trainingstag?**")
        day_cols = st.columns(min(len(split_days), 4))
        selected_day = st.session_state.get("selected_training_day")

        for i, day_name in enumerate(split_order):
            muscles_in_day = split_days.get(day_name, [])
            icons = " ".join(RP_VOLUMES.get(mg, {}).get("icon", "💪") for mg in muscles_in_day)
            is_selected = selected_day == day_name
            with day_cols[i % len(day_cols)]:
                if st.button(
                    f"{'✅ ' if is_selected else ''}{day_name}\n{icons}",
                    key=f"day_{day_name}", use_container_width=True,
                    type="primary" if is_selected else "secondary"
                ):
                    st.session_state["selected_training_day"] = day_name
                    st.rerun()

        selected_day = st.session_state.get("selected_training_day")
        if not selected_day or selected_day not in split_days:
            st.info("Wähle einen Trainingstag um fortzufahren.")
            st.stop()

        session_muscles = split_days[selected_day]
        st.success(f"**{selected_day}**: {', '.join(session_muscles)}")
    else:
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

    def suggested_weight(ten_rm: float, rir_low: int, rir_high: int) -> float:
        """Weight suggestion based on 10RM and target RIR range.
        Each RIR ≈ 2.5% of 10RM. At 0 RIR = 100% of 10RM."""
        rir_mid = (rir_low + rir_high) / 2
        raw = ten_rm * (1 - rir_mid * 0.025)
        # Round to nearest 2.5 kg
        return round(raw / 2.5) * 2.5

    def recommended_exercises(sets: int) -> tuple[int, str]:
        """Returns (count, reason) based on weekly set volume."""
        if sets <= 8:
            return 1, "≤8 Sets — eine Übung reicht"
        elif sets <= 14:
            return 2, "8–14 Sets — 2 Übungen für bessere Qualität"
        else:
            return 3, ">14 Sets — 2–3 Übungen, um Erschöpfung zu verteilen"

    session_sets = {}

    for mg in session_muscles:
        vol = RP_VOLUMES.get(mg, {})
        cfg = muscle_configs.get(mg, {})
        exercises = cfg.get("exercises", [e["name"] for e in EXERCISES.get(mg, [])][:2])

        start_sets = cfg.get("start_sets", vol.get("MEV", 8))
        deload_sets = max(vol.get("MEV", 6) - 2, 2)
        if week_num > meso["weeks"]:
            target_sets = deload_sets
        else:
            target_sets = min(start_sets + (week_num - 1) * 2, vol.get("MRV", 20))

        with st.expander(
            f"{vol.get('icon', '💪')} **{mg}** — Ziel: {target_sets} Sets · RIR {rir['label']}",
            expanded=True
        ):
            st.caption(
                f"Führe jeden Arbeitssatz so aus, dass du am Ende noch **{rir['low']}–{rir['high']} Wdh. "
                f"in Reserve** hättest. {rir['desc']}."
            )

            all_options = [e["name"] for e in EXERCISES.get(mg, [])]

            # ── Per-exercise blocks ───────────────────────────────────────────
            rec_count, rec_reason = recommended_exercises(target_sets)
            st.info(f"💡 Empfehlung: **{rec_count} Übung{'en' if rec_count > 1 else ''}** — {rec_reason}")

            ex_count_key = f"ex_count_{mg}"
            prev_count_key = f"ex_count_prev_{mg}"
            if ex_count_key not in st.session_state:
                st.session_state[ex_count_key] = rec_count

            # If exercise count changed, reset all nsets so suggested values apply cleanly
            if st.session_state.get(prev_count_key) != st.session_state[ex_count_key]:
                for i in range(st.session_state[ex_count_key] + 2):
                    st.session_state.pop(f"nsets_{mg}_{i}", None)
                st.session_state[prev_count_key] = st.session_state[ex_count_key]

            mg_sets = []
            sets_logged = 0

            for ex_idx in range(st.session_state[ex_count_key]):
                st.markdown(f"**Übung {ex_idx + 1}**")
                ec = st.columns([4, 1])

                default_ex = exercises[ex_idx] if ex_idx < len(exercises) else exercises[0] if exercises else all_options[0]
                chosen_ex = ec[0].selectbox(
                    "Übung",
                    options=all_options,
                    index=all_options.index(default_ex) if default_ex in all_options else 0,
                    key=f"ex_sel_{mg}_{ex_idx}",
                    label_visibility="collapsed"
                )

                # 10RM input + weight suggestion
                stored_10rm = get_ten_rm(chosen_ex)
                trm_col1, trm_col2 = st.columns([2, 3])
                ten_rm_val = trm_col1.number_input(
                    "10RM (kg)",
                    min_value=0.0, step=2.5,
                    value=float(stored_10rm) if stored_10rm else 0.0,
                    key=f"tenrm_{mg}_{ex_idx}",
                    help="Dein maximales Gewicht für 10 saubere Wiederholungen"
                )
                if ten_rm_val > 0:
                    if stored_10rm != ten_rm_val:
                        save_ten_rm(chosen_ex, ten_rm_val)
                    w_suggested = suggested_weight(ten_rm_val, rir["low"], rir["high"])
                    trm_col2.success(
                        f"Vorgeschlagenes Gewicht diese Woche: **{w_suggested:.1f} kg** "
                        f"({100 - (rir['low'] + rir['high']) / 2 * 2.5:.0f}% vom 10RM · {rir['label']})"
                    )

                # Split target sets evenly across all exercise blocks
                total_ex = st.session_state[ex_count_key]
                base = target_sets // total_ex
                # last exercise gets the remainder
                suggested = base + (target_sets % total_ex) if ex_idx == total_ex - 1 else base
                suggested = max(1, suggested)

                num_sets = ec[1].number_input(
                    "Sets",
                    min_value=1, max_value=target_sets + 4,
                    value=suggested,
                    key=f"nsets_{mg}_{ex_idx}",
                    label_visibility="collapsed"
                )

                hc = st.columns([1, 2, 2, 3])
                hc[0].caption("Set")
                hc[1].caption("Gewicht (kg)")
                hc[2].caption("Wdh.")
                hc[3].caption(f"RIR (Ziel: {rir['label']})")

                global_set = sets_logged + 1
                for s in range(1, int(num_sets) + 1):
                    sc = st.columns([1, 2, 2, 3])
                    sc[0].markdown(f"**{global_set}**")
                    w_default = suggested_weight(ten_rm_val, rir["low"], rir["high"]) if ten_rm_val > 0 else 0.0
                    weight = sc[1].number_input(
                        "", min_value=0.0, step=2.5,
                        value=w_default,
                        key=f"w_{mg}_{ex_idx}_{s}", label_visibility="collapsed"
                    )
                    reps = sc[2].number_input(
                        "", min_value=1, max_value=50, value=10,
                        key=f"r_{mg}_{ex_idx}_{s}", label_visibility="collapsed"
                    )
                    rir_actual = sc[3].select_slider(
                        "", options=[0, 1, 2, 3, 4, 5, 6],
                        value=rir["low"],
                        format_func=lambda x: f"{x} RIR",
                        key=f"rir_{mg}_{ex_idx}_{s}", label_visibility="collapsed"
                    )
                    if rir_actual > rir["high"] + 1:
                        sc[3].caption("⬆️ zu leicht")
                    elif rir_actual < rir["low"] - 1:
                        sc[3].caption("⬇️ zu schwer")

                    mg_sets.append({
                        "exercise": chosen_ex, "set": global_set,
                        "weight": weight, "reps": reps, "rir": rir_actual
                    })
                    global_set += 1

                sets_logged += int(num_sets)

                if st.session_state[ex_count_key] > 1:
                    if st.button(f"✕ Übung {ex_idx + 1} entfernen", key=f"rem_ex_{mg}_{ex_idx}"):
                        st.session_state[ex_count_key] = max(1, st.session_state[ex_count_key] - 1)
                        st.rerun()

                if ex_idx < st.session_state[ex_count_key] - 1:
                    st.divider()

            # Total sets indicator
            zone_color = "🟢" if sets_logged == target_sets else ("🟡" if abs(sets_logged - target_sets) <= 2 else "🔴")
            st.caption(f"{zone_color} {sets_logged} / {target_sets} Ziel-Sets")

            if st.button(f"➕ Übung hinzufügen ({mg})", key=f"add_ex_{mg}"):
                st.session_state[ex_count_key] += 1
                st.rerun()

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
                # Store RIR in the rpe column for backwards compatibility
                save_set(workout_id, mg, s_data["exercise"], s_data["set"],
                         s_data["weight"], s_data["reps"], s_data["rir"])
            fb = session_sets.get(mg + "__feedback", {})
            if fb:
                save_feedback(workout_id, mg, fb["pump"], fb["soreness"],
                              perf_map.get(fb["performance"], 3), notes)

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
            w_rir = get_rir_target(w["week_number"], meso["weeks"],
                                   is_deload=(w["week_number"] > meso["weeks"]))
            with st.expander(
                f"📅 {w['date']} — Woche {w['week_number']} · Ziel war {w_rir['label']}"
            ):
                sets = get_sets(w["id"])
                if sets:
                    df = pd.DataFrame(sets)[["muscle_group", "exercise", "set_number", "weight", "reps", "rpe"]]
                    df.columns = ["Muskelgruppe", "Übung", "Set", "Gewicht", "Wdh.", "RIR"]
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
        df_vol = pd.DataFrame(vol_data)
        pivot = df_vol.pivot(index="muscle_group", columns="week_number",
                             values="set_count").fillna(0)
        pivot.columns = [f"Woche {c}" for c in pivot.columns]
        st.dataframe(pivot.astype(int), use_container_width=True)

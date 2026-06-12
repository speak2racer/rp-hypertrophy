import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import date
from database import (
    get_mesocycles, get_muscle_configs, create_workout, get_workouts,
    save_set, get_sets, save_feedback, get_feedback, get_sets_per_muscle_per_week,
    update_mesocycle_status, get_ten_rm, save_ten_rm
)
from data.rp_volumes import RP_VOLUMES
from data.exercises import EXERCISES

st.set_page_config(page_title="Training", page_icon="🏋️", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.set-row { display:flex; gap:8px; align-items:center; padding:4px 0; border-bottom:1px solid #333; }
.week-badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }
.rir-banner { padding:10px 16px; border-radius:8px; font-size:1rem; font-weight:600; margin-bottom:8px; }
div[data-testid="stNumberInput"] input { text-align:center; }
</style>
""", unsafe_allow_html=True)

# ── RIR logic (RP: 3→3→2→2→1 for 5 weeks) ───────────────────────────────────

def week_rir(week: int, total_weeks: int) -> int:
    """Single RIR target per week. Blocks: first third=3, middle=2, last third=1."""
    if week > total_weeks:
        return 4  # deload
    import math
    b1 = math.ceil(total_weeks / 3)
    b2 = math.ceil(2 * total_weeks / 3)
    if week <= b1:
        return 3
    elif week <= b2:
        return 2
    return 1

RIR_CONFIG = {
    4: {"label": "Deload",  "pct": 0.875, "color": "#1a73e8", "bg": "#0d2a4a"},
    3: {"label": "3 RIR",   "pct": 0.875, "color": "#34a853", "bg": "#0d2a17"},
    2: {"label": "2 RIR",   "pct": 0.925, "color": "#fbbc04", "bg": "#2a2000"},
    1: {"label": "1 RIR",   "pct": 0.975, "color": "#ea4335", "bg": "#2a0d0a"},
    0: {"label": "0 RIR",   "pct": 1.0,   "color": "#ea4335", "bg": "#2a0d0a"},
}

def suggested_weight(ten_rm: float, rir: int) -> float:
    pct = RIR_CONFIG.get(rir, RIR_CONFIG[2])["pct"]
    return round(ten_rm * pct / 2.5) * 2.5

def recommended_exercises(sets: int) -> int:
    if sets <= 8:  return 1
    if sets <= 14: return 2
    return 3

# ── Active mesocycle ──────────────────────────────────────────────────────────
mesocycles = get_mesocycles()
active = [m for m in mesocycles if m["status"] in ("active", "deload")]

if not active:
    st.title("🏋️ Training")
    st.warning("Kein aktiver Mesozyklus.")
    if st.button("➕ Mesozyklus erstellen", type="primary"):
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

# ── Header ────────────────────────────────────────────────────────────────────
display_week = current_week if not is_deload else meso["weeks"] + 1
rir = week_rir(current_week, meso["weeks"]) if not is_deload else 4
rcfg = RIR_CONFIG[rir]

col_title, col_meta = st.columns([3, 2])
col_title.title("🏋️ Training")
with col_meta:
    st.markdown(f"""
    <div style='text-align:right; padding-top:12px'>
        <span style='font-size:0.85rem; color:#888'>{meso['name']} · {meso.get('split_template','')}</span><br>
        <span style='font-size:1.1rem; font-weight:700'>
            Woche {display_week}/{meso['weeks']}
            &nbsp;
            <span style='color:{rcfg["color"]}'>● {rcfg["label"]}</span>
        </span>
    </div>
    """, unsafe_allow_html=True)

# Week progress bar
if not is_deload:
    cols_w = st.columns(meso["weeks"] + 1)
    for w in range(1, meso["weeks"] + 1):
        r = week_rir(w, meso["weeks"])
        rc = RIR_CONFIG[r]
        is_now = w == current_week
        cols_w[w-1].markdown(
            f"<div style='text-align:center;padding:5px 2px;border-radius:6px;"
            f"background:{'#1f3a5f' if is_now else 'transparent'};"
            f"border:{'2px solid ' + rc['color'] if is_now else '1px solid #333'};"
            f"font-size:0.75rem'>"
            f"<b>W{w}</b><br><span style='color:{rc['color']}'>{rc['label']}</span></div>",
            unsafe_allow_html=True
        )
    cols_w[meso["weeks"]].markdown(
        "<div style='text-align:center;padding:5px 2px;border-radius:6px;"
        "border:1px solid #333;font-size:0.75rem'>"
        "<b>DL</b><br><span style='color:#1a73e8'>Deload</span></div>",
        unsafe_allow_html=True
    )
else:
    st.info("🔵 **Deload** — 2 Sets, ~87% vom 10RM, ~halbe Wdh.")
    if st.button("Deload abschließen"):
        update_mesocycle_status(meso["id"], "completed")
        st.rerun()

# RIR banner
st.markdown(
    f"<div style='background:{rcfg['bg']};border-left:4px solid {rcfg['color']};"
    f"padding:8px 14px;border-radius:4px;margin:8px 0;font-size:0.9rem'>"
    f"<b style='color:{rcfg['color']}'>{rcfg['label']}</b> — "
    f"Stoppe jeden Satz wenn du noch <b>{rir} Wdh.</b> in Reserve hast. "
    f"Gewichtszone: <b>{int(rcfg['pct']*100)}% vom 10RM</b></div>",
    unsafe_allow_html=True
)

st.divider()

tab_new, tab_history = st.tabs(["▶ Neue Session", "📋 Verlauf"])

with tab_new:
    # ── Session meta ──────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    workout_date = c1.date_input("Datum", value=date.today())
    week_num = c2.number_input("Woche", min_value=1,
                               max_value=meso["weeks"] + 1, value=current_week)
    active_rir = week_rir(week_num, meso["weeks"]) if week_num <= meso["weeks"] else 4

    # ── Day selector ──────────────────────────────────────────────────────────
    if split_days:
        st.markdown("##### Trainingstag")
        n = min(len(split_days), 6)
        day_cols = st.columns(n)
        selected_day = st.session_state.get("selected_training_day")

        for i, day_name in enumerate(split_order):
            muscles_in_day = split_days.get(day_name, [])
            icons = "".join(RP_VOLUMES.get(mg, {}).get("icon", "💪") for mg in muscles_in_day)
            is_sel = selected_day == day_name
            rc_day = RIR_CONFIG[active_rir]
            with day_cols[i % n]:
                btn_style = f"background:{rc_day['bg']};border:2px solid {rc_day['color']}" if is_sel else ""
                if st.button(
                    f"{'✓ ' if is_sel else ''}{day_name}\n{icons}",
                    key=f"day_{day_name}",
                    use_container_width=True,
                    type="primary" if is_sel else "secondary"
                ):
                    st.session_state["selected_training_day"] = day_name
                    # clear ex counts when day changes
                    for k in list(st.session_state.keys()):
                        if k.startswith("ex_count_") or k.startswith("ex_count_prev_"):
                            del st.session_state[k]
                    st.rerun()

        selected_day = st.session_state.get("selected_training_day")
        if not selected_day or selected_day not in split_days:
            st.info("Wähle einen Trainingstag.")
            st.stop()
        session_muscles = split_days[selected_day]

    else:
        session_muscles = []
        for mg in meso["muscle_groups"]:
            icon = RP_VOLUMES.get(mg, {}).get("icon", "💪")
            if st.checkbox(f"{icon} {mg}", key=f"sess_{mg}"):
                session_muscles.append(mg)
        if not session_muscles:
            st.info("Wähle Muskelgruppen.")
            st.stop()

    st.divider()

    # ── Exercise blocks ───────────────────────────────────────────────────────
    session_sets = {}
    rcfg_active = RIR_CONFIG[active_rir]

    for mg in session_muscles:
        vol = RP_VOLUMES.get(mg, {})
        cfg = muscle_configs.get(mg, {})
        exercises = cfg.get("exercises", [e["name"] for e in EXERCISES.get(mg, [])][:2])
        start_sets = cfg.get("start_sets", vol.get("MEV", 8))
        target_sets = (max(vol.get("MEV", 6) - 2, 2) if week_num > meso["weeks"]
                       else min(start_sets + (week_num - 1) * 2, vol.get("MRV", 20)))

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin-top:16px;margin-bottom:4px'>"
            f"<span style='font-size:1.3rem'>{vol.get('icon','💪')}</span>"
            f"<span style='font-size:1.1rem;font-weight:700'>{mg}</span>"
            f"<span style='color:#888;font-size:0.85rem'>Ziel: {target_sets} Sets &nbsp;·&nbsp; "
            f"<span style='color:{rcfg_active['color']}'>{rcfg_active['label']}</span></span>"
            f"</div>",
            unsafe_allow_html=True
        )

        all_options = [e["name"] for e in EXERCISES.get(mg, [])]
        rec_ex = recommended_exercises(target_sets)

        ex_count_key = f"ex_count_{mg}"
        prev_count_key = f"ex_count_prev_{mg}"
        if ex_count_key not in st.session_state:
            st.session_state[ex_count_key] = rec_ex
        if st.session_state.get(prev_count_key) != st.session_state[ex_count_key]:
            for i in range(st.session_state[ex_count_key] + 2):
                st.session_state.pop(f"nsets_{mg}_{i}", None)
            st.session_state[prev_count_key] = st.session_state[ex_count_key]

        mg_sets = []
        sets_logged = 0

        for ex_idx in range(st.session_state[ex_count_key]):
            with st.container(border=True):
                # Exercise selector + sets count
                h1, h2, h3 = st.columns([5, 1, 1])
                default_ex = (exercises[ex_idx] if ex_idx < len(exercises)
                              else exercises[0] if exercises else all_options[0] if all_options else "")
                chosen_ex = h1.selectbox(
                    "Übung", options=all_options,
                    index=all_options.index(default_ex) if default_ex in all_options else 0,
                    key=f"ex_sel_{mg}_{ex_idx}", label_visibility="collapsed"
                )

                total_ex = st.session_state[ex_count_key]
                base = target_sets // total_ex
                suggested_sets = base + (target_sets % total_ex) if ex_idx == total_ex - 1 else base
                num_sets = h2.number_input(
                    "Sets", min_value=1, max_value=target_sets + 6,
                    value=max(1, suggested_sets),
                    key=f"nsets_{mg}_{ex_idx}", label_visibility="collapsed"
                )

                # 10RM + weight suggestion
                stored_10rm = get_ten_rm(chosen_ex)
                r1, r2 = st.columns([2, 3])
                ten_rm_val = r1.number_input(
                    "10RM (kg)", min_value=0.0, step=2.5,
                    value=float(stored_10rm) if stored_10rm else 0.0,
                    key=f"tenrm_{mg}_{ex_idx}",
                    help="Maximales Gewicht für 10 saubere Wiederholungen"
                )
                if ten_rm_val > 0:
                    if stored_10rm != ten_rm_val:
                        save_ten_rm(chosen_ex, ten_rm_val)
                    w_sug = suggested_weight(ten_rm_val, active_rir)
                    r2.markdown(
                        f"<div style='padding:8px;border-radius:4px;background:{rcfg_active['bg']};"
                        f"border:1px solid {rcfg_active['color']};margin-top:4px;font-size:0.85rem'>"
                        f"Vorschlag: <b style='font-size:1.1rem'>{w_sug:.1f} kg</b> "
                        f"<span style='color:#888'>({int(rcfg_active['pct']*100)}% · {rcfg_active['label']})</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    w_default = suggested_weight(ten_rm_val, active_rir)
                else:
                    w_default = 0.0

                # Set table
                st.markdown(
                    f"<div style='display:grid;grid-template-columns:30px 1fr 1fr 1fr;gap:4px;"
                    f"padding:4px 0;color:#888;font-size:0.75rem;font-weight:600'>"
                    f"<div>#</div><div>Gewicht kg</div><div>Wdh.</div>"
                    f"<div>RIR <span style='color:{rcfg_active['color']}'>(Ziel: {active_rir})</span></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                global_set = sets_logged + 1
                for s in range(1, int(num_sets) + 1):
                    sc = st.columns([1, 3, 3, 3])
                    sc[0].markdown(f"<div style='padding-top:8px;color:#888'>{global_set}</div>",
                                   unsafe_allow_html=True)
                    weight = sc[1].number_input(
                        "", min_value=0.0, step=2.5, value=w_default,
                        key=f"w_{mg}_{ex_idx}_{s}", label_visibility="collapsed"
                    )
                    reps = sc[2].number_input(
                        "", min_value=1, max_value=50, value=10,
                        key=f"r_{mg}_{ex_idx}_{s}", label_visibility="collapsed"
                    )
                    rir_actual = sc[3].selectbox(
                        "", options=[0, 1, 2, 3, 4, 5, 6],
                        index=active_rir,
                        format_func=lambda x: f"{x} RIR{'  ⬆️' if x > active_rir + 1 else ('  ⬇️' if x < active_rir - 1 else '')}",
                        key=f"rir_{mg}_{ex_idx}_{s}", label_visibility="collapsed"
                    )
                    mg_sets.append({
                        "exercise": chosen_ex, "set": global_set,
                        "weight": weight, "reps": reps, "rir": rir_actual
                    })
                    global_set += 1

                sets_logged += int(num_sets)

                # Remove exercise button (if more than 1)
                if st.session_state[ex_count_key] > 1:
                    if h3.button("✕", key=f"rem_ex_{mg}_{ex_idx}",
                                 help="Übung entfernen"):
                        st.session_state[ex_count_key] -= 1
                        st.rerun()

        # Sets indicator + add exercise
        indicator_col, btn_col = st.columns([3, 2])
        diff = sets_logged - target_sets
        if diff == 0:
            indicator_col.markdown(f"<span style='color:#34a853'>✓ {sets_logged} Sets</span>",
                                   unsafe_allow_html=True)
        elif diff < 0:
            indicator_col.markdown(
                f"<span style='color:#fbbc04'>{sets_logged}/{target_sets} Sets "
                f"({diff} unter Ziel)</span>", unsafe_allow_html=True)
        else:
            indicator_col.markdown(
                f"<span style='color:#ea4335'>{sets_logged}/{target_sets} Sets "
                f"(+{diff} über Ziel)</span>", unsafe_allow_html=True)

        if btn_col.button(f"➕ Übung", key=f"add_ex_{mg}", use_container_width=True):
            st.session_state[ex_count_key] += 1
            st.rerun()

        session_sets[mg] = mg_sets

        # Compact feedback
        with st.expander("Feedback nach letztem Set", expanded=False):
            fc = st.columns(3)
            pump = fc[0].slider("Pump 💉", 1, 5, 3, key=f"pump_{mg}")
            soreness = fc[1].slider("Soreness 😣", 1, 5, 3, key=f"sor_{mg}")
            perf = fc[2].select_slider(
                "Performance",
                options=["–2", "–1", "=", "+1", "+2"],
                value="=", key=f"perf_{mg}"
            )
        session_sets[mg + "__feedback"] = {"pump": pump, "soreness": soreness, "performance": perf}

    st.divider()
    notes = st.text_area("Notizen", placeholder="Wie war die Session?", label_visibility="collapsed")

    if st.button("💾 Session speichern", type="primary", use_container_width=True):
        workout_id = create_workout(meso["id"], workout_date, week_num, notes)
        perf_map = {"–2": 1, "–1": 2, "=": 3, "+1": 4, "+2": 5}
        for mg in session_muscles:
            for s_data in session_sets.get(mg, []):
                save_set(workout_id, mg, s_data["exercise"], s_data["set"],
                         s_data["weight"], s_data["reps"], s_data["rir"])
            fb = session_sets.get(mg + "__feedback", {})
            if fb:
                save_feedback(workout_id, mg, fb["pump"], fb["soreness"],
                              perf_map.get(fb["performance"], 3), notes)
        for k in list(st.session_state.keys()):
            if k.startswith("ex_count") or k == "selected_training_day":
                del st.session_state[k]
        st.success("✅ Gespeichert!")
        st.rerun()

# ── History tab ───────────────────────────────────────────────────────────────
with tab_history:
    workouts = get_workouts(meso["id"])
    if not workouts:
        st.info("Noch keine Sessions.")
    else:
        for w in workouts:
            w_rir = week_rir(w["week_number"], meso["weeks"])
            rc = RIR_CONFIG.get(w_rir, RIR_CONFIG[2])
            with st.expander(
                f"📅 {w['date']} · Woche {w['week_number']} · "
                f"{rc['label']}"
            ):
                sets = get_sets(w["id"])
                if sets:
                    df = pd.DataFrame(sets)[["muscle_group", "exercise", "set_number", "weight", "reps", "rpe"]]
                    df.columns = ["Muskel", "Übung", "Set", "kg", "Wdh.", "RIR"]
                    st.dataframe(df, use_container_width=True, hide_index=True)
                for fb in get_feedback(w["id"]):
                    perf_l = {1: "–2", 2: "–1", 3: "=", 4: "+1", 5: "+2"}
                    st.caption(
                        f"**{fb['muscle_group']}** · "
                        f"Pump {fb['pump']}/5 · Soreness {fb['soreness']}/5 · "
                        f"Performance {perf_l.get(fb['performance'], '?')}"
                    )
                if w.get("notes"):
                    st.caption(f"📝 {w['notes']}")

    st.divider()
    vol_data = get_sets_per_muscle_per_week(meso["id"])
    if vol_data:
        st.subheader("Volumen")
        df_vol = pd.DataFrame(vol_data)
        pivot = df_vol.pivot(index="muscle_group", columns="week_number",
                             values="set_count").fillna(0).astype(int)
        pivot.columns = [f"W{c}" for c in pivot.columns]
        st.dataframe(pivot, use_container_width=True)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from datetime import date
from data.rp_volumes import RP_VOLUMES, MUSCLE_GROUPS
from styles import inject_css
from auth import require_auth, render_sidebar_user, init_auth, get_effective_user_id
from data.exercises import EXERCISES
from database import create_mesocycle, save_muscle_config, get_mesocycles, update_mesocycle_status
from calibration import get_calibrated_volumes

# ── Muscle categories & indirect stimulus ────────────────────────────────────
_PUSH  = ["Chest", "Schulter Seite", "Triceps"]
_PULL  = ["Lat", "Oberer Rücken", "Schulter Hinten", "Biceps"]
_LEGS  = ["Quads", "Hamstrings", "Glutes", "Calves"]
_CORE  = ["Abs"]

# Muscles that get meaningful indirect work from compound movements
_INDIRECT = {
    "Triceps":        "Mittrainiert durch alle Drückbewegungen (Bench, OHP)",
    "Biceps":         "Mittrainiert durch alle Zugbewegungen (Rudern, Pulldown)",
    "Schulter Hinten":"Mittrainiert durch Rudern (Lat, Oberer Rücken)",
    "Hamstrings":     "Leicht mittrainiert durch Kniebeugen",
    "Glutes":         "Mittrainiert durch Kniebeugen, Deadlifts und Ausfallschritte — separates Training für maximales Wachstum optional",
    "Calves":         "Leicht mittrainiert durch Kniebeugen und Deadlifts",
    "Abs":            "Als Stabilisator bei Kniebeugen, Deadlift und OHP aktiv",
}

_MG_CATEGORIES = {
    "Drücken (Push)": _PUSH,
    "Ziehen (Pull)":  _PULL,
    "Beine":          _LEGS,
    "Core":           _CORE,
}

# Default selected muscles (exclude optional/indirect ones by default)
_DEFAULT_SELECTED = ["Chest", "Lat", "Oberer Rücken", "Schulter Seite", "Schulter Hinten",
                     "Biceps", "Triceps", "Quads", "Hamstrings"]


def _prioritize_day(muscles: list[str], priority: set[str]) -> list[str]:
    """Move priority muscles to the front of a training day."""
    return [m for m in muscles if m in priority] + [m for m in muscles if m not in priority]


def auto_generate_split(n_days: int, selected: list[str],
                        priority: list[str] | None = None) -> tuple[dict, list]:
    """Returns (split_days, split_order) for the given muscles and day count.
    Priority muscles get extra frequency (placed on more days) and appear first in each session.
    """
    s = set(selected)
    p = set(priority or [])
    push = [m for m in _PUSH if m in s]
    pull = [m for m in _PULL if m in s]
    legs = [m for m in _LEGS if m in s]
    core = [m for m in _CORE if m in s]

    def f(*mgs):
        return [m for m in mgs if m in s]

    if n_days == 2:
        all_mg = push + pull + legs + core
        days = {"Full Body A": list(all_mg), "Full Body B": list(all_mg)}
        order = ["Full Body A", "Full Body B"]

    elif n_days == 3:
        days = {
            "Push": push + core,
            "Pull": pull,
            "Legs": legs + [c for c in core if c not in push],
        }
        order = ["Push", "Pull", "Legs"]
        # Priority: add priority muscle to an extra day if it only appears once
        for pm in p:
            current_freq = sum(1 for mgs in days.values() if pm in mgs)
            if current_freq < 2:
                # Find the day that does NOT already have it and is most logical
                for day in order:
                    if pm not in days[day]:
                        days[day] = days[day] + [pm]
                        break

    elif n_days == 4:
        upper_a = f("Chest", "Lat", "Oberer Rücken", "Schulter Seite", "Triceps")
        lower_a = f("Quads", "Hamstrings", "Calves") + core
        upper_b = f("Chest", "Lat", "Schulter Hinten", "Schulter Seite", "Biceps")
        lower_b = f("Quads", "Glutes", "Calves") + [c for c in core if c not in lower_a]
        days  = {"Upper A": upper_a, "Lower A": lower_a, "Upper B": upper_b, "Lower B": lower_b}
        order = ["Upper A", "Lower A", "Upper B", "Lower B"]
        # Priority: if priority muscle appears only once, add to the B-variant of its day
        _day_pairs = [("Upper A", "Upper B"), ("Lower A", "Lower B")]
        for pm in p:
            for da, db in _day_pairs:
                if pm in days[da] and pm not in days[db]:
                    days[db] = [pm] + days[db]
                    break
                elif pm in days[db] and pm not in days[da]:
                    days[da] = [pm] + days[da]
                    break

    elif n_days == 5:
        upper_a = f("Chest", "Lat", "Oberer Rücken", "Schulter Seite")
        lower_a = f("Quads", "Hamstrings", "Calves")
        upper_b = f("Chest", "Lat", "Schulter Hinten", "Biceps", "Triceps")
        lower_b = f("Quads", "Glutes") + core
        arm_sh  = f("Schulter Seite", "Schulter Hinten", "Biceps", "Triceps", "Calves")
        days  = {"Upper A": upper_a, "Lower A": lower_a,
                 "Upper B": upper_b, "Lower B": lower_b}
        order = ["Upper A", "Lower A", "Upper B", "Lower B"]
        if arm_sh:
            days["Arme & Schulter"] = arm_sh
            order.append("Arme & Schulter")
        # Priority: add to extra day where not yet present
        for pm in p:
            freq = sum(1 for mgs in days.values() if pm in mgs)
            if freq < 3:
                for day in order:
                    if pm not in days[day]:
                        days[day] = [pm] + days[day]
                        break

    else:  # 6
        pull_base = f("Lat", "Oberer Rücken", "Schulter Hinten", "Biceps")
        legs_base = f("Quads", "Hamstrings", "Glutes", "Calves")
        days = {
            "Push A":  push,
            "Pull A":  pull_base,
            "Legs A":  legs_base,
            "Push B":  push + core,
            "Pull B":  pull_base[:],
            "Legs B":  legs_base + [c for c in core if c not in push],
        }
        order = ["Push A", "Pull A", "Legs A", "Push B", "Pull B", "Legs B"]

    # Move priority muscles to front of every day they appear in
    if p:
        days = {d: _prioritize_day(mgs, p) for d, mgs in days.items()}

    return days, order


def _freq_status(actual: int, recommended: int) -> tuple[str, str]:
    if actual >= recommended:
        return "🟢", f"{actual}× / Wo. (empfohlen {recommended}×)"
    elif actual >= recommended - 1:
        return "🟡", f"{actual}× / Wo. (empfohlen {recommended}×, knapp)"
    else:
        return "🔴", f"{actual}× / Wo. (empfohlen {recommended}×, zu wenig)"

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

# ── Step 2a: Trainingstage ────────────────────────────────────────────────────
st.subheader("2. Trainingsplanung")

n_days = st.select_slider(
    "Wie viele Tage pro Woche möchtest du trainieren?",
    options=[2, 3, 4, 5, 6],
    value=st.session_state.get("n_days_select", 4),
    format_func=lambda x: f"{x} Tage / Woche",
    key="n_days_select",
)

st.markdown("**Welche Muskelgruppen möchtest du direkt trainieren?**")
st.caption(
    "Muskeln die du nicht ankreuzt werden durch Compound-Übungen indirekt mittrainiert — "
    "das kann für manche Muskeln (z.B. Waden, Abs) ausreichen."
)

# ── Muscle group selector (grouped by category) ───────────────────────────────
_prev_sel_key = "_mg_selection"
if _prev_sel_key not in st.session_state:
    st.session_state[_prev_sel_key] = list(_DEFAULT_SELECTED)

chosen_muscles = []
for cat_name, cat_mgs in _MG_CATEGORIES.items():
    st.markdown(f"**{cat_name}**")
    cols_mg = st.columns(len(cat_mgs))
    for col, mg in zip(cols_mg, cat_mgs):
        indirect_note = _INDIRECT.get(mg)
        icon = RP_VOLUMES[mg].get("icon", "💪")
        label = f"{icon} {mg}"
        default_checked = mg in st.session_state[_prev_sel_key]
        checked = col.checkbox(label, value=default_checked, key=f"mg_cb_{mg}",
                               help=indirect_note or "Wird direkt trainiert")
        if checked:
            chosen_muscles.append(mg)

st.session_state[_prev_sel_key] = chosen_muscles

# Show which selected muscles have indirect coverage note
_indirect_selected = [mg for mg in MUSCLE_GROUPS if mg not in chosen_muscles and mg in _INDIRECT]
if _indirect_selected:
    st.caption(
        "**Indirekt mittrainiert** (nicht explizit im Plan): "
        + " · ".join(f"{RP_VOLUMES[m].get('icon','')} {m}" for m in _indirect_selected)
    )

if not chosen_muscles:
    st.warning("Bitte mindestens eine Muskelgruppe auswählen.")
    st.stop()

# ── Priority muscles ──────────────────────────────────────────────────────────
st.markdown("**Priorität (optional)** — welche 2 Muskelgruppen sollen bevorzugt werden?")
st.caption(
    "Priorisierte Muskeln erhalten höhere Trainingsfrequenz, stehen am Anfang jeder Session "
    "und starten näher an MAV statt MEV."
)
priority_muscles = st.multiselect(
    "Bis zu 2 Muskelgruppen priorisieren",
    options=chosen_muscles,
    default=[m for m in st.session_state.get("_priority_muscles", []) if m in chosen_muscles],
    max_selections=2,
    format_func=lambda m: f"{RP_VOLUMES[m].get('icon','💪')} {m}",
    key="priority_muscles_select",
    label_visibility="collapsed",
)
st.session_state["_priority_muscles"] = priority_muscles

# ── Reset edit cache on change ────────────────────────────────────────────────
_config_key = (n_days, tuple(chosen_muscles), tuple(priority_muscles))
if st.session_state.get("_last_config") != _config_key:
    for k in list(st.session_state.keys()):
        if k.startswith("edit_") or k.startswith("sort_state_"):
            del st.session_state[k]
    st.session_state["_last_config"] = _config_key

# ── Generate split from selected muscles ─────────────────────────────────────
_auto_days, _auto_order = auto_generate_split(n_days, chosen_muscles, priority_muscles)
# Remove empty days
_auto_days = {d: mgs for d, mgs in _auto_days.items() if mgs}
_auto_order = [d for d in _auto_order if d in _auto_days]

# ── Customise (optional) ──────────────────────────────────────────────────────
try:
    from streamlit_sortables import sort_items
    _has_sortables = True
except ImportError:
    _has_sortables = False

with st.expander("🔧 Split anpassen (optional)", expanded=False):
    edited_days = {}
    edited_order = []
    for day_name in _auto_order:
        # Use session state to persist user's drag changes across reruns
        _state_key = f"sort_state_{day_name}"
        auto_day_muscles = [m for m in _auto_days.get(day_name, []) if m in chosen_muscles]
        day_muscles = [m for m in st.session_state.get(_state_key, auto_day_muscles) if m in chosen_muscles]
        bench_muscles = [m for m in chosen_muscles if m not in day_muscles]

        new_name = st.text_input(
            "Tag-Name", value=day_name, key=f"rename_{day_name}",
        ).strip() or day_name

        if _has_sortables:
            st.caption("Ziehen zum Verschieben — links = im Training, rechts = nicht an dem Tag")
            result = sort_items(
                [
                    {"header": "Im Training", "items": list(day_muscles)},
                    {"header": "Nicht an dem Tag", "items": list(bench_muscles)},
                ],
                multi_containers=True,
                key=f"sort_{day_name}",
            )
            chosen_day = [m for m in result[0] if m in chosen_muscles]
            st.session_state[_state_key] = chosen_day
        else:
            chosen_day = st.multiselect(
                "Muskelgruppen", options=chosen_muscles, default=day_muscles,
                key=f"edit_{day_name}", label_visibility="collapsed",
            )
            st.session_state[_state_key] = chosen_day

        edited_days[new_name] = chosen_day
        edited_order.append(new_name)
        st.divider()
    split_days = edited_days
    split_order = edited_order

# ── Split preview + Frequenz-Analyse (aus finalem split_days) ────────────────
freq_actual = {mg: sum(1 for mgs in split_days.values() if mg in mgs) for mg in chosen_muscles}

_SPLIT_NAMES = {2: "Full Body", 3: "Push/Pull/Legs", 4: "Upper/Lower", 5: "Upper/Lower+", 6: "PPL×2"}
st.markdown(f"**Dein Split — {_SPLIT_NAMES.get(n_days, '')} ({n_days} Tage):**")
preview_cols = st.columns(min(len(split_days), 3))
for i, (day_name, muscles) in enumerate(split_days.items()):
    with preview_cols[i % len(preview_cols)]:
        icons = " ".join(RP_VOLUMES.get(mg, {}).get("icon", "💪") for mg in muscles)
        n_sets_est = sum(
            max(1, round(RP_VOLUMES.get(mg, {}).get("MEV", 6) / max(freq_actual.get(mg, 1), 1)))
            for mg in muscles
        )
        st.info(
            f"**{day_name}**\n\n{icons}\n\n"
            + "\n".join(f"• {mg}" for mg in muscles)
            + f"\n\n~{n_sets_est} Sets"
        )

with st.container(border=True):
    st.markdown("**Frequenz-Analyse:**")
    cols_freq = st.columns(4)
    for i, mg in enumerate(chosen_muscles):
        rec    = RP_VOLUMES[mg]["freq_per_week"]
        actual = freq_actual[mg]
        icon_freq, label_freq = _freq_status(actual, rec)
        icon_mg = RP_VOLUMES[mg].get("icon", "💪")
        cols_freq[i % 4].markdown(
            f"{icon_freq} **{icon_mg} {mg}**  \n"
            f"<span style='color:#888;font-size:0.8rem'>{label_freq}</span>",
            unsafe_allow_html=True,
        )

selected_template_name = f"Auto {n_days}d"
selected_muscles = list(dict.fromkeys(mg for mgs in split_days.values() for mg in mgs))

if not selected_muscles:
    st.warning("Keine Muskelgruppen definiert.")
    st.stop()

st.divider()

# ── Step 3: Übungsaufteilung ──────────────────────────────────────────────────
st.subheader("3. Übungsaufteilung")
st.caption(
    "Pro Muskelgruppe wird automatisch die beste Übung pro Tag gewählt (🟢 = hoher SFR). "
    "Bei mehrfachem Training pro Woche werden verschiedene Übungen für verschiedene Winkel verwendet."
)

with st.expander("ℹ️ Was bedeuten MEV, MAV, MRV?", expanded=False):
    st.markdown("""
| Begriff | Bedeutung | Praxis |
|---------|-----------|--------|
| **MEV** | Mindestanzahl Sätze/Woche damit der Muskel wächst | Startpunkt nach Deload |
| **MAV** | Optimaler Bereich für maximales Wachstum | Ziel-Bereich im Meso |
| **MRV** | Maximale Sätze die du noch erholen kannst | Nie dauerhaft überschreiten |
""")

calibrated = {mg: get_calibrated_volumes(mg) for mg in selected_muscles}

# ── Auto-assign: best exercise per muscle per day ─────────────────────────────
# Build ordered exercise pool per muscle (high SFR first)
_ex_pool = {}
for mg in selected_muscles:
    high = [e["name"] for e in EXERCISES.get(mg, []) if e["sfr"] == "high"]
    med  = [e["name"] for e in EXERCISES.get(mg, []) if e["sfr"] != "high"]
    _ex_pool[mg] = high + med

# For each muscle, map day → suggested exercise (rotate through pool)
_muscle_day_order = {}  # {mg: [day1, day2, ...]} in split_order sequence
for day in split_order:
    for mg in split_days.get(day, []):
        _muscle_day_order.setdefault(mg, []).append(day)

_auto_ex = {}  # {mg: {day: suggested_exercise}}
for mg, days in _muscle_day_order.items():
    pool = _ex_pool.get(mg, [])
    _auto_ex[mg] = {}
    for i, day in enumerate(days):
        _auto_ex[mg][day] = pool[i % len(pool)] if pool else ""

# ── UI: tab per training day ──────────────────────────────────────────────────
day_ex_choices = {}  # {day: {mg: [exercise, ...]}}

day_tabs = st.tabs(split_order)
for tab, day in zip(day_tabs, split_order):
    with tab:
        day_muscles = split_days.get(day, [])
        if not day_muscles:
            st.caption("Keine Muskelgruppen an diesem Tag.")
            continue

        day_ex_choices[day] = {}
        cols = st.columns(2)
        for i, mg in enumerate(day_muscles):
            cal  = calibrated[mg]
            vol  = RP_VOLUMES.get(mg, {})
            icon = vol.get("icon", "💪")
            sfr_map = {e["name"]: e["sfr"] for e in EXERCISES.get(mg, [])}
            all_opts = _ex_pool.get(mg, [])
            freq = len(_muscle_day_order.get(mg, [day]))

            trains_on = _muscle_day_order.get(mg, [day])
            freq_idx  = trains_on.index(day) + 1
            auto_pick = _auto_ex.get(mg, {}).get(day, all_opts[0] if all_opts else "")

            mev   = cal.get("MEV",      vol.get("MEV", "?"))
            mav_l = cal.get("MAV_low",  vol.get("MAV_low", "?"))
            mav_h = cal.get("MAV_high", vol.get("MAV_high", "?"))
            mrv   = cal.get("MRV",      vol.get("MRV", "?"))

            is_prio = mg in priority_muscles
            if meso_type == "strength":
                start_sets = max(cal["MEV"], 3)
            else:
                start_sets = (max(cal["recommended_start"], cal.get("MAV_low", cal["recommended_start"]))
                              if is_prio else cal["recommended_start"])
            sets_per_session = max(1, round(start_sets / freq))

            freq_label = f"Training {freq_idx}/{freq}" if freq > 1 else ""
            prio_badge = " ⭐" if is_prio else ""

            with cols[i % 2]:
                st.markdown(
                    f"**{icon} {mg}{prio_badge}**"
                    + (f" <span style='color:#888;font-size:0.8rem'>({freq_label})</span>" if freq_label else ""),
                    unsafe_allow_html=True,
                )

                # How many exercises to use for this muscle this session
                max_ex = min(3, len(all_opts))
                # Auto-suggest 2 exercises when ≥ 5 sets/session
                default_n_ex = 2 if sets_per_session >= 5 and max_ex >= 2 else 1
                n_ex = st.radio(
                    "Übungen",
                    options=list(range(1, max_ex + 1)),
                    index=default_n_ex - 1,
                    horizontal=True,
                    key=f"n_ex_{day}_{mg}",
                    format_func=lambda x: f"{x} Übung{'en' if x > 1 else ''}",
                    label_visibility="collapsed",
                )

                # Show set distribution info
                sets_each = [sets_per_session // n_ex + (1 if j < sets_per_session % n_ex else 0)
                             for j in range(n_ex)]
                st.caption(
                    f"MEV {mev} / MAV {mav_l}–{mav_h} / MRV {mrv} · "
                    f"{sets_per_session} Sets/Session"
                    + (f" → {' + '.join(str(s) for s in sets_each)} Sets" if n_ex > 1 else "")
                )

                chosen_exs = []
                for ex_idx in range(n_ex):
                    # Suggest different exercises per slot (rotate pool)
                    pool_idx = (trains_on.index(day) + ex_idx) % len(all_opts) if all_opts else 0
                    fallback = all_opts[pool_idx] if all_opts else ""
                    sel = st.selectbox(
                        f"Übung {ex_idx + 1}",
                        options=all_opts,
                        index=all_opts.index(fallback) if fallback in all_opts else 0,
                        key=f"ex_{day}_{mg}_{ex_idx}",
                        label_visibility="collapsed",
                        format_func=lambda x: f"{'🟢' if sfr_map.get(x)=='high' else '🟡'} {x}",
                    )
                    chosen_exs.append(sel)

                day_ex_choices[day][mg] = chosen_exs

# ── Collect into muscle_configs (exercises ordered by day-rotation) ───────────
muscle_configs = {}
for mg in selected_muscles:
    cal  = calibrated[mg]
    vol  = RP_VOLUMES.get(mg, {})
    days = _muscle_day_order.get(mg, [])
    freq = len(days) if days else 1

    is_priority = mg in priority_muscles
    if meso_type == "strength":
        start_sets = max(cal["MEV"], 3)
        progression = [start_sets] * weeks
    else:
        if is_priority:
            # Priority: start at MAV_low instead of recommended_start, progress faster
            start_sets = max(cal["recommended_start"], cal.get("MAV_low", cal["recommended_start"]))
        else:
            start_sets = cal["recommended_start"]
        progression = [min(start_sets + (w-1)*2, cal["MRV"]) for w in range(1, weeks+1)]

    # Flatten: [ex_day1_slot1, ex_day1_slot2, ex_day2_slot1, ...]
    # Training page rotates through this list by (day_rotation + ex_idx) % len
    ordered_exercises = []
    for d in days:
        ex_list = day_ex_choices.get(d, {}).get(mg, [])
        if isinstance(ex_list, list):
            ordered_exercises.extend([e for e in ex_list if e])
        elif ex_list:
            ordered_exercises.append(ex_list)
    if not ordered_exercises:
        ordered_exercises = [_ex_pool.get(mg, [""])[0]]

    muscle_configs[mg] = {
        "start_sets": start_sets,
        "exercises": ordered_exercises,
        "cal": cal,
        "progression": progression,
    }

st.divider()

# ── Step 4: Summary ───────────────────────────────────────────────────────────
st.subheader("4. Zusammenfassung")

total_w1 = sum(c["start_sets"] for c in muscle_configs.values())
total_peak = sum(c["progression"][-1] for c in muscle_configs.values())

col1, col2, col3, col4 = st.columns(4)
col1.metric("Split", f"{n_days} Tage/Wo.")
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

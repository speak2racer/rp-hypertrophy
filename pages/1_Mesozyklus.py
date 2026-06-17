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

# ── Kategorien & Indirekt-Hinweise ───────────────────────────────────────────
_PUSH = ["Chest", "Schulter Seite", "Triceps"]
_PULL = ["Lat", "Oberer Rücken", "Schulter Hinten", "Biceps"]
_LEGS = ["Quads", "Hamstrings", "Glutes", "Calves"]
_CORE = ["Abs"]

_INDIRECT = {
    "Triceps":         "Wird durch alle Drückübungen (Bankdrücken, OHP) mittrainiert",
    "Biceps":          "Wird durch alle Zugübungen (Rudern, Pulldown) mittrainiert",
    "Schulter Hinten": "Wird durch Rudern mittrainiert",
    "Hamstrings":      "Wird leicht durch Kniebeugen mittrainiert",
    "Glutes":          "Wird durch Kniebeugen und Deadlifts mittrainiert",
    "Calves":          "Wird leicht durch Kniebeugen und Deadlifts mittrainiert",
    "Abs":             "Wird als Stabilisator bei Kniebeugen, Deadlift und OHP aktiv",
}

_MG_CATEGORIES = {
    "Drücken": _PUSH,
    "Ziehen":  _PULL,
    "Beine":   _LEGS,
    "Core":    _CORE,
}

_DEFAULT_SELECTED = [
    "Chest", "Lat", "Oberer Rücken", "Schulter Seite", "Schulter Hinten",
    "Biceps", "Triceps", "Quads", "Hamstrings",
]


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
def _prioritize_day(muscles: list, priority: set) -> list:
    return [m for m in muscles if m in priority] + [m for m in muscles if m not in priority]


def auto_generate_split(n_days: int, selected: list,
                        priority: list | None = None) -> tuple[dict, list]:
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
        days  = {"Full Body A": list(all_mg), "Full Body B": list(all_mg)}
        order = ["Full Body A", "Full Body B"]

    elif n_days == 3:
        days = {
            "Push": push + core,
            "Pull": pull,
            "Legs": legs + [c for c in core if c not in push],
        }
        order = ["Push", "Pull", "Legs"]
        for pm in p:
            if sum(1 for mgs in days.values() if pm in mgs) < 2:
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
        for pm in p:
            for da, db in [("Upper A", "Upper B"), ("Lower A", "Lower B")]:
                if pm in days[da] and pm not in days[db]:
                    days[db] = [pm] + days[db]; break
                elif pm in days[db] and pm not in days[da]:
                    days[da] = [pm] + days[da]; break

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
        for pm in p:
            if sum(1 for mgs in days.values() if pm in mgs) < 3:
                for day in order:
                    if pm not in days[day]:
                        days[day] = [pm] + days[day]; break

    else:  # 6
        pull_base = f("Lat", "Oberer Rücken", "Schulter Hinten", "Biceps")
        legs_base = f("Quads", "Hamstrings", "Glutes", "Calves")
        days = {
            "Push A": push,
            "Pull A": pull_base,
            "Legs A": legs_base,
            "Push B": push + core,
            "Pull B": pull_base[:],
            "Legs B": legs_base + [c for c in core if c not in push],
        }
        order = ["Push A", "Pull A", "Legs A", "Push B", "Pull B", "Legs B"]

    if p:
        days = {d: _prioritize_day(mgs, p) for d, mgs in days.items()}
    return days, order


def _freq_badge(actual: int, recommended: int) -> str:
    if actual >= recommended:
        return f"🟢 {actual}×/Wo."
    elif actual >= recommended - 1:
        return f"🟡 {actual}×/Wo. (knapp)"
    return f"🔴 {actual}×/Wo. (zu wenig)"


def _macro_recommendation(mesocycles: list) -> tuple[str, str, str]:
    done = [m for m in mesocycles if m["status"] in ("completed", "active", "deload")]
    done_sorted = sorted(done, key=lambda m: m.get("created_at", ""), reverse=True)
    if not done_sorted:
        return ("hypertrophy",
                "💪 Empfehlung: Hypertrophie-Meso",
                "Starte mit einem Hypertrophie-Meso um Muskelvolumen aufzubauen.")
    hyp_streak = 0
    for m in done_sorted:
        if (m.get("meso_type") or "hypertrophy") == "strength":
            break
        hyp_streak += 1
    last_type = done_sorted[0].get("meso_type") or "hypertrophy"
    if last_type == "strength":
        return ("hypertrophy", "💪 Empfehlung: Hypertrophie-Meso",
                "Nach dem Kraft-Meso jetzt Hypertrophie — dein verbessertes 1RM erlaubt mehr Gewicht bei hohem Volumen.")
    if hyp_streak >= 3:
        return ("strength", "🏋️ Empfehlung: Kraft-Meso",
                f"{hyp_streak} Hypertrophie-Mesos in Folge — Zeit das 1RM zu steigern.")
    if hyp_streak == 2:
        return ("strength", "🏋️ Empfehlung: Kraft-Meso (optional)",
                "Nach 2 Hypertrophie-Mesos wäre ein Kraft-Block sinnvoll — spätestens nach dem nächsten.")
    return ("hypertrophy", "💪 Empfehlung: Hypertrophie-Meso",
            f"Noch {3 - hyp_streak - 1} weiterer Hypertrophie-Meso sinnvoll vor dem nächsten Kraft-Block.")


# ── Seiten-Setup ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Mesozyklus-Planer", page_icon="📅", layout="wide")
inject_css()
init_auth()
user = require_auth()
render_sidebar_user()

st.markdown("""
<div class='page-header'>
    <p class='page-title'>📅 Mesozyklus-Planer</p>
    <p class='page-sub'>Plane deinen nächsten Trainings-Zyklus</p>
</div>
""", unsafe_allow_html=True)

all_mesos = get_mesocycles(user_id=get_effective_user_id())
rec_type, rec_title, rec_text = _macro_recommendation(all_mesos)

# ════════════════════════════════════════════════════════════════════════════
# SCHRITT 1 · GRUNDEINSTELLUNGEN
# ════════════════════════════════════════════════════════════════════════════
st.markdown("### Schritt 1 · Grundeinstellungen")
with st.container(border=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        meso_name = st.text_input(
            "Name des Mesozyklus",
            value=f"Meso {date.today().strftime('%b %Y')}",
            placeholder="z.B. Sommer Aufbau",
        )
    with c2:
        start_date = st.date_input("Startdatum", value=date.today())
    with c3:
        weeks = st.slider(
            "Trainingswochen",
            min_value=3, max_value=8, value=5,
            help="Anzahl Wochen vor dem Deload",
        )
    st.caption(f"Deload-Woche: Woche {weeks + 1} · Gesamtdauer: {weeks + 1} Wochen")

    st.divider()

    _default_type_idx = 0 if rec_type == "hypertrophy" else 1
    meso_type = st.radio(
        "Trainingstyp",
        options=["hypertrophy", "strength"],
        format_func=lambda x: (
            "💪 Hypertrophie — viel Volumen, 8–12 Wdh., Muskelaufbau"
            if x == "hypertrophy"
            else "🏋️ Kraft — schwere Gewichte, 3–6 Wdh., 1RM steigern"
        ),
        horizontal=True,
        index=_default_type_idx,
        key="meso_type_select",
    )

    # Makrozyklus-Empfehlung kompakt
    done_mesos = [m for m in all_mesos if m["status"] in ("completed", "active", "deload")]
    if done_mesos:
        icons = " › ".join(
            ("💪" if (m.get("meso_type") or "hypertrophy") == "hypertrophy" else "🏋️") + " " + m["name"]
            for m in sorted(done_mesos, key=lambda x: x.get("created_at", ""))[-5:]
        ) + " › **Jetzt**"
        st.caption(f"{rec_title}  ·  {rec_text}")
        st.caption(icons)
    else:
        st.caption(f"{rec_title}  ·  {rec_text}")

    if meso_type == "strength":
        st.info(
            "**Kraft-Meso:** Geringeres Volumen (nahe MEV), hohe Intensität (80–95 % 1RM), 3–6 Wdh. "
            "Steigert das 1RM → im nächsten Hypertrophie-Meso kannst du mit mehr Gewicht bei gleichem Volumen trainieren.",
        )

# ════════════════════════════════════════════════════════════════════════════
# SCHRITT 2 · MUSKELGRUPPEN & TRAININGSTAGE
# ════════════════════════════════════════════════════════════════════════════
st.markdown("### Schritt 2 · Muskelgruppen & Trainingstage")
with st.container(border=True):

    n_days = st.select_slider(
        "Wie viele Tage pro Woche möchtest du trainieren?",
        options=[2, 3, 4, 5, 6],
        value=st.session_state.get("n_days_select", 4),
        format_func=lambda x: f"{x} Tage / Woche",
        key="n_days_select",
    )

    st.markdown("**Welche Muskelgruppen möchtest du direkt trainieren?**")
    st.caption(
        "Nicht angehakte Muskeln werden durch Compound-Übungen indirekt mittrainiert — "
        "für viele reicht das aus. Fahre über die ⓘ für Details."
    )

    if "_mg_selection" not in st.session_state:
        st.session_state["_mg_selection"] = list(_DEFAULT_SELECTED)

    chosen_muscles: list[str] = []
    cat_cols = st.columns(len(_MG_CATEGORIES))
    for col, (cat_name, cat_mgs) in zip(cat_cols, _MG_CATEGORIES.items()):
        with col:
            st.markdown(f"**{cat_name}**")
            for mg in cat_mgs:
                icon = RP_VOLUMES[mg].get("icon", "💪")
                hint = _INDIRECT.get(mg, "Wird direkt trainiert")
                checked = col.checkbox(
                    f"{icon} {mg}",
                    value=mg in st.session_state["_mg_selection"],
                    key=f"mg_cb_{mg}",
                    help=hint,
                )
                if checked:
                    chosen_muscles.append(mg)

    st.session_state["_mg_selection"] = chosen_muscles

    indirect_shown = [mg for mg in MUSCLE_GROUPS if mg not in chosen_muscles and mg in _INDIRECT]
    if indirect_shown:
        st.caption(
            "Indirekt mittrainiert: "
            + "  ·  ".join(f"{RP_VOLUMES[m].get('icon','')} {m}" for m in indirect_shown)
        )

    if not chosen_muscles:
        st.warning("Bitte mindestens eine Muskelgruppe auswählen.")
        st.stop()

    st.divider()

    st.markdown("**Priorität** *(optional)*")
    st.caption(
        "Bis zu 2 Muskelgruppen die du bevorzugt entwickeln möchtest. "
        "Sie werden häufiger trainiert, stehen am Anfang jeder Session "
        "und starten näher am optimalen Trainingsvolumen (MAV)."
    )
    priority_muscles = st.multiselect(
        "Muskelgruppen priorisieren",
        options=chosen_muscles,
        default=[m for m in st.session_state.get("_priority_muscles", []) if m in chosen_muscles],
        max_selections=2,
        format_func=lambda m: f"{RP_VOLUMES[m].get('icon','💪')} {m}",
        key="priority_muscles_select",
        label_visibility="collapsed",
    )
    st.session_state["_priority_muscles"] = priority_muscles

# Konfigurationsänderung → Split-Anpassungen zurücksetzen
_config_key = (n_days, tuple(chosen_muscles), tuple(priority_muscles))
if st.session_state.get("_last_config") != _config_key:
    for k in list(st.session_state.keys()):
        if k.startswith(("edit_", "sort_state_", "sort_order_state_",
                          "rename_", "day_name_", "n_ex_", "ex_")):
            del st.session_state[k]
    st.session_state["_last_config"] = _config_key

# Initialwerte: beim ersten Laden aus Auto-Split befüllen, danach aus session_state
_auto_days, _auto_order = auto_generate_split(n_days, chosen_muscles, priority_muscles)
_auto_days  = {d: mgs for d, mgs in _auto_days.items() if mgs}
_auto_order = [d for d in _auto_order if d in _auto_days]

# Feste Slot-Keys für n_days Tage — intern immer eindeutig, unabhängig vom Tagnamen
_slot_keys = [f"slot_{i}" for i in range(n_days)]

for i, sk in enumerate(_slot_keys):
    if f"day_name_{sk}" not in st.session_state:
        _default_dn  = _auto_order[i] if i < len(_auto_order) else f"Tag {i + 1}"
        _default_mgs = [m for m in _auto_days.get(_default_dn, []) if m in chosen_muscles]
        st.session_state[f"day_name_{sk}"]  = _default_dn
        st.session_state[f"sort_state_{sk}"] = _default_mgs

# ════════════════════════════════════════════════════════════════════════════
# SCHRITT 3 · TRAININGSAUFTEILUNG
# ════════════════════════════════════════════════════════════════════════════
st.markdown("### Schritt 3 · Trainingsaufteilung")
st.caption(
    "Weise jedem Tag beliebige Muskelgruppen zu. "
    "Die Reihenfolge der Auswahl bestimmt auch die Trainingsreihenfolge innerhalb des Tages."
)

# split_days: Slot-Key → Muskelliste  (intern eindeutig, kein Überschreiben bei gleichem Namen)
split_days: dict[str, list]  = {}
split_order: list[str]       = []   # Slot-Keys
display_names: dict[str, str] = {}  # Slot-Key → Anzeigename

for sk in _slot_keys:
    cur_name = st.session_state.get(f"day_name_{sk}", sk)
    cur_mgs  = [m for m in st.session_state.get(f"sort_state_{sk}", []) if m in chosen_muscles]

    with st.container(border=True):
        name_col, sel_col = st.columns([1, 3])
        with name_col:
            new_name = st.text_input(
                "Tag-Name", value=cur_name, key=f"rename_{sk}",
                label_visibility="collapsed", placeholder="z.B. Push A",
            ).strip() or cur_name
            st.session_state[f"day_name_{sk}"] = new_name

        with sel_col:
            active = st.multiselect(
                "Muskelgruppen",
                options=chosen_muscles,
                default=cur_mgs,
                key=f"edit_{sk}",
                format_func=lambda m: f"{RP_VOLUMES[m].get('icon','💪')} {m}",
                label_visibility="collapsed",
            )

    st.session_state[f"sort_state_{sk}"] = active
    split_days[sk]       = active
    split_order.append(sk)
    display_names[sk]    = new_name

# ── Frequenz-Analyse ─────────────────────────────────────────────────────────
freq_actual = {mg: sum(1 for mgs in split_days.values() if mg in mgs)
               for mg in chosen_muscles}

with st.container(border=True):
    st.markdown("**Frequenz-Analyse**")
    st.caption(
        "🟢 Frequenz erreicht · 🟡 knapp · 🔴 zu niedrig für optimales Muskelwachstum. "
        "MEV = Mindestvolumen · MAV = optimaler Bereich · MRV = Maximum."
    )
    freq_cols = st.columns(min(len(chosen_muscles), 4))
    for i, mg in enumerate(chosen_muscles):
        rec     = RP_VOLUMES[mg]["freq_per_week"]
        badge   = _freq_badge(freq_actual[mg], rec)
        icon_mg = RP_VOLUMES[mg].get("icon", "💪")
        freq_cols[i % 4].markdown(
            f"**{icon_mg} {mg}**  \n"
            f"<span style='font-size:0.8rem;color:#888'>{badge}</span>",
            unsafe_allow_html=True,
        )

selected_muscles = list(dict.fromkeys(mg for mgs in split_days.values() for mg in mgs))
if not selected_muscles:
    st.warning("Keine Muskelgruppen im Plan — bitte Aufteilung anpassen.")
    st.stop()

# ════════════════════════════════════════════════════════════════════════════
# WECHSELWOCHE (optional)
# ════════════════════════════════════════════════════════════════════════════
_n_types = len(split_order)
with st.container(border=True):
    st.markdown("**Wechselwoche** *(optional)*")
    st.caption(
        "Trainierst du z. B. 3× pro Woche mit 2 verschiedenen Trainingstagen (A und B), "
        "wechseln die Wochen automatisch: **Woche 1 → A, B, A** · **Woche 2 → B, A, B**. "
        "So bekommt jeder Tag gleich viele 'erste' und 'letzte' Positionen in der Woche."
    )

    use_alt = st.toggle(
        "Wechselwoche aktivieren",
        value=st.session_state.get("_use_alternating", False),
        key="_use_alternating",
    )

    if use_alt and _n_types >= 2:
        # Wie viele physische Trainingstage pro Woche?
        alt_days = st.select_slider(
            "Physische Trainingstage pro Woche",
            options=list(range(2, 7)),
            value=st.session_state.get("_alt_days", min(3, _n_types + 1)),
            format_func=lambda x: f"{x} Tage / Woche",
            key="_alt_days",
        )

        # Baue 2-Wochen-Rotation: Session i → split_order[i % n_types]
        _cycle = [split_order[i % _n_types] for i in range(alt_days * 2)]
        _woche1 = _cycle[:alt_days]
        _woche2 = _cycle[alt_days:]

        w1c, w2c = st.columns(2)
        with w1c:
            st.markdown("**Woche 1:**")
            st.markdown("  →  ".join(f"`{display_names.get(d, d)}`" for d in _woche1))
        with w2c:
            st.markdown("**Woche 2:**")
            st.markdown("  →  ".join(f"`{display_names.get(d, d)}`" for d in _woche2))

        if alt_days % _n_types == 0:
            st.info(
                f"Bei {alt_days} Tagen und {_n_types} Split-Typen ist kein Wechsel nötig — "
                "jede Woche hat die gleiche Reihenfolge. Wähle eine ungerade Anzahl Tage für echten Wechsel.",
            )

        stored_split_order = _cycle
    elif use_alt and _n_types < 2:
        st.warning("Du brauchst mindestens 2 verschiedene Trainingstage für die Wechselwoche.")
        stored_split_order = split_order
    else:
        stored_split_order = split_order

# ════════════════════════════════════════════════════════════════════════════
# SCHRITT 4 · ÜBUNGSAUSWAHL
# ════════════════════════════════════════════════════════════════════════════
st.markdown("### Schritt 4 · Übungsauswahl")
st.caption(
    "Für jede Muskelgruppe wird automatisch die beste Übung vorausgewählt. "
    "🟢 = hoher SFR (viel Stimulus, wenig Erschöpfung) · 🟡 = mittel. "
    "Du kannst jederzeit eine andere Übung wählen oder mehrere kombinieren."
)

calibrated = {mg: get_calibrated_volumes(mg) for mg in selected_muscles}

_ex_pool: dict[str, list] = {}
for mg in selected_muscles:
    high = [e["name"] for e in EXERCISES.get(mg, []) if e["sfr"] == "high"]
    med  = [e["name"] for e in EXERCISES.get(mg, []) if e["sfr"] != "high"]
    _ex_pool[mg] = high + med

_muscle_day_order: dict[str, list] = {}
for day in split_order:
    for mg in split_days.get(day, []):
        _muscle_day_order.setdefault(mg, []).append(day)

day_ex_choices: dict[str, dict] = {}
day_tabs = st.tabs([display_names.get(sk, sk) for sk in split_order])

for tab, day in zip(day_tabs, split_order):
    with tab:
        day_muscles = split_days.get(day, [])
        if not day_muscles:
            st.caption("Keine Muskelgruppen für diesen Tag definiert.")
            continue

        day_ex_choices[day] = {}

        for mg in day_muscles:
            cal      = calibrated[mg]
            vol      = RP_VOLUMES.get(mg, {})
            icon     = vol.get("icon", "💪")
            all_opts = _ex_pool.get(mg, [])
            sfr_map  = {e["name"]: e["sfr"] for e in EXERCISES.get(mg, [])}
            trains_on = _muscle_day_order.get(mg, [day])
            freq      = len(trains_on)
            freq_idx  = (trains_on.index(day) + 1) if day in trains_on else 1

            is_prio = mg in priority_muscles
            if meso_type == "strength":
                start_sets = max(cal["MEV"], 3)
            else:
                start_sets = (
                    max(cal["recommended_start"], cal.get("MAV_low", cal["recommended_start"]))
                    if is_prio else cal["recommended_start"]
                )
            sets_per_session = max(1, round(start_sets / freq))

            mev   = cal.get("MEV",      vol.get("MEV", "?"))
            mav_l = cal.get("MAV_low",  vol.get("MAV_low", "?"))
            mav_h = cal.get("MAV_high", vol.get("MAV_high", "?"))
            mrv   = cal.get("MRV",      vol.get("MRV", "?"))

            prio_badge = " ⭐" if is_prio else ""
            freq_label = f" · Training {freq_idx}/{freq}" if freq > 1 else ""

            with st.container(border=True):
                h_col, meta_col = st.columns([3, 2])
                with h_col:
                    st.markdown(f"**{icon} {mg}{prio_badge}**{freq_label}")
                with meta_col:
                    st.caption(
                        f"MEV {mev} · MAV {mav_l}–{mav_h} · MRV {mrv} · "
                        f"**{sets_per_session} Sets/Session**"
                    )

                if not all_opts:
                    st.warning("Keine Übungen im Katalog für diese Muskelgruppe.")
                    day_ex_choices[day][mg] = []
                    continue

                max_ex = min(3, len(all_opts))
                default_n_ex = 2 if sets_per_session >= 5 and max_ex >= 2 else 1

                radio_col, *ex_cols = st.columns([1] + [3] * max_ex)
                with radio_col:
                    n_ex = st.radio(
                        "Anz. Übungen",
                        options=list(range(1, max_ex + 1)),
                        index=default_n_ex - 1,
                        key=f"n_ex_{day}_{mg}",
                        format_func=lambda x: f"{x}×",
                        label_visibility="collapsed",
                    )

                sets_each = [
                    sets_per_session // n_ex + (1 if j < sets_per_session % n_ex else 0)
                    for j in range(n_ex)
                ]

                chosen_exs = []
                for ex_idx in range(n_ex):
                    pool_offset = trains_on.index(day) if day in trains_on else 0
                    pool_idx    = (pool_offset + ex_idx) % len(all_opts)
                    fallback    = all_opts[pool_idx]
                    _sfr_map    = sfr_map  # capture for lambda
                    with ex_cols[ex_idx]:
                        sel = st.selectbox(
                            f"{sets_each[ex_idx]} Sets",
                            options=all_opts,
                            index=all_opts.index(fallback) if fallback in all_opts else 0,
                            key=f"ex_{day}_{mg}_{ex_idx}",
                            format_func=lambda x, sm=_sfr_map: (
                                f"{'🟢' if sm.get(x) == 'high' else '🟡'} {x}"
                            ),
                        )
                        chosen_exs.append(sel)

                day_ex_choices[day][mg] = chosen_exs

# Muscle-Configs zusammenbauen
muscle_configs: dict[str, dict] = {}
for mg in selected_muscles:
    cal  = calibrated[mg]
    days = _muscle_day_order.get(mg, [])
    freq = len(days) if days else 1

    is_prio = mg in priority_muscles
    if meso_type == "strength":
        start_sets = max(cal["MEV"], 3)
        progression = [start_sets] * weeks
    else:
        start_sets = (
            max(cal["recommended_start"], cal.get("MAV_low", cal["recommended_start"]))
            if is_prio else cal["recommended_start"]
        )
        progression = [min(start_sets + (w - 1) * 2, cal["MRV"]) for w in range(1, weeks + 1)]

    ordered_exercises: list[str] = []
    for d in days:
        ex_list = day_ex_choices.get(d, {}).get(mg, [])
        if isinstance(ex_list, list):
            ordered_exercises.extend(e for e in ex_list if e)
        elif ex_list:
            ordered_exercises.append(ex_list)
    if not ordered_exercises:
        pool = _ex_pool.get(mg, [])
        ordered_exercises = [pool[0]] if pool else [""]

    muscle_configs[mg] = {
        "start_sets": start_sets,
        "exercises":  ordered_exercises,
        "progression": progression,
    }

# ════════════════════════════════════════════════════════════════════════════
# ZUSAMMENFASSUNG & ERSTELLEN
# ════════════════════════════════════════════════════════════════════════════
st.markdown("### Zusammenfassung")
with st.container(border=True):
    total_w1   = sum(c["start_sets"]       for c in muscle_configs.values())
    total_peak = sum(c["progression"][-1]  for c in muscle_configs.values())

    m1, m2, m3, m4 = st.columns(4)
    _phys_days = len(stored_split_order) // 2 if use_alt and len(stored_split_order) > len(split_order) else n_days
    m1.metric("Split",         f"{_phys_days} Tage / Wo." + (" · ABA/BAB" if use_alt and len(stored_split_order) > len(split_order) else ""))
    m2.metric("Trainingstage", len(split_days))
    m3.metric("Startvolumen",  f"{total_w1} Sets / Wo.")
    m4.metric("Peakvolumen",   f"{total_peak} Sets / Wo.")

    st.divider()

    if not meso_name:
        st.warning("Bitte einen Namen für den Mesozyklus eingeben.")
    else:
        if st.button("✅ Mesozyklus erstellen", type="primary", use_container_width=True):
            for m in all_mesos:
                if m["status"] == "active":
                    update_mesocycle_status(m["id"], "completed")

            # Konvertiere Slot-Keys zu Display-Namen für die DB
            _db_split_days  = {display_names.get(sk, sk): mgs for sk, mgs in split_days.items()}
            _db_split_order = [display_names.get(sk, sk) for sk in stored_split_order]

            meso_id = create_mesocycle(
                meso_name, start_date, weeks, weeks + 1, selected_muscles,
                split_template=f"Auto {n_days}d",
                split_days=_db_split_days,
                split_order=_db_split_order,
                user_id=get_effective_user_id(),
                meso_type=meso_type,
            )

            for mg, cfg in muscle_configs.items():
                save_muscle_config(meso_id, mg, cfg["start_sets"], cfg["exercises"])

            st.success(f"✅ Mesozyklus **{meso_name}** wurde erstellt!")
            st.balloons()
            if st.button("▶ Zum Training"):
                st.switch_page("pages/2_Training.py")

"""
Automatic MEV/MAV/MRV calibration from historical mesocycle data.

Logic per muscle group:
- MEV: lowest weekly set count where performance was still improving (≥3)
- MAV: week range where pump was high (≥3.5) AND soreness moderate (≤3.5) AND performance good (≥3)
- MRV: first week where soreness consistently high (>3.5) OR performance declining (<3)
"""

from database import get_all_feedback_for_meso, get_sets_per_muscle_per_week, get_mesocycles
from data.rp_volumes import RP_VOLUMES


def _get_weekly_stats(meso_id: int, muscle_group: str) -> list[dict]:
    """Returns per-week aggregated feedback + set counts for a muscle group."""
    feedback = get_all_feedback_for_meso(meso_id)
    vol_data = get_sets_per_muscle_per_week(meso_id)

    # Build volume lookup: week → sets
    vol_map = {
        row["week_number"]: row["set_count"]
        for row in vol_data
        if row["muscle_group"] == muscle_group
    }

    # Build feedback lookup: week → list of feedback entries
    fb_by_week: dict[int, list] = {}
    for fb in feedback:
        if fb["muscle_group"] != muscle_group:
            continue
        w = fb["week_number"]
        fb_by_week.setdefault(w, []).append(fb)

    weeks = sorted(set(list(vol_map.keys()) + list(fb_by_week.keys())))
    result = []
    for w in weeks:
        fbs = fb_by_week.get(w, [])
        sets = vol_map.get(w, 0)
        if not fbs:
            result.append({"week": w, "sets": sets, "pump": None, "soreness": None, "performance": None})
            continue
        result.append({
            "week": w,
            "sets": sets,
            "pump": sum(f["pump"] for f in fbs) / len(fbs),
            "soreness": sum(f["soreness"] for f in fbs) / len(fbs),
            "performance": sum(f["performance"] for f in fbs) / len(fbs),
        })
    return result


def calibrate_muscle(meso_id: int, muscle_group: str) -> dict:
    """
    Returns calibrated MEV, MAV_low, MAV_high, MRV for a muscle group
    based on feedback data from the given mesocycle.
    Also returns a human-readable explanation per landmark.
    """
    base = RP_VOLUMES.get(muscle_group, {
        "MEV": 8, "MAV_low": 12, "MAV_high": 20, "MRV": 22
    })
    weekly = _get_weekly_stats(meso_id, muscle_group)

    # Filter to weeks with feedback
    with_fb = [w for w in weekly if w["pump"] is not None]

    if len(with_fb) < 1:
        return {
            "MEV": base["MEV"], "MAV_low": base["MAV_low"],
            "MAV_high": base["MAV_high"], "MRV": base["MRV"],
            "recommended_start": base["MEV"],
            "source": "literature",
            "confidence": "low",
            "explanations": {"MEV": "Noch kein Feedback — Literaturwert.",
                             "MAV": "Noch kein Feedback — Literaturwert.",
                             "MRV": "Noch kein Feedback — Literaturwert."},
        }

    # ── MEV detection ─────────────────────────────────────────────────────────
    # Lowest volume week where performance was still ≥ 3 (improving/stable)
    mev_candidates = [w for w in with_fb if w["performance"] >= 3.0]
    if mev_candidates:
        mev_week = min(mev_candidates, key=lambda x: x["sets"])
        detected_mev = max(mev_week["sets"], 2)
        mev_explanation = (
            f"Woche {mev_week['week']}: {mev_week['sets']} Sets mit "
            f"Performance {mev_week['performance']:.1f}/5 — niedrigstes Volumen mit positivem Fortschritt."
        )
    else:
        detected_mev = base["MEV"]
        mev_explanation = "Keine Woche mit positiver Performance gefunden — Literaturwert beibehalten."

    # ── MRV detection ─────────────────────────────────────────────────────────
    # First week where soreness > 3.5 OR performance < 3 (excluding deload week)
    non_deload = with_fb[:-1] if len(with_fb) > 1 else with_fb
    mrv_candidates = [
        w for w in non_deload
        if w["soreness"] > 3.5 or w["performance"] < 3.0
    ]
    if mrv_candidates:
        mrv_week = mrv_candidates[0]  # first sign of overreaching
        detected_mrv = max(mrv_week["sets"] - 1, detected_mev + 2)
        mrv_explanation = (
            f"Woche {mrv_week['week']}: {mrv_week['sets']} Sets — "
            f"Soreness {mrv_week['soreness']:.1f}/5, Performance {mrv_week['performance']:.1f}/5. "
            f"MRV bei {detected_mrv} Sets gesetzt (eine Stufe darunter)."
        )
    else:
        # No MRV hit — can likely handle more volume
        max_sets_done = max(w["sets"] for w in with_fb)
        detected_mrv = min(max_sets_done + 4, base["MRV"] + 4)
        mrv_explanation = (
            f"MRV nie erreicht — du hast bis {max_sets_done} Sets toleriert ohne Warnsignale. "
            f"MRV auf {detected_mrv} Sets hochgesetzt."
        )

    # ── MAV detection ─────────────────────────────────────────────────────────
    # Weeks with high pump (≥3.5), moderate soreness (≤3.5), good performance (≥3)
    mav_weeks = [
        w for w in with_fb
        if w["pump"] >= 3.5 and w["soreness"] <= 3.5 and w["performance"] >= 3.0
        and w["sets"] >= detected_mev and w["sets"] <= detected_mrv
    ]
    if mav_weeks:
        mav_sets = [w["sets"] for w in mav_weeks]
        detected_mav_low = max(min(mav_sets), detected_mev)
        detected_mav_high = min(max(mav_sets), detected_mrv)
        best_week = max(mav_weeks, key=lambda x: x["pump"] + x["performance"] - x["soreness"])
        mav_explanation = (
            f"Optimales Fenster: {detected_mav_low}–{detected_mav_high} Sets/Woche. "
            f"Bestes Woche {best_week['week']}: Pump {best_week['pump']:.1f}, "
            f"Soreness {best_week['soreness']:.1f}, Performance {best_week['performance']:.1f}."
        )
    else:
        # Fallback: interpolate between MEV and MRV
        detected_mav_low = detected_mev + round((detected_mrv - detected_mev) * 0.25)
        detected_mav_high = detected_mev + round((detected_mrv - detected_mev) * 0.75)
        mav_explanation = "Kein klares MAV-Fenster erkannt — aus MEV/MRV interpoliert."

    # ── Recommended start for next meso ──────────────────────────────────────
    # Start at lower end of MAV (not MEV — we already know MEV from last meso)
    recommended_start = detected_mav_low
    # Clamp to sane range
    recommended_start = max(detected_mev, min(recommended_start, detected_mav_high))

    return {
        "MEV": detected_mev,
        "MAV_low": detected_mav_low,
        "MAV_high": detected_mav_high,
        "MRV": detected_mrv,
        "recommended_start": recommended_start,
        "source": "calibrated",
        "confidence": "high" if len(with_fb) >= 4 else ("medium" if len(with_fb) >= 2 else "low"),
        "explanations": {
            "MEV": mev_explanation,
            "MAV": mav_explanation,
            "MRV": mrv_explanation,
        },
        "weeks_with_data": len(with_fb),
    }


def get_best_previous_meso(muscle_group: str, exclude_meso_id: int = None) -> dict | None:
    """Returns the most recent meso (active or completed) that trained this muscle group."""
    mesocycles = get_mesocycles()
    candidates = [
        m for m in mesocycles
        if m["status"] in ("completed", "active", "deload")
        and muscle_group in m.get("muscle_groups", [])
        and (exclude_meso_id is None or m["id"] != exclude_meso_id)
    ]
    # Prefer completed, then active with most feedback weeks
    completed = [m for m in candidates if m["status"] == "completed"]
    if completed:
        return completed[0]
    return candidates[0] if candidates else None


def get_calibrated_volumes(muscle_group: str, exclude_meso_id: int = None) -> dict:
    """
    Main entry point: returns calibrated volumes for a muscle group
    using the most recent completed mesocycle. Falls back to literature values.
    """
    prev = get_best_previous_meso(muscle_group, exclude_meso_id)
    if prev:
        result = calibrate_muscle(prev["id"], muscle_group)
        result["source_meso"] = prev["name"]
        result["source_meso_id"] = prev["id"]
        return result

    # No history — return literature values
    base = RP_VOLUMES.get(muscle_group, {"MEV": 8, "MAV_low": 12, "MAV_high": 20, "MRV": 22})
    return {
        **base,
        "recommended_start": base["MEV"],
        "source": "literature",
        "confidence": "low",
        "explanations": {
            "MEV": "Kein vorheriger Zyklus — RP-Literaturwert.",
            "MAV": "Kein vorheriger Zyklus — RP-Literaturwert.",
            "MRV": "Kein vorheriger Zyklus — RP-Literaturwert.",
        },
    }

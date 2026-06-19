# Volume Landmarks per muscle group (sets per week)
# Source: RP (Renaissance Periodization) – Dr. Mike Israetel
# MV  = Maintenance Volume   (Volumen um Muskelmasse zu halten)
# MEV = Minimum Effective Volume  (Minimum für Wachstumsreiz)
# MAV = Maximum Adaptive Volume   (optimaler Wachstumsbereich)
# MRV = Maximum Recoverable Volume (Obergrenze Erholung)
# Freq = empfohlene Trainingsfrequenz pro Woche

RP_VOLUMES = {
    # ── Brust ─────────────────────────────────────────────────────────────────
    "Chest": {
        "MV": 4, "MEV": 6, "MAV_low": 7, "MAV_high": 19, "MRV": 22,
        "freq_per_week": 2, "icon": "🫀",
    },

    # ── Rücken (aufgeteilt) ────────────────────────────────────────────────────
    # RP zählt Back als Einheit (MEV 10, MRV 20-35).
    # Wir teilen Lat (60%) / Oberer Rücken (40%) auf.
    "Lat": {
        "MV": 4, "MEV": 6, "MAV_low": 7, "MAV_high": 12, "MRV": 16,
        "freq_per_week": 2, "icon": "🔙",
    },
    "Oberer Rücken": {
        "MV": 2, "MEV": 4, "MAV_low": 4, "MAV_high": 8, "MRV": 12,
        "freq_per_week": 2, "icon": "🔝",
    },
    "Traps": {
        "MV": 0, "MEV": 4, "MAV_low": 7, "MAV_high": 24, "MRV": 25,
        "freq_per_week": 3, "icon": "🗻",
    },

    # ── Schultern ──────────────────────────────────────────────────────────────
    "Schulter Vorne": {
        # MEV = 0: wird durch Pressing (Bench/OHP) vollständig mittrainiert
        "MV": 0, "MEV": 0, "MAV_low": 0, "MAV_high": 12, "MRV": 16,
        "freq_per_week": 3, "icon": "⬆️",
    },
    "Schulter Seite": {
        "MV": 6, "MEV": 8, "MAV_low": 9, "MAV_high": 24, "MRV": 25,
        "freq_per_week": 3, "icon": "↔️",
    },
    "Schulter Hinten": {
        # MEV = 0: wird durch Rowing-Bewegungen mittrainiert
        "MV": 0, "MEV": 6, "MAV_low": 7, "MAV_high": 17, "MRV": 20,
        "freq_per_week": 3, "icon": "⬇️",
    },

    # ── Arme ──────────────────────────────────────────────────────────────────
    "Biceps": {
        "MV": 4, "MEV": 8, "MAV_low": 9, "MAV_high": 19, "MRV": 26,
        "freq_per_week": 2, "icon": "💪",
    },
    "Triceps": {
        "MV": 4, "MEV": 6, "MAV_low": 7, "MAV_high": 19, "MRV": 22,
        "freq_per_week": 3, "icon": "🔱",
    },
    "Forearms": {
        "MV": 0, "MEV": 4, "MAV_low": 9, "MAV_high": 19, "MRV": 22,
        "freq_per_week": 3, "icon": "🤜",
    },

    # ── Beine ─────────────────────────────────────────────────────────────────
    "Quads": {
        "MV": 6, "MEV": 8, "MAV_low": 9, "MAV_high": 17, "MRV": 20,
        "freq_per_week": 2, "icon": "🦵",
    },
    "Hamstrings": {
        "MV": 3, "MEV": 4, "MAV_low": 5, "MAV_high": 12, "MRV": 16,
        "freq_per_week": 2, "icon": "🦿",
    },
    "Glutes": {
        # MEV = 0: wird durch Squats/Deadlifts ausreichend mittrainiert
        "MV": 0, "MEV": 0, "MAV_low": 4, "MAV_high": 12, "MRV": 16,
        "freq_per_week": 2, "icon": "🍑",
    },
    "Calves": {
        "MV": 0, "MEV": 4, "MAV_low": 9, "MAV_high": 19, "MRV": 22,
        "freq_per_week": 4, "icon": "🦶",
    },

    # ── Core / Sonstiges ──────────────────────────────────────────────────────
    "Abs": {
        "MV": 0, "MEV": 0, "MAV_low": 7, "MAV_high": 24, "MRV": 25,
        "freq_per_week": 3, "icon": "🫁",
    },
}

MUSCLE_GROUPS = list(RP_VOLUMES.keys())

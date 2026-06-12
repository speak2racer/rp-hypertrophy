# Volume Landmarks per muscle group (sets per week)
# Based on hypertrophy research literature
# MEV = Minimum Effective Volume, MAV = Maximum Adaptive Volume, MRV = Maximum Recoverable Volume

RP_VOLUMES = {
    "Chest": {
        "MEV": 8, "MAV_low": 12, "MAV_high": 20, "MRV": 22,
        "freq_per_week": 2, "icon": "💪"
    },
    "Lat": {
        "MEV": 8, "MAV_low": 12, "MAV_high": 18, "MRV": 22,
        "freq_per_week": 2, "icon": "🔙"
    },
    "Oberer Rücken": {
        "MEV": 8, "MAV_low": 12, "MAV_high": 18, "MRV": 22,
        "freq_per_week": 3, "icon": "🔝"
    },
    "Schulter Seite": {
        "MEV": 6, "MAV_low": 12, "MAV_high": 18, "MRV": 22,
        "freq_per_week": 3, "icon": "↔️"
    },
    "Biceps": {
        "MEV": 8, "MAV_low": 14, "MAV_high": 20, "MRV": 26,
        "freq_per_week": 2, "icon": "💪"
    },
    "Triceps": {
        "MEV": 6, "MAV_low": 10, "MAV_high": 14, "MRV": 18,
        "freq_per_week": 2, "icon": "💪"
    },
    "Quads": {
        "MEV": 8, "MAV_low": 12, "MAV_high": 18, "MRV": 20,
        "freq_per_week": 2, "icon": "🦵"
    },
    "Hamstrings & Glutes": {
        "MEV": 6, "MAV_low": 10, "MAV_high": 18, "MRV": 22,
        "freq_per_week": 2, "icon": "🦵"
    },
    "Calves": {
        "MEV": 8, "MAV_low": 12, "MAV_high": 16, "MRV": 20,
        "freq_per_week": 3, "icon": "🦶"
    },
    "Abs": {
        "MEV": 0, "MAV_low": 16, "MAV_high": 20, "MRV": 25,
        "freq_per_week": 3, "icon": "🫁"
    },
}

MUSCLE_GROUPS = list(RP_VOLUMES.keys())

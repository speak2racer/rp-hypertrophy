"""
Predefined training split templates.
Each template has named training days with pre-assigned muscle groups.
"""

TEMPLATES = {
    "PPL 6-Tage": {
        "description": "Push / Pull / Legs — 6 Tage, 2 Rotationen",
        "days": {
            "Push A":  ["Chest", "Schulter Seite", "Triceps"],
            "Pull A":  ["Lat", "Oberer Rücken", "Biceps"],
            "Legs A":  ["Quads", "Hamstrings & Glutes", "Calves"],
            "Push B":  ["Chest", "Schulter Seite", "Triceps"],
            "Pull B":  ["Lat", "Oberer Rücken", "Biceps"],
            "Legs B":  ["Quads", "Hamstrings & Glutes", "Calves", "Abs"],
        },
        "suggested_order": ["Push A", "Pull A", "Legs A", "Push B", "Pull B", "Legs B"],
    },
    "Push/Pull 4-Tage": {
        "description": "Push / Pull — 4 Tage, Beine in Push & Pull integriert",
        "days": {
            "Push A": ["Chest", "Schulter Seite", "Triceps", "Quads"],
            "Pull A": ["Lat", "Oberer Rücken", "Biceps", "Hamstrings & Glutes"],
            "Push B": ["Chest", "Schulter Seite", "Triceps", "Quads", "Calves"],
            "Pull B": ["Lat", "Oberer Rücken", "Biceps", "Hamstrings & Glutes", "Abs"],
        },
        "suggested_order": ["Push A", "Pull A", "Push B", "Pull B"],
    },
    "Push/Pull 6-Tage": {
        "description": "Push / Pull — 6 Tage, Quads bei Push, Hamstrings & Glutes bei Pull",
        "days": {
            "Push A": ["Chest", "Schulter Seite", "Triceps", "Quads"],
            "Pull A": ["Lat", "Oberer Rücken", "Biceps", "Hamstrings & Glutes"],
            "Push B": ["Chest", "Schulter Seite", "Triceps", "Quads", "Calves"],
            "Pull B": ["Lat", "Oberer Rücken", "Biceps", "Hamstrings & Glutes"],
            "Push C": ["Chest", "Schulter Seite", "Triceps", "Quads", "Abs"],
            "Pull C": ["Lat", "Oberer Rücken", "Biceps", "Hamstrings & Glutes", "Calves"],
        },
        "suggested_order": ["Push A", "Pull A", "Push B", "Pull B", "Push C", "Pull C"],
    },
    "Upper/Lower 4-Tage": {
        "description": "Oberkörper / Unterkörper — 4 Tage, 2 Rotationen",
        "days": {
            "Upper A": ["Chest", "Lat", "Oberer Rücken", "Schulter Seite", "Triceps"],
            "Lower A": ["Quads", "Hamstrings & Glutes", "Calves"],
            "Upper B": ["Chest", "Lat", "Oberer Rücken", "Schulter Seite", "Biceps"],
            "Lower B": ["Quads", "Hamstrings & Glutes", "Calves", "Abs"],
        },
        "suggested_order": ["Upper A", "Lower A", "Upper B", "Lower B"],
    },
    "Upper/Lower 5-Tage": {
        "description": "Oberkörper / Unterkörper — 5 Tage mit Arm-/Schulter-Tag",
        "days": {
            "Upper A":  ["Chest", "Lat", "Oberer Rücken", "Schulter Seite"],
            "Lower A":  ["Quads", "Hamstrings & Glutes", "Calves"],
            "Upper B":  ["Chest", "Lat", "Oberer Rücken", "Biceps", "Triceps"],
            "Lower B":  ["Quads", "Hamstrings & Glutes", "Abs"],
            "Arms":     ["Schulter Seite", "Oberer Rücken", "Biceps", "Triceps", "Calves"],
        },
        "suggested_order": ["Upper A", "Lower A", "Upper B", "Lower B", "Arms"],
    },
    "Full Body 3-Tage": {
        "description": "Ganzkörper — 3 Tage mit Schwerpunktwechsel",
        "days": {
            "Full Body A": ["Chest", "Lat", "Schulter Seite", "Quads", "Hamstrings & Glutes", "Calves"],
            "Full Body B": ["Chest", "Lat", "Oberer Rücken", "Quads", "Biceps", "Triceps"],
            "Full Body C": ["Chest", "Lat", "Schulter Seite", "Hamstrings & Glutes", "Calves", "Abs"],
        },
        "suggested_order": ["Full Body A", "Full Body B", "Full Body C"],
    },
    "Bro Split 5-Tage": {
        "description": "Klassischer Bro Split — eine Muskelgruppe pro Tag",
        "days": {
            "Chest":      ["Chest", "Triceps"],
            "Back":       ["Lat", "Oberer Rücken", "Biceps"],
            "Shoulders":  ["Schulter Seite", "Oberer Rücken"],
            "Arms":       ["Biceps", "Triceps", "Abs"],
            "Legs":       ["Quads", "Hamstrings & Glutes", "Calves"],
        },
        "suggested_order": ["Chest", "Back", "Shoulders", "Arms", "Legs"],
    },
    "Custom": {
        "description": "Eigenes Template — du definierst Tage und Muskelgruppen",
        "days": {},
        "suggested_order": [],
    },
}

TEMPLATE_NAMES = list(TEMPLATES.keys())

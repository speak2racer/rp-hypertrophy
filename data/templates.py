"""
Predefined training split templates.
Each template has named training days with pre-assigned muscle groups.
"""

TEMPLATES = {
    "PPL 6-Tage": {
        "description": "Push / Pull / Legs — 6 Tage, 2 Rotationen",
        "days": {
            "Push A":  ["Chest", "Schulter Seite", "Triceps"],
            "Pull A":  ["Lat", "Oberer Rücken", "Schulter Hinten", "Biceps"],
            "Legs A":  ["Quads", "Hamstrings", "Glutes", "Calves"],
            "Push B":  ["Chest", "Schulter Seite", "Triceps"],
            "Pull B":  ["Lat", "Oberer Rücken", "Schulter Hinten", "Biceps"],
            "Legs B":  ["Quads", "Hamstrings", "Calves", "Abs"],
        },
        "suggested_order": ["Push A", "Pull A", "Legs A", "Push B", "Pull B", "Legs B"],
    },
    "Push/Pull 6-Tage": {
        "description": "Push / Pull — 6 Tage, 3 Rotationen (keine Beine als eigener Tag)",
        "days": {
            "Push A": ["Chest", "Schulter Seite", "Triceps"],
            "Pull A": ["Lat", "Oberer Rücken", "Schulter Hinten", "Biceps", "Hamstrings"],
            "Push B": ["Chest", "Schulter Seite", "Triceps"],
            "Pull B": ["Lat", "Oberer Rücken", "Schulter Hinten", "Biceps", "Quads"],
            "Push C": ["Chest", "Schulter Seite", "Triceps"],
            "Pull C": ["Lat", "Oberer Rücken", "Schulter Hinten", "Biceps", "Glutes", "Calves"],
        },
        "suggested_order": ["Push A", "Pull A", "Push B", "Pull B", "Push C", "Pull C"],
    },
    "Push/Pull 4-Tage": {
        "description": "Push / Pull — 4 Tage, 2 Rotationen",
        "days": {
            "Push A": ["Chest", "Schulter Seite", "Triceps"],
            "Pull A": ["Lat", "Oberer Rücken", "Schulter Hinten", "Biceps"],
            "Push B": ["Chest", "Schulter Seite", "Triceps"],
            "Pull B": ["Lat", "Oberer Rücken", "Schulter Hinten", "Biceps"],
        },
        "suggested_order": ["Push A", "Pull A", "Push B", "Pull B"],
    },
    "Upper/Lower 4-Tage": {
        "description": "Oberkörper / Unterkörper — 4 Tage, 2 Rotationen",
        "days": {
            "Upper A": ["Chest", "Lat", "Oberer Rücken", "Schulter Seite", "Schulter Hinten", "Biceps", "Triceps"],
            "Lower A": ["Quads", "Hamstrings", "Glutes", "Calves"],
            "Upper B": ["Chest", "Lat", "Oberer Rücken", "Schulter Seite", "Schulter Hinten", "Biceps", "Triceps"],
            "Lower B": ["Quads", "Hamstrings", "Glutes", "Abs"],
        },
        "suggested_order": ["Upper A", "Lower A", "Upper B", "Lower B"],
    },
    "Upper/Lower 5-Tage": {
        "description": "Oberkörper / Unterkörper — 5 Tage mit zusätzlichem Arm-/Schulter-Tag",
        "days": {
            "Upper A":  ["Chest", "Lat", "Oberer Rücken", "Schulter Seite", "Schulter Hinten"],
            "Lower A":  ["Quads", "Hamstrings", "Glutes", "Calves"],
            "Upper B":  ["Chest", "Lat", "Oberer Rücken", "Biceps", "Triceps"],
            "Lower B":  ["Quads", "Hamstrings", "Calves", "Abs"],
            "Arms":     ["Biceps", "Triceps", "Schulter Seite", "Schulter Hinten"],
        },
        "suggested_order": ["Upper A", "Lower A", "Upper B", "Lower B", "Arms"],
    },
    "Full Body 3-Tage": {
        "description": "Ganzkörper — 3 Tage mit Schwerpunktwechsel",
        "days": {
            "Full Body A": ["Chest", "Lat", "Quads", "Hamstrings"],
            "Full Body B": ["Schulter Seite", "Schulter Hinten", "Lat", "Oberer Rücken", "Quads", "Glutes", "Biceps"],
            "Full Body C": ["Chest", "Schulter Seite", "Hamstrings", "Calves", "Triceps"],
        },
        "suggested_order": ["Full Body A", "Full Body B", "Full Body C"],
    },
    "Bro Split 5-Tage": {
        "description": "Klassischer Bro Split — eine Muskelgruppe pro Tag",
        "days": {
            "Chest":      ["Chest", "Triceps"],
            "Back":       ["Lat", "Oberer Rücken", "Biceps"],
            "Shoulders":  ["Schulter Seite", "Schulter Hinten", "Abs"],
            "Arms":       ["Biceps", "Triceps"],
            "Legs":       ["Quads", "Hamstrings", "Glutes", "Calves"],
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

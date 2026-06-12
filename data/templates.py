"""
Predefined training split templates.
Each template has named training days with pre-assigned muscle groups.
"""

TEMPLATES = {
    "PPL 6-Tage": {
        "description": "Push / Pull / Legs — 6 Tage, 2 Rotationen",
        "days": {
            "Push A":  ["Chest", "Shoulders", "Triceps"],
            "Pull A":  ["Back", "Biceps"],
            "Legs A":  ["Quads", "Hamstrings", "Glutes", "Calves"],
            "Push B":  ["Chest", "Shoulders", "Triceps"],
            "Pull B":  ["Back", "Biceps"],
            "Legs B":  ["Quads", "Hamstrings", "Calves", "Abs"],
        },
        "suggested_order": ["Push A", "Pull A", "Legs A", "Push B", "Pull B", "Legs B"],
    },
    "Push/Pull 6-Tage": {
        "description": "Push / Pull — 6 Tage, 3 Rotationen (keine Beine als eigener Tag)",
        "days": {
            "Push A": ["Chest", "Shoulders", "Triceps"],
            "Pull A": ["Back", "Biceps", "Hamstrings"],
            "Push B": ["Chest", "Shoulders", "Triceps"],
            "Pull B": ["Back", "Biceps", "Quads"],
            "Push C": ["Chest", "Shoulders", "Triceps"],
            "Pull C": ["Back", "Biceps", "Glutes", "Calves"],
        },
        "suggested_order": ["Push A", "Pull A", "Push B", "Pull B", "Push C", "Pull C"],
    },
    "Push/Pull 4-Tage": {
        "description": "Push / Pull — 4 Tage, 2 Rotationen",
        "days": {
            "Push A": ["Chest", "Shoulders", "Triceps"],
            "Pull A": ["Back", "Biceps"],
            "Push B": ["Chest", "Shoulders", "Triceps"],
            "Pull B": ["Back", "Biceps"],
        },
        "suggested_order": ["Push A", "Pull A", "Push B", "Pull B"],
    },
    "Upper/Lower 4-Tage": {
        "description": "Oberkörper / Unterkörper — 4 Tage, 2 Rotationen",
        "days": {
            "Upper A": ["Chest", "Back", "Shoulders", "Biceps", "Triceps"],
            "Lower A": ["Quads", "Hamstrings", "Glutes", "Calves"],
            "Upper B": ["Chest", "Back", "Shoulders", "Biceps", "Triceps"],
            "Lower B": ["Quads", "Hamstrings", "Glutes", "Abs"],
        },
        "suggested_order": ["Upper A", "Lower A", "Upper B", "Lower B"],
    },
    "Upper/Lower 5-Tage": {
        "description": "Oberkörper / Unterkörper — 5 Tage mit zusätzlichem Arm-/Schulter-Tag",
        "days": {
            "Upper A":  ["Chest", "Back", "Shoulders"],
            "Lower A":  ["Quads", "Hamstrings", "Glutes", "Calves"],
            "Upper B":  ["Chest", "Back", "Biceps", "Triceps"],
            "Lower B":  ["Quads", "Hamstrings", "Calves", "Abs"],
            "Arms":     ["Biceps", "Triceps", "Shoulders"],
        },
        "suggested_order": ["Upper A", "Lower A", "Upper B", "Lower B", "Arms"],
    },
    "Full Body 3-Tage": {
        "description": "Ganzkörper — 3 Tage mit Schwerpunktwechsel",
        "days": {
            "Full Body A": ["Chest", "Back", "Quads", "Hamstrings"],
            "Full Body B": ["Shoulders", "Back", "Quads", "Glutes", "Biceps"],
            "Full Body C": ["Chest", "Shoulders", "Hamstrings", "Calves", "Triceps"],
        },
        "suggested_order": ["Full Body A", "Full Body B", "Full Body C"],
    },
    "Bro Split 5-Tage": {
        "description": "Klassischer Bro Split — eine Muskelgruppe pro Tag",
        "days": {
            "Chest":     ["Chest", "Triceps"],
            "Back":      ["Back", "Biceps"],
            "Shoulders": ["Shoulders", "Abs"],
            "Arms":      ["Biceps", "Triceps"],
            "Legs":      ["Quads", "Hamstrings", "Glutes", "Calves"],
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

EXERCISES = {
    "Chest": [
        # Compound Press
        {"name": "Flat Barbell Bench Press", "equipment": "Barbell", "sfr": "high"},
        {"name": "Incline Barbell Bench Press", "equipment": "Barbell", "sfr": "high"},
        {"name": "Decline Barbell Bench Press", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Flat Dumbbell Press", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Incline Dumbbell Press", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Decline Dumbbell Press", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Machine Chest Press", "equipment": "Machine", "sfr": "high"},
        {"name": "Incline Machine Press", "equipment": "Machine", "sfr": "high"},
        {"name": "Smith Machine Bench Press", "equipment": "Machine", "sfr": "medium"},
        {"name": "Dips (chest focus)", "equipment": "Bodyweight", "sfr": "medium"},
        # Fly / Isolation
        {"name": "Cable Fly (mid)", "equipment": "Cable", "sfr": "high"},
        {"name": "Low-to-High Cable Fly", "equipment": "Cable", "sfr": "high"},
        {"name": "High-to-Low Cable Fly", "equipment": "Cable", "sfr": "high"},
        {"name": "Pec Deck", "equipment": "Machine", "sfr": "high"},
        {"name": "Flat DB Fly", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Incline DB Fly", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "DB Pullover", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Landmine Press", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Push-Up", "equipment": "Bodyweight", "sfr": "medium"},
    ],
    "Back": [
        # Vertical Pull
        {"name": "Pull-Up", "equipment": "Bodyweight", "sfr": "high"},
        {"name": "Chin-Up", "equipment": "Bodyweight", "sfr": "high"},
        {"name": "Lat Pulldown (wide grip)", "equipment": "Machine", "sfr": "high"},
        {"name": "Lat Pulldown (neutral grip)", "equipment": "Machine", "sfr": "high"},
        {"name": "Straight-Arm Pulldown", "equipment": "Cable", "sfr": "medium"},
        {"name": "Single-Arm Pulldown", "equipment": "Cable", "sfr": "high"},
        # Horizontal Pull
        {"name": "Barbell Row", "equipment": "Barbell", "sfr": "high"},
        {"name": "Pendlay Row", "equipment": "Barbell", "sfr": "high"},
        {"name": "T-Bar Row", "equipment": "Barbell", "sfr": "high"},
        {"name": "Seated Cable Row (wide)", "equipment": "Cable", "sfr": "high"},
        {"name": "Seated Cable Row (narrow)", "equipment": "Cable", "sfr": "high"},
        {"name": "Single-Arm DB Row", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Chest-Supported DB Row", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Chest-Supported Machine Row", "equipment": "Machine", "sfr": "high"},
        {"name": "Meadows Row", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Seated Machine Row", "equipment": "Machine", "sfr": "high"},
        # Hinge
        {"name": "Deadlift", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Rack Pull", "equipment": "Barbell", "sfr": "medium"},
        # Rear Delt / Upper Back
        {"name": "Face Pull", "equipment": "Cable", "sfr": "high"},
        {"name": "Band Pull-Apart", "equipment": "Equipment", "sfr": "high"},
    ],
    "Shoulders": [
        # Press
        {"name": "Seated DB Press", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Standing DB Press", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Barbell OHP (seated)", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Barbell OHP (standing)", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Machine Shoulder Press", "equipment": "Machine", "sfr": "medium"},
        {"name": "Smith Machine OHP", "equipment": "Machine", "sfr": "medium"},
        {"name": "Arnold Press", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Landmine Lateral Raise", "equipment": "Barbell", "sfr": "high"},
        # Lateral / Side Delt
        {"name": "Dumbbell Lateral Raise", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Cable Lateral Raise", "equipment": "Cable", "sfr": "high"},
        {"name": "Machine Lateral Raise", "equipment": "Machine", "sfr": "high"},
        {"name": "Leaning Cable Lateral Raise", "equipment": "Cable", "sfr": "high"},
        # Rear Delt
        {"name": "Face Pull", "equipment": "Cable", "sfr": "high"},
        {"name": "Rear Delt Fly (DB)", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Rear Delt Fly (Machine)", "equipment": "Machine", "sfr": "high"},
        {"name": "Reverse Pec Deck", "equipment": "Machine", "sfr": "high"},
        {"name": "High Cable Rear Delt Fly", "equipment": "Cable", "sfr": "high"},
        {"name": "Prone Y-Raise", "equipment": "Dumbbell", "sfr": "medium"},
    ],
    "Biceps": [
        {"name": "Barbell Curl", "equipment": "Barbell", "sfr": "high"},
        {"name": "EZ-Bar Curl", "equipment": "Barbell", "sfr": "high"},
        {"name": "Incline DB Curl", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Standing DB Curl", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Hammer Curl", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Concentration Curl", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Cable Curl (low pulley)", "equipment": "Cable", "sfr": "high"},
        {"name": "Cable Curl (high pulley)", "equipment": "Cable", "sfr": "high"},
        {"name": "Preacher Curl (machine)", "equipment": "Machine", "sfr": "high"},
        {"name": "Preacher Curl (EZ-Bar)", "equipment": "Barbell", "sfr": "high"},
        {"name": "Spider Curl", "equipment": "Barbell", "sfr": "high"},
        {"name": "Cross-Body Hammer Curl", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Reverse Curl", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Drag Curl", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Zottman Curl", "equipment": "Dumbbell", "sfr": "medium"},
    ],
    "Triceps": [
        # Overhead (long head stretch)
        {"name": "Overhead Cable Extension", "equipment": "Cable", "sfr": "high"},
        {"name": "DB Overhead Extension (two-arm)", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "DB Overhead Extension (one-arm)", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "EZ-Bar Overhead Extension", "equipment": "Barbell", "sfr": "high"},
        {"name": "Skull Crusher (flat)", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Skull Crusher (incline)", "equipment": "Barbell", "sfr": "high"},
        # Pushdown
        {"name": "Cable Pushdown (rope)", "equipment": "Cable", "sfr": "high"},
        {"name": "Cable Pushdown (bar)", "equipment": "Cable", "sfr": "high"},
        {"name": "Reverse Pushdown", "equipment": "Cable", "sfr": "medium"},
        # Compound
        {"name": "Close-Grip Bench Press", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Dips (tricep focus)", "equipment": "Bodyweight", "sfr": "medium"},
        {"name": "Smith Machine CG Press", "equipment": "Machine", "sfr": "medium"},
        # Machine
        {"name": "Tricep Machine Press", "equipment": "Machine", "sfr": "high"},
        {"name": "Kickback", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Kickback (cable)", "equipment": "Cable", "sfr": "high"},
    ],
    "Quads": [
        # Squat variations
        {"name": "Barbell Back Squat", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Barbell Front Squat", "equipment": "Barbell", "sfr": "high"},
        {"name": "Goblet Squat", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Pause Squat", "equipment": "Barbell", "sfr": "high"},
        {"name": "Smith Machine Squat", "equipment": "Machine", "sfr": "medium"},
        # Press / Machine
        {"name": "Leg Press", "equipment": "Machine", "sfr": "high"},
        {"name": "Hack Squat (machine)", "equipment": "Machine", "sfr": "high"},
        {"name": "Pendulum Squat", "equipment": "Machine", "sfr": "high"},
        {"name": "V-Squat", "equipment": "Machine", "sfr": "high"},
        # Isolation
        {"name": "Leg Extension", "equipment": "Machine", "sfr": "high"},
        # Lunge / Unilateral
        {"name": "Bulgarian Split Squat", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Bulgarian Split Squat (barbell)", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Walking Lunges", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Reverse Lunge", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Step-Up", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Sissy Squat", "equipment": "Bodyweight", "sfr": "high"},
    ],
    "Hamstrings": [
        # Hip hinge
        {"name": "Romanian Deadlift (barbell)", "equipment": "Barbell", "sfr": "high"},
        {"name": "Romanian Deadlift (dumbbell)", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Stiff-Leg Deadlift", "equipment": "Barbell", "sfr": "high"},
        {"name": "Good Morning", "equipment": "Barbell", "sfr": "medium"},
        {"name": "45° Back Extension", "equipment": "Machine", "sfr": "high"},
        {"name": "Deadlift", "equipment": "Barbell", "sfr": "medium"},
        # Curl
        {"name": "Leg Curl (lying)", "equipment": "Machine", "sfr": "high"},
        {"name": "Leg Curl (seated)", "equipment": "Machine", "sfr": "high"},
        {"name": "Leg Curl (standing)", "equipment": "Machine", "sfr": "high"},
        {"name": "Nordic Curl", "equipment": "Bodyweight", "sfr": "medium"},
        {"name": "Glute-Ham Raise", "equipment": "Machine", "sfr": "medium"},
        {"name": "Cable Pull-Through", "equipment": "Cable", "sfr": "high"},
        {"name": "Swiss Ball Leg Curl", "equipment": "Equipment", "sfr": "medium"},
    ],
    "Glutes": [
        # Hip thrust / Bridge
        {"name": "Barbell Hip Thrust", "equipment": "Barbell", "sfr": "high"},
        {"name": "Smith Machine Hip Thrust", "equipment": "Machine", "sfr": "high"},
        {"name": "DB Hip Thrust", "equipment": "Dumbbell", "sfr": "high"},
        {"name": "Single-Leg Hip Thrust", "equipment": "Bodyweight", "sfr": "high"},
        {"name": "Glute Bridge", "equipment": "Bodyweight", "sfr": "medium"},
        {"name": "Frog Pump", "equipment": "Bodyweight", "sfr": "medium"},
        # Abduction
        {"name": "Cable Kickback", "equipment": "Cable", "sfr": "high"},
        {"name": "Abductor Machine", "equipment": "Machine", "sfr": "medium"},
        {"name": "Cable Hip Abduction", "equipment": "Cable", "sfr": "high"},
        {"name": "Monster Walk (band)", "equipment": "Equipment", "sfr": "medium"},
        # Compound
        {"name": "Sumo Deadlift", "equipment": "Barbell", "sfr": "medium"},
        {"name": "Bulgarian Split Squat", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Step-Up", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Reverse Hyper", "equipment": "Machine", "sfr": "high"},
        {"name": "45° Back Extension (glute focus)", "equipment": "Machine", "sfr": "high"},
        {"name": "Cable Pull-Through", "equipment": "Cable", "sfr": "high"},
    ],
    "Calves": [
        # Standing (gastrocnemius)
        {"name": "Standing Calf Raise (machine)", "equipment": "Machine", "sfr": "high"},
        {"name": "Standing Calf Raise (Smith)", "equipment": "Machine", "sfr": "high"},
        {"name": "Standing Calf Raise (DB)", "equipment": "Dumbbell", "sfr": "medium"},
        {"name": "Single-Leg Calf Raise (BW)", "equipment": "Bodyweight", "sfr": "high"},
        {"name": "Donkey Calf Raise", "equipment": "Machine", "sfr": "high"},
        # Seated (soleus)
        {"name": "Seated Calf Raise", "equipment": "Machine", "sfr": "high"},
        {"name": "Seated Calf Raise (DB)", "equipment": "Dumbbell", "sfr": "medium"},
        # Leg press
        {"name": "Leg Press Calf Raise", "equipment": "Machine", "sfr": "medium"},
        {"name": "Tibialis Raise", "equipment": "Bodyweight", "sfr": "high"},
    ],
    "Abs": [
        # Weighted flexion
        {"name": "Cable Crunch", "equipment": "Cable", "sfr": "high"},
        {"name": "Machine Crunch", "equipment": "Machine", "sfr": "high"},
        {"name": "Decline Weighted Crunch", "equipment": "Equipment", "sfr": "high"},
        # Hanging
        {"name": "Hanging Leg Raise", "equipment": "Bodyweight", "sfr": "high"},
        {"name": "Hanging Knee Raise", "equipment": "Bodyweight", "sfr": "medium"},
        {"name": "Toes to Bar", "equipment": "Bodyweight", "sfr": "high"},
        # Rollout / Anti-extension
        {"name": "Ab Wheel Rollout", "equipment": "Equipment", "sfr": "high"},
        {"name": "Barbell Rollout", "equipment": "Barbell", "sfr": "high"},
        {"name": "Decline Crunch", "equipment": "Bodyweight", "sfr": "medium"},
        # Rotation / Anti-rotation
        {"name": "Cable Woodchop", "equipment": "Cable", "sfr": "high"},
        {"name": "Pallof Press", "equipment": "Cable", "sfr": "medium"},
        # Plank / Isometric
        {"name": "Plank", "equipment": "Bodyweight", "sfr": "medium"},
        {"name": "Dead Bug", "equipment": "Bodyweight", "sfr": "medium"},
        {"name": "L-Sit", "equipment": "Bodyweight", "sfr": "medium"},
        # Crunch variations
        {"name": "Crunch", "equipment": "Bodyweight", "sfr": "medium"},
        {"name": "Reverse Crunch", "equipment": "Bodyweight", "sfr": "high"},
        {"name": "Bicycle Crunch", "equipment": "Bodyweight", "sfr": "medium"},
        {"name": "Sit-Up", "equipment": "Bodyweight", "sfr": "medium"},
    ],
}

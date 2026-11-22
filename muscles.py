"""Which muscles an exercise works, and how much tension each muscle got.

Pure Python (runs in MicroPython in the browser and in CPython for tests).

Each set gives its primary muscles 1 set and its secondary muscles 0.5.
A set with more than 3 reps in reserve is too easy to count fully, so it
counts as half. The goal is GOAL_SETS hard sets per muscle per day.
"""

GOAL_SETS = 2

# id -> display name. The ids match the mesh names in body3d.js.
MUSCLES = [
    ("chest", "Chest"),
    ("front_delts", "Front delts"),
    ("side_delts", "Side delts"),
    ("rear_delts", "Rear delts"),
    ("biceps", "Biceps"),
    ("triceps", "Triceps"),
    ("forearms", "Forearms"),
    ("traps", "Traps"),
    ("lats", "Lats"),
    ("lower_back", "Lower back"),
    ("abs", "Abs"),
    ("obliques", "Obliques"),
    ("glutes", "Glutes"),
    ("quads", "Quads"),
    ("hamstrings", "Hamstrings"),
    ("calves", "Calves"),
]
MUSCLE_NAMES = dict(MUSCLES)

P, S = 1.0, 0.5  # primary, secondary

# First matching rule wins, so specific names come before generic ones.
RULES = [
    (("close grip bench", "close-grip bench", "jm press"), {"triceps": P, "chest": S, "front_delts": S}),
    (("incline bench", "incline press", "incline db press", "incline dumbbell press", "incline smith"), {"chest": P, "front_delts": P, "triceps": S}),
    (("bench", "chest press", "push up", "push-up", "pushup"), {"chest": P, "triceps": S, "front_delts": S}),
    (("skull", "tricep", "pushdown", "push down", "overhead extension", "french press"), {"triceps": P}),
    (("face pull", "rear delt", "reverse fly", "reverse pec"), {"rear_delts": P, "traps": S}),
    (("fly", "flye", "pec deck", "crossover"), {"chest": P, "front_delts": S}),
    (("dip",), {"chest": P, "triceps": P, "front_delts": S}),
    (("romanian", "rdl", "stiff leg", "good morning"), {"hamstrings": P, "glutes": P, "lower_back": S}),
    (("leg curl", "hamstring curl", "nordic"), {"hamstrings": P}),
    (("leg extension",), {"quads": P}),
    (("deadlift",), {"glutes": P, "hamstrings": P, "lower_back": P, "traps": S, "forearms": S, "quads": S}),
    (("hip thrust", "glute bridge", "kickback"), {"glutes": P, "hamstrings": S}),
    (("squat", "leg press", "lunge", "split squat", "step up", "hack"), {"quads": P, "glutes": P, "hamstrings": S}),
    (("calf",), {"calves": P}),
    (("lateral raise", "side raise", "upright row"), {"side_delts": P, "traps": S}),
    (("front raise",), {"front_delts": P}),
    (("overhead press", "ohp", "shoulder press", "military", "arnold", "push press"), {"front_delts": P, "side_delts": S, "triceps": S}),
    (("shrug",), {"traps": P, "forearms": S}),
    (("pull up", "pull-up", "pullup", "chin", "pulldown", "pull down", "pullover"), {"lats": P, "biceps": S, "rear_delts": S}),
    (("row",), {"lats": P, "traps": P, "rear_delts": S, "biceps": S}),
    (("wrist", "farmer", "forearm"), {"forearms": P}),
    (("hammer curl",), {"biceps": P, "forearms": P}),
    (("curl",), {"biceps": P, "forearms": S}),
    (("back extension", "hyperextension", "superman"), {"lower_back": P, "glutes": S}),
    (("twist", "woodchop", "side plank", "oblique"), {"obliques": P, "abs": S}),
    (("crunch", "sit up", "sit-up", "situp", "plank", "leg raise", "ab ", "abs", "rollout"), {"abs": P, "obliques": S}),
]


def detect(exercise_name):
    """Muscles for an exercise name, or {} if it isn't recognised."""
    # Keywords must start at a word boundary ("machine" must not match "chin").
    name = " " + exercise_name.lower().replace("-", " ").replace("_", " ") + " "
    for keywords, muscles in RULES:
        for k in keywords:
            if " " + k.replace("-", " ") in name:
                return dict(muscles)
    return {}


def muscles_for(exercise_name, custom):
    """User-chosen muscles win over auto-detection."""
    k = exercise_name.strip().lower()
    if k in custom:
        return dict(custom[k])
    return detect(exercise_name)


def set_credit(rir):
    """Hard sets (RIR 0-3, or blank = to failure) count fully."""
    if rir is None or rir <= 3:
        return 1.0
    return 0.5


def tension(sets, custom):
    """Total effective sets per muscle id for a list of logged sets."""
    totals = {}
    for s in sets:
        credit = set_credit(s.get("rir"))
        for m, w in muscles_for(s["exercise"], custom).items():
            totals[m] = totals.get(m, 0.0) + w * credit
    return totals


# Colour stops: (effective sets, hex). Untrained muscles stay neutral grey.
UNTRAINED = "#5c5c5c"
STOPS = [
    (0.0, (253, 224, 71)),   # yellow: touched
    (1.0, (249, 115, 22)),   # orange: halfway
    (2.0, (239, 68, 68)),    # red: goal reached
    (4.0, (153, 27, 27)),    # dark red: lots of volume
]


def color_for(sets):
    if sets <= 0:
        return UNTRAINED
    if sets >= STOPS[-1][0]:
        r, g, b = STOPS[-1][1]
        return "#%02x%02x%02x" % (r, g, b)
    for i in range(len(STOPS) - 1):
        a_v, a_c = STOPS[i]
        b_v, b_c = STOPS[i + 1]
        if a_v <= sets <= b_v:
            t = (sets - a_v) / (b_v - a_v)
            rgb = [int(round(a_c[j] + (b_c[j] - a_c[j]) * t)) for j in range(3)]
            return "#%02x%02x%02x" % (rgb[0], rgb[1], rgb[2])
    return UNTRAINED


def fmt_sets(x):
    text = "%.1f" % x
    return text[:-2] if text.endswith(".0") else text


def body_data(totals):
    """Per-muscle colour + label for the 3D model."""
    out = {}
    for mid, label in MUSCLES:
        v = totals.get(mid, 0.0)
        mark = " (goal met)" if v >= GOAL_SETS else ""
        out[mid] = {
            "color": color_for(v),
            "label": "%s: %s / %d sets%s" % (label, fmt_sets(v), GOAL_SETS, mark),
        }
    return out

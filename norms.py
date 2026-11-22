"""Rough "average gym-goer" benchmarks, used for the weight and reps effects.

These are ballpark 1-rep maxes (kg) for a typical recreational lifter, not
elite standards. Dumbbell numbers are per hand. They make the logging
screen fun; they aren't a judgement.
"""

# First match wins (word-boundary match), so specific names come first.
AVG_1RM_KG = [
    (("dumbbell bench", "db bench", "dumbbell press", "db press"), 30),
    (("incline bench", "incline press"), 65),
    (("close grip bench", "close-grip bench"), 70),
    (("bench",), 80),
    (("chest press",), 70),
    (("front squat",), 80),
    (("hack squat",), 120),
    (("leg press",), 180),
    (("split squat", "lunge", "step up"), 50),
    (("squat",), 100),
    (("romanian", "rdl", "stiff leg"), 90),
    (("deadlift",), 125),
    (("hip thrust", "glute bridge"), 110),
    (("leg curl", "hamstring curl"), 50),
    (("leg extension",), 70),
    (("calf",), 100),
    (("overhead press", "ohp", "military", "shoulder press", "push press"), 50),
    (("arnold",), 22),
    (("lateral raise", "side raise"), 12),
    (("front raise",), 12),
    (("rear delt", "reverse fly"), 10),
    (("face pull",), 30),
    (("upright row",), 45),
    (("barbell row", "bent over row", "bent-over row", "pendlay"), 75),
    (("dumbbell row", "db row", "one arm row"), 35),
    (("row",), 65),
    (("pulldown", "pull down"), 65),
    (("shrug",), 100),
    (("hammer curl",), 18),
    (("dumbbell curl", "db curl", "incline curl", "concentration"), 16),
    (("preacher",), 30),
    (("curl",), 35),
    (("skull", "french press"), 35),
    (("pushdown", "push down", "tricep"), 35),
    (("pec deck",), 60),
    (("fly", "flye"), 18),
]


def _match(name, keywords):
    padded = " " + name.lower().replace("-", " ") + " "
    for k in keywords:
        if " " + k.replace("-", " ") in padded:
            return True
    return False


def avg_1rm_kg(exercise_name):
    """Average 1RM in kg, or None if we have no benchmark."""
    for keywords, kg in AVG_1RM_KG:
        if _match(exercise_name, keywords):
            return float(kg)
    return None


def avg_working_kg(exercise_name):
    """Typical weight for a set of ~10 (Epley: 1RM / (1 + 10/30) = 75%)."""
    one = avg_1rm_kg(exercise_name)
    return None if one is None else one * 0.75


# (minimum ratio, tier, headline)
TIERS = [
    (1.5, "beast", "Way above average"),
    (1.15, "heavy", "Heavier than average"),
    (0.85, "avg", "Right around average"),
    (0.0, "light", "Lighter than average"),
]


def compare(value, average):
    """Compare a value to the average. Returns None when there's no benchmark."""
    if average is None or average <= 0 or value is None or value <= 0:
        return None
    ratio = value / average
    for minimum, tier, headline in TIERS:
        if ratio >= minimum:
            return {
                "tier": tier,
                "ratio": ratio,
                "headline": headline,
                "pct": int(round(ratio * 100)),
            }
    return None

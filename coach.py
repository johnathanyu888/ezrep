"""EZRep training math.

Pure Python with no imports beyond `math`, so it runs both in the browser
(PyScript / MicroPython) and under regular CPython for tests.

Core ideas
----------
* Estimated 1RM uses the Epley formula on *reps to failure*
  (reps done + reps in reserve), so a set of 8 @ RIR 2 counts like 10 to failure.
* Your first set of an exercise is the freshest; each extra set costs some
  capacity. We measure that drop from today's sets when we can, otherwise we
  use a default per goal.
* Each goal has a rep range and a target RIR. The next set's reps are what you
  can do at that weight minus the target RIR.
"""

import math

KG_PER_LB = 0.45359237

GOALS = {
    "explosive": {
        "label": "Explosiveness",
        "rir": 1,
        "reps": (3, 5),
        "fatigue": 0.015,
        "tip": "Move every rep as fast as you can. Stop about 1 rep short of failure so bar speed stays high.",
    },
    "strength": {
        "label": "Strength",
        "rir": 1,
        "reps": (3, 6),
        "fatigue": 0.025,
        "tip": "Heavy, crisp reps. Leave about 1 in the tank and rest 3-5 min between sets.",
    },
    "hypertrophy": {
        "label": "Hypertrophy",
        "rir": 0,
        "reps": (6, 12),
        "fatigue": 0.04,
        "tip": "Take every set to true failure (0 RIR). Expect reps to drop each set, which is normal.",
    },
    "endurance": {
        "label": "Endurance",
        "rir": 1,
        "reps": (12, 20),
        "fatigue": 0.04,
        "tip": "Lighter weight, high reps, short rests (30-60 s).",
    },
}


def e1rm(weight, reps, rir=0):
    """Estimated 1-rep max (Epley) from a set, counting reps in reserve."""
    total = reps + (rir or 0)
    if weight <= 0 or total <= 0:
        return 0.0
    if total <= 1:
        return float(weight)
    return weight * (1 + total / 30.0)


def reps_at(one_rm, weight):
    """How many reps to failure you can do at `weight` (inverse Epley)."""
    if weight <= 0 or one_rm <= 0:
        return 0.0
    if weight >= one_rm:
        return 1.0 if weight <= one_rm * 1.01 else 0.0
    return max(1.0, 30.0 * (one_rm / weight - 1))


def weight_for(one_rm, reps):
    """Heaviest weight you can lift for `reps` reps to failure."""
    if reps <= 1:
        return float(one_rm)
    return one_rm / (1 + reps / 30.0)


def round_weight(weight, unit):
    """Round to a loadable plate step: 5 lb or 2.5 kg."""
    step = 2.5 if unit == "kg" else 5.0
    return max(step, round(weight / step) * step)


def to_unit(weight_kg, unit):
    return weight_kg if unit == "kg" else weight_kg / KG_PER_LB


def from_unit(weight, unit):
    return weight if unit == "kg" else weight * KG_PER_LB


def set_e1rm(s):
    return e1rm(s["weight"], s["reps"], s.get("rir") or 0)


def group_sessions(sets):
    """Map date -> list of sets (sorted by time) for one exercise."""
    sessions = {}
    for s in sets:
        sessions.setdefault(s["date"], []).append(s)
    for d in sessions:
        sessions[d].sort(key=lambda x: x["ts"])
    return sessions


def fresh_e1rm(sets, today):
    """Best estimate of your *fresh* 1RM for one exercise.

    If you've trained it today, set 1 is the freshest reading of today's form.
    Otherwise use the best set across your last 3 sessions.
    """
    sessions = group_sessions(sets)
    if today in sessions:
        todays = sessions[today]
        return max(set_e1rm(todays[0]), max(set_e1rm(s) for s in todays))
    past = sorted([d for d in sessions if d < today], reverse=True)[:3]
    best = 0.0
    for d in past:
        for s in sessions[d]:
            best = max(best, set_e1rm(s))
    return best


def fatigue_rate(todays_sets, goal):
    """Fraction of strength lost per set. Measured from today when possible."""
    default = GOALS[goal]["fatigue"]
    n = len(todays_sets)
    if n < 2:
        return default
    first = set_e1rm(todays_sets[0])
    last = set_e1rm(todays_sets[-1])
    if first <= 0:
        return default
    measured = (first - last) / first / (n - 1)
    # Blend with the default so one sloppy set doesn't swing it wildly.
    rate = 0.6 * measured + 0.4 * default
    return min(0.10, max(0.0, rate))


def recommend(sets, today, goal, unit):
    """Recommend the next set for one exercise.

    `sets` are dicts with weight (in `unit`), reps, rir (or None), date, ts.
    Returns None if there's no data for this exercise yet.
    """
    g = GOALS[goal]
    lo, hi = g["reps"]
    target_rir = g["rir"]
    one_rm = fresh_e1rm(sets, today)
    if one_rm <= 0:
        return None

    todays = group_sessions(sets).get(today, [])
    n = len(todays)
    rate = fatigue_rate(todays, goal)

    if n == 0:
        # First set: you're freshest here, so aim at the middle of the range.
        mid = (lo + hi) // 2
        w = round_weight(weight_for(one_rm, mid + target_rir), unit)
        projected = one_rm
        reason = "Set 1 is your freshest set, so this is where you'll hit your best numbers."
    else:
        last = todays[-1]
        projected = set_e1rm(last) * (1 - rate)
        w = float(last["weight"])
        reason = "Set %d: about %d%% weaker than set 1 because of fatigue." % (
            n + 1,
            round(100 * (1 - projected / one_rm)) if one_rm else 0,
        )

    reps = int(math.floor(reps_at(projected, w) - target_rir))

    if reps < lo:
        # Too heavy for this goal now, so drop the weight.
        new_w = round_weight(weight_for(projected, lo + target_rir), unit)
        if new_w < w:
            w = new_w
            reason += " Drop the weight to stay in the %d-%d rep range." % (lo, hi)
        reps = int(math.floor(reps_at(projected, w) - target_rir))
        # Plate rounding can land just too heavy; step down until in range.
        step = 2.5 if unit == "kg" else 5.0
        tries = 0
        while reps < lo and w - step > 0 and tries < 10:
            w -= step
            reps = int(math.floor(reps_at(projected, w) - target_rir))
            tries += 1
    elif reps > hi + 2:
        new_w = round_weight(weight_for(projected, hi + target_rir), unit)
        if new_w > w:
            w = new_w
            reason += " Add weight, because you're above the %d-%d rep range." % (lo, hi)
        reps = int(math.floor(reps_at(projected, w) - target_rir))

    reps = max(1, reps)
    return {
        "set_number": n + 1,
        "weight": w,
        "reps": reps,
        "rir": target_rir,
        "e1rm": one_rm,
        "fatigue_pct": round(rate * 100, 1),
        "reason": reason,
        "tip": g["tip"],
        "range": (lo, hi),
    }

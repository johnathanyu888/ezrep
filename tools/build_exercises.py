"""Build data/exercises.json from free-exercise-db (public domain, Unlicense).

Source: https://github.com/yuhonas/free-exercise-db (dist/exercises.json)

Usage:
    python tools/build_exercises.py path/to/exercises.json data/exercises.json

Output is a compact list of [name, {ezrep_muscle_id: weight}] where primary
muscles get 1 and secondary muscles 0.5. Stretching and cardio entries are
dropped. The source's generic "shoulders" is split into front/side/rear delts
from the exercise name.
"""

import json
import sys

SKIP_CATEGORIES = {"stretching", "cardio"}

DIRECT = {
    "chest": "chest",
    "triceps": "triceps",
    "biceps": "biceps",
    "forearms": "forearms",
    "lats": "lats",
    "traps": "traps",
    "middle back": "traps",     # rhomboids / mid traps
    "lower back": "lower_back",
    "calves": "calves",
    "glutes": "glutes",
    "abductors": "glutes",      # glute medius / minimus
    "hamstrings": "hamstrings",
    "quadriceps": "quads",
    # adductors and neck aren't tracked by EZRep
}

SIDE = ("lateral", "side ", "upright row", "y raise", "lu raise")
REAR = ("rear", "reverse fly", "reverse flye", "face pull", "bent over raise",
        "bent-over raise", "posterior", "reverse machine fly", "back fly")
OBLIQUE = ("oblique", "twist", "side bend", "woodchop", "wood chop", "russian", "side plank",
           "windmill", "saxon", "landmine 180")


def map_muscle(src, name):
    n = name.lower()
    if src == "shoulders":
        if any(k in n for k in REAR):
            return "rear_delts"
        if any(k in n for k in SIDE):
            return "side_delts"
        return "front_delts"
    if src == "abdominals":
        return "obliques" if any(k in n for k in OBLIQUE) else "abs"
    return DIRECT.get(src)


def build(entries):
    out = []
    for e in entries:
        if e.get("category") in SKIP_CATEGORIES:
            continue
        muscles = {}
        for src in e.get("secondaryMuscles", []):
            m = map_muscle(src, e["name"])
            if m:
                muscles[m] = max(muscles.get(m, 0), 0.5)
        for src in e.get("primaryMuscles", []):
            m = map_muscle(src, e["name"])
            if m:
                muscles[m] = 1.0
        if muscles:
            out.append([e["name"], muscles])
    out.sort(key=lambda x: x[0].lower())
    return out


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        data = build(json.load(f))
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    print("wrote %d exercises to %s" % (len(data), dst))

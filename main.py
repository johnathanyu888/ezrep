"""EZRep UI: runs in the browser via PyScript (MicroPython).

All data lives in this browser's localStorage. No account, no server.
Weights are stored in kg and converted to your chosen unit for display.
"""

import json

from pyscript import document, window, when

import coach

STORAGE_KEY = "ezrep.v1"


# ---------- storage ----------

def load_state():
    state = {"unit": "lb", "goal": "hypertrophy", "sets": []}
    try:
        raw = window.localStorage.getItem(STORAGE_KEY)
        if raw:
            saved = json.loads(raw)
            state.update(saved)
    except Exception:
        pass
    return state


def save_state():
    try:
        window.localStorage.setItem(STORAGE_KEY, json.dumps(STATE))
    except Exception:
        pass


STATE = load_state()


# ---------- helpers ----------

def q(sel):
    return document.querySelector(sel)


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt(x):
    text = "%.1f" % float(x)
    return text[:-2] if text.endswith(".0") else text


def today_str():
    d = window.Date.new()
    return "%04d-%02d-%02d" % (d.getFullYear(), d.getMonth() + 1, d.getDate())


def pretty_date(iso):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    y, m, d = iso.split("-")
    return "%s %d, %s" % (months[int(m) - 1], int(d), y)


def key(name):
    return name.strip().lower()


def unit():
    return STATE["unit"]


def display_sets(exercise_name):
    """Sets for one exercise with weights converted to the display unit."""
    k = key(exercise_name)
    out = []
    for s in STATE["sets"]:
        if key(s["exercise"]) == k:
            c = dict(s)
            c["weight"] = coach.to_unit(s["weight"], unit())
            out.append(c)
    return out


def exercise_names():
    seen = {}
    for s in sorted(STATE["sets"], key=lambda x: x["ts"], reverse=True):
        k = key(s["exercise"])
        if k not in seen:
            seen[k] = s["exercise"]
    return list(seen.values())


def parse_num(text):
    try:
        return float(text)
    except Exception:
        return None


# ---------- rendering ----------

def render_settings():
    q("#unit").innerText = unit()
    for el in document.querySelectorAll(".unitLabel"):
        el.innerText = unit()
    q("#goal").value = STATE["goal"]


def render_datalist():
    q("#exerciseList").innerHTML = "".join(
        '<option value="%s"></option>' % esc(n) for n in exercise_names()
    )


def render_coach():
    name = q("#exercise").value.strip()
    box = q("#coach")
    if not name:
        box.hidden = True
        return
    sets = display_sets(name)
    rec = coach.recommend(sets, today_str(), STATE["goal"], unit())
    box.hidden = False
    q("#coachTitle").innerText = "Coach: " + name
    g = coach.GOALS[STATE["goal"]]
    q("#targetRir").innerText = str(g["rir"])
    today_count = len([s for s in sets if s["date"] == today_str()])
    q("#setCount").innerText = str(today_count)

    if rec is None:
        q("#e1rm").innerText = "–"
        q("#nextSet").innerHTML = (
            '<p class="big">New exercise</p>'
            '<p>Log your first set and I\'ll estimate your 1RM and plan the next set. '
            'For %s, aim for %d-%d reps.</p>' % (g["label"].lower(), g["reps"][0], g["reps"][1])
        )
        q("#coachNote").innerText = g["tip"]
        return

    q("#e1rm").innerText = fmt(rec["e1rm"]) + " " + unit()
    rir_text = "to failure" if rec["rir"] == 0 else "%d rep%s in reserve" % (
        rec["rir"], "" if rec["rir"] == 1 else "s")
    q("#nextSet").innerHTML = (
        '<p class="label">Next: set %d</p>'
        '<p class="big">%s %s &times; %d</p>'
        '<p>Stop %s. %s</p>'
        '<button type="button" class="ghost" id="useRec" data-w="%s" data-r="%d">Fill in this set</button>'
        % (rec["set_number"], fmt(rec["weight"]), unit(), rec["reps"],
           rir_text, esc(rec["reason"]), fmt(rec["weight"]), rec["reps"])
    )
    q("#coachNote").innerText = rec["tip"]


def set_row(s, idx):
    w = coach.to_unit(s["weight"], unit())
    rir = s.get("rir")
    rir_txt = " · RIR %d" % rir if rir is not None else ""
    est = coach.e1rm(w, s["reps"], rir or 0)
    return (
        '<li><span class="setno">%d</span>'
        '<span class="setmain">%s %s &times; %d%s</span>'
        '<span class="est">1RM ~%s</span>'
        '<button class="x" data-del="%s" title="Delete set">&times;</button></li>'
        % (idx, fmt(w), unit(), s["reps"], rir_txt, fmt(est), esc(s["id"]))
    )


def grouped(sets_):
    order, groups = [], {}
    for s in sorted(sets_, key=lambda x: x["ts"]):
        k = key(s["exercise"])
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(s)
    return [(groups[k][0]["exercise"], groups[k]) for k in order]


def render_today():
    t = today_str()
    todays = [s for s in STATE["sets"] if s["date"] == t]
    if not todays:
        q("#today").innerHTML = '<p class="empty">No sets yet. Log your first one above.</p>'
        return
    html = []
    for name, ss in grouped(todays):
        html.append('<div class="ex"><h3 data-pick="%s">%s</h3><ol>' % (esc(name), esc(name)))
        for i, s in enumerate(ss):
            html.append(set_row(s, i + 1))
        html.append("</ol></div>")
    q("#today").innerHTML = "".join(html)


def render_history():
    t = today_str()
    dates = sorted(set(s["date"] for s in STATE["sets"] if s["date"] != t), reverse=True)
    if not dates:
        q("#history").innerHTML = '<p class="empty">Nothing logged before today.</p>'
        return
    html = []
    for d in dates[:30]:
        day = [s for s in STATE["sets"] if s["date"] == d]
        html.append('<details><summary>%s <small>%d sets</small></summary>' % (pretty_date(d), len(day)))
        for name, ss in grouped(day):
            best = max(coach.e1rm(coach.to_unit(s["weight"], unit()), s["reps"], s.get("rir") or 0) for s in ss)
            parts = ", ".join(
                "%s&times;%d" % (fmt(coach.to_unit(s["weight"], unit())), s["reps"]) for s in ss
            )
            html.append(
                '<p class="hist"><strong data-pick="%s">%s</strong> %s <span class="est">1RM ~%s %s</span></p>'
                % (esc(name), esc(name), parts, fmt(best), unit())
            )
        html.append("</details>")
    q("#history").innerHTML = "".join(html)


def render_all():
    render_settings()
    render_datalist()
    render_coach()
    render_today()
    render_history()


# ---------- events ----------

@when("submit", "#logForm")
def on_log(event):
    event.preventDefault()
    name = q("#exercise").value.strip()
    w = parse_num(q("#weight").value)
    r = parse_num(q("#reps").value)
    rir_raw = q("#rir").value.strip()
    rir = parse_num(rir_raw) if rir_raw else None
    if not name or w is None or w < 0 or r is None or r < 1:
        return
    # Reuse the existing spelling of an exercise so history groups together.
    for existing in exercise_names():
        if key(existing) == key(name):
            name = existing
            break
    ts = window.Date.now()
    STATE["sets"].append({
        "id": str(int(ts)),
        "ts": ts,
        "date": today_str(),
        "exercise": name,
        "weight": coach.from_unit(w, unit()),
        "reps": int(r),
        "rir": int(rir) if rir is not None else None,
    })
    save_state()
    q("#reps").value = ""
    q("#rir").value = ""
    render_all()
    q("#reps").focus()


@when("input", "#exercise")
def on_exercise(event):
    render_coach()


@when("change", "#goal")
def on_goal(event):
    STATE["goal"] = q("#goal").value
    save_state()
    render_coach()


@when("click", "#unit")
def on_unit(event):
    old = unit()
    STATE["unit"] = "kg" if old == "lb" else "lb"
    w = parse_num(q("#weight").value)
    if w is not None:
        q("#weight").value = fmt(coach.to_unit(coach.from_unit(w, old), unit()))
    save_state()
    render_all()


@when("click", "main")
def on_main_click(event):
    target = event.target
    del_id = target.getAttribute("data-del")
    if del_id:
        STATE["sets"] = [s for s in STATE["sets"] if s["id"] != del_id]
        save_state()
        render_all()
        return
    pick = target.getAttribute("data-pick")
    if pick:
        q("#exercise").value = pick
        render_coach()
        window.scrollTo(0, 0)
        return
    if target.id == "useRec":
        q("#weight").value = target.getAttribute("data-w")
        q("#reps").value = target.getAttribute("data-r")
        q("#reps").focus()


@when("click", "#exportBtn")
def on_export(event):
    data = json.dumps(STATE)
    a = document.createElement("a")
    a.href = "data:application/json;charset=utf-8," + window.encodeURIComponent(data)
    a.download = "ezrep-backup-%s.json" % today_str()
    a.click()


@when("click", "#clearBtn")
def on_clear(event):
    if window.confirm("Delete ALL logged sets from this device? This can't be undone."):
        STATE["sets"] = []
        save_state()
        render_all()


render_all()
q("#loading").hidden = True
q("#app").hidden = False
q("#exercise").focus()

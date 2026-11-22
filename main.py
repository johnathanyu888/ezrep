"""EZRep UI: runs in the browser via PyScript (MicroPython).

All data lives in this browser's localStorage. No account, no server.
Weights are stored in kg and converted to your chosen unit for display.
"""

import json

from pyscript import document, window, when

import coach
import muscles

STORAGE_KEY = "ezrep.v1"


# ---------- storage ----------

def load_state():
    state = {"unit": "lb", "goal": "hypertrophy", "sets": [], "custom": {}}
    try:
        raw = window.localStorage.getItem(STORAGE_KEY)
        if raw:
            state.update(json.loads(raw))
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


def key(name):
    return name.strip().lower()


def unit():
    return STATE["unit"]


def parse_num(text):
    try:
        return float(text)
    except Exception:
        return None


# ---------- dates (MicroPython has no datetime, so use JS Date) ----------

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def iso(d):
    return "%04d-%02d-%02d" % (d.getFullYear(), d.getMonth() + 1, d.getDate())


def jsdate(iso_s):
    y, m, d = iso_s.split("-")
    return window.Date.new(int(y), int(m) - 1, int(d))


def today_str():
    return iso(window.Date.new())


def add_days(iso_s, n):
    d = jsdate(iso_s)
    d.setDate(d.getDate() + n)
    return iso(d)


def week_start(iso_s):
    """Monday of the week containing iso_s."""
    return add_days(iso_s, -((jsdate(iso_s).getDay() + 6) % 7))


def pretty_date(iso_s):
    d = jsdate(iso_s)
    return "%s, %s %d, %d" % (DAYS[d.getDay()], MONTHS[d.getMonth()], d.getDate(), d.getFullYear())


def short_date(iso_s):
    d = jsdate(iso_s)
    return "%s %d" % (MONTHS[d.getMonth()], d.getDate())


# ---------- view state ----------

VIEW = {"mode": "day", "date": today_str()}
PICKER = {"open": False}


# ---------- data helpers ----------

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


def sets_on(date):
    return [s for s in STATE["sets"] if s["date"] == date]


def exercise_names():
    seen = {}
    for s in sorted(STATE["sets"], key=lambda x: x["ts"], reverse=True):
        k = key(s["exercise"])
        if k not in seen:
            seen[k] = s["exercise"]
    return list(seen.values())


def grouped(sets_):
    order, groups = [], {}
    for s in sorted(sets_, key=lambda x: x["ts"]):
        k = key(s["exercise"])
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(s)
    return [(groups[k][0]["exercise"], groups[k]) for k in order]


# ---------- rendering: settings + log form ----------

def render_settings():
    q("#unit").innerText = unit()
    for el in document.querySelectorAll(".unitLabel"):
        el.innerText = unit()
    q("#goal").value = STATE["goal"]


def render_datalist():
    q("#exerciseList").innerHTML = "".join(
        '<option value="%s"></option>' % esc(n) for n in exercise_names()
    )


def render_muscles_line():
    name = q("#exercise").value.strip()
    line = q("#musclesLine")
    picker = q("#musclePicker")
    if not name:
        line.innerHTML = ""
        picker.hidden = True
        return
    worked = muscles.muscles_for(name, STATE["custom"])
    if worked:
        parts = []
        for mid, w in sorted(worked.items(), key=lambda kv: -kv[1]):
            label = muscles.MUSCLE_NAMES[mid]
            parts.append(label if w >= 1 else label + " (½)")
        line.innerHTML = (
            'Works: <strong>%s</strong> <button type="button" tabindex="-1" class="link" data-act="edit-muscles">%s</button>'
            % (esc(", ".join(parts)), "Done" if PICKER["open"] else "Edit")
        )
    else:
        line.innerHTML = "Pick the muscles this exercise works:"
    show = PICKER["open"] or not worked
    picker.hidden = not show
    if show:
        picker.innerHTML = "".join(
            '<button type="button" tabindex="-1" class="pill%s" data-mus="%s">%s</button>'
            % (" on" if mid in worked else "", mid, label)
            for mid, label in muscles.MUSCLES
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
    q("#setCount").innerText = str(len([s for s in sets if s["date"] == today_str()]))

    if rec is None:
        q("#e1rm").innerText = "–"
        q("#nextSet").innerHTML = (
            '<p class="big">New exercise</p>'
            "<p>Log your first set and I'll estimate your 1RM and plan the next set. "
            "For %s, aim for %d-%d reps.</p>" % (g["label"].lower(), g["reps"][0], g["reps"][1])
        )
        q("#coachNote").innerText = g["tip"]
        return

    q("#e1rm").innerText = fmt(rec["e1rm"]) + " " + unit()
    rir_text = "to failure" if rec["rir"] == 0 else "%d rep%s in reserve" % (
        rec["rir"], "" if rec["rir"] == 1 else "s")
    q("#nextSet").innerHTML = (
        '<p class="label">Next: set %d</p>'
        '<p class="big">%s %s &times; %d</p>'
        "<p>Stop %s. %s</p>"
        '<button type="button" class="ghost" data-act="use-rec" data-w="%s" data-r="%d">Fill in this set</button>'
        % (rec["set_number"], fmt(rec["weight"]), unit(), rec["reps"],
           rir_text, esc(rec["reason"]), fmt(rec["weight"]), rec["reps"])
    )
    q("#coachNote").innerText = rec["tip"]


# ---------- rendering: muscle map ----------

def render_map():
    date = VIEW["date"]
    totals = muscles.tension(sets_on(date), STATE["custom"])
    q("#body3d").setAttribute("data-muscles", json.dumps(muscles.body_data(totals)))
    q("#mapDate").innerText = "· " + ("Today" if date == today_str() else short_date(date))
    hit = sorted([(v, m) for m, v in totals.items() if v > 0], reverse=True)
    if not hit:
        q("#muscleList").innerHTML = '<p class="empty">No sets logged for this day.</p>'
        return
    chips = []
    for v, mid in hit:
        done = v >= muscles.GOAL_SETS
        chips.append(
            '<span class="mchip%s"><i style="background:%s"></i>%s %s/%d%s</span>'
            % (" done" if done else "", muscles.color_for(v), muscles.MUSCLE_NAMES[mid],
               muscles.fmt_sets(v), muscles.GOAL_SETS, " ✓" if done else "")
        )
    q("#muscleList").innerHTML = "".join(chips)


# ---------- rendering: calendar ----------

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


def render_day():
    date = VIEW["date"]
    label = pretty_date(date)
    if date == today_str():
        label = "Today · " + label
    q("#calTitle").innerText = label
    day = sets_on(date)
    if not day:
        q("#calBody").innerHTML = '<p class="empty">Nothing logged this day.</p>'
        return
    html = []
    for name, ss in grouped(day):
        html.append('<div class="ex"><h4 data-pick="%s">%s</h4><ol>' % (esc(name), esc(name)))
        for i, s in enumerate(ss):
            html.append(set_row(s, i + 1))
        html.append("</ol></div>")
    q("#calBody").innerHTML = "".join(html)


def render_week():
    start = week_start(VIEW["date"])
    end = add_days(start, 6)
    q("#calTitle").innerText = "%s – %s" % (short_date(start), short_date(end))
    today = today_str()
    rows, total_sets, days_trained = [], 0, 0
    for i in range(7):
        d = add_days(start, i)
        day = sets_on(d)
        total_sets += len(day)
        if day:
            days_trained += 1
            names = ", ".join(n for n, _ in grouped(day))
            summary = '<span class="wsum">%s</span><span class="wcount">%d set%s</span>' % (esc(names), len(day), "" if len(day) == 1 else "s")
        else:
            summary = '<span class="wsum muted">Rest</span>'
        jd = jsdate(d)
        cls = "wday" + (" today" if d == today else "") + (" sel" if d == VIEW["date"] else "")
        rows.append(
            '<button type="button" class="%s" data-day="%s">'
            '<span class="wdate"><b>%s</b>%d</span>%s</button>'
            % (cls, d, DAYS[jd.getDay()], jd.getDate(), summary)
        )
    rows.append('<p class="hint">%d set%s across %d training day%s this week. Tap a day to open it.</p>'
                % (total_sets, "" if total_sets == 1 else "s", days_trained, "" if days_trained == 1 else "s"))
    q("#calBody").innerHTML = "".join(rows)


def render_calendar():
    q("#modeDay").className = "on" if VIEW["mode"] == "day" else ""
    q("#modeWeek").className = "on" if VIEW["mode"] == "week" else ""
    if VIEW["mode"] == "day":
        render_day()
    else:
        render_week()


def render_all():
    render_settings()
    render_datalist()
    render_muscles_line()
    render_coach()
    render_map()
    render_calendar()


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
    # Reuse the existing spelling of an exercise so sets group together.
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
    VIEW["date"] = today_str()
    PICKER["open"] = False
    q("#reps").value = ""
    q("#rir").value = ""
    render_all()
    q("#reps").focus()


@when("input", "#exercise")
def on_exercise(event):
    PICKER["open"] = False
    render_muscles_line()
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


@when("click", "#modeDay")
def on_mode_day(event):
    VIEW["mode"] = "day"
    render_calendar()


@when("click", "#modeWeek")
def on_mode_week(event):
    VIEW["mode"] = "week"
    render_calendar()


def shift(days):
    VIEW["date"] = add_days(VIEW["date"], days)
    render_calendar()
    render_map()


@when("click", "#calPrev")
def on_prev(event):
    shift(-1 if VIEW["mode"] == "day" else -7)


@when("click", "#calNext")
def on_next(event):
    shift(1 if VIEW["mode"] == "day" else 7)


@when("click", "#calToday")
def on_today(event):
    VIEW["date"] = today_str()
    render_calendar()
    render_map()


def toggle_muscle(mid):
    name = q("#exercise").value.strip()
    if not name:
        return
    current = muscles.muscles_for(name, STATE["custom"])
    if mid in current:
        current.pop(mid)
    else:
        current[mid] = 1.0
    if current:
        STATE["custom"][key(name)] = current
    else:
        STATE["custom"].pop(key(name), None)
    save_state()
    render_muscles_line()
    render_map()


@when("click", "main")
def on_main_click(event):
    t = event.target.closest("[data-del],[data-pick],[data-act],[data-mus],[data-day]")
    if t is None:
        return
    del_id = t.getAttribute("data-del")
    if del_id:
        STATE["sets"] = [s for s in STATE["sets"] if s["id"] != del_id]
        save_state()
        render_all()
        return
    pick = t.getAttribute("data-pick")
    if pick:
        q("#exercise").value = pick
        PICKER["open"] = False
        render_muscles_line()
        render_coach()
        window.scrollTo(0, 0)
        return
    mus = t.getAttribute("data-mus")
    if mus:
        PICKER["open"] = True
        toggle_muscle(mus)
        return
    day = t.getAttribute("data-day")
    if day:
        VIEW["date"] = day
        VIEW["mode"] = "day"
        render_calendar()
        render_map()
        return
    act = t.getAttribute("data-act")
    if act == "edit-muscles":
        PICKER["open"] = not PICKER["open"]
        render_muscles_line()
    elif act == "use-rec":
        q("#weight").value = t.getAttribute("data-w")
        q("#reps").value = t.getAttribute("data-r")
        q("#reps").focus()


@when("click", "#exportBtn")
def on_export(event):
    a = document.createElement("a")
    a.href = "data:application/json;charset=utf-8," + window.encodeURIComponent(json.dumps(STATE))
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

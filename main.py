"""EZRep UI: runs in the browser via PyScript (MicroPython).

All data lives in this browser's localStorage. No account, no server.
Weights are stored in kg and converted to your chosen unit for display.
"""

import json

from pyscript import document, window, when

import coach
import muscles
import norms

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
# The goal picker was removed from the UI; coach advice uses hypertrophy.
STATE["goal"] = "hypertrophy"


def keep_storage():
    """Ask the browser not to evict our localStorage (e.g. Safari's 7-day rule)."""
    try:
        if window.navigator.storage and window.navigator.storage.persist:
            window.navigator.storage.persist()
    except Exception:
        pass


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


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def retrigger(el, cls):
    """Restart a CSS animation by removing and re-adding its class."""
    el.classList.remove(cls)
    el.offsetWidth  # force reflow
    el.classList.add(cls)


# ---------- dates (MicroPython has no datetime, so use JS Date) ----------

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
LONG_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


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


def long_date(iso_s):
    d = jsdate(iso_s)
    return "%s, %s %d, %d" % (DAYS[d.getDay()], MONTHS[d.getMonth()][:3], d.getDate(), d.getFullYear())


# ---------- app state ----------

VIEW = {"date": today_str()}
WIZ = {"step": 0, "name": "", "picker": False, "sug_reps": None}
CAL = {"y": 0, "m": 0}


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


def canonical(name):
    for existing in exercise_names():
        if key(existing) == key(name):
            return existing
    return name.strip()


def grouped(sets_):
    order, groups = [], {}
    for s in sorted(sets_, key=lambda x: x["ts"]):
        k = key(s["exercise"])
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(s)
    return [(groups[k][0]["exercise"], groups[k]) for k in order]


def last_set(name):
    ss = sorted(display_sets(name), key=lambda x: x["ts"])
    return ss[-1] if ss else None


def recommendation(name):
    return coach.recommend(display_sets(name), today_str(), STATE["goal"], unit())


def muscle_chips(totals, only=None):
    hit = sorted([(v, m) for m, v in totals.items() if v > 0 and (only is None or m in only)], reverse=True)
    chips = []
    for v, mid in hit:
        done = v >= muscles.GOAL_SETS
        chips.append(
            '<span class="mchip%s"><i style="background:%s"></i>%s %s/%d%s</span>'
            % (" done" if done else "", muscles.color_for(v), muscles.MUSCLE_NAMES[mid],
               muscles.fmt_sets(v), muscles.GOAL_SETS, " ✓" if done else "")
        )
    return "".join(chips)


# ---------- main screen: day view ----------

def render_settings():
    for b in document.querySelectorAll(".unitSwitch button"):
        b.className = "on" if b.getAttribute("data-unit") == unit() else ""


def render_day():
    date = VIEW["date"]
    t = today_str()
    if date == t:
        main = "Today"
    elif date == add_days(t, -1):
        main = "Yesterday"
    elif date == add_days(t, 1):
        main = "Tomorrow"
    else:
        main = LONG_DAYS[jsdate(date).getDay()]
    q("#dateMain").innerText = main
    q("#dateSub").innerText = long_date(date)

    day = sets_on(date)
    totals = muscles.tension(day, STATE["custom"])
    q("#dayModel").setAttribute("data-muscles", json.dumps(muscles.body_data(totals)))
    q("#muscleList").innerHTML = muscle_chips(totals)

    if not day:
        msg = "No sets yet. Tap <b>Track a set</b> to start." if date == t else "Nothing logged this day."
        q("#daySets").innerHTML = '<p class="empty center">%s</p>' % msg
        return
    html = []
    for name, ss in grouped(day):
        html.append('<div class="ex"><h4>%s <small>%s</small></h4><ol>' % (esc(name), plural(len(ss), "set")))
        for i, s in enumerate(ss):
            w = coach.to_unit(s["weight"], unit())
            html.append(
                '<li><span class="setno">%d</span><span class="setmain">%s %s &times; %d</span>'
                '<span class="est">1RM ~%s</span>'
                '<button class="x" data-del="%s" title="Delete set">&times;</button></li>'
                % (i + 1, fmt(w), unit(), s["reps"], fmt(coach.e1rm(w, s["reps"])), esc(s["id"]))
            )
        html.append("</ol></div>")
    q("#daySets").innerHTML = "".join(html)


def go_day(delta):
    VIEW["date"] = add_days(VIEW["date"], delta)
    render_day()
    retrigger(q("#dayScroll"), "slide-l" if delta > 0 else "slide-r")


@when("click", "#prevDay")
def on_prev_day(event):
    go_day(-1)


@when("click", "#nextDay")
def on_next_day(event):
    go_day(1)


SWIPE = {"x": None, "y": None}


@when("pointerdown", "#dayPanel")
def on_swipe_start(event):
    if event.target.closest(".body3d") is not None:
        SWIPE["x"] = None
        return
    SWIPE["x"] = event.clientX
    SWIPE["y"] = event.clientY


@when("pointerup", "#dayPanel")
def on_swipe_end(event):
    if SWIPE["x"] is None:
        return
    dx = event.clientX - SWIPE["x"]
    dy = event.clientY - SWIPE["y"]
    SWIPE["x"] = None
    if abs(dx) > 60 and abs(dx) > abs(dy) * 1.5:
        go_day(1 if dx < 0 else -1)  # swipe left = next day


@when("click", "#daySets")
def on_day_click(event):
    t = event.target.closest("[data-del]")
    if t is None:
        return
    del_id = t.getAttribute("data-del")
    STATE["sets"] = [s for s in STATE["sets"] if s["id"] != del_id]
    save_state()
    render_day()


@when("click", ".unitSwitch")
def on_unit(event):
    b = event.target.closest("[data-unit]")
    if b is None:
        return
    new = b.getAttribute("data-unit")
    old = unit()
    if new == old:
        return
    inp = q("#wWeight")
    w = parse_num(inp.value)
    if w:
        inp.value = fmt(coach.round_weight(coach.to_unit(coach.from_unit(w, old), new), new))
    STATE["unit"] = new
    save_state()
    render_settings()
    render_step1()
    render_day()


# ---------- calendar sheet ----------

def render_calendar():
    y, m = CAL["y"], CAL["m"]
    q("#calMonth").innerText = "%s %d" % (MONTHS[m - 1], y)
    offset = (window.Date.new(y, m - 1, 1).getDay() + 6) % 7
    days = window.Date.new(y, m, 0).getDate()
    counts = {}
    for s in STATE["sets"]:
        counts[s["date"]] = counts.get(s["date"], 0) + 1
    t = today_str()
    cells = ["<span></span>"] * offset
    for d in range(1, days + 1):
        ds = "%04d-%02d-%02d" % (y, m, d)
        cls = "cday"
        if ds in counts:
            cls += " has"
        if ds == t:
            cls += " today"
        if ds == VIEW["date"]:
            cls += " sel"
        badge = '<em>%d</em>' % counts[ds] if ds in counts else ""
        cells.append('<button type="button" class="%s" data-cal="%s">%d%s</button>' % (cls, ds, d, badge))
    q("#calGrid").innerHTML = "".join(cells)


def open_calendar():
    d = jsdate(VIEW["date"])
    CAL["y"], CAL["m"] = d.getFullYear(), d.getMonth() + 1
    render_calendar()
    q("#calendar").hidden = False


def close_calendar():
    q("#calendar").hidden = True


def shift_month(n):
    m = CAL["m"] + n
    y = CAL["y"]
    if m < 1:
        m, y = 12, y - 1
    elif m > 12:
        m, y = 1, y + 1
    CAL["y"], CAL["m"] = y, m
    render_calendar()


@when("click", "#calBtn")
def on_cal_open(event):
    open_calendar()


@when("click", "#calClose")
def on_cal_close(event):
    close_calendar()


@when("click", "#calendar")
def on_cal_backdrop(event):
    if event.target.id == "calendar":
        close_calendar()


@when("click", "#calPrev")
def on_cal_prev(event):
    shift_month(-1)


@when("click", "#calNext")
def on_cal_next(event):
    shift_month(1)


@when("click", "#calToday")
def on_cal_today(event):
    VIEW["date"] = today_str()
    close_calendar()
    render_day()


@when("click", "#calGrid")
def on_cal_pick(event):
    t = event.target.closest("[data-cal]")
    if t is None:
        return
    VIEW["date"] = t.getAttribute("data-cal")
    close_calendar()
    render_day()


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
        close_calendar()
        render_day()


# ---------- track-a-set wizard ----------

STEP_INPUTS = {0: "#wExercise", 1: "#wWeight", 2: "#wReps"}


def build_embers():
    spans = []
    for i in range(22):
        spans.append(
            '<span style="left:%d%%;animation-delay:%.2fs;animation-duration:%.2fs;width:%dpx;height:%dpx"></span>'
            % ((i * 37 + 11) % 100, (i * 0.53) % 3.0, 2.2 + (i % 5) * 0.45, 4 + i % 4, 4 + i % 4)
        )
    q("#fxLayer").innerHTML = "".join(spans)


def set_fx(tier):
    wiz = q("#wizard")
    for t in ("light", "avg", "heavy", "beast"):
        wiz.classList.remove("fx-" + t)
    if tier:
        wiz.classList.add("fx-" + tier)


def show_step(n):
    WIZ["step"] = n
    for i in range(4):
        el = q("#step%d" % i)
        el.hidden = i != n
    retrigger(q("#step%d" % n), "enter")
    dots = document.querySelectorAll("#wizDots i")
    for i in range(3):
        dots.item(i).className = "on" if i <= min(n, 2) else ""
    q("#wizDots").hidden = n == 3
    set_fx(None)
    if n == 0:
        render_step0()
    elif n == 1:
        render_step1()
    elif n == 2:
        render_step2()
    elif n == 3:
        render_step3()
    if n in STEP_INPUTS:
        inp = q(STEP_INPUTS[n])
        inp.focus()
        if n > 0:
            inp.select()


def open_wizard():
    WIZ["name"] = ""
    WIZ["picker"] = False
    WIZ["sug_reps"] = None
    q("#wExercise").value = ""
    q("#wizard").hidden = False
    document.body.classList.add("locked")
    show_step(0)


def close_wizard():
    q("#wizard").hidden = True
    document.body.classList.remove("locked")
    set_fx(None)
    VIEW["date"] = today_str()
    render_day()


@when("click", "#trackBtn")
def on_track(event):
    open_wizard()


@when("click", "#wizClose")
def on_wiz_close(event):
    close_wizard()


@when("click", "#wDone")
def on_wiz_done(event):
    close_wizard()


@when("click", "#wizBack")
def on_wiz_back(event):
    if WIZ["step"] in (0, 3):
        close_wizard()
    else:
        show_step(WIZ["step"] - 1)


# Step 0: exercise + muscles

def render_step0():
    name = q("#wExercise").value.strip()
    recent = [n for n in exercise_names() if not name or key(name) in key(n)][:6]
    q("#wRecent").innerHTML = "".join(
        '<button type="button" class="pill" tabindex="-1" data-recent="%s">%s</button>' % (esc(n), esc(n))
        for n in recent if key(n) != key(name)
    )
    worked = muscles.muscles_for(name, STATE["custom"]) if name else {}
    data = {}
    for mid, w in worked.items():
        data[mid] = {"color": "#f5f5f5" if w >= 1 else "#a3a3a3", "glow": True,
                     "label": muscles.MUSCLE_NAMES[mid]}
    q("#wizModel").setAttribute("data-muscles", json.dumps(data))
    q("#wizModel").hidden = not name

    if not name:
        q("#wMusclesLabel").innerText = ""
        q("#wMuscles").innerHTML = ""
        q("#wConfirm0").disabled = True
        return
    if worked and not WIZ["picker"]:
        q("#wMusclesLabel").innerHTML = 'Muscles worked <button type="button" class="link" tabindex="-1" id="wEditMuscles">Edit</button>'
        items = sorted(worked.items(), key=lambda kv: -kv[1])
        q("#wMuscles").innerHTML = "".join(
            '<span class="pill on%s">%s</span>' % ("" if w >= 1 else " half", muscles.MUSCLE_NAMES[m])
            for m, w in items
        )
    else:
        q("#wMusclesLabel").innerHTML = (
            "Tap the muscles this works" if not worked
            else 'Tap to change <button type="button" class="link" tabindex="-1" id="wEditMuscles">Done</button>'
        )
        q("#wMuscles").innerHTML = "".join(
            '<button type="button" tabindex="-1" class="pill%s" data-mus="%s">%s</button>'
            % (" on" if mid in worked else "", mid, label)
            for mid, label in muscles.MUSCLES
        )
    q("#wConfirm0").disabled = not worked


@when("input", "#wExercise")
def on_wiz_exercise(event):
    WIZ["picker"] = False
    render_step0()


@when("click", "#step0")
def on_step0_click(event):
    t = event.target
    if t.id == "wEditMuscles":
        WIZ["picker"] = not WIZ["picker"]
        render_step0()
        return
    r = t.closest("[data-recent]")
    if r is not None:
        q("#wExercise").value = r.getAttribute("data-recent")
        WIZ["picker"] = False
        render_step0()
        return
    m = t.closest("[data-mus]")
    if m is not None:
        name = q("#wExercise").value.strip()
        current = muscles.muscles_for(name, STATE["custom"])
        mid = m.getAttribute("data-mus")
        if mid in current:
            current.pop(mid)
        else:
            current[mid] = 1.0
        if current:
            STATE["custom"][key(name)] = current
        else:
            STATE["custom"].pop(key(name), None)
        save_state()
        WIZ["picker"] = True
        render_step0()


def confirm0():
    name = q("#wExercise").value.strip()
    if not name or not muscles.muscles_for(name, STATE["custom"]):
        return
    WIZ["name"] = canonical(name)
    rec = recommendation(WIZ["name"])
    last = last_set(WIZ["name"])
    if rec:
        q("#wWeight").value = fmt(rec["weight"])
    elif last:
        q("#wWeight").value = fmt(last["weight"])
    else:
        q("#wWeight").value = ""
    show_step(1)


@when("click", "#wConfirm0")
def on_confirm0(event):
    confirm0()


# Step 1: weight

def verdict_html(cmp, value_text, avg_text, what):
    if cmp is None:
        return '<p class="vSub">No average on file for this exercise yet, so just lift.</p>'
    width = min(100, cmp["ratio"] * 50)
    return (
        '<div class="meter"><div class="fill" style="width:%d%%"></div><div class="avgMark"></div></div>'
        '<div class="meterLbl"><span>light</span><span>avg</span><span>heavy</span></div>'
        '<p class="vHead">%s</p>'
        '<p class="vSub">%s is %d%% of the average %s (~%s).</p>'
        % (width, cmp["headline"], value_text, cmp["pct"], what, avg_text)
    )


def render_step1():
    name = WIZ["name"]
    q("#wEx1").innerText = name
    w = parse_num(q("#wWeight").value)
    avg_kg = norms.avg_working_kg(name)
    avg = coach.to_unit(avg_kg, unit()) if avg_kg else None
    cmp = norms.compare(w, avg)
    q("#wVerdict1").innerHTML = verdict_html(
        cmp, "%s %s" % (fmt(w or 0), unit()),
        "%s %s" % (fmt(coach.round_weight(avg, unit())) if avg else "", unit()),
        "working weight for 10 reps") if w else '<p class="vSub">Type the weight you used.</p>'
    set_fx(cmp["tier"] if cmp and w else None)
    rec = recommendation(name)
    chip = q("#wCoach")
    if rec:
        chip.hidden = False
        stop = "to failure" if rec["rir"] == 0 else "stop %d short" % rec["rir"]
        chip.innerHTML = "Coach · set %d: <b>%s %s &times; %d</b> (%s)" % (
            rec["set_number"], fmt(rec["weight"]), unit(), rec["reps"], stop)
        chip.setAttribute("data-w", fmt(rec["weight"]))
        chip.setAttribute("data-r", str(rec["reps"]))
    else:
        chip.hidden = True
    q("#wConfirm1").disabled = not (w and w > 0)


@when("input", "#wWeight")
def on_wiz_weight(event):
    render_step1()
    retrigger(q("#step1 .numBox"), "bump")


@when("click", "#wCoach")
def on_wiz_coach(event):
    chip = q("#wCoach")
    q("#wWeight").value = chip.getAttribute("data-w")
    WIZ["sug_reps"] = int(chip.getAttribute("data-r"))
    render_step1()


def confirm1():
    w = parse_num(q("#wWeight").value)
    if not w or w <= 0:
        return
    rec = recommendation(WIZ["name"])
    last = last_set(WIZ["name"])
    reps = WIZ["sug_reps"]
    if reps is None and rec and abs(rec["weight"] - w) < 0.01:
        reps = rec["reps"]
    if reps is None and last:
        reps = last["reps"]
    q("#wReps").value = str(reps) if reps else ""
    show_step(2)


@when("click", "#wConfirm1")
def on_confirm1(event):
    confirm1()


# Step 2: reps

def render_step2():
    name = WIZ["name"]
    q("#wEx2").innerText = name
    w = parse_num(q("#wWeight").value) or 0
    r = parse_num(q("#wReps").value)
    if not r or r < 1:
        q("#wVerdict2").innerHTML = '<p class="vSub">How many reps did you get?</p>'
        q("#wSave").disabled = True
        set_fx(None)
        return
    one = coach.e1rm(w, int(r))
    avg_kg = norms.avg_1rm_kg(name)
    avg = coach.to_unit(avg_kg, unit()) if avg_kg else None
    cmp = norms.compare(one, avg)
    html = '<p class="bigStat">Est. 1RM <b>%s %s</b></p>' % (fmt(one), unit())
    html += verdict_html(cmp, "Your est. 1RM", "%s %s" % (fmt(coach.round_weight(avg, unit())) if avg else "", unit()),
                         "lifter's max")
    q("#wVerdict2").innerHTML = html
    set_fx(cmp["tier"] if cmp else None)
    q("#wSave").disabled = False


@when("input", "#wReps")
def on_wiz_reps(event):
    render_step2()
    retrigger(q("#step2 .numBox"), "bump")


def save_set():
    w = parse_num(q("#wWeight").value)
    r = parse_num(q("#wReps").value)
    if not w or not r or r < 1:
        return
    ts = window.Date.now()
    STATE["sets"].append({
        "id": str(int(ts)),
        "ts": ts,
        "date": today_str(),
        "exercise": WIZ["name"],
        "weight": coach.from_unit(w, unit()),
        "reps": int(r),
        "rir": None,
    })
    save_state()
    WIZ["sug_reps"] = None
    show_step(3)


@when("click", "#wSave")
def on_save(event):
    save_set()


# Step 3: done

def render_step3():
    name = WIZ["name"]
    t = today_str()
    n_today = len([s for s in sets_on(t) if key(s["exercise"]) == key(name)])
    w = parse_num(q("#wWeight").value) or 0
    r = int(parse_num(q("#wReps").value) or 0)
    q("#doneTitle").innerText = "Set %d logged!" % n_today
    q("#doneSub").innerText = "%s · %s %s × %d" % (name, fmt(w), unit(), r)
    rec = recommendation(name)
    if rec:
        stop = "to failure" if rec["rir"] == 0 else "stop %d short of failure" % rec["rir"]
        q("#doneNext").innerHTML = (
            '<p class="label">Next set</p><p class="big">%s %s &times; %d</p><p>%s. %s</p>'
            % (fmt(rec["weight"]), unit(), rec["reps"], stop[0].upper() + stop[1:], esc(rec["reason"]))
        )
    else:
        q("#doneNext").innerHTML = ""
    worked = muscles.muscles_for(name, STATE["custom"])
    totals = muscles.tension(sets_on(t), STATE["custom"])
    q("#doneMuscles").innerHTML = muscle_chips(totals, worked)


@when("click", "#wAgain")
def on_again(event):
    q("#wWeight").value = ""
    rec = recommendation(WIZ["name"])
    last = last_set(WIZ["name"])
    if rec:
        q("#wWeight").value = fmt(rec["weight"])
    elif last:
        q("#wWeight").value = fmt(last["weight"])
    show_step(1)


# +/- buttons and Enter key

@when("click", ".adj")
def on_adj(event):
    btn = event.target.closest("[data-adj]")
    d = int(btn.getAttribute("data-adj"))
    if WIZ["step"] == 1:
        inp = q("#wWeight")
        step = 2.5 if unit() == "kg" else 5.0
        v = (parse_num(inp.value) or 0) + d * step
        inp.value = fmt(max(0, v))
        render_step1()
        retrigger(q("#step1 .numBox"), "bump")
    elif WIZ["step"] == 2:
        inp = q("#wReps")
        v = int(parse_num(inp.value) or 0) + d
        inp.value = str(max(1, v))
        render_step2()
        retrigger(q("#step2 .numBox"), "bump")


@when("keydown", "#wizard")
def on_wiz_key(event):
    if event.key == "Escape":
        close_wizard()
    elif event.key == "Enter":
        event.preventDefault()
        s = WIZ["step"]
        if s == 0:
            confirm0()
        elif s == 1:
            confirm1()
        elif s == 2:
            save_set()


# ---------- start ----------

keep_storage()
build_embers()
render_settings()
render_day()
q("#loading").hidden = True
q("#app").hidden = False

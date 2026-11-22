"""EZRep UI: runs in the browser via PyScript (MicroPython).

All data lives in this browser's localStorage. No account, no server.
Weights are stored in kg and converted to your chosen unit for display.
"""

import json

from pyscript import document, window, when
from pyscript.ffi import create_proxy

import coach
import muscles
import norms

STORAGE_KEY = "ezrep.v1"


# ---------- storage ----------

def load_state():
    state = {"unit": "lb", "goal": "hypertrophy", "sets": [], "custom": {},
             "routine": {}, "timer": {"secs": 90, "auto": True, "start": None}}
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

try:
    with open("data/exercises.json") as f:
        muscles.load_db(json.load(f))
except Exception:
    pass  # keyword rules still work without the database


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


def mmss(secs):
    secs = int(secs)
    sign = "-" if secs < 0 else ""
    secs = abs(secs)
    return "%s%d:%02d" % (sign, secs // 60, secs % 60)


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
MON_FIRST = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


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


def weekday(iso_s):
    """0 = Monday ... 6 = Sunday."""
    return (jsdate(iso_s).getDay() + 6) % 7


def week_start(iso_s):
    return add_days(iso_s, -weekday(iso_s))


def short_date(iso_s):
    d = jsdate(iso_s)
    return "%s %d" % (MONTHS[d.getMonth()][:3], d.getDate())


def long_date(iso_s):
    d = jsdate(iso_s)
    return "%s, %s %d" % (DAYS[d.getDay()], MONTHS[d.getMonth()][:3], d.getDate())


# ---------- app state ----------

# date: selected day. anchor: Monday of the bottom row of the 2-week strip.
VIEW = {"date": today_str(), "anchor": week_start(today_str()), "open": {}}
WIZ = {"step": 0, "name": "", "picker": False, "sug_reps": None, "fire": 0}
CAL = {"y": 0, "m": 0}
ROUTINE_UI = {"day": weekday(today_str())}


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


def sets_in_week(ws):
    we = add_days(ws, 6)
    return [s for s in STATE["sets"] if ws <= s["date"] <= we]


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
    db = muscles.DB_BY_NAME.get(key(name))
    if db:
        return db[0]
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


# ---------- routine + queue ----------

def routine_for(wd):
    return STATE["routine"].get(str(wd), [])


def queue_items():
    """Today's routine with how many sets are done for each."""
    t = today_str()
    done = {}
    for s in sets_on(t):
        done[key(s["exercise"])] = done.get(key(s["exercise"]), 0) + 1
    items = []
    for i, item in enumerate(routine_for(weekday(t))):
        n = done.get(key(item["name"]), 0)
        items.append({"name": item["name"], "target": item["sets"], "done": n, "i": i})
    # Unfinished first, otherwise routine order (MicroPython's sort isn't stable).
    items.sort(key=lambda it: (it["done"] >= it["target"], it["i"]))
    return items


def render_queue():
    t = today_str()
    items = queue_items()
    q("#queueTitle").innerText = "Up next · %s" % LONG_DAYS[jsdate(t).getDay()]
    if not items:
        q("#queueRow").innerHTML = (
            '<p class="empty small">No routine for today. '
            '<button type="button" class="link" data-act="routine">Set one up</button></p>'
        )
        return
    chips = []
    for it in items:
        finished = it["done"] >= it["target"]
        chips.append(
            '<button type="button" class="qchip%s" data-queue="%s"><b>%s</b><small>%s%d/%d sets</small></button>'
            % (" done" if finished else "", esc(it["name"]), esc(it["name"]),
               "✓ " if finished else "", it["done"], it["target"])
        )
    q("#queueRow").innerHTML = "".join(chips)


def next_in_queue(after_name):
    for it in queue_items():
        if it["done"] < it["target"] and key(it["name"]) != key(after_name):
            return it["name"]
    return None


@when("click", "#queue")
def on_queue_click(event):
    t = event.target.closest("[data-queue],[data-act]")
    if t is None:
        return
    if t.getAttribute("data-act") == "routine":
        open_routine()
        return
    open_wizard(t.getAttribute("data-queue"))


@when("click", "#routineBtn")
def on_routine_btn(event):
    open_routine()


def open_routine():
    ROUTINE_UI["day"] = weekday(today_str())
    names = [it[0] for it in muscles.DB] + exercise_names()
    q("#routineSuggest").innerHTML = "".join('<option value="%s"></option>' % esc(n) for n in names)
    render_routine()
    q("#routine").hidden = False


def render_routine():
    d = ROUTINE_UI["day"]
    tabs = []
    for i, name in enumerate(MON_FIRST):
        n = len(routine_for(i))
        tabs.append('<button type="button" class="%s" data-rday="%d">%s%s</button>'
                    % ("on" if i == d else "", i, name, '<em>%d</em>' % n if n else ""))
    q("#routineTabs").innerHTML = "".join(tabs)
    items = routine_for(d)
    if not items:
        q("#routineList").innerHTML = '<p class="empty center">Rest day. Add exercises below.</p>'
        return
    rows = []
    for i, it in enumerate(items):
        rows.append(
            '<div class="rrow"><span class="rname">%s</span>'
            '<button type="button" class="mini" data-rsets="%d" data-d="-1" aria-label="Fewer sets">&minus;</button>'
            '<span class="rsets">%s</span>'
            '<button type="button" class="mini" data-rsets="%d" data-d="1" aria-label="More sets">+</button>'
            '<button type="button" class="x" data-rdel="%d" aria-label="Remove">&times;</button></div>'
            % (esc(it["name"]), i, plural(it["sets"], "set"), i, i)
        )
    q("#routineList").innerHTML = "".join(rows)


def routine_add():
    name = q("#routineInput").value.strip()
    if not name:
        return
    d = str(ROUTINE_UI["day"])
    STATE["routine"].setdefault(d, []).append({"name": canonical(name), "sets": 3})
    save_state()
    q("#routineInput").value = ""
    render_routine()
    render_queue()


@when("click", "#routineAdd")
def on_routine_add(event):
    routine_add()


@when("keydown", "#routineInput")
def on_routine_key(event):
    if event.key == "Enter":
        event.preventDefault()
        routine_add()


@when("click", "#routine")
def on_routine_click(event):
    t = event.target
    if t.id == "routine" or t.closest("#routineClose") is not None:
        q("#routine").hidden = True
        return
    b = t.closest("[data-rday],[data-rsets],[data-rdel]")
    if b is None:
        return
    d = str(ROUTINE_UI["day"])
    items = STATE["routine"].get(d, [])
    if b.getAttribute("data-rday") is not None:
        ROUTINE_UI["day"] = int(b.getAttribute("data-rday"))
    elif b.getAttribute("data-rsets") is not None:
        i = int(b.getAttribute("data-rsets"))
        items[i]["sets"] = max(1, min(10, items[i]["sets"] + int(b.getAttribute("data-d"))))
    elif b.getAttribute("data-rdel") is not None:
        items.pop(int(b.getAttribute("data-rdel")))
    save_state()
    render_routine()
    render_queue()


# ---------- main screen: week + day ----------

def render_week():
    t = today_str()
    sel = VIEW["date"]
    ws = week_start(sel)
    cur = week_start(t)
    if ws == cur:
        main = "This week"
    elif ws == add_days(cur, -7):
        main = "Last week"
    else:
        main = "Week of " + short_date(ws)
    q("#weekMain").innerText = main
    q("#weekSub").innerText = "%s – %s" % (short_date(ws), short_date(add_days(ws, 6)))
    q("#nextWeek").disabled = VIEW["anchor"] >= cur

    # 2-week strip: the week before the anchor, then the anchor week.
    counts = {}
    for s in STATE["sets"]:
        counts[s["date"]] = counts.get(s["date"], 0) + 1
    cells = ['<span class="dow">%s</span>' % d[0] for d in MON_FIRST]
    start = add_days(VIEW["anchor"], -7)
    for i in range(14):
        d = add_days(start, i)
        cls = "bday"
        if week_start(d) == ws:
            cls += " inweek"
        if d == sel:
            cls += " sel"
        if d == t:
            cls += " today"
        if d in counts:
            cls += " has"
        future = d > t
        cells.append('<button type="button" class="%s" data-day="%s"%s>%d<i></i></button>'
                     % (cls, d, " disabled" if future else "", jsdate(d).getDate()))
    q("#biweek").innerHTML = "".join(cells)

    # Weekly muscle model: goal is 2 sets per muscle per week.
    totals = muscles.tension(sets_in_week(ws), STATE["custom"])
    q("#dayModel").setAttribute("data-muscles", json.dumps(muscles.body_data(totals)))
    q("#muscleList").innerHTML = muscle_chips(totals)
    todo = [label for mid, label in muscles.MUSCLES if totals.get(mid, 0) < muscles.GOAL_SETS]
    q("#todoMuscles").innerText = ("Still to hit this week: " + ", ".join(todo)) if todo else "Every muscle hit its goal this week!"


def render_day():
    date = VIEW["date"]
    t = today_str()
    label = "Today" if date == t else ("Yesterday" if date == add_days(t, -1) else LONG_DAYS[jsdate(date).getDay()])
    q("#dayHead").innerText = "%s · %s" % (label, long_date(date))
    day = sets_on(date)
    if not day:
        msg = "No sets yet today." if date == t else "Nothing logged this day."
        q("#daySets").innerHTML = '<p class="empty center">%s</p>' % msg
        return
    opened = VIEW["open"]
    html = []
    for name, ss in grouped(day):
        k = date + "|" + key(name)
        is_open = opened.get(k, False)
        html.append(
            '<div class="ex%s"><button type="button" class="exHead" data-fold="%s">'
            '<strong>%s</strong><small>%s</small></button><ol>'
            % (" open" if is_open else "", esc(k), esc(name), plural(len(ss), "set"))
        )
        for i, s in enumerate(ss):
            w = coach.to_unit(s["weight"], unit())
            fire = s.get("fire")
            fires = ' <span class="fireTag">%s</span>' % ("🔥" * fire) if fire else ""
            html.append(
                '<li><span class="setno">%d</span><span class="setmain">%s %s &times; %d%s</span>'
                '<span class="est">1RM ~%s</span>'
                '<button class="x" data-del="%s" title="Delete set">&times;</button></li>'
                % (i + 1, fmt(w), unit(), s["reps"], fires,
                   fmt(coach.e1rm(w, s["reps"], s.get("rir") or 0)), esc(s["id"]))
            )
        html.append("</ol></div>")
    q("#daySets").innerHTML = "".join(html)


def render_main():
    if VIEW["date"] > today_str():
        VIEW["date"] = today_str()
    render_queue()
    render_week()
    render_day()


def shift_week(delta):
    t = today_str()
    cur = week_start(t)
    anchor = add_days(VIEW["anchor"], 7 * delta)
    if anchor > cur:
        return
    VIEW["anchor"] = anchor
    d = add_days(anchor, weekday(VIEW["date"]))
    VIEW["date"] = d if d <= t else t
    render_week()
    render_day()
    retrigger(q("#dayScroll"), "slide-l" if delta > 0 else "slide-r")


@when("click", "#prevWeek")
def on_prev_week(event):
    shift_week(-1)


@when("click", "#nextWeek")
def on_next_week(event):
    shift_week(1)


@when("click", "#biweek")
def on_biweek(event):
    b = event.target.closest("[data-day]")
    if b is None or b.disabled:
        return
    VIEW["date"] = b.getAttribute("data-day")
    render_week()
    render_day()


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
        shift_week(1 if dx < 0 else -1)  # swipe left = later week


@when("click", "#daySets")
def on_day_click(event):
    f = event.target.closest("[data-fold]")
    if f is not None:
        k = f.getAttribute("data-fold")
        VIEW["open"][k] = not VIEW["open"].get(k, False)
        f.parentElement.classList.toggle("open")
        return
    t = event.target.closest("[data-del]")
    if t is None:
        return
    del_id = t.getAttribute("data-del")
    STATE["sets"] = [s for s in STATE["sets"] if s["id"] != del_id]
    save_state()
    render_main()


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


def render_settings():
    for b in document.querySelectorAll(".unitSwitch button"):
        b.className = "on" if b.getAttribute("data-unit") == unit() else ""


def on_visible(event=None):
    # Coming back after midnight: keep "today" in sync with the real date.
    if not document.hidden:
        t = today_str()
        if week_start(t) > VIEW["anchor"]:
            VIEW["anchor"] = week_start(t)
            VIEW["date"] = t
        render_main()
        tick()


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
        cells.append('<button type="button" class="%s" data-cal="%s"%s>%d%s</button>'
                     % (cls, ds, " disabled" if ds > t else "", d, badge))
    q("#calGrid").innerHTML = "".join(cells)
    ty = int(t[:4])
    tm = int(t[5:7])
    q("#calNext").disabled = (y, m) >= (ty, tm)


def open_calendar():
    d = jsdate(VIEW["date"])
    CAL["y"], CAL["m"] = d.getFullYear(), d.getMonth() + 1
    render_calendar()
    q("#calendar").hidden = False


def close_calendar():
    q("#calendar").hidden = True


def pick_date(d):
    VIEW["date"] = d
    VIEW["anchor"] = week_start(d)
    close_calendar()
    render_week()
    render_day()


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
    pick_date(today_str())


@when("click", "#calGrid")
def on_cal_pick(event):
    t = event.target.closest("[data-cal]")
    if t is None or t.disabled:
        return
    pick_date(t.getAttribute("data-cal"))


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
        render_main()


# ---------- rest timer ----------

AUDIO = {"ctx": None}
TIMER = {"alarmed": False}
RING_BIG = 2 * 3.14159265 * 100
RING_MINI = 2 * 3.14159265 * 16


def timer_cfg():
    return STATE["timer"]


def unlock_audio():
    """Audio must be created during a tap; reuse it later for the alarm."""
    try:
        if AUDIO["ctx"] is None:
            AUDIO["ctx"] = window.AudioContext.new()
        AUDIO["ctx"].resume()
    except Exception:
        pass


def beep():
    ctx = AUDIO["ctx"]
    if ctx is None:
        return
    try:
        now = ctx.currentTime
        for i in range(3):
            osc = ctx.createOscillator()
            gain = ctx.createGain()
            osc.frequency.value = 880
            gain.gain.value = 0.25
            osc.connect(gain)
            gain.connect(ctx.destination)
            osc.start(now + i * 0.3)
            osc.stop(now + i * 0.3 + 0.18)
    except Exception:
        pass


def start_timer():
    unlock_audio()
    timer_cfg()["start"] = window.Date.now()
    TIMER["alarmed"] = False
    save_state()
    tick()


def stop_timer():
    timer_cfg()["start"] = None
    save_state()
    tick()


def tick(*args):
    cfg = timer_cfg()
    target = cfg["secs"]
    running = cfg.get("start") is not None
    if not running and q("#timer").hidden and WIZ["step"] != 4:
        q("#timerBar").hidden = True
        return  # idle: nothing to update
    elapsed = (window.Date.now() - cfg["start"]) / 1000 if running else 0
    progress = min(1.0, elapsed / target) if target else 1.0
    done = running and elapsed >= target

    # Full-screen ring
    q("#bigRing").style.strokeDashoffset = str(RING_BIG * (1 - progress))
    q("#timerTime").innerText = mmss(elapsed)
    if not running:
        sub = "Ready · rest %s" % mmss(target)
    elif done:
        sub = "Time for your next set! (+%s)" % mmss(elapsed - target)
    else:
        sub = "%s left" % mmss(target - elapsed)
    q("#timerSub").innerText = sub
    q("#timerTarget").innerText = mmss(target)
    q("#timerStart").innerText = "Restart" if running else "Start"
    q("#timerStop").hidden = not running
    sheet = q("#timer")
    if done:
        sheet.classList.add("ringDone")
    else:
        sheet.classList.remove("ringDone")

    # Mini bar on the main screen
    bar = q("#timerBar")
    bar.hidden = not running
    q("#miniRing").style.strokeDashoffset = str(RING_MINI * (1 - progress))
    q("#miniTime").innerText = mmss(elapsed)
    q("#miniTarget").innerText = "Go!" if done else "/ " + mmss(target)
    if done:
        bar.classList.add("ringDone")
    else:
        bar.classList.remove("ringDone")

    # Rest card on the "set logged" screen
    rest = q("#doneRest")
    if running and WIZ["step"] == 4:
        rest.hidden = False
        rest.innerHTML = ("<b>%s</b> rested · %s" % (mmss(elapsed), "go for your next set!" if done
                          else "%s to go" % mmss(target - elapsed)))
        if done:
            rest.classList.add("ringDone")
        else:
            rest.classList.remove("ringDone")
    elif WIZ["step"] == 4:
        rest.hidden = False
        rest.innerHTML = "Start rest timer (%s)" % mmss(target)
        rest.classList.remove("ringDone")

    # Alarm once when the rest is over
    if done and not TIMER["alarmed"]:
        TIMER["alarmed"] = True
        beep()
        try:
            window.navigator.vibrate(600)
        except Exception:
            pass


def render_timer_settings():
    cfg = timer_cfg()
    for b in document.querySelectorAll("#timerPresets button"):
        b.className = "on" if int(b.getAttribute("data-preset")) == cfg["secs"] else ""
    q("#timerAuto").checked = bool(cfg.get("auto"))


def open_timer():
    unlock_audio()
    render_timer_settings()
    tick()
    q("#timer").hidden = False


@when("click", "#timerBtn")
def on_timer_btn(event):
    open_timer()


@when("click", "#timerBar")
def on_timer_bar(event):
    open_timer()


@when("click", "#timerClose")
def on_timer_close(event):
    q("#timer").hidden = True


@when("click", "#timerStart")
def on_timer_start(event):
    start_timer()


@when("click", "#timerStop")
def on_timer_stop(event):
    stop_timer()


@when("click", "#timer")
def on_timer_click(event):
    b = event.target.closest("[data-preset],[data-tadj]")
    if b is None:
        return
    cfg = timer_cfg()
    if b.getAttribute("data-preset") is not None:
        cfg["secs"] = int(b.getAttribute("data-preset"))
    else:
        cfg["secs"] = max(15, min(900, cfg["secs"] + int(b.getAttribute("data-tadj"))))
    TIMER["alarmed"] = False if cfg.get("start") is None else TIMER["alarmed"]
    save_state()
    render_timer_settings()
    tick()


@when("change", "#timerAuto")
def on_timer_auto(event):
    timer_cfg()["auto"] = bool(q("#timerAuto").checked)
    save_state()


@when("click", "#doneRest")
def on_done_rest(event):
    if timer_cfg().get("start") is None:
        start_timer()
    else:
        open_timer()


# ---------- track-a-set wizard ----------

STEP_INPUTS = {0: "#wExercise", 1: "#wWeight", 2: "#wReps"}
N_STEPS = 5

# How hard was the set? fires -> reps in reserve
FIRE_RIR = {1: 5, 2: 3, 3: 2, 4: 1, 5: 0}
FIRE_TEXT = {
    1: ("Easy", "Lots left in the tank (5+ more reps)."),
    2: ("Moderate", "Could have done about 3 more."),
    3: ("Hard", "About 2 reps left."),
    4: ("Very hard", "Maybe 1 more rep."),
    5: ("All-out", "To failure, nothing left."),
}


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
    for i in range(N_STEPS):
        q("#step%d" % i).hidden = i != n
    retrigger(q("#step%d" % n), "enter")
    dots = document.querySelectorAll("#wizDots i")
    for i in range(4):
        dots.item(i).className = "on" if i <= min(n, 3) else ""
    q("#wizDots").hidden = n == 4
    set_fx(None)
    if n == 0:
        render_step0()
    elif n == 1:
        render_step1()
    elif n == 2:
        render_step2()
    elif n == 3:
        render_step3()
    elif n == 4:
        render_step4()
    if n in STEP_INPUTS:
        inp = q(STEP_INPUTS[n])
        inp.focus()
        if n > 0:
            inp.select()


def prefill_weight(name):
    rec = recommendation(name)
    last = last_set(name)
    if rec:
        q("#wWeight").value = fmt(rec["weight"])
    elif last:
        q("#wWeight").value = fmt(last["weight"])
    else:
        q("#wWeight").value = ""


def open_wizard(name=None):
    WIZ["picker"] = False
    WIZ["sug_reps"] = None
    WIZ["fire"] = 0
    q("#wizard").hidden = False
    document.body.classList.add("locked")
    if name:
        WIZ["name"] = canonical(name)
        q("#wExercise").value = WIZ["name"]
        prefill_weight(WIZ["name"])
        show_step(1)
    else:
        WIZ["name"] = ""
        q("#wExercise").value = ""
        show_step(0)


def close_wizard():
    q("#wizard").hidden = True
    document.body.classList.remove("locked")
    set_fx(None)
    WIZ["step"] = 0
    VIEW["date"] = today_str()
    VIEW["anchor"] = week_start(VIEW["date"])
    render_main()


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
    if WIZ["step"] in (0, 4):
        close_wizard()
    else:
        show_step(WIZ["step"] - 1)


# Step 0: exercise + muscles

def render_step0():
    name = q("#wExercise").value.strip()
    recent = [n for n in exercise_names() if not name or key(name) in key(n)][:4]
    found = muscles.db_search(name, 8) if name else []
    seen = {key(name): True}
    pills = []
    for n in recent + found:
        if key(n) in seen:
            continue
        seen[key(n)] = True
        pills.append('<button type="button" class="pill" tabindex="-1" data-recent="%s">%s</button>' % (esc(n), esc(n)))
    q("#wRecent").innerHTML = "".join(pills[:8])

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
    prefill_weight(WIZ["name"])
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
        q("#wConfirm2").disabled = True
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
    q("#wConfirm2").disabled = False


@when("input", "#wReps")
def on_wiz_reps(event):
    render_step2()
    retrigger(q("#step2 .numBox"), "bump")


def confirm2():
    r = parse_num(q("#wReps").value)
    if not r or r < 1:
        return
    show_step(3)


@when("click", "#wConfirm2")
def on_confirm2(event):
    confirm2()


# Step 3: how hard (fires)

def render_step3():
    q("#wEx3").innerText = WIZ["name"]
    f = WIZ["fire"]
    for b in document.querySelectorAll("#wFires button"):
        b.className = "lit" if int(b.getAttribute("data-fire")) <= f else ""
    if f:
        title, sub = FIRE_TEXT[f]
        q("#wFireLabel").innerText = title
        q("#wFireSub").innerText = sub
    else:
        q("#wFireLabel").innerText = "Tap the fires"
        q("#wFireSub").innerText = "How close to failure did you get? This tunes your next set."
    q("#wizard").setAttribute("data-fire", str(f))
    q("#wSave").disabled = not f


@when("click", "#wFires")
def on_fire(event):
    b = event.target.closest("[data-fire]")
    if b is None:
        return
    WIZ["fire"] = int(b.getAttribute("data-fire"))
    render_step3()
    retrigger(q("#wFires"), "bump")


def save_set(fire):
    w = parse_num(q("#wWeight").value)
    r = parse_num(q("#wReps").value)
    if not w or not r or r < 1:
        return
    unlock_audio()
    ts = window.Date.now()
    STATE["sets"].append({
        "id": str(int(ts)),
        "ts": ts,
        "date": today_str(),
        "exercise": WIZ["name"],
        "weight": coach.from_unit(w, unit()),
        "reps": int(r),
        "rir": FIRE_RIR[fire] if fire else None,
        "fire": fire or None,
    })
    save_state()
    WIZ["sug_reps"] = None
    if timer_cfg().get("auto"):
        start_timer()
    show_step(4)


@when("click", "#wSave")
def on_save(event):
    save_set(WIZ["fire"])


@when("click", "#wSkipRate")
def on_skip_rate(event):
    save_set(0)


# Step 4: done

def render_step4():
    q("#wizard").removeAttribute("data-fire")
    name = WIZ["name"]
    t = today_str()
    n_today = len([s for s in sets_on(t) if key(s["exercise"]) == key(name)])
    w = parse_num(q("#wWeight").value) or 0
    r = int(parse_num(q("#wReps").value) or 0)
    q("#doneTitle").innerText = "Set %d logged!" % n_today
    fire_txt = (" · " + "🔥" * WIZ["fire"]) if WIZ["fire"] else ""
    q("#doneSub").innerText = "%s · %s %s × %d%s" % (name, fmt(w), unit(), r, fire_txt)
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
    totals = muscles.tension(sets_in_week(week_start(t)), STATE["custom"])
    q("#doneMuscles").innerHTML = muscle_chips(totals, worked)
    nxt = next_in_queue(name)
    btn = q("#wNextEx")
    if nxt:
        btn.hidden = False
        btn.innerText = "Next up: %s" % nxt
        btn.setAttribute("data-next", nxt)
    else:
        btn.hidden = True
    tick()


@when("click", "#wAgain")
def on_again(event):
    WIZ["fire"] = 0
    prefill_weight(WIZ["name"])
    show_step(1)


@when("click", "#wNextEx")
def on_next_ex(event):
    open_wizard(q("#wNextEx").getAttribute("data-next"))


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
            confirm2()
        elif s == 3 and WIZ["fire"]:
            save_set(WIZ["fire"])


# ---------- start ----------

keep_storage()
build_embers()
render_settings()
render_main()
tick()
window.setInterval(create_proxy(tick), 250)
document.addEventListener("visibilitychange", create_proxy(on_visible))
q("#loading").hidden = True
q("#app").hidden = False

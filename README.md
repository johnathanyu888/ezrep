# EZRep

**Live:** https://ezrep-fawn.vercel.app

A dead-simple gym tracker. Tap **Track a set** and answer three full-screen questions:
exercise, weight, reps. EZRep estimates your 1-rep max and tells you what your next set should be for your goal.

- **One question at a time.** Typing the exercise auto-detects the muscles it works and highlights them on a 3D anatomy figure.
- **Live effects.** Weight is compared to a rough average working weight and reps to an average lifter's 1RM, from blue "lighter than average" up to a red "way above average" with embers. Benchmarks are in [`norms.py`](norms.py).

- **No account.** Everything is saved in your browser's localStorage. Use *Export backup* to keep a copy.
- **Written in Python.** It runs in the browser with [PyScript](https://pyscript.net) (MicroPython), so there's no server to host.
- **3D muscle map.** Each set you log credits the muscles that exercise works: 1 set for primary muscles, ½ for secondary. The goal is **2 sets per muscle**. Colors go grey (untouched) → yellow → orange → red (goal met) → dark red (4+). Drag to rotate, tap a muscle for its count. Exercises it doesn't recognize let you pick the muscles yourself.
- **Day view + calendar.** Swipe left/right (or use the arrows) to change days. The calendar button opens a month grid where you can jump to any day.
- **Works on your phone.** Open the GitHub Pages URL, then use *Add to Home Screen*.

## Features

- **Track a set** in 4 full-screen questions: exercise, weight, reps, and **how hard it was** (1-5 fires).
  The fire rating becomes reps in reserve (5 = failure, 4 = 1 left, 3 = 2 left, 2 = 3 left, 1 = 5+ left),
  which tunes the 1RM estimate and the next set's weight and reps.
- **800+ exercises.** Typing searches a public-domain exercise database ([free-exercise-db](https://github.com/yuhonas/free-exercise-db))
  and fills in primary and secondary muscles. Your own muscle picks always win.
- **Weekly muscle map.** The 3D model shows this week's sets per muscle against a goal of 2.
  Grey means still to train. A 2-week date strip, week arrows, swipe and a month calendar let you look back. Future days are locked.
- **Weekly routine + Up next queue.** Plan exercises per weekday. Today's appear as a queue; tap one to log it.
- **Rest timer.** Ring countdown with presets, ±15s, auto-start after each set, and a beep and vibration when rest is over.
- Foldable set list per exercise.

## How the coaching works

| Goal          | Rep range | Target RIR |
|---------------|-----------|------------|
| Explosiveness | 3–5       | 1          |
| Strength      | 3–6       | 1          |
| Hypertrophy   | 6–12      | 0 (failure)|
| Endurance     | 12–20     | 1          |

- **Est. 1RM**: Epley formula, assuming each logged set went close to failure.
- **Set 1 is the freshest.** With no sets logged today, EZRep picks a weight from your recent best for the middle of your goal's rep range.
- **Fatigue.** After set 1, it measures how much you've dropped from set to set today and projects the next set. It then subtracts your target RIR. If you'd fall below the rep range it lowers the weight, and if you're well above the range it raises it.

Training math is in [`coach.py`](coach.py), exercise→muscle mapping in [`muscles.py`](muscles.py), and the UI in [`main.py`](main.py). The only JavaScript is [`body3d.js`](body3d.js), which renders the 3D anatomy model with three.js. Python decides the colors.

## Run locally

```
python -m http.server 8000
```

Then open http://localhost:8000.

## Tests

```
python -m unittest test_coach test_muscles test_norms
```

## Your data

Everything is saved in your browser's localStorage on that device. It stays there between visits, so
there's nothing to download each day. EZRep also asks the browser to keep the storage persistent. On
iPhone, add it to your Home Screen so Safari doesn't clear site data for apps you haven't opened in a while.
*Export backup* (in the calendar sheet) is only a safety copy. Data doesn't sync between devices.

## Hosting

It's a static site with no server or build step. Deploy it on **Vercel**: sign in at vercel.com with
GitHub → *Add New → Project* → import `ezrep` → *Deploy* (framework preset: *Other*, no build command).
It's deployed at https://ezrep-fawn.vercel.app, and every push to `main` redeploys automatically.
GitHub Pages (*Settings → Pages → main / root*) works too.

## Credits

The 3D muscle model is from [Z-Anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy) /
BodyParts3D © DBCLS, via [hoik-muscle-model](https://github.com/kalibismail/hoik-muscle-model),
licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). See [CREDITS.md](CREDITS.md).

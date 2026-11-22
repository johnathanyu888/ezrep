# EZRep

A dead-simple gym tracker. Log exercise, weight, reps, and (optionally) reps in reserve.
EZRep estimates your 1-rep max and tells you what your next set should be for your goal.

- **No account.** Everything is saved in your browser's localStorage. Use *Export backup* to keep a copy.
- **Written in Python.** It runs in the browser with [PyScript](https://pyscript.net) (MicroPython), so there's no server to host.
- **Works on your phone.** Open the GitHub Pages URL, then use *Add to Home Screen*.

## How the coaching works

| Goal          | Rep range | Target RIR |
|---------------|-----------|------------|
| Explosiveness | 3–5       | 1          |
| Strength      | 3–6       | 1          |
| Hypertrophy   | 6–12      | 0 (failure)|
| Endurance     | 12–20     | 1          |

- **Est. 1RM**: Epley formula on reps to failure (reps + RIR).
- **Set 1 is the freshest.** With no sets logged today, EZRep picks a weight from your recent best for the middle of your goal's rep range.
- **Fatigue.** After set 1, it measures how much you've dropped from set to set today and projects the next set. It then subtracts your target RIR. If you'd fall below the rep range it lowers the weight, and if you're well above the range it raises it.

All the math is in [`coach.py`](coach.py). The UI is in [`main.py`](main.py).

## Run locally

```
python -m http.server 8000
```

Then open http://localhost:8000.

## Tests

```
python -m unittest test_coach
```

## Put it on your phone (GitHub Pages)

Repo → **Settings → Pages** → Source: *Deploy from a branch* → Branch: `main` / root → Save.
After a minute it's live at `https://<user>.github.io/ezrep/`.

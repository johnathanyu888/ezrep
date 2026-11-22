# EZRep

<p align="center">
  <img src="icon.svg" width="96" alt="EZRep icon">
</p>

<p align="center">
  <a href="https://ezrep-fawn.vercel.app"><img alt="Live app" src="https://img.shields.io/badge/live-ezrep--fawn.vercel.app-3ddc97?style=for-the-badge"></a>
</p>
<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-PyScript%20%C2%B7%20MicroPython-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="three.js" src="https://img.shields.io/badge/3D-three.js-111111?style=flat-square&logo=threedotjs&logoColor=white">
  <img alt="Vercel" src="https://img.shields.io/badge/hosted%20on-Vercel-111111?style=flat-square&logo=vercel&logoColor=white">
  <img alt="No account" src="https://img.shields.io/badge/account-not%20needed-555555?style=flat-square">
  <img alt="Data" src="https://img.shields.io/badge/data-stays%20on%20your%20device-555555?style=flat-square">
</p>


**Live:** https://ezrep-fawn.vercel.app

Super simple gym progress tracker.

<p align="center">
  <img src="docs/screenshots/home.jpg" width="300" alt="EZRep home screen: Track a set, Up next queue, week strip and a 3D muscle map colored by weekly sets">
</p>

## Screenshots

<table>
  <tr>
    <td align="center"><img src="docs/screenshots/exercise.jpg" width="190" alt="Question 1: the exercise, with worked muscles highlighted on the 3D model"><br><sub><b>1 · Pick the exercise</b><br>muscles light up on the model</sub></td>
    <td align="center"><img src="docs/screenshots/weight.jpg" width="190" alt="Question 2: the weight, with a 'way above average' red ember effect"><br><sub><b>2 · Enter the weight</b><br>live effects vs. the average lifter</sub></td>
    <td align="center"><img src="docs/screenshots/effort.jpg" width="190" alt="Question 4: five fire icons rating how hard the set was"><br><sub><b>3 · Rate the effort</b><br>1–5 fires tune your next set</sub></td>
    <td align="center"><img src="docs/screenshots/logged.jpg" width="190" alt="Set logged screen with the coach's next-set advice and rest countdown"><br><sub><b>4 · Set logged</b><br>next-set advice + rest countdown</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/screenshots/timer.jpg" width="190" alt="Rest timer ring counting down from 1:30 with presets"><br><sub><b>Rest timer</b><br>counts down, then beeps</sub></td>
    <td align="center"><img src="docs/screenshots/routine.jpg" width="190" alt="Weekly routine sheet with exercises and set targets for Sunday"><br><sub><b>Weekly routine</b><br>feeds the Up next queue</sub></td>
    <td align="center"><img src="docs/screenshots/calendar.jpg" width="190" alt="Month calendar with dots on workout days and a monthly summary"><br><sub><b>Calendar</b><br>jump to any past workout</sub></td>
    <td align="center"><img src="docs/screenshots/home.jpg" width="190" alt="Home screen with the weekly 3D muscle map"><br><sub><b>Weekly muscle map</b><br>goal: 2 sets per muscle</sub></td>
  </tr>
</table>

---

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

---

## Your data

Everything is saved in your browser's localStorage on that device. It stays there between visits, so
there's nothing to download each day. EZRep also asks the browser to keep the storage persistent. On
iPhone, add it to your Home Screen so Safari doesn't clear site data for apps you haven't opened in a while.
*Export backup* (in the calendar sheet) is only a safety copy. Data doesn't sync between devices.

---

## Credits

The 3D muscle model is from [Z-Anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy) /
BodyParts3D © DBCLS, via [hoik-muscle-model](https://github.com/kalibismail/hoik-muscle-model),
licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). See [CREDITS.md](CREDITS.md).

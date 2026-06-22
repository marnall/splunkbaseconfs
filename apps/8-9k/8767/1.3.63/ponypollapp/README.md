<div align="center">
  <img src="src/package/appserver/static/banner.png" alt="Pony Poll banner" width="520" />

  # Pony Poll

  **Interactive quiz app for Splunk — no extra infrastructure needed**

  ![version](https://img.shields.io/badge/version-1.3.62-blue)
  ![Splunk](https://img.shields.io/badge/Splunk-≥8.x-orange)
  ![AppInspect](https://img.shields.io/badge/AppInspect-approved-green)
  ![React](https://img.shields.io/badge/React-16-61dafb)

</div>

Pony Poll turns any Splunk instance into a live interactive quiz. Participants join through the Splunk Web UI, enter a nickname, and answer timed questions with instant scoring and feedback. All answers are stored as native Splunk events — no external database or middleware required.

Wondering why there is a pony? Meet Buttercup in Splunk's own story: [The Story of Buttercup, the Splunk Pwny](https://www.splunk.com/en_us/blog/splunklife/the-story-of-buttercup-the-splunk-pwny.html).

---

## Table of contents

- [Quick start](#quick-start)
- [Screenshots](#screenshots)
- [Features](#features)
- [Installation](#installation)
- [Architecture](#architecture)
- [Admin tab — running a quiz](#admin-tab--running-a-quiz)
- [Editor](#editor)
- [Analytics](#analytics)
- [Quiz library & GitHub sync](#quiz-library--github-sync)
- [Question types reference](#question-types-reference)
- [Import/Export JSON format](#importexport-json-format)
- [Configuration](#configuration)
- [Roles & permissions](#roles--permissions)
- [Splunk SPL examples](#splunk-spl-examples)
- [Upgrade instructions](#upgrade-instructions)
- [Troubleshooting](#troubleshooting)
- [External data sources](#external-data-sources)
- [Music Credits](#music-credits)
- [Support](#support)
- [License](#license)

---

## Audience & prerequisites

| Who | What they need |
|---|---|
| **Host / presenter** | Splunk admin or `ponypoll_admin` role; access to Splunk Web |
| **Participants** | Any modern browser with access to Splunk Web (no Splunk account required if anonymous access is configured) |
| **App installer** | Splunk admin rights to upload apps and restart Splunk |

> Participants do **not** need Splunk knowledge — they interact only with the `/play` URL.  
> Hosts are assumed to be comfortable with Splunk Web basics.

---

## Quick start

```
Install app → create questions in the Editor → share the /play URL → watch answers flow into Splunk
```

| Goal | Where to go |
|---|---|
| Run a self-paced quiz | **Poll** tab → nickname → Start |
| Host a live synchronized session | **Admin** tab → pick quiz → Synchronized → Start |
| Show a wall-screen during a session | Open `/projector` on a second display — auto-updates with each phase |
| Build or edit questions | **Editor** tab — 6 question types, drag-to-reorder, images |
| Import a ready-made quiz | Editor → **Library** (bundled) or **GitHub** (live sync) |
| Analyse results | **Analytics** tab — leaderboard, KPIs, difficulty breakdown, session filter |
| Install | Upload `ponypollapp.tar.gz` in **Apps → Manage Apps** |

---

## Screenshots

### Poll — participant view

| Start screen | Question with image | Wrong answer reveal |
|---|---|---|
| ![Poll — start screen, pony mascot, nickname field](docs/screenshots/start.png) | ![Poll — timed question with image, answer choices](docs/screenshots/participant-question.png) | ![Poll — incorrect answer highlighted, explanation shown](docs/screenshots/participant-reveal-wrong.png) |

Music and sound effect toggles are available directly on the start screen — no need to visit Settings first. Each participant controls their own preference independently.

![Start screen with Music and Sounds toggles below the Start Poll button](docs/screenshots/setup-audio-toggles.png)

### Admin — quiz control room

| Quiz active — QR code for participants | Question range selected |
|---|---|
| ![Admin — active quiz, QR code and URL for participants](docs/screenshots/host-idle.png) | ![Admin — Questions: From # – #, inputs showing 1–12 of 42](docs/screenshots/host-idle-range.png) |

### Admin — lobby (waiting for participants)

The session number is displayed prominently so the host can announce it to the room.

| Waiting for participants | First participant joined |
|---|---|
| ![Admin lobby — session number, QR code, 0 joined](docs/screenshots/host-lobby.png) | ![Admin lobby — 1 joined, Launch Quiz button active](docs/screenshots/host-lobby-joined.png) |

### Editor

| Editing a question | Quiz Library — Bundled | Quiz Library — GitHub |
|---|---|---|
| ![Editor — single-answer question, answer choices, explanation](docs/screenshots/editor-question.png) | ![Editor — Quiz Library modal, bundled quizzes](docs/screenshots/editor-library.png) | ![Editor — Quiz Library modal, live GitHub quizzes](docs/screenshots/editor-library-github.png) |

### Analytics

![Analytics — KPI scorecards, leaderboard, question difficulty table, recent sessions](docs/screenshots/analytics.png)

### Settings

![Settings — default view toggle, poll title, audio toggles, version info](docs/screenshots/settings.png)

The **Splunk index for poll answers** field lets you change which index Pony Poll writes to and reads from. It's backed by a Splunk search macro (`ponypoll_index`) so every analytics query, dashboard panel, ad-hoc SPL and the System Check resolve through the same source of truth. Default is `ponypoll`. See [Changing the Splunk index](#changing-the-splunk-index) below for the full procedure.

The built-in **System Check** runs automatically when you open Settings and verifies that all required Splunk components are working: KV Store read/write access, the `ponypoll_index` macro, configured index existence and data, and answer submission via `receivers/simple`.

![System Check — all checks passing with event count](docs/screenshots/settings-system-check.png)

The **Quiz music** and **Sound effects** toggles let each participant enable or disable background music and SFX independently. The preference is stored per browser. Three per-slot **Music tracks** dropdowns (Lobby / Question / Win) sit just below the music toggle — pick a different track for any slot from the bundled set, or click **↻ GitHub** to merge in extra tracks from the live catalogue at [`audio/manifest.json`](audio/manifest.json) (requires outbound HTTPS to `raw.githubusercontent.com`). See [Music Credits](#music-credits) for track attribution.

![Settings — default view, poll title, audio toggles, system check](docs/screenshots/settings-music.png)

---

## Features

| Feature | Detail |
|---|---|
| **6 question types** | Single correct · Multiple correct · Yes / No · Free text · Slider / Rating · Word cloud |
| **Synchronized host mode** | Presenter controls pace; sessions auto-numbered `00001`, `00002`, …; server-authoritative timer; answer distribution + explanation callout + per-question leaderboard |
| **Self-paced mode** | Each participant runs at their own speed |
| **Projector view** | Read-only `/projector` URL mirrors the live session on a wall screen — phases: idle QR, lobby nicknames, question + timer, reveal bars, final podium |
| **Post-quiz review** | After finishing, participants see a per-question breakdown: correct/incorrect, their answer, the correct answer, and explanation hints |
| **Admin tab** | Unified control room for both modes — QR code, short URL, session badge, projector link, live participant nickname list |
| **Editor** | WYSIWYG question editor — 6 types, drag-to-reorder, image support, explanations, **duplicate quiz** |
| **Quiz library** | Bundled quizzes importable with one click; **GitHub** button syncs latest quizzes live |
| **Export / Import** | JSON file per quiz — portable between any Splunk instances |
| **Random question subset** | Play N random questions from a larger pool each session |
| **Analytics** | KPI scorecards, leaderboard, per-question difficulty, recent sessions — no SPL needed |
| **KV Store backed** | Questions, quizzes, config, and session state in Splunk KV Store |
| **No extra infrastructure** | Events written directly via `receivers/simple`; no Python scripts or sidecars |
| **Participant permissions** | `ponypoll_user` role ships with `edit_tcp` + `edit_kvstore` so non-admin users can play |
| **Quiz music** | Lobby, question, and win music from OpenGameArt.org (CC0); toggle per browser in Settings |

---

## Installation

### Step 1 — Download

Go to the [**Releases page**](https://github.com/bautt/ponypollApp/releases/latest) and download **`ponypollapp.tar.gz`**.

### Step 2 — Install in Splunk

1. Log in to Splunk Web as an administrator.
2. Click the **gear icon** next to "Apps", or go to **Apps → Manage Apps**.
3. Click **Install app from file** (top-right).
4. Select the downloaded tarball and click **Upload**.
5. Restart Splunk if prompted.

> **Splunk Cloud:** Use the self-service app install in the Admin Console, or contact your Splunk admin.

### Step 3 — First run

1. Open **Pony Poll** — you land on the **Poll** tab.
2. Go to the **Editor** tab and create your first question, or click **Library** to import a pre-built quiz.
3. Go to the **Admin** tab, pick a quiz, and click **Activate for Self-paced** (or start a Synchronized session).
4. Share the **Play URL** with participants.

### Three entry points

| URL | Who it's for | What they see |
|---|---|---|
| `/app/ponypollapp/poll` | Host / presenter | Full app — Poll, Editor, Analytics, Settings |
| `/app/ponypollapp/play` | Participants | Quiz only — nickname input, questions, score |
| `/app/ponypollapp/projector` | Wall screen / projector | Read-only audience display, auto-updates with session |

Share `/play` with your audience. All three URLs appear in the Splunk navigation bar.

**Getting back to the admin app when Play is the default view:**

| Method | How |
|---|---|
| **Admin link** | Hover the bottom-right corner of `/play` |
| **URL bypass** | Navigate to `/app/ponypollapp/poll?admin` — skips the redirect for that session |

### Requirements

| Requirement | Notes |
|---|---|
| Splunk Enterprise ≥ 8.x | KV Store must be enabled (requires a valid non-free license) |
| Splunk Cloud | Tested and working — AppInspect approved |
| Browser | Any modern browser (Chrome, Firefox, Edge, Safari) |

> No Node.js, Python, or build tools are needed to run the app — the pre-built JavaScript bundle is included in the tarball.

---

## Architecture

Pony Poll runs entirely inside Splunk — no external database, no sidecar processes, no Python scripts on the critical path.

```
Browser (host)        Browser (participant)         Splunk
      │                        │                       │
      │── KV Store REST ───────┼───────────────────────▶ ponypoll_quizzes
      │   (questions, config,  │                         ponypoll_questions
      │    session state)      │                         ponypoll_config
      │                        │                         ponypoll_presence
      │── receivers/simple ────┼───────────────────────▶ index=ponypoll
      │   (answer events)      │── receivers/simple ──▶   sourcetype=ponypoll_answer
      │                        │                                      ponypoll_attempt
      │◀─ Analytics (SPL) ─────┼───────────────────────▶             ponypoll_presence
```

**Key components:**

| Component | Technology | Purpose |
|---|---|---|
| Frontend | React 16 + Splunk UI Toolkit, served as a compiled JS bundle | All UI — Poll, Admin, Editor, Analytics, Projector, Settings |
| Session state | KV Store (`ponypoll_presence`, `ponypoll_config`) | Lobby nicknames, active quiz, synchronized session control |
| Quiz storage | KV Store (`ponypoll_quizzes`, `ponypoll_questions`) | Question bank, quiz metadata |
| Answer events | `receivers/simple` → Splunk index `ponypoll` | All participant answers stored as searchable events |
| Analytics | Splunk search (SPL via REST) | Leaderboard, difficulty, session history |
| Index macro | `ponypoll_index` in `macros.conf` | Single source of truth for the target index across all queries |

The app is a **single-page React app** embedded in Splunk XML dashboard templates. It uses the Splunk REST API (`/services/`) directly from the browser for all data access — no custom Python scripts run at query time.

---

## Admin tab — running a quiz

### Self-paced mode

```
Admin tab → pick a quiz → Mode: Self-paced → Activate for Self-paced
  → participants open /play and run the quiz at their own pace
```

### Synchronized mode

The host controls the question flow for everyone simultaneously.

```
Admin tab → pick a quiz → Mode: Synchronized → Start Synchronized Session
  → a session number is auto-assigned (00001, 00002, …)
  → participants scan the QR code or open /play
  → they see the session number, enter a nickname, and appear in the lobby
  → host clicks Launch Quiz (N joined)
  → questions advance on the host's command — all participants see the same question at the same second
  → host clicks Reveal Answers → distribution bars + explanation + interim leaderboard shown to all
  → host clicks Next Question … repeat until done
  → final podium shown to all participants
  → Start New Session returns to the control room
```

### Projector view

The projector view is a dedicated read-only display designed to be shown on a wall screen, TV, or second monitor while the host runs the quiz from their own device.

**How to set it up:**

1. Start a synchronized session from the **Admin** tab.
2. In the JoinInfo panel (Idle or Lobby screen), click **📽 Projector view ↗** — this opens the projector URL in a new tab.
3. Move or cast that tab to the projector / second display.
4. The screen requires no interaction — it polls the session every 3 seconds and updates automatically.

The projector URL is also available in the Splunk navigation bar as **📽 Projector**.

**What the audience sees at each phase:**

| Phase | Display |
|---|---|
| **Idle** (no session) | App logo, large QR code + play URL — participants can scan in advance |
| **Waiting** (lobby open) | Giant session number `#XYZ`, QR code + play URL, live participant count, nickname chips as people join |
| **Question live** | Question number, question text, colour-coded option tiles (A/B/C/D), live countdown timer bar |
| **Reveal** | Question + answer distribution bars (% per option), top-5 leaderboard |
| **Done** | Podium (🥇🥈🥉) with names and scores, full top-10 below |

| Waiting — lobby | Question live |
|---|---|
| ![Projector — waiting lobby, session number, QR code, play URL](docs/screenshots/projector-lobby.png) | ![Projector — question with image, answer tiles, countdown timer](docs/screenshots/projector-question.png) |

The projector view contains no admin controls — it is safe to leave open on a shared screen.

---

### Key features

| Feature | Detail |
|---|---|
| **Auto-numbered sessions** | Sessions named `00001`, `00002`, … automatically — no manual entry needed |
| **Session visibility** | Number shown prominently on every admin panel and on the participant lobby screen |
| **"Tell participants" cue** | JoinInfo panel shows `Tell participants: session #NNNNN` next to the QR code |
| **Server-authoritative timer** | All clients compute remaining time from `question_started_at` in KV Store — no clock drift |
| **Answer distribution** | Horizontal bars per option shown after reveal on both host and participant screens |
| **Explanation callout** | Optional "why" text per question shown as a callout after reveal |
| **Podium** | Top 3 players shown on a visual podium at the end of a synchronized session |
| **Random question subset** | Choose how many questions to play at session-start |
| **Auto-switch on /play** | The `/play` URL detects a live sync session every 1.5 s — participants are routed automatically |

---

## Editor

The **Editor** tab is for building and managing quiz content.

### Toolbar

| Button | Action |
|---|---|
| **Drag handle** | Drag questions to reorder — order is auto-saved |
| **Delete** | Delete the selected question (with confirmation) |
| **Export** | Download the current quiz as a JSON file |
| **Import** | Load questions from a JSON file (Replace or Append) |
| **Library** | Import a bundled pre-built quiz |
| **GitHub** | Sync and import quizzes from the GitHub repository |

### Question fields

| Field | Notes |
|---|---|
| **Question text** | The question shown to participants |
| **Type** | Single · Multi · Yes/No · Free text · Slider · Word cloud |
| **Time limit** | Countdown in seconds |
| **Image** | Optional image URL displayed above the question |
| **Answers** | Options with correct marking (not for slider / freetext) |
| **Explanation** | Optional "why" text shown as a callout after reveal |

Each question is saved individually to KV Store — there is no "Save All".

---

## Analytics

The **Analytics** tab gives a live view of results without writing any SPL.

![Analytics — filters, KPI scorecards, leaderboard, question difficulty table, recent sessions](docs/screenshots/analytics.png)

### Filters

| Filter | Options |
|---|---|
| **Time range** | Last 15 min / 1h / 4h / 24h / 7 days / 30 days / All time |
| **Quiz** | Any quiz, or *All quizzes* |
| **Session** | Any session number, or *All sessions* — defaults to the most recent |
| **Nickname** | Any individual player, or *All players* |

### Panels

| Panel | What it shows |
|---|---|
| **Quiz completions** | Count of `quiz_complete` events |
| **Unique players** | Distinct nicknames across completed quizzes |
| **Avg / Top score** | Mean and single highest `total_score` |
| **Answers submitted** | Total `ponypoll_answer` event count |
| **Leaderboard** | Top 20 players ranked by best score, with gold/silver/bronze medals |
| **Question difficulty** | % correct and avg points per question |
| **Recent sessions** | Last 50 session events with timestamp, player, score |

A matching **Splunk dashboard** (Simple XML) is also available at `/app/ponypollapp/analytics_dashboard` for further SPL-level analysis.

---

## Quiz library & GitHub sync

### Bundled quizzes

| Quiz | Questions | Topics |
|---|---|---|
| [Splunk4Champions2 — Full Workshop Quiz](quizzes/splunk4champions2-workshop.json) | 42 | SmartStore, buckets, tstats, search modes, lookups, CIM, Dashboard Studio, SPL optimisation — all 6 question types |
| [Splunk4Champions — Advanced Topics](quizzes/splunk4champions.json) | 22 | tstats, buckets, bloom filters, Dashboard Studio, SmartStore, search performance |
| [Splunk Basics](quizzes/splunk-basics.json) | 15 | Components, ports, SPL commands, data lifecycle, forwarders, KV Store |
| [Greek Mythology Trivia](quizzes/greek-mythology.json) | 47 | Mythology questions with Wikimedia artwork images |

### Adding quizzes to the library

1. Create a JSON file in `quizzes/` following the [JSON schema](#importexport-json-format)
2. Add an entry to `quizzes/manifest.json`
3. Copy the file to `src/package/appserver/static/quizzes/`
4. Run `make build` — webpack copies static files automatically
5. Commit and push — the GitHub sync button serves the new quiz without a new app deployment

Created an interesting quiz and want to share it with others? Open a GitHub issue or contact the project maintainer.

---

## Question types reference

| Type | How it works | Scoring |
|---|---|---|
| `single` | One correct answer from up to 4 options | Speed bonus: 500–1000 pts |
| `multi` | Multiple correct answers — all must match | Speed bonus: 500–1000 pts |
| `yesno` | Yes or No | Speed bonus: 500–1000 pts |
| `freetext` | Open text, stored as-is | 100 pts for any non-empty answer |
| `slider` | Numeric range (configurable min/max/step/unit) | 50 pts for participation |
| `wordcloud` | Participants submit up to N words during the time limit; host sees a live SVG word cloud sized by frequency | 100 pts for any non-empty submission |

---

## Import/Export JSON format

The exported JSON is an array of question objects.

```json
[
  {
    "text": "Question text shown to participants",
    "type": "single | multi | yesno | freetext | slider | wordcloud",
    "timeLimit": 30,
    "explanation": "Optional 'why' shown after the answer is revealed",
    "options": [ { "id": "A", "text": "...", "correct": true } ],
    "sliderMin": 1, "sliderMax": 10, "sliderStep": 1, "sliderUnit": "",
    "wordcloudMaxWords": 7, "wordcloudMaxChars": 32
  }
]
```

<details>
<summary>Full field reference</summary>

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | **yes** | Question text |
| `type` | string | **yes** | `single`, `multi`, `yesno`, `freetext`, `slider`, or `wordcloud` |
| `timeLimit` | number | no | Countdown in seconds (default: `30`) |
| `explanation` | string | no | "Why" callout shown after reveal |
| `options` | array | for `single`/`multi`/`yesno` | `[{ "id": "A", "text": "...", "correct": true }]` |
| `sliderMin/Max/Step` | number | for `slider` | Range and step (defaults: 1, 10, 1) |
| `sliderUnit` | string | for `slider` | Label shown next to value, e.g. `"/10"` |
| `wordcloudMaxWords` | number | for `wordcloud` | Max words per participant (default: 7, range: 1–20) |
| `wordcloudMaxChars` | number | for `wordcloud` | Max chars per word chip (default: 32, range: 4–64) |

> `_key` and `quiz_id` are stripped on export and regenerated on import — JSON files are fully portable.

</details>

<details>
<summary>One example per question type</summary>

**single**
```json
{
  "text": "In Splunk Metrics, dimensions are…",
  "type": "single",
  "timeLimit": 25,
  "explanation": "Dimensions are key-value metadata pairs stored alongside metric measurements (e.g. host=web01, region=eu-west). Metric values themselves are numeric measurements under dot-separated names.",
  "image": "",
  "options": [
    {
      "id": "A",
      "text": "Numeric measurement values at a point in time",
      "correct": false
    },
    {
      "id": "B",
      "text": "Dot-separated segments of a metric name",
      "correct": false
    },
    {
      "id": "C",
      "text": "Key-value pairs that add contextual metadata to a measurement",
      "correct": true
    },
    {
      "id": "D",
      "text": "Index configuration parameters in indexes.conf",
      "correct": false
    }
  ]
}
```

**multi**
```json
{
  "text": "Which are Splunk search commands? (Select all that apply)",
  "type": "multi", "timeLimit": 40,
  "options": [
    { "id": "A", "text": "stats",     "correct": true  },
    { "id": "B", "text": "timechart", "correct": true  },
    { "id": "C", "text": "WHERE",     "correct": false },
    { "id": "D", "text": "table",     "correct": true  }
  ]
}
```

**yesno**
```json
{
  "text": "Was the installation straightforward?",
  "type": "yesno", "timeLimit": 20,
  "options": [
    { "id": "A", "text": "Yes", "correct": true  },
    { "id": "B", "text": "No",  "correct": false }
  ]
}
```

**freetext**
```json
{ "text": "What is your favourite Splunk feature?", "type": "freetext", "timeLimit": 60, "options": [] }
```

For a graded freetext question, list accepted answers in `options` with `correct: true`. Matching is case-insensitive; `*` is a wildcard for zero or more characters, so `"text": "splunk*"` matches "splunk", "splunkbase", "splunk cloud". An empty `options` array makes the question open-ended (any non-empty answer gets a participation score).

**slider**
```json
{
  "text": "Rate your confidence with Splunk (1 = beginner, 10 = expert)",
  "type": "slider", "timeLimit": 30, "options": [],
  "sliderMin": 1, "sliderMax": 10, "sliderStep": 1, "sliderUnit": "/10"
}
```

**wordcloud**
```json
{
  "text": "Name one thing Splunk does better than anything else",
  "type": "wordcloud", "timeLimit": 30,
  "wordcloudMaxWords": 7, "wordcloudMaxChars": 32
}
```

</details>

---

## Configuration

All settings are in the **Settings** tab inside the app.

| Setting | Default | Description |
|---|---|---|
| Poll title | `Pony Poll` | Shown on the start screen |
| Default view | `Poll` | Switch to `Play` to make `/play` the default entry point |
| Splunk index for poll answers | `ponypoll` | Backs the `ponypoll_index` search macro — see [below](#changing-the-splunk-index) |

> **Active quiz** is set from the **Admin** tab — pick a quiz and click **Activate for Self-paced**.

The two text settings live in the `ponypoll_config` KV Store collection; the index is stored in the `ponypoll_index` Splunk search macro in `local/macros.conf` (so it survives app upgrades).

### Changing the Splunk index

By default, Pony Poll writes to and reads from `index=ponypoll`, which is created by the app's `indexes.conf`. To redirect Pony Poll at a different index in production, change the value in **Settings → Splunk index for poll answers** and click **Save Settings**. Pony Poll updates the `ponypoll_index` macro and every component switches over (Admin, Analytics, the bundled analytics dashboard XML, the System Check, and the answer-submit path).

A few prerequisites are NOT auto-provisioned and must be done by a Splunk admin:

1. **Create the destination index** — Splunk → Settings → Data → Indexes (or via `indexes.conf` in your own app).
2. **Grant role search access** — extend `srchIndexesAllowed` for `ponypoll_user` / `ponypoll_admin` in `authorize.conf` to include the new index (the defaults grant only `ponypoll`).
3. **Allow participant writes** — add `[indexes/<your-index>] access = read : [ ponypoll_admin, admin, sc_admin, power ], write : [ * ]` to `default.meta` (or use a local override).

After saving, the **System Check** flags any of the above that are still missing. The `ponypoll_index` macro can also be edited directly in Splunk → Settings → Advanced Search → Search Macros if you prefer; Pony Poll re-reads it on every Settings page load.

The sourcetype distinguishes the event class: `ponypoll_answer`, `ponypoll_attempt`, `ponypoll_presence`. None of those change when the index is reconfigured.

---

## Roles & permissions

The app ships two custom roles:

| Role | Inherits from | Purpose |
|---|---|---|
| `ponypoll_admin` | `admin` | Edit questions, quizzes, config; view analytics |
| `ponypoll_user` | `user` | Take the quiz and submit answers only |

All built-in Splunk roles work out of the box — no role assignment required for standard installs.

### Capabilities on `ponypoll_user`

| Capability | Why it is needed |
|---|---|
| `edit_kvstore` | Write nickname into the synchronized session lobby |
| `edit_tcp` | Required by `receivers/simple` to accept events from non-admin users |

---

## Splunk SPL examples

All examples use the `` `ponypoll_index` `` search macro instead of a hardcoded `index=ponypoll`, so they automatically follow the [configured index](#changing-the-splunk-index).

```spl
-- All answers for a session
`ponypoll_index` session_id="<id>" | table _time nickname question answer correct points

-- Leaderboard (best score per player)
`ponypoll_index` sourcetype=ponypoll_attempt event=quiz_complete
| stats max(total_score) as best_score by nickname | sort -best_score

-- Correct rate by question
`ponypoll_index` type!=freetext type!=slider
| stats count as total, sum(eval(correct="true")) as correct_count by question
| eval pct_correct=round(correct_count/total*100, 1) | sort -pct_correct

-- Word cloud — top terms for a question
`ponypoll_index` type=wordcloud question="Name one thing*"
| eval words=split(answer,",") | mvexpand words
| eval word=trim(words) | where len(word)>0
| stats count by word | sort -count | head 30
```

---

## Music Credits

Quiz music is played during the lobby, questions, and win screen. All tracks are from [OpenGameArt.org](https://opengameart.org) and are freely licensed (CC0 / public domain).

| Track | Used for | Author | Source |
|---|---|---|---|
| Bossa Nova ("8bit Bossa") | Lobby / setup | Joth | [opengameart.org/content/bossa-nova](https://opengameart.org/content/bossa-nova) |
| Along the Way | Questions / countdown | congusbongus | [opengameart.org/content/along-the-way](https://opengameart.org/content/along-the-way) |
| Win Music #1 (track 1-3) | Win / results | commissioned by OpenGameArt | [opengameart.org/content/win-music-1](https://opengameart.org/content/win-music-1) |

Music can be toggled on or off per browser in **Settings → Quiz music**. Each browser can also pick a different track per slot from the **Music tracks** dropdowns, and merge in extra tracks from the live catalogue at [`audio/manifest.json`](audio/manifest.json) via the **↻ GitHub** button. Sound effects are synthesised in the browser (Web Audio API) and do not depend on any files.

### Contributing tracks

The music catalogue is fully extensible without rebuilding the app:

1. Drop a CC0 / public-domain audio file under [`audio/<subfolder>/`](audio/).
2. Add an entry to [`audio/manifest.json`](audio/manifest.json) — schema documented in [`audio/README.md`](audio/README.md).
3. Open a PR. Once merged, the track is live for any installation via **↻ GitHub**.

---

## Upgrade instructions

Pony Poll stores all user data (questions, quizzes, config, answers) outside the app bundle — in Splunk KV Store and the `ponypoll` index — so upgrades are non-destructive.

### Standard upgrade

1. Download the latest `ponypollapp.tar.gz` from the [Releases page](https://github.com/bautt/ponypollApp/releases/latest).
2. Go to **Apps → Manage Apps → Install app from file**.
3. Select the tarball, check **Upgrade app**, and click **Upload**.
4. Restart Splunk if prompted.

All questions, quizzes, and historical answers are preserved. Settings (poll title, index, default view, music preferences) are stored in KV Store and in `local/macros.conf` — neither is touched by the upgrade.

### What changes between versions

Each release includes a changelog on the [Releases page](https://github.com/bautt/ponypollApp/releases). Check there for any manual migration steps if upgrading across multiple major versions.

### Downgrade

Reinstall any previous release tarball using the same **Upgrade app** flow. KV Store schema changes are backward-compatible in all released versions.

---

## External data sources

Pony Poll makes outbound requests to the following third-party services. All calls are **user-initiated** (never automatic on startup):

| Service | URL | When called | Purpose |
|---|---|---|---|
| is.gd / v.gd | `https://is.gd/create.php` / `https://v.gd/create.php` | Host clicks **Shorten URL** in the Admin panel | Creates a short link to the participant `/play` URL. The host's Splunk server hostname is sent. A consent prompt is shown before the first call. |
| GitHub (raw content) | `https://raw.githubusercontent.com/bautt/ponypollApp/main/quizzes/` | User clicks **↻ Refresh** in the Editor → GitHub library | Fetches the public quiz manifest and quiz JSON files. No credentials are sent. |
| GitHub (raw content) | `https://raw.githubusercontent.com/bautt/ponypollApp/main/audio/` | User clicks **↻ GitHub** in Settings → Music tracks | Fetches the public audio manifest. No credentials are sent. |

No data is collected or transmitted automatically. All external calls require explicit user action.

---

## Troubleshooting

### Participants cannot join or submit answers

> ⚠️ **Participants must be logged into Splunk Web** with an account that has the `ponypoll_user` role (or `admin`). Without it, they can open `/play` but cannot register their nickname in the lobby or submit answers.

Assign the `ponypoll_user` role to all participant accounts before the session — this is a one-time setup by a Splunk admin:

1. Go to **Settings → Users and Authentication → Users**.
2. Edit each participant's account and add the `ponypoll_user` role.
3. Alternatively, assign the role to an existing role that participants already have (e.g. `user`) by editing it under **Settings → Users and Authentication → Roles**.

> For open workshops where participants have no personal Splunk account, ask your Splunk admin to create shared workshop credentials with the `ponypoll_user` role assigned in advance.

### System Check failures

Open the **Settings** tab — the System Check runs automatically and shows a green tick or red flag for each component:

| Red item | What to do |
|---|---|
| **KV Store readable / writable** | Confirm KV Store is running: **Settings → Server controls → KVStore** should show "Running" |
| **ponypoll_index macro** | Go to **Settings → Advanced Search → Search macros** and verify `ponypoll_index` exists; re-install the app if missing |
| **Poll index exists** | The `ponypoll` index is created by `indexes.conf` on install — a Splunk restart is required for new indexes to become active |
| **Poll index has data** | Run at least one quiz to generate events, or verify the index name in Settings matches where events are being written |
| **Answer submission works** | The `ponypoll_user` role needs the `edit_tcp` capability — assign it or add the role to the participant's account |

### Other symptoms

| Symptom | What to do |
|---|---|
| Lobby shows 0 participants despite people joining | Check KV Store status — presence heartbeats use KV Store writes |
| Participant count flickers (1 → 0 → 1) | Harmless — KV Store presence write timing; resolves within one heartbeat cycle (~10 s) |
| Projector shows wrong or stale content | Refresh the projector page; confirm the session is still active in the Admin tab |
| Analytics shows no answers | Run the System Check — confirm the index and macro are correct |
| Short URL button fails | Outbound HTTPS to `is.gd` / `v.gd` must be reachable from the browser |
| App not visible in the Splunk nav menu | Go to **Apps → Manage Apps** and confirm Pony Poll is enabled |
| Top navigation menu missing after login | You are likely on the `/play` page — navigate directly to the app: `…/en-GB/app/ponypollapp/poll`. The `/play` view intentionally hides the Splunk chrome so participants see only the quiz. |

---

## Support

- **Bug reports & feature requests:** [GitHub Issues](https://github.com/bautt/ponypollApp/issues)
- **Questions:** Open a discussion on the GitHub repository

---

## License

MIT — see [LICENSE](LICENSE).

> For developer documentation — build setup, architecture, file structure, key functions, and contribution guide — see [DEVELOPMENT.md](DEVELOPMENT.md).

---

*Built with Splunk, React, and Buttercup.*

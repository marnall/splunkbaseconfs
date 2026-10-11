# Queens for Splunk

Version 1.0.0 · by Daniel Spavin

Queens is a logic puzzle: place one queen in every row, every column and every colour region of the board, with no two queens touching, not even diagonally. Queens for Splunk brings it to your Splunk deployment, with Buttercup the pony as the queen, a puzzle of the day that everyone plays, practice puzzles, hints and high scores.

## Features

- **Puzzle of the day:** the same puzzle for everyone each day (by UTC date), following a weekly rhythm from an 8×8 easy on Monday to a 12×12 hard on Sunday. Only your first attempt counts on the daily leaderboard.
- **Practice:** 1,500 puzzles from 8×8 to 12×12 in easy, medium and hard, separate from the daily puzzles. Each practice puzzle has its own leaderboard of best times.
- **Every puzzle is fair:** each has exactly one solution and can be solved with logic alone, without guessing.
- **Hints** that point out mistakes and explain the next logical move.
- **High Scores:** today's leaderboard, past daily puzzles, top players, records for each board size and difficulty, and recent games.
- **Streaks:** 🔥 count the days in a row you've solved the puzzle of the day. Weekends are free: skipping Saturday and Sunday doesn't break a streak.
- **Copy result:** share your time, rank and streak in Slack or Teams with one click.
- Follows each user's light or dark theme.

## How to play

| Action | How |
|---|---|
| Mark a cell "no queen here" | Click it (an X appears) |
| Place a queen | Click an X |
| Clear a cell | Click the queen |
| Mark or clear many cells | Drag across them (start on an empty cell to mark, on an X to clear) |
| Undo / start over | Undo, Reset |
| Get help | Hint |

A game is a **perfect game** ★ when you make no mistakes (no queen placed on a wrong cell, even if you remove it) and use no hints. The **How to play** button in the app has the full rules with examples.

## Requirements

- Splunk Enterprise with the **KV store** enabled (it stores the scores).
- No extra roles or capabilities: every user who can open the app can play and see the scores.

## Installation

1. In Splunk Web, go to **Apps > Manage Apps > Install app from file**, choose the `queens_for_splunk` package and upload it. Alternatively, extract the package into `$SPLUNK_HOME/etc/apps/`.
2. Restart Splunk if prompted.
3. Open **Queens for Splunk** from the app menu.

## Using the app

- **Play:** choose **Puzzle of the day** or **Practice** in the left-hand panel, press **Start** and solve the board. Today's leaderboard is shown beside the game.
- **High Scores:** leaderboards and records. Use ◀ ▶ to see the puzzle of the day for earlier dates.
- **Search:** the scores can be searched like any other lookup (below).

## Scores and data

Each solved puzzle is saved as one record in the KV store collection `queens_scores`:

| Field | Meaning |
|---|---|
| `user` | Splunk username of the player |
| `game_id` | Puzzle id, e.g. `d10-h-3f9a1c7e2b` (daily) or `q08-e-5ec373c0d8` (practice) |
| `mode`, `daily_date` | `daily` (with its date) or `practice` |
| `size`, `difficulty` | Board size (8 to 12) and difficulty |
| `time_ms` | Time from Start to solving, measured by the server |
| `clicks`, `hints`, `mistakes` | Counts for the game |
| `perfect`, `comment` | Perfect game (no mistakes, no hints) |
| `completed_at` | When it was solved (epoch seconds) |

Search them with the `queens_scores_lookup` lookup, for example today's daily leaderboard:

```
| inputlookup queens_scores_lookup where mode="daily"
| where daily_date=strftime(now(), "%Y-%m-%d")
| sort 0 time_ms
| table user time_ms clicks hints perfect
```

The app also keeps a private collection, `queens_sessions`, with one record per started game (who started which puzzle, and when), used to time games and to save each game only once.

The app stores Splunk usernames with each score. It sends no data outside your Splunk deployment.

## Permissions

- All users can read `queens_scores`.
- Scores are written only by the app's own endpoints (`/services/queens/start` and `/services/queens/finish`), which take the player from their Splunk login. Users can't add, change or delete scores directly.
- `admin` and `sc_admin` can manage the collections, for example to remove a score:

```
| inputlookup queens_scores_lookup | where NOT (user="someone" AND game_id="q08-e-5ec373c0d8") | outputlookup queens_scores_lookup
```

## Troubleshooting

| Problem | What to try |
|---|---|
| "Scores can't be loaded right now" | The KV store may be unavailable. Check it with `\| rest /services/kvstore/status`, then press **Try again**. |
| "Your score wasn't saved" | Press **Try again** on the result card. Your time from the first attempt is kept. |
| The page is blank or out of date after an upgrade | Refresh the browser. If that doesn't help, open `/en-US/_bump` in Splunk Web, press the button, then refresh. |

## Uninstalling

Remove the app from **Apps > Manage Apps**, or delete `$SPLUNK_HOME/etc/apps/queens_for_splunk` and restart Splunk. To delete the scores first, clear the collection with `| outputlookup queens_scores_lookup` on an empty result (run as an admin).

## Release notes

**1.0.0:** first release.

## Support and licence

Queens for Splunk is made by Daniel Spavin.

Licensed under the Splunkbase End User License Agreement for Third-Party Content.

If you find any bugs or have feature requests, you can reach me on Slack as @spav or email: daniel@spavin.net

"""
Server-side rules for saving Queens scores. No Splunk imports, so it can be unit tested.

Flow:
  start(user, game_id)       -> records a game session with the server's start time
  finish(user, submission)   -> checks the session and the solution, then saves the score

The server decides everything that matters for the leaderboards: who the player is
(from their Splunk login), how long they took (its own clock), whether the solution
is correct, and whether a game counts as the puzzle of the day.
"""

import datetime
import json
import os
import time

SCORES = "queens_scores"
SESSIONS = "queens_sessions"

# Fastest believable solve: one second per queen (a 12x12 needs at least 12 seconds)
MIN_MS_PER_QUEEN = 1000
# A game must be finished within a day of pressing Start
MAX_SESSION_SECONDS = 24 * 60 * 60


class QueensError(Exception):
    """A request the server refuses, with the HTTP status to return."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def queens_of(layout):
    """Cell indexes of the queens (lowercase letters) in a layout string."""
    cells = layout.split("-", 1)[1].replace("/", "")
    return sorted(i for i, ch in enumerate(cells) if ch.islower())


def size_of(layout):
    return int(layout.split("-", 1)[0])


def fnv1a(text):
    """Same 32-bit FNV-1a hash as the app's JavaScript (lib/puzzles.js)."""
    h = 0x811C9DC5
    for ch in text:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def utc_today(now):
    return datetime.datetime.fromtimestamp(now, datetime.timezone.utc).strftime("%Y-%m-%d")


def days_between(start, end):
    parse = lambda d: datetime.date.fromisoformat(d)  # noqa: E731
    return (parse(end) - parse(start)).days


class Puzzles:
    """The puzzles the app ships, exported from @splunk/queens-game at build time."""

    def __init__(self, practice, daily):
        self.practice = practice  # [{id, layout, difficulty}]
        self.daily = daily  # [{date, id, layout, difficulty}], one per date in order
        self.by_id = {p["id"]: p for p in practice + daily}
        self.practice_sorted = sorted(practice, key=lambda p: p["id"])

    @classmethod
    def load(cls, path=None):
        path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "queens_puzzles.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(data["practice"], data["daily"])

    def daily_for(self, date):
        """
        The puzzle of the day, matching dailyPuzzle() in the app: the dated daily puzzle
        from the first date on (repeating after the last), before that a practice puzzle
        picked by hashing the date.
        """
        if self.daily and date >= self.daily[0]["date"]:
            index = days_between(self.daily[0]["date"], date) % len(self.daily)
            return self.daily[index]
        return self.practice_sorted[fnv1a("queens-daily-" + date) % len(self.practice_sorted)]


def as_count(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise QueensError(400, "%s must be a whole number of 0 or more" % name)
    return value


class Game:
    """
    @param kv: KV store client with insert(collection, record) -> key, get(collection, key),
               update(collection, key, record) and query(collection, query) -> [records]
    @param puzzles: Puzzles
    @param clock: returns the current time in seconds
    """

    def __init__(self, kv, puzzles, clock=time.time):
        self.kv = kv
        self.puzzles = puzzles
        self.clock = clock

    def _has_daily(self, user, date):
        return bool(self.kv.query(SCORES, {"user": user, "mode": "daily", "daily_date": date}))

    def start(self, user, game_id):
        puzzle = self.puzzles.by_id.get(game_id)
        if not puzzle:
            raise QueensError(404, "Unknown puzzle %s" % game_id)
        now = self.clock()
        today = utc_today(now)
        # Only today's puzzle, and only the first finished attempt, counts as daily
        daily = self.puzzles.daily_for(today)["id"] == game_id and not self._has_daily(user, today)
        session = {
            "user": user,
            "game_id": game_id,
            "mode": "daily" if daily else "practice",
            "daily_date": today if daily else "",
            "started_at": now,
            "used": False,
        }
        key = self.kv.insert(SESSIONS, session)
        return {"session": key, "mode": session["mode"], "daily_date": session["daily_date"]}

    def finish(self, user, submission):
        key = submission.get("session")
        session = self.kv.get(SESSIONS, key) if isinstance(key, str) and key else None
        if not session or session.get("user") != user:
            raise QueensError(403, "This game wasn't started by you")
        if session.get("used"):
            raise QueensError(409, "This game has already been saved")

        puzzle = self.puzzles.by_id[session["game_id"]]
        queens = submission.get("queens")
        if not isinstance(queens, list) or sorted(queens) != queens_of(puzzle["layout"]):
            raise QueensError(400, "That isn't the solution to this puzzle")

        # A retry after a failed save keeps the time of the first attempt
        now = float(session.get("finished_at") or self.clock())
        elapsed_ms = int(round((now - float(session["started_at"])) * 1000))
        size = size_of(puzzle["layout"])
        if elapsed_ms < size * MIN_MS_PER_QUEEN:
            raise QueensError(400, "That was too fast to be believable")
        if elapsed_ms > MAX_SESSION_SECONDS * 1000:
            raise QueensError(400, "This game was started too long ago to be saved")

        clicks = as_count(submission.get("clicks"), "clicks")
        hints = as_count(submission.get("hints"), "hints")
        mistakes = as_count(submission.get("mistakes"), "mistakes")

        # Mark the session used before saving, so it can only be saved once
        session["used"] = True
        session["finished_at"] = now
        self.kv.update(SESSIONS, key, {k: v for k, v in session.items() if not k.startswith("_")})

        mode = session["mode"]
        if mode == "daily" and self._has_daily(user, session["daily_date"]):
            mode = "practice"  # another attempt at today's puzzle was saved first
        perfect = mistakes == 0 and hints == 0
        record = {
            "user": user,
            "game_id": session["game_id"],
            "mode": mode,
            "daily_date": session["daily_date"] if mode == "daily" else "",
            "size": size,
            "difficulty": puzzle.get("difficulty", ""),
            "time_ms": elapsed_ms,
            "clicks": clicks,
            "mistakes": mistakes,
            "hints": hints,
            "perfect": perfect,
            "comment": "Perfect game" if perfect else "",
            "completed_at": int(now),
        }
        try:
            record["_key"] = self.kv.insert(SCORES, record)
        except Exception:
            # Saving failed: free the session again so the player can retry
            session["used"] = False
            self.kv.update(SESSIONS, key, {k: v for k, v in session.items() if not k.startswith("_")})
            raise
        return record

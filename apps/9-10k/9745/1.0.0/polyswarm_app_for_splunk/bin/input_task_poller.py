"""Modular input that follows sandbox detonations to their conclusion.

Registered in default/inputs.conf as

    [input_task_poller://polyswarm_sandbox_tasks]

Design section 4.3 asks for "the submit-and-poll model from our apps as a
dashboard backed by a KV-store task table and a polling modular input with
backoff". `bin/cmd_detonate.py` is the submit and writes the row;
`default/data/ui/views/sandbox.xml` is the tray and reads it. This is the part
in between, and it is the only thing in the app that ever moves a task row
forward.

THE INPUT KIND IS THIS FILE'S OWN NAME, AND THAT COUPLING IS NOT OPTIONAL
-------------------------------------------------------------------------
splunkd discovers a modular input by scanning an app's bin directory, running
each script with `--scheme`, and taking THE SCRIPT'S FILE NAME as the input
kind. So the stanza in inputs.conf is `[input_task_poller://<name>]` because
this file is `input_task_poller.py`, which is the name design section 6 gives
it. Renaming the file renames the input kind, which orphans every stanza a
customer has configured: their input stops running and nothing reports why,
because from splunkd's side the input kind simply no longer exists.

WHY THE POLLER EXISTS AT ALL, WHICH IS A PLATFORM BUG AND NOT A DESIGN CHOICE
-----------------------------------------------------------------------------
`/v3/sandbox/sandboxtask/my-tasks` HANGS, which design section 0 item 5 records
as one of the two open platform bugs. Listing the account's own tasks is the
obvious way to drive a tray, and it is not available. So this app keeps its own
worklist in the `ps_sandbox_tasks` collection and reads one task at a time by
id, which is why a row is a receipt rather than a cache entry and why losing one
is unrecoverable. `bin/task_store.py` carries that argument in full, and
`ps_client.sandbox_task_status` carries the avoidance in its docstring, because
a reader who "simplifies" this onto my-tasks hangs a modular input and nothing
in a Splunk input's own logs says why.

CONSTRAINT C7: CHECKPOINTED, AND SAFE TO RUN TWICE
--------------------------------------------------
**The checkpoint is the row state, and there is deliberately no checkpoint
file.** That is a decision rather than an omission, so here is the reasoning in
the place a reader will look for the missing file.

A checkpoint exists to answer "where did I get to". For an input that pulls a
stream, the answer is a position and it belongs in a document of its own. For
this input the answer is per row and the rows are already durable: each one
carries the platform's status, `poll_attempts`, and `next_poll_at`. Those three
fields are the state, they are written in the same document as the thing they
describe, and they are written by the same call that records the answer.

What a separate checkpoint document would add is a second source of truth about
the same rows, and one specific failure with it: a run that wrote its
checkpoint and failed to write a row, or the reverse, would leave the two
disagreeing, and the disagreement that matters is the one where the checkpoint
says a task is up to date while its row sits unpolled forever. There is no
reconciling read available, because my-tasks hangs.

Three properties follow, and each has a test:

  * **A terminal row is never polled again.** `map_status()` reads the stored
    word, `is_terminal()` decides, and a settled row is skipped before any
    request is considered. Two runs over a settled collection make zero
    requests, which is the C7 property stated as a measurement.
  * **A row that is not due yet is skipped.** `next_poll_at` is compared
    against the clock, so running the input twice in one minute does not poll
    a row twice.
  * **Every write is an upsert of the same document.** The document id is
    derived from the task id, so a re-run rewrites a row rather than adding
    one, and a row written twice with the same answer is indistinguishable
    from a row written once.

THE BACKOFF, AND WHAT IT IS FOR
-------------------------------
`BACKOFF_SCHEDULE` grows 30, 60, 120 then 300 seconds and stops. It is per row
rather than per input, because the rows are independent: a detonation submitted
a minute ago and one submitted an hour ago want different attention, and an
input-wide interval can only serve one of them.

The schedule is why the input's own interval can be short without being
expensive. A live detonation settles in minutes, so the first two intervals are
tight enough to feel immediate in a tray. A task that has been running for an
hour is either a long detonation or one the platform has lost, and neither is
served by asking every thirty seconds, so the interval flattens at five
minutes. The ceiling matters because a status request is an API request against
the customer's account: a row that never settles would otherwise cost 2,880
requests a day for as long as it sits there.

**The schedule advances whether or not the answer arrived.** A failed request
is a poll attempt, so it moves `poll_attempts` and `next_poll_at` exactly as a
successful one does. The alternative was to advance only on success, and it
turns one unreachable task into a request every run forever.

THE BACKOFF IS NOT A CEILING, AND THE ROW NEEDS ONE
---------------------------------------------------
The five minute floor bounds what a stale row costs per hour and bounds nothing
about what it costs in total. QA found the consequence: nothing abandoned a
row, so a task the platform will never settle, a 404, a status read that keeps
failing, a detonation dropped platform-side, was polled every five minutes for
as long as the row existed. 288 metered requests a day, per stale row, with
only `max_polls` slowing the accumulation by spreading it over runs.

So a row has a per-task ceiling now, and it is app-owned state rather than a
status word: `task_store.POLL_ABANDONED_AT_FIELD` is stamped, the platform's
own last word stays in `status`, `is_due()` skips the row from then on, and the
row is kept because it is the receipt for a metered detonation. Three routes
reach it, and the block above MAX_TASK_AGE_HOURS_ARGUMENT argues each: the
platform's own task expiration, three consecutive answers with no payload, and
`max_task_age_hours` as the fallback for a row neither of those speaks about.

WHAT IS SPENT, AND WHAT IS NOT
------------------------------
A status read is a GET. It creates nothing, it books no virtual machine, and it
cannot produce a second detonation, which is why `ps_client` retries it while
retrying nothing in the submit path. It is still an outbound request against
the customer's account, so this input carries its own ceiling: `max_polls`
bounds the requests one run may spend, defaults to fifty, and cannot be
configured above `MAX_POLLS_HARD_CAP`. A run that hits the ceiling stops,
reports `limit_reached` on its finish line, and leaves the remaining rows for
the next run, which is C11's refuse-rather-than-proceed shape applied to an
input.

**This input ships enabled, which is a deliberate exception to defect class
B8.** B8 says anything that spends quota or money ships opt-in, and the reason
this one does not is that it spends nothing on its own behalf: with no
detonations there are no rows, and with no rows there are no requests. The
spend that matters already happened when somebody ran `polyswarmdetonate`, and
a detonation nobody follows up is a purchase with no result, which is strictly
worse than the requests this input makes. So the opt-in is the detonation, and
this is how it finishes.

WHAT REACHES THE LOG
--------------------
One start line and one finish line per run, through `ps_log`, so the whitelist
is the only route a value has into a log file. The finish line uses the app's
existing count vocabulary rather than inventing keys:

    records        rows in the collection this run considered
    lookups        status requests this run actually spent
    cache_stores   rows written back
    cache_degraded whether the KV store failed anything
    limit          the per-run ceiling in force
    limit_reached  whether the run stopped at it
    abandoned      rows this run stopped following
    reason         the class name of the last failure, when there was one

Each abandoned row also gets its own line, `event=abandon`, whose `reason`
names which of the three routes retired it: PlatformExpiration, TaskNotFound or
TaskAgeCeiling.

Note the omissions, which are the same omissions every other component in this
app makes: there is no key for a task id, a URL, a family, or a C2 address.
The rows carry the customer's data and `ps_log` has no name it could travel
under.

Importing this module is side effect free. It only runs when splunkd invokes it.
"""

import os
import sys
import time

# Vendored dependencies. Must precede the splunklib import. See bin/lib/README.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import ps_log
import task_store
import ps_splunkd
from ps_client import AuthenticationError, ClientConfigurationError, get_client

from splunklib.modularinput import Argument, Scheme, Script  # noqa: E402

APP_NAME = "polyswarm_app_for_splunk"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "input_task_poller"

# The input kind, which is this file's own basename. See the module docstring:
# splunkd derives it from the file name, so this constant is a statement of
# that fact rather than a setting anything reads.
INPUT_KIND = "input_task_poller"

# Per-row polling intervals, in seconds, indexed by attempts already made.
#
# The last entry is the ceiling and is used for every attempt past it, so the
# schedule is 30, 60, 120, then 300 forever. A tuple rather than a formula: a
# reader can see the whole schedule, and a test can assert it position by
# position, which is not true of a doubling expression with a cap on it.
BACKOFF_SCHEDULE = (30.0, 60.0, 120.0, 300.0)

# The per-run ceiling on status requests, and the hard limit on it.
#
# CONSTRAINT C11'S SHAPE, APPLIED TO AN INPUT. The cap is explicit, it is
# declared rather than implied, and a run that reaches it stops and says so
# instead of continuing. Fifty is sized against what the collection can
# plausibly hold: an Enterprise plan includes 30 detonations a month, so fifty
# in flight at once is already an unusual day, and the rows left over are
# polled by the next run rather than dropped.
#
# The hard cap is what keeps the ceiling structural. An operator can lower
# max_polls or raise it within reason; they cannot turn the input into an
# unbounded loop over a collection by typing a large number into a form.
DEFAULT_MAX_POLLS = 50
MAX_POLLS_HARD_CAP = 200

# The argument name on the input, and the interval the shipped stanza uses.
# Both are duplicated in default/inputs.conf and README/inputs.conf.spec, and
# a test asserts the three agree: defect class B5 is a config sample that
# contradicts a code default.
MAX_POLLS_ARGUMENT = "max_polls"
DEFAULT_INTERVAL_SECONDS = 120

# ---------------------------------------------------------------------------
# The per-task ceiling, which is the bound max_polls is not
# ---------------------------------------------------------------------------
#
# `max_polls` bounds what ONE RUN may spend. It is not a bound on what a row
# may cost, and until this ceiling existed there was none: the backoff flattens
# at five minutes and nothing ever gave up, so a task the platform will never
# settle was polled every five minutes for as long as the row existed. That is
# 288 metered requests a day, per stale row, for nothing, and the shapes that
# produce one are ordinary rather than exotic: a 404 for a task id the platform
# does not know, a status read that keeps failing, a detonation dropped
# platform-side. QA FINDING 46.
#
# So a row gets a ceiling, and there are three ways to reach it. Two are the
# platform's own statement about the task and one is this app's guess, which is
# the order they are applied in:
#
#   1. THE PLATFORM'S EXPIRATION, about three hours after the task was created
#      in every recorded response. A task past it that is still non-terminal is
#      a task the platform has stopped working on. This is preferred to
#      everything below it because it is the platform's number rather than
#      ours. See task_store.RESPONSE_EXPIRATION_FIELD.
#   2. THREE CONSECUTIVE POLLS WITH NO PAYLOAD. ps_client answers None for a
#      404 and for a failed read alike, and a task the platform cannot find
#      will not become findable. Three rather than one because the same None
#      covers a transient failure, and three intervals of backoff is long
#      enough that a run of three is a statement rather than a coincidence.
#   3. `max_task_age_hours`, the app's own ceiling, for a row the two above
#      never speak about: a response that carries no readable expiration, or a
#      row that keeps answering with a payload and never settles.
#
# WHAT ABANDONMENT IS NOT IS A STATUS. task_store.map_status()'s rule is that
# an unrecognised or absent platform status never settles a task, and writing a
# status word of this app's own would break it from the other side. So the row
# keeps whatever the platform last said and gains
# task_store.POLL_ABANDONED_AT_FIELD beside it, which is_due() reads. The row
# is never deleted: it is the receipt for a metered detonation and my-tasks
# hangs, so the record has to outlive the poller's interest in it.
MAX_TASK_AGE_HOURS_ARGUMENT = "max_task_age_hours"

# 24 hours, and the number is argued rather than picked.
#
# It has to be well above how long a real detonation takes, because a row
# abandoned while the sandbox is still working is a paid detonation whose
# result this app then never reads. A URL detonation settles in minutes and the
# platform's own expiration is about three hours, so a day is roughly eight
# times the platform's own patience: a row that is still unsettled after it has
# either lost its expiration field or stopped answering sensibly.
#
# It also has to be small enough to matter. At the five minute backoff floor, a
# stale row costs 288 requests a day, so a ceiling of a day bounds one stale
# row at about that and a week's holiday at about the same rather than at 2,000.
DEFAULT_MAX_TASK_AGE_HOURS = 24

# The range an operator may ask for. One hour is the floor because a ceiling
# below the platform's own three hour expiration would abandon live tasks, and
# one week is the ceiling because past it the setting is not a ceiling any more.
MIN_MAX_TASK_AGE_HOURS = 1
MAX_MAX_TASK_AGE_HOURS = 168

SECONDS_PER_HOUR = 3600.0

# How many consecutive no-payload answers abandon a row. See item 2 above.
MAX_NOT_FOUND_POLLS = 3

# Which route retired a row, as it reaches the log's `reason` key.
#
# Written as constants because a test asserts the exact strings: they are what
# an operator searches the log for, and `reason` elsewhere in this app carries
# an exception's class name, so these are shaped like one. None of them names
# the task, the target or anything else off the row: ps_log has no key those
# could travel under.
EXPIRATION_REASON = "PlatformExpiration"
NOT_FOUND_REASON = "TaskNotFound"
AGE_CEILING_REASON = "TaskAgeCeiling"

MAX_TASK_AGE_HOURS_DESCRIPTION = (
    "How long a detonation may stay unsettled before the poller stops asking "
    "about it. The row is kept, with whatever the platform last said, and is "
    "not polled again. The platform's own task expiration, and three "
    "consecutive not-found answers, both abandon a row sooner. Defaults to "
    "{0} hours, at least {1} and at most {2}.".format(
        DEFAULT_MAX_TASK_AGE_HOURS,
        MIN_MAX_TASK_AGE_HOURS,
        MAX_MAX_TASK_AGE_HOURS,
    )
)

SCHEME_TITLE = "PolySwarm sandbox task poller"

SCHEME_DESCRIPTION = (
    "Follows PolySwarm sandbox detonations submitted by the polyswarmdetonate "
    "command or the PolySwarm Detonate alert action, and updates each task in "
    "the ps_sandbox_tasks collection until it settles. Reads only tasks this "
    "app submitted. Makes no request when there is nothing in flight."
)

MAX_POLLS_DESCRIPTION = (
    "Most status requests one run may spend. Each in-flight detonation costs "
    "at most one request per run, and rows above this ceiling are left for the "
    "next run. Defaults to {0}, and cannot exceed {1}.".format(
        DEFAULT_MAX_POLLS, MAX_POLLS_HARD_CAP
    )
)


# ---------------------------------------------------------------------------
# The schedule: pure
# ---------------------------------------------------------------------------


def read_attempts(row):
    """Return how many times a row has been polled. Pure.

    Zero for a row that carries no count, which is what a row written by the
    detonate command looks like, and zero for a value that is not a readable
    non-negative number. A negative or unreadable count reads as "not polled
    yet" rather than as an error, because the consequence is one early poll
    and the alternative is a row that is never polled again.
    """
    if not isinstance(row, dict):
        return 0
    value = row.get(task_store.POLL_ATTEMPTS_FIELD)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    if value != value or value in (float("inf"), float("-inf")):
        return 0
    if value < 0:
        return 0
    return int(value)


def _positive_number(value):
    """Return a stored positive number as a float, or None. Pure.

    The same reading every stored clock in this app gets: a boolean is not a
    number, a NaN and an infinity are not clock readings, and zero or below is
    the absent value rather than a moment.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    if value <= 0:
        return None
    return float(value)


def read_abandoned_at(row):
    """Return the moment the poller gave up on a row, or None. Pure."""
    if not isinstance(row, dict):
        return None
    return _positive_number(row.get(task_store.POLL_ABANDONED_AT_FIELD))


def is_abandoned(row):
    """True when the poller has already given up on a row. Pure.

    Read as a field rather than inferred from anything, which is the point of
    the field existing: the alternative was a status word of this app's own,
    and task_store.map_status()'s rule is that a status never comes from here.
    """
    return read_abandoned_at(row) is not None


def read_not_found(row):
    """Return how many consecutive polls of a row came back empty. Pure.

    Zero for a row with no count and for a value that is not a readable
    non-negative number, which is the same direction read_attempts takes: an
    unreadable counter reads as "this has not happened" rather than as an
    error, so the consequence is one more poll and not a row abandoned on a
    misreading.
    """
    if not isinstance(row, dict):
        return 0
    value = row.get(task_store.POLL_NOT_FOUND_FIELD)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    if value != value or value in (float("inf"), float("-inf")):
        return 0
    if value < 0:
        return 0
    return int(value)


def row_age_anchor(row):
    """Return the moment a row's age is measured from, or None. Pure.

    `submitted_at` first, because the age that matters is how long the
    detonation has been unsettled and that is when it was submitted.
    `updated_at` second, because the poller writes it on every poll, so a row
    that lost its submission time still has a clock to age against.

    None when neither is readable, and then the row is NEVER ABANDONED ON AGE.
    That direction is deliberate: a row with no readable clock is a
    hand-edited or half-written document, and guessing its age would abandon a
    live detonation. It still reaches the ceiling by the two platform-driven
    routes, which need no clock of ours.
    """
    if not isinstance(row, dict):
        return None
    for name in (task_store.SUBMITTED_AT_FIELD, task_store.UPDATED_AT_FIELD):
        moment = _positive_number(row.get(name))
        if moment is not None:
            return moment
    return None


def is_past_age_ceiling(row, now, max_task_age_hours):
    """True when a row has been unsettled longer than the ceiling allows. Pure.

    :param row: the stored row.
    :param now: epoch seconds.
    :param max_task_age_hours: the stanza's ceiling, in hours.
    """
    anchor = row_age_anchor(row)
    if anchor is None:
        return False
    ceiling = float(max_task_age_hours) * SECONDS_PER_HOUR
    return (float(now) - anchor) > ceiling


def is_past_platform_expiration(payload, now):
    """True when the platform's own expiration for a task has passed. Pure.

    Read off the response rather than off the row, because it is not stored:
    see the note on task_store.RESPONSE_EXPIRATION_FIELD. A response with no
    readable expiration answers False, which falls back to the age ceiling.
    """
    expires_at = task_store.read_expiration_epoch(payload)
    if expires_at is None:
        return False
    return float(now) > expires_at


def interval_for(attempts):
    """Return the wait a row earns by being polled, given its prior attempts.

    Pure, and the index is the count BEFORE this poll rather than after it, so
    the schedule a row experiences is the schedule as written: a row polled for
    the first time waits 30 seconds, then 60, then 120, then 300 for as long as
    it stays unsettled.

    The first poll of a fresh row is not delayed at all. A row with no
    next_poll_at is due immediately, which is what makes the detonate command
    able to write a row without knowing anything about this schedule.

    Anything past the end of the schedule gets the last entry, which is the cap.
    """
    if attempts < 0:
        attempts = 0
    if attempts >= len(BACKOFF_SCHEDULE):
        return BACKOFF_SCHEDULE[-1]
    return BACKOFF_SCHEDULE[attempts]


def next_poll_at(now, attempts):
    """Return the epoch second before which a row is left alone. Pure.

    :param now: epoch seconds at the moment of the poll.
    :param attempts: how many times the row had been polled BEFORE this one.
    """
    return float(now) + interval_for(attempts)


def is_due(row, now):
    """True when a row may be polled on this run. Pure, and no I/O.

    Three conditions, in the order that spends the least:

      1. The poller has not already given up on the row.
         `poll_abandoned_at` is set, so it is skipped: this is the per-task
         ceiling arriving, and it is checked first because it is the cheapest
         answer and the most final one. Nothing in the app clears the field, so
         an abandoned row is skipped for good unless an operator clears it.
      2. The stored status is not terminal. `map_status()` applies the current
         release's reading of the platform's own word, per this app's rule that
         the reading is never stored.
      3. `next_poll_at` has passed. AN ABSENT OR UNREADABLE VALUE IS DUE NOW,
         which is what makes a row written by the detonate command get polled
         on the next run without the command having to know the schedule.

    A `next_poll_at` far in the future, from a corrected clock or another
    search head, would otherwise park a row forever, so the value is only
    honoured while it is within one full schedule of the present. That is the
    same reasoning verdict_cache applies to a document written in the future:
    a row that cannot be aged would be immortal.
    """
    if not isinstance(row, dict):
        return False
    if is_abandoned(row):
        return False
    if task_store.is_terminal_platform_status(row.get(task_store.STATUS_FIELD)):
        return False

    value = row.get(task_store.NEXT_POLL_AT_FIELD)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return True
    if value != value or value in (float("inf"), float("-inf")):
        return True

    moment = float(now)
    if value <= moment:
        return True
    # Beyond the whole schedule's reach is a clock problem, not a schedule.
    return value - moment > BACKOFF_SCHEDULE[-1]


def schedule_fields(now, attempts):
    """Return the two checkpoint fields for a row just polled. Pure.

    :param now: epoch seconds at the moment of the poll.
    :param attempts: how many times the row had been polled before this one,
        which is both what the count becomes plus one and the index the wait
        comes from. One argument for both because they are one fact.
    """
    return {
        task_store.POLL_ATTEMPTS_FIELD: attempts + 1,
        task_store.NEXT_POLL_AT_FIELD: next_poll_at(now, attempts),
    }


# ---------------------------------------------------------------------------
# The polling pass
# ---------------------------------------------------------------------------


class TaskPoller(object):
    """Polls the non-terminal rows of one collection, once.

    Split out from the Script subclass for the reason Detonator and
    UsageReporter are split out of their commands: a modular input script
    cannot be driven outside splunkd's own handshake, so logic left inside it
    is logic no test can reach. This class takes anything with a
    `sandbox_task_status()` method and anything with `list_tasks()` and
    `save_task()`, so the whole pass runs with a fake client, a fake KV store
    and a fake clock.
    """

    def __init__(
        self,
        client,
        store,
        max_polls=DEFAULT_MAX_POLLS,
        max_task_age_hours=DEFAULT_MAX_TASK_AGE_HOURS,
        now=None,
    ):
        """
        :param client: anything with a sandbox_task_status() method.
        :param store: a task_store.TaskStore, or anything with list_tasks()
            and save_task().
        :param max_polls: the per-run ceiling on status requests.
        :param max_task_age_hours: the per-task ceiling, in hours. See the
            block above MAX_TASK_AGE_HOURS_ARGUMENT.
        :param now: a callable returning epoch seconds, for tests.
        """
        self.client = client
        self.store = store
        self.max_polls = min(int(max_polls), MAX_POLLS_HARD_CAP)
        # Held inside its range, and a value BELOW the floor reads as the
        # default rather than as the floor. That is the safe direction here and
        # it is the opposite of what a clamp usually does: the floor is above
        # the platform's own three hour expiration, so quietly rounding a zero
        # up to one hour would start abandoning detonations that are still
        # running. Above the ceiling is clamped, because that direction only
        # costs requests.
        asked = int(max_task_age_hours)
        if asked < MIN_MAX_TASK_AGE_HOURS:
            asked = DEFAULT_MAX_TASK_AGE_HOURS
        self.max_task_age_hours = min(asked, MAX_MAX_TASK_AGE_HOURS)
        self._now = time.time if now is None else now

        # Counters, read by the caller for its finish line. Every spend
        # assertion in the tests reads these rather than a fake's internals.
        self.considered = 0
        self.polls = 0
        self.writes = 0
        self.settled = 0
        self.failures = 0
        self.limit_reached = False

        # Rows this run gave up on. Reported on the finish line, because a
        # feed that has stopped following a detonation is something an operator
        # should be able to see happening rather than discover in the
        # collection.
        self.abandoned = 0

        # The class name of the last failure, which is the only thing about a
        # failure that reaches a log line. See ps_client.get_api_key for why
        # the message is dropped rather than sanitized.
        self.last_failure = None

        # True when an authentication failure stopped the run. Distinguished
        # from an ordinary failure because it is not per row: the same key
        # will be refused for every other task, so continuing would spend a
        # rejected request per row in flight.
        self.authentication_failed = False

    def run(self):
        """Poll every due row, up to the ceiling. Returns the rows written.

        Nothing raises out of here. An input runs unattended on a schedule, so
        the useful behaviour for a single bad row is to record it and carry on
        to the next: the alternative loses every other row's update to one
        task's failure. That is not the catch-all constraint C6 forbids,
        because nothing is fabricated and nothing is swallowed silently: each
        failure is counted, the last one's class name reaches the finish line,
        and the run reports its outcome as degraded.
        """
        rows = self.store.list_tasks()
        self.considered = len(rows)

        for row in rows:
            if self.authentication_failed:
                break
            if not is_due(row, self._now()):
                continue
            if self.polls >= self.max_polls:
                self.limit_reached = True
                break
            self._poll(row)

        return self.writes

    def _poll(self, row):
        """Poll one row and write what came back."""
        task_id = task_store.read_scalar(row.get(task_store.TASK_ID_FIELD))
        if task_id is None:
            # A row with no readable task id cannot be polled and cannot be
            # written either, because the document id comes from the task id.
            # It is counted as a failure rather than skipped quietly: the only
            # way to get one is a hand-edited collection, and an operator who
            # did that should see it on the finish line.
            self.failures += 1
            self.last_failure = "MissingTaskId"
            return

        attempts = read_attempts(row)
        moment = float(self._now())

        if is_past_age_ceiling(row, moment, self.max_task_age_hours):
            # THE CEILING IS CHECKED BEFORE THE REQUEST, so a row that has
            # timed out costs nothing on the run that retires it. See the block
            # above MAX_TASK_AGE_HOURS_ARGUMENT for the three routes here and
            # why the platform's own expiration is preferred to this one: that
            # route needs a response to read it out of, so it is applied below,
            # and in ordinary use it fires hours before this one does.
            self._abandon(row, moment, AGE_CEILING_REASON)
            return

        payload = None
        try:
            self.polls += 1
            payload = self.client.sandbox_task_status(task_id)
        except AuthenticationError as error:
            # Not per row. Every subsequent call carries the same rejected
            # credential, so the run stops here and the operator gets one line
            # rather than one per task in flight.
            self.authentication_failed = True
            self.failures += 1
            self.last_failure = type(error).__name__
            ps_log.warning(
                LOG_COMPONENT, "status", "error", reason=type(error).__name__
            )
        except Exception as error:
            self.failures += 1
            self.last_failure = type(error).__name__
            ps_log.warning(
                LOG_COMPONENT, "status", "error", reason=type(error).__name__
            )

        if self.authentication_failed:
            # The run is over and nothing was learned about this row. It is
            # left exactly as it was, so the next run after the key is fixed
            # polls it immediately rather than waiting out a backoff it did
            # not earn.
            return

        if payload is None:
            # Two causes and one behaviour. The request failed, or the platform
            # answered not-found for a task id it does not know: ps_client
            # returns None for both a 204 and a 404.
            #
            # NEITHER SETTLES THE ROW. Marking a task failed because we could
            # not read it would settle a task the platform has not settled,
            # which is exactly the defect map_status() refuses to commit for an
            # unrecognised status word. The schedule still advances, so an
            # unreachable task backs off to five minutes rather than being
            # asked about on every run forever.
            #
            # AND IT IS COUNTED. Backing off to five minutes bounds what one
            # row costs per hour and does not bound what it costs, so the third
            # consecutive empty answer abandons the row: a task the platform
            # cannot find will not become findable. The count is stored on the
            # row because the state is per row, exactly as the schedule is.
            empty_polls = read_not_found(row) + 1
            schedule = schedule_fields(moment, attempts)
            schedule[task_store.POLL_NOT_FOUND_FIELD] = empty_polls
            if empty_polls >= MAX_NOT_FOUND_POLLS:
                self._abandon(
                    row, moment, NOT_FOUND_REASON, extra=schedule
                )
                return
            self._save(row, moment, schedule)
            return

        updated = task_store.build_updated_row(row, payload, updated_at=moment)
        if updated is None:
            # The response named a different task, or the row has no id to
            # write under. build_updated_row explains why writing anyway would
            # be the worst available outcome on this collection.
            self.failures += 1
            self.last_failure = "TaskIdMismatch"
            return

        settled = task_store.is_terminal_platform_status(
            updated.get(task_store.STATUS_FIELD)
        )
        if settled:
            self.settled += 1

        schedule = schedule_fields(moment, attempts)
        if read_not_found(row):
            # The answer arrived, so the run of empty ones is over. Written
            # back as zero rather than left alone, because the counter counts
            # CONSECUTIVE answers: a row that failed twice, answered, then
            # failed once would otherwise be abandoned on a run of one.
            #
            # Only written when there is something to reset, so an ordinary row
            # that has never failed carries no such field at all.
            schedule[task_store.POLL_NOT_FOUND_FIELD] = 0

        if not settled and is_past_platform_expiration(payload, moment):
            # THE PLATFORM'S OWN CEILING, and it is preferred to this app's for
            # the reason task_store.RESPONSE_EXPIRATION_FIELD gives: it is the
            # platform saying when it stops working on the task rather than
            # this app guessing. About three hours in every recorded response,
            # against a default age ceiling of a day.
            #
            # Only for a row the platform has NOT settled. A finished
            # detonation is past its expiration too, and abandoning a settled
            # row would be a state change for no reason: is_due() already
            # leaves it alone.
            self._abandon(updated, moment, EXPIRATION_REASON, extra=schedule)
            return

        self._save(updated, moment, schedule)

    def _abandon(self, row, moment, reason, extra=None):
        """Give up on one row: store the abandonment stamp and count it.

        THE PLATFORM'S STATUS IS LEFT EXACTLY AS IT WAS. Nothing in this method
        touches `status`, and that is the rule rather than an omission: an app
        that wrote a status word of its own would settle a task the platform
        has not settled, which is what task_store.map_status() refuses to do
        from the other direction. The row keeps the platform's last word and
        gains a field saying this app has stopped asking.

        The row is not deleted either. It is the receipt for a metered
        detonation, and the platform's own task listing hangs, so the record
        has to outlive the poller's interest in it.

        :param reason: one short constant naming which of the three routes
            retired the row. It reaches the log and nothing else.
        :param extra: fields to write alongside, which is how a poll that was
            actually spent still advances the schedule it earned.
        """
        fields = dict(extra or {})
        fields[task_store.POLL_ABANDONED_AT_FIELD] = moment
        self.abandoned += 1
        ps_log.info(LOG_COMPONENT, "abandon", "refused", reason=reason)
        self._save(row, moment, fields)

    def _save(self, row, moment, fields):
        """Store one row with `fields` written over it.

        PROJECTED ONTO THE DECLARED FIELD LIST, and that is not tidiness. A
        document read out of the KV store carries splunkd's own `_key` and
        `_user` alongside the row, and save_task writes back every key it is
        given: an unprojected round trip would add fields to the collection
        that collections.conf does not declare and that the lookup does not
        project, which is a column that exists and cannot be read.
        """
        document = dict(
            (name, row[name])
            for name in task_store.ALL_FIELDS
            if row.get(name) is not None
        )
        document.update(fields or {})
        document[task_store.UPDATED_AT_FIELD] = moment
        if self.store.save_task(document):
            self.writes += 1


# ---------------------------------------------------------------------------
# The splunkd seam
# ---------------------------------------------------------------------------


def read_max_polls(parameters):
    """Return the ceiling one input stanza asks for. Pure.

    Every unreadable value reads as the default, which is the direction that
    keeps the input running: a stanza with `max_polls = many` in it should
    poll fifty rows and not none. A value above the hard cap is clamped rather
    than refused for the same reason, and validate_input() below is where an
    operator is told about it, at the point they can still fix it.
    """
    if not isinstance(parameters, dict):
        return DEFAULT_MAX_POLLS
    raw = parameters.get(MAX_POLLS_ARGUMENT)
    if raw is None:
        return DEFAULT_MAX_POLLS
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_MAX_POLLS
    if value < 1:
        return DEFAULT_MAX_POLLS
    return min(value, MAX_POLLS_HARD_CAP)


def read_max_task_age_hours(parameters):
    """Return the per-task ceiling one input stanza asks for, in hours. Pure.

    Every unreadable value reads as the default, for the reason
    read_max_polls() gives: a stanza with `max_task_age_hours = a day` in it
    should use the default ceiling rather than none at all. A value outside the
    range is brought into it rather than refused, and validate_input() below is
    where an operator is told, at the point they can still fix it.

    THE CLAMP IS THE SAFE DIRECTION IN BOTH DIRECTIONS HERE, which is worth
    saying because it usually is not. Too low would abandon live detonations,
    and the floor is above the platform's own expiration, so it cannot. Too
    high would let a stale row cost requests for a week, and the ceiling bounds
    that.
    """
    if not isinstance(parameters, dict):
        return DEFAULT_MAX_TASK_AGE_HOURS
    raw = parameters.get(MAX_TASK_AGE_HOURS_ARGUMENT)
    if raw is None:
        return DEFAULT_MAX_TASK_AGE_HOURS
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_MAX_TASK_AGE_HOURS
    if value < MIN_MAX_TASK_AGE_HOURS:
        return DEFAULT_MAX_TASK_AGE_HOURS
    return min(value, MAX_MAX_TASK_AGE_HOURS)


def build_service(metadata):
    """Return a splunklib service scoped to this app.

    NOT `Script.service`, AND THE DIFFERENCE IS NOT COSMETIC. The base class
    builds its service with no app namespace, and both things this input needs
    are namespaced objects: the API key lives in this app's storage/passwords,
    and the task rows live in this app's KV store collection. A service in the
    default namespace addresses neither, and the failure is a 404 from splunkd
    on a healthy install, which reads as "no tasks" rather than as a
    misconfiguration.

    The construction itself is ps_splunkd.build_service, which the detonate
    alert action also uses: it is handed the same two values in its payload and
    needs the same namespace, and two copies of that constructor is how one of
    them ends up in the default namespace.

    :param metadata: the input definition's metadata mapping, which carries
        `server_uri` and `session_key`.
    :return: an authenticated splunklib.client.Service.
    """
    return ps_splunkd.build_service(
        metadata["server_uri"], metadata["session_key"], app=APP_NAME
    )


def poll_once(
    service,
    max_polls=DEFAULT_MAX_POLLS,
    max_task_age_hours=DEFAULT_MAX_TASK_AGE_HOURS,
    now=None,
):
    """Run one polling pass and write one finish line. Returns the poller.

    The whole of what an input invocation does, with the splunkd handshake
    lifted off it, so a test drives this with a fake service.
    """
    timer = ps_log.Timer()
    ps_log.info(LOG_COMPONENT, "start", "ok")

    try:
        client = get_client(service)
    except ClientConfigurationError:
        # CONSTRAINT C8, AND ZERO NETWORK CALLS ON THE WAY OUT. An
        # unconfigured app is the ordinary state of a fresh install, and this
        # input is enabled, so it is reached on every install before a key is
        # saved. One line an operator can search for, no stack trace, and no
        # request: get_client refuses before building a client at all. The
        # message is not logged because it belongs to the setup page and
        # ps_log has no key it could travel under.
        ps_log.warning(
            LOG_COMPONENT,
            "finish",
            "refused",
            reason="ClientConfigurationError",
            duration_ms=timer.duration_ms,
        )
        return None

    store = task_store.TaskStore(service)
    poller = TaskPoller(
        client,
        store,
        max_polls=max_polls,
        max_task_age_hours=max_task_age_hours,
        now=now,
    )
    poller.run()

    degraded = bool(poller.failures) or bool(store.degraded)
    ps_log.info(
        LOG_COMPONENT,
        "finish",
        "degraded" if degraded else "ok",
        records=poller.considered,
        lookups=poller.polls,
        cache_stores=poller.writes,
        cache_degraded=store.degraded,
        limit=poller.max_polls,
        limit_reached=poller.limit_reached,
        # Rows this run stopped following. Zero on an ordinary run, and a count
        # rather than anything about which rows: ps_log has no key a task id
        # could travel under. Each one also has its own line, naming which of
        # the three routes retired it.
        abandoned=poller.abandoned,
        reason=poller.last_failure,
        duration_ms=timer.duration_ms,
    )
    return poller


class TaskPollerScript(Script):
    """The splunkd entry point. Everything testable is above this line."""

    def get_scheme(self):
        """Declare the input kind and its two arguments.

        `use_external_validation` is on so that a ceiling above the hard cap is
        reported when an operator saves the input rather than being silently
        clamped on the next run. `use_single_instance` is off: each stanza gets
        its own process, which is what keeps one broken stanza from taking the
        others down with it.
        """
        scheme = Scheme(SCHEME_TITLE)
        scheme.description = SCHEME_DESCRIPTION
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        for name, title, description in (
            (
                MAX_POLLS_ARGUMENT,
                "Maximum status requests per run",
                MAX_POLLS_DESCRIPTION,
            ),
            (
                MAX_TASK_AGE_HOURS_ARGUMENT,
                "Give up on a task after, in hours",
                MAX_TASK_AGE_HOURS_DESCRIPTION,
            ),
        ):
            argument = Argument(name)
            argument.title = title
            argument.description = description
            argument.data_type = Argument.data_type_number
            argument.required_on_create = False
            argument.required_on_edit = False
            scheme.add_argument(argument)

        return scheme

    def validate_input(self, definition):
        """Refuse a ceiling that is not a number, or is above the hard cap.

        The refusal is the point: an operator typing 5000 into this field is
        asking for something the app will not do, and clamping it silently
        teaches them it worked.
        """
        self._validate_max_task_age_hours(definition.parameters)

        raw = definition.parameters.get(MAX_POLLS_ARGUMENT)
        if raw is None or str(raw).strip() == "":
            return
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            raise ValueError(
                "{0} must be a whole number of status requests.".format(
                    MAX_POLLS_ARGUMENT
                )
            )
        if value < 1:
            raise ValueError(
                "{0} must be at least 1. Disable the input instead of setting "
                "it to zero.".format(MAX_POLLS_ARGUMENT)
            )
        if value > MAX_POLLS_HARD_CAP:
            raise ValueError(
                "{0} cannot exceed {1}. Each status request is an API request "
                "against this account.".format(
                    MAX_POLLS_ARGUMENT, MAX_POLLS_HARD_CAP
                )
            )

    def _validate_max_task_age_hours(self, parameters):
        """Refuse a per-task ceiling outside the range it may take.

        Both ends are refused rather than clamped, and each end refuses
        something different. Below the floor would abandon detonations that are
        still running, because the platform's own expiration is about three
        hours: a ceiling of one hour is an operator asking the app to throw
        away results they have paid for. Above the ceiling stops being a
        ceiling, and the whole point of the setting is that a row cannot cost
        requests indefinitely.
        """
        raw = parameters.get(MAX_TASK_AGE_HOURS_ARGUMENT)
        if raw is None or str(raw).strip() == "":
            return
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            raise ValueError(
                "{0} must be a whole number of hours.".format(
                    MAX_TASK_AGE_HOURS_ARGUMENT
                )
            )
        if value < MIN_MAX_TASK_AGE_HOURS:
            raise ValueError(
                "{0} must be at least {1} hour. A shorter ceiling would stop "
                "following detonations that are still running: the platform's "
                "own task expiration is about three hours.".format(
                    MAX_TASK_AGE_HOURS_ARGUMENT, MIN_MAX_TASK_AGE_HOURS
                )
            )
        if value > MAX_MAX_TASK_AGE_HOURS:
            raise ValueError(
                "{0} cannot exceed {1} hours. A task nothing has settled by "
                "then costs one API request per row every five minutes for as "
                "long as it is followed.".format(
                    MAX_TASK_AGE_HOURS_ARGUMENT, MAX_MAX_TASK_AGE_HOURS
                )
            )

    def stream_events(self, inputs, ew):
        """Run one pass per configured stanza.

        NO EVENT IS WRITTEN, and that is deliberate. This input's output is
        the state of the task rows, which the tray reads through the lookup
        definition, and its diagnostics are `ps_log` lines that splunkd
        indexes into `_internal` on its own. Writing the rows into an index as
        well would put the customer's detonated URLs into a second place with
        a second retention policy, for a tray that already has them.

        A deployment with two stanzas polls the same collection twice, which is
        harmless because the pass is idempotent: the second run finds the rows
        it just wrote either terminal or not yet due.
        """
        service = build_service(self._input_definition.metadata)
        for parameters in (inputs.inputs or {}).values():
            poll_once(
                service,
                max_polls=read_max_polls(parameters),
                max_task_age_hours=read_max_task_age_hours(parameters),
            )


def main(argv=None):
    """Console entry point invoked by splunkd."""
    return TaskPollerScript().run(argv if argv is not None else sys.argv)


if __name__ == "__main__":
    sys.exit(main())

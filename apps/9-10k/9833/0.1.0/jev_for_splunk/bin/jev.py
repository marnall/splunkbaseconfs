#!/usr/bin/env python
"""`| jev`: ask TypeSafe's Jev model typed questions about each result row; answers become fields.

    ... | jev questions=<set> state="<field>,<field>,..."
    ... | jev noul="Does this message report a failed login?" state=_raw
    ... | jev choice="Which team should handle this?" options="network,security,other" state="short_description"
    ... | jev score="How urgently should an operator act?" levels="nothing to do|look next shift|act today" state="mnemonic,examples"

Every call sends the named state fields to the TypeSafe API. The command therefore needs the
run_jev capability, never sends more than maxrows rows, and writes one audit line per chunk of
rows to jev_for_splunk.log (field names and counts, never values). Answers are cached in the KV
store as each slice of rows completes, so a cancelled search keeps what it paid for.

This file is wiring only. Decisions are in jev_setup.py, the row loop in jev_engine.py, the
protocol in jev_client.py; all three are tested without Splunk.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from splunklib.searchcommands import Configuration, Option, StreamingCommand, dispatch, validators  # noqa: E402

import jev_audit  # noqa: E402
import jev_cache  # noqa: E402
import jev_client  # noqa: E402
import jev_engine  # noqa: E402
import jev_setup  # noqa: E402
import jev_splunk  # noqa: E402


@Configuration(distributed=False)
class JevCommand(StreamingCommand):
    questions = Option(require=False, doc="Question set in jev.conf")
    noul = Option(require=False, doc="Inline yes or no question")
    choice = Option(require=False, doc="Inline choice question; needs options=")
    # Not "options": splunklib keeps its own view of the parsed options in SearchCommand.options, and an
    # attribute of that name replaces it, so the command dies at startup. Same trick as "as" below.
    choice_options = Option(name="options", require=False, doc="Comma-separated options for choice=")
    score = Option(require=False, doc="Inline score question; needs levels=")
    levels = Option(require=False, doc="Pipe-separated level descriptions for score=")
    as_ = Option(name="as", require=False, validate=validators.Fieldname(), doc="Field name for the inline answer")
    state = Option(require=True, doc="Comma-separated fields sent as state; a.b nests, a.* takes a prefix")
    maxrows = Option(require=False, validate=validators.Integer(1))
    cache = Option(require=False, validate=validators.Boolean())
    workers = Option(require=False, validate=validators.Integer(1, 32))

    _engine = None
    _log = None
    _told_skipped = False

    def _warn(self, text):
        # splunklib runs its first argument through str.format(); an API or KV store error quotes a JSON body.
        self.write_warning("{}", text)

    def _fail(self, error, text):
        self.write_error("{}", text)
        self.logger.error("Abnormal exit: %s", error)
        sys.exit(1)

    def _start(self):
        info = self._metadata.searchinfo
        if not jev_setup.has_capability(jev_splunk.current_context(self.service)):
            raise ValueError("jev: this search sends data to a third party and needs the %s capability, "
                             "which your roles do not have." % jev_setup.CAPABILITY)
        config = jev_splunk.read_settings(info.session_key)
        conf = {s.name: dict(s.content) for s in self.service.confs["jev"]}
        plan = jev_setup.plan({"questions": self.questions, "noul": self.noul, "choice": self.choice,
                               "options": self.choice_options, "score": self.score, "levels": self.levels, "as": self.as_,
                               "state": self.state, "maxrows": self.maxrows, "cache": self.cache,
                               "workers": self.workers}, conf, config)
        for warning in plan.warnings:
            self._warn(warning)
        self._log = jev_splunk.get_logger(info.session_key)

        cache = None
        if plan.use_cache:
            try:
                cache = jev_cache.Cache(jev_splunk.KV(self.service), lifetime_days=config["cache_days"])
            except Exception as e:
                self._warn("jev: the answer cache is unavailable (%s); continuing without it" % e)
        opener = jev_client.make_opener(config["proxy_url"])

        def ask(state):
            return jev_client.ask(state, plan.questions, config["api_key"], model=plan.model, opener=opener,
                                  url=config["url"])

        engine = jev_engine.Engine(plan, ask, cache=cache, warn=self._warn)
        if plan.use_cache and cache is None:
            engine.cache_state = "unavailable"
        return engine

    def _audit(self, before, started):
        delta = self._engine.totals.since(before)
        if delta.rows or delta.sent:
            info = self._metadata.searchinfo
            self._log.info(jev_audit.audit_line(info.username, info.sid, info.app, self.questions or self.noul
                                                or self.choice or self.score, self._engine.plan.fields, delta,
                                                time.time() - started, self._engine.cache_state))

    def stream(self, records):
        started = time.time()
        if self._engine is None:
            try:
                self._engine = self._start()
            except ValueError as e:
                self._fail(e, str(e))
            except Exception as e:  # Splunk unreachable, jev.conf not visible: say which, not a bare traceback
                self._fail(e, "jev: could not start: %s: %s" % (type(e).__name__, e))
        before = self._engine.totals.copy()
        try:
            for record in self._engine.process(records):
                yield record
        except jev_client.JevError as e:
            self._audit(before, started)
            before = self._engine.totals.copy()  # so that the finally below finds nothing new and writes no second line
            self._fail(e, "jev: stopped, because every other row would fail the same way: %s" % e)
        finally:
            self._audit(before, started)
        if self._engine.totals.skipped and not self._told_skipped:
            self._told_skipped = True
            self._warn("jev: maxrows=%d was reached; rows beyond it were not sent and carry jev_skipped=1"
                       % self._engine.plan.maxrows)


dispatch(JevCommand, sys.argv, sys.stdin, sys.stdout, __name__)

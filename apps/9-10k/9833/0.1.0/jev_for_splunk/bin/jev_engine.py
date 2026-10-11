"""How rows become answers: slices, cache, parallel calls, the row ceiling, and when to stop.

No Splunk import and no HTTP here. jev.py hands in a function that asks the API about one
state, and optionally a cache; tests hand in fakes. Rows are processed in slices: look the
slice up in the cache, ask the API about the rest in parallel, store the new answers, move on.
A search that is cancelled or fails keeps every finished slice.
"""
from concurrent.futures import ThreadPoolExecutor

import jev_audit
import jev_cache
import jev_client

SLICE = 200


class Plan:
    """Everything one invocation decided before the first row."""

    def __init__(self, questions, fields, model, labels=None, maxrows=1000, workers=8, rename=None):
        self.questions, self.fields, self.model = questions, fields, model
        self.labels, self.maxrows, self.workers, self.rename = labels or {}, maxrows, workers, rename


class Engine:
    def __init__(self, plan, ask, cache=None, warn=lambda message: None, slice_size=SLICE):
        """ask(state) -> API reply, raising jev_client.JevError. cache: a jev_cache.Cache or None."""
        self.plan, self.ask, self.cache, self.warn = plan, ask, cache, warn
        self.slice_size = slice_size
        self.totals = jev_audit.Totals()
        self.cache_state = "on" if cache else "off"
        self._fatal = None
        # splunklib writes a chunk's header from the first record it is given and drops, without a word, any
        # field that first appears on a later one. So every record gets every output field, blank unless set.
        names = {name: "" for name in jev_client.answer_fields(plan.questions, plan.labels)}
        self._blank = jev_client.rename_answer(names, plan.rename) if plan.rename else names
        self._blank.update({"jev_model": "", "jev_cached": "", "jev_error": "", "jev_skipped": ""})

    def process(self, records):
        """Yield every record, in order, with its answers or with jev_error or jev_skipped."""
        batch = []
        for record in records:
            batch.append(record)
            if len(batch) == self.slice_size:
                for done in self._slice(batch):
                    yield done
                batch = []
        for done in self._slice(batch):
            yield done

    def _cached(self, keys):
        if self.cache:
            try:
                return self.cache.get_many(keys)
            except jev_cache.CacheUnavailable as e:
                self._drop_cache(e)
        return {}

    def _store(self, replies):
        if self.cache:
            try:
                self.cache.put_many(replies)
            except jev_cache.CacheUnavailable as e:
                self._drop_cache(e)

    def _drop_cache(self, error):
        self.cache, self.cache_state = None, "unavailable"
        self.warn("jev: the answer cache is unavailable (%s); continuing without it, so a cancelled "
                  "search will lose its answers" % error)

    def _ask_one(self, item):
        key, state = item
        if self._fatal:
            return key, None
        try:
            return key, self.ask(state)
        except jev_client.JevError as e:
            if e.fatal:
                self._fatal = e
            return key, e
        except Exception as e:  # a bug or an unforeseen reply must cost one row, not a slice of paid answers
            # Only its kind is shown. http.client refuses a header with a line break in it by quoting the
            # header, and the header is the API key; the text of an exception we did not foresee is not ours
            # to vouch for.
            return key, jev_client.JevError("unexpected %s while asking the API" % type(e).__name__)

    def _slice(self, batch):
        plan, totals = self.plan, self.totals
        states = [jev_client.build_state(r, plan.fields) for r in batch]
        keys = [jev_cache.cache_key(plan.model, plan.questions, s) if s else None for s in states]
        known = self._cached([k for k in keys if k])

        to_send = {}
        for key, state in zip(keys, states):
            if key and key not in known and key not in to_send and totals.sent + len(to_send) < plan.maxrows:
                to_send[key] = state
        with ThreadPoolExecutor(plan.workers) as pool:
            outcomes = dict(pool.map(self._ask_one, to_send.items()))
        totals.sent += sum(1 for o in outcomes.values() if o is not None)
        fresh = {k: o for k, o in outcomes.items() if isinstance(o, dict)}
        for reply in fresh.values():
            totals.add_usage(reply)
        self._store(fresh)
        if self._fatal:
            raise self._fatal

        for record, key in zip(batch, keys):
            totals.rows += 1
            record.update(self._blank)
            reply = known.get(key) or fresh.get(key)
            if reply:
                fields = jev_client.flatten_answers(reply["answers"], plan.labels)
                record.update(jev_client.rename_answer(fields, plan.rename) if plan.rename else fields)
                record["jev_model"] = reply.get("model") or plan.model
                hit = key in known
                record["jev_cached"] = 1 if hit else 0
                totals.cached += 1 if hit else 0
            elif key is None:
                record["jev_error"] = "none of the state fields has a value on this row"
                totals.failed += 1
            elif isinstance(outcomes.get(key), Exception):
                record["jev_error"] = str(outcomes[key])
                totals.failed += 1
            else:
                record["jev_skipped"] = 1
                totals.skipped += 1
            yield record

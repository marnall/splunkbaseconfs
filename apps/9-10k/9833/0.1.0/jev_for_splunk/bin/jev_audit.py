"""The audit record of one `jev` invocation: who sent which fields of how many rows to a third party.

It names the state fields and never holds their values. Lines are key="value" pairs so Splunk
extracts them from index=_internal without any configuration.
"""


class Totals:
    """Counters the engine fills in. rows: seen. sent: API calls made. cached, failed, skipped: rows."""
    FIELDS = ("rows", "sent", "cached", "failed", "skipped", "input_tokens")

    def __init__(self):
        for f in self.FIELDS:
            setattr(self, f, 0)

    def since(self, earlier):
        """The difference between now and an earlier copy(): one audit line per chunk can then be summed."""
        delta = Totals()
        for f in self.FIELDS:
            setattr(delta, f, getattr(self, f) - getattr(earlier, f))
        return delta

    def copy(self):
        return self.since(Totals())

    def add_usage(self, reply):
        self.input_tokens += int((reply.get("usage") or {}).get("input_tokens") or 0)


def _quoted(value):
    return '"%s"' % str(value).replace("\\", "\\\\").replace('"', "'").replace("\n", " ")


def audit_line(user, sid, app, questions, state_fields, totals, duration, cache):
    """questions: the set name, or the inline question text (cut at 200 characters).
    cache: "on", "off" or "unavailable"."""
    pairs = [("action", "jev"), ("user", user), ("sid", sid), ("app", app), ("questions", str(questions)[:200]),
             ("state_fields", ",".join(state_fields))]
    pairs += [(f, getattr(totals, f)) for f in Totals.FIELDS]
    pairs += [("duration", "%.2f" % duration), ("cache", cache)]
    return " ".join("%s=%s" % (k, v if isinstance(v, int) else _quoted(v)) for k, v in pairs)

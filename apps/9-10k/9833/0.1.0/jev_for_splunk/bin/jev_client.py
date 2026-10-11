"""Client for TypeSafe's Jev model (https://docs.typesafe.ai/api), standard library only.

Jev answers typed questions about a piece of state: a Choice (one of a set), a Score (a position on
ordered levels) or a Noul (the probability a statement is true). This module turns the question
sets in jev.conf into the documented request, calls the API, and flattens the answers into Splunk
fields. It has no Splunk imports so it can be tested, and reused by tools, outside Splunk. The
TypeSafe SDK needs Python 3.10 and pydantic; Splunk still runs search commands on 3.9.
"""
import json
import random
import time
import urllib.error
import urllib.request

BASE_URL = "https://api.typesafe.ai"
API_URL = BASE_URL + "/v1/systemone"
DEFAULT_MODEL = "jev-latest"
RETRYABLE = {429, 500, 502, 503, 504, 529}
FATAL = {401, 422}
MAX_SCORE_LEVELS = 10
MAX_CHOICE_OPTIONS = 255


class JevError(Exception):
    """The API refused the request, or stayed unavailable through every retry.

    fatal is true when every other row would fail the same way (a rejected key, a rejected
    question), so the caller should stop instead of paying for the same answer again."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status
        self.fatal = status in FATAL


def _numbered(stanza, prefix):
    rows = [(int(k[len(prefix):]), v) for k, v in stanza.items() if k.startswith(prefix) and k[len(prefix):].isdigit()]
    return [v for _, v in sorted(rows)]


def _question(stanza):
    q = {"type": stanza["type"], "instructions": stanza["instructions"]}
    if q["type"] == "choice":
        q["criteria"] = {k[len("option."):]: v for k, v in stanza.items() if k.startswith("option.")}
    elif q["type"] == "score":
        q["criteria"] = _numbered(stanza, "level.")
    elif "true" in stanza or "false" in stanza:
        q["criteria"] = {k: stanza[k] for k in ("true", "false") if k in stanza}
    return q


def parse_question_sets(conf):
    """{"<set>/<question>": {key: value}} as read from jev.conf -> {set: {question: API question}}."""
    sets = {}
    for name, stanza in conf.items():
        if "/" in name and stanza.get("type"):
            set_name, qid = name.split("/", 1)
            sets.setdefault(set_name, {})[qid] = _question(stanza)
    return sets


def score_labels(conf, set_name):
    """Short display names for score levels (label.N); they are never sent to the model."""
    out = {}
    for name, stanza in conf.items():
        if name.startswith(set_name + "/"):
            labels = {int(k[len("label."):]): v for k, v in stanza.items() if k.startswith("label.")}
            if labels:
                out[name.split("/", 1)[1]] = labels
    return out


def flatten_answers(answers, labels):
    """Typed answers -> flat fields: jev_<q>, jev_<q>_confidence, jev_<q>_label, jev_<q>_probabilities."""
    fields = {}
    for qid, a in answers.items():
        key = "jev_" + qid
        fields[key] = a.get(a.get("type"))
        if "confidence" in a:
            fields[key + "_confidence"] = a["confidence"]
        if a.get("probabilities"):
            fields[key + "_probabilities"] = json.dumps(a["probabilities"], sort_keys=True)
            if a.get("type") == "score" and qid in labels:
                top = max(a["probabilities"], key=a["probabilities"].get)
                fields[key + "_label"] = labels[qid].get(int(top), top)
    return fields


def answer_fields(questions, labels):
    """Every field flatten_answers can produce for these questions, in a stable order, before any answer
    exists. Splunk takes a chunk's columns from its first row, so every row must carry all of them."""
    names = []
    for qid, q in questions.items():
        names.append("jev_" + qid)
        if q.get("type") in ("choice", "score"):
            names += ["jev_%s_confidence" % qid, "jev_%s_probabilities" % qid]
        if q.get("type") == "score" and qid in labels:
            names.append("jev_%s_label" % qid)
    return names


def build_state(row, fields):
    """The named fields of one result row as the request state. A dotted name nests
    (cmdb.location -> {"cmdb": {"location": ...}}), "prefix.*" takes every field under the
    prefix, a multivalue field becomes a list, and empty fields are left out."""
    names = []
    for f in fields:
        names.extend(sorted(k for k in row if k.startswith(f[:-1])) if f.endswith(".*") else [f])
    state = {}
    for name in names:
        value = row.get(name)
        if value in (None, "", []):
            continue
        node, parts = state, name.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return state


def inline_question(noul=None, choice=None, score=None, options=None, levels=None):
    """One ad hoc question from the command line -> {"answer": API question}.

    options is comma-separated, levels is pipe-separated because a level is a sentence and
    sentences contain commas. Option names need no description, so their criteria are null."""
    given = [name for name, text in (("noul", noul), ("choice", choice), ("score", score)) if text]
    if len(given) != 1:
        raise ValueError("give exactly one of noul=, choice= or score=")
    if noul:
        if options or levels:
            raise ValueError("noul= takes neither options= nor levels=")
        return {"answer": {"type": "noul", "instructions": noul}}
    if choice:
        names = [o.strip() for o in (options or "").split(",") if o.strip()]
        if levels or len(names) < 2:
            raise ValueError('choice= needs options="a,b,..." with at least two options, and no levels=')
        return {"answer": {"type": "choice", "instructions": choice, "criteria": {n: None for n in names}}}
    described = [lv.strip() for lv in (levels or "").split("|") if lv.strip()]
    if options or len(described) < 2:
        raise ValueError('score= needs levels="first|second|..." with at least two levels, and no options=')
    return {"answer": {"type": "score", "instructions": score, "criteria": described}}


def validate_questions(questions):
    """Refuse, before any data leaves, what the API would refuse with a 422 on every row."""
    for qid, q in questions.items():
        if q.get("type") not in ("choice", "score", "noul"):
            raise ValueError("question %r: type must be choice, score or noul, not %r" % (qid, q.get("type")))
        if not q.get("instructions"):
            raise ValueError("question %r has no instructions" % qid)
        criteria = q.get("criteria")
        if q["type"] == "score" and not 2 <= len(criteria or []) <= MAX_SCORE_LEVELS:
            raise ValueError("question %r: a score needs 2 to %d levels, found %d" % (qid, MAX_SCORE_LEVELS, len(criteria or [])))
        if q["type"] == "choice" and not 2 <= len(criteria or {}) <= MAX_CHOICE_OPTIONS:
            raise ValueError("question %r: a choice needs 2 to %d options, found %d" % (qid, MAX_CHOICE_OPTIONS, len(criteria or {})))


def rename_answer(fields, name):
    """as=<name> for an inline question: jev_answer, jev_answer_confidence, ... -> <name>, <name>_confidence, ..."""
    return {(name + k[len("jev_answer"):] if k.startswith("jev_answer") else k): v for k, v in fields.items()}


def endpoint(base_url):
    return (base_url or BASE_URL).rstrip("/") + "/v1/systemone"


def make_opener(proxy_url=None):
    """urlopen, or the same through an HTTP proxy. The result has the signature ask() expects."""
    if not proxy_url:
        return urllib.request.urlopen
    return urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})).open


def backoff(attempt, rand=random.random):
    """Seconds to wait before retry number attempt (0 is the first retry).

    Equal jitter: half the exponential step is fixed, half is random. With up to 32 workers
    refused in the same second, a fixed delay would send them all back in the same second too.
    The fixed half keeps successive waits increasing, which the tests rely on."""
    step = min(0.5 * 2 ** attempt, 8)
    return step / 2 + rand() * step / 2


def _retry_after(error):
    try:
        return min(float(error.headers.get("Retry-After")), 30.0)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def ask(state, questions, api_key, model=DEFAULT_MODEL, opener=urllib.request.urlopen, sleep=time.sleep,
        retries=4, timeout=30, url=API_URL, rand=random.random):
    """One request: every question is answered in parallel over the same state."""
    body = json.dumps({"model": model, "state": state, "questions": questions}).encode()
    request = urllib.request.Request(url, data=body, headers={"Authorization": "Bearer " + api_key,
                                                              "Content-Type": "application/json"})
    for attempt in range(retries + 1):
        wait = 0.0
        try:
            with opener(request, timeout=timeout) as response:
                raw = response.read()
            try:
                return json.loads(raw.decode())
            except ValueError:  # includes UnicodeDecodeError: a gateway page, not an API reply; a retry would not change it
                raise JevError("TypeSafe API returned a body that is not JSON: %r" % raw[:100])
        except urllib.error.HTTPError as e:
            if e.code not in RETRYABLE or attempt == retries:
                raise JevError("TypeSafe API returned HTTP %s: %s" % (e.code, e.read().decode()[:300]), status=e.code)
            wait = _retry_after(e)
        except OSError as e:  # URLError, socket.timeout (not a TimeoutError before Python 3.10), connection resets, TLS errors
            if attempt == retries:
                raise JevError("TypeSafe API unreachable: %s" % getattr(e, "reason", e))
        sleep(max(wait, backoff(attempt, rand)))

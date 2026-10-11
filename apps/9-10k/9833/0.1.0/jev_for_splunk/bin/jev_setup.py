"""Everything `jev` decides before the first row: settings, options, the question set, permission.

Pure functions over plain dicts, so every refusal can be tested without Splunk. A refusal is a
ValueError whose message is shown to the person who ran the search.
"""
import jev_client
import jev_engine

APP = "jev_for_splunk"
CAPABILITY = "run_jev"
TRUE = ("1", "true", "t", "yes", "y", "on")


def _int(stanza, name, default, low, high):
    try:
        return max(low, min(high, int(stanza.get(name) or default)))
    except (TypeError, ValueError):
        return default


def settings(typesafe=None, proxy=None, limits=None):
    """The three stanzas of jev_for_splunk_settings.conf (any may be missing) -> one flat dict."""
    typesafe, proxy, limits = typesafe or {}, proxy or {}, limits or {}
    proxy_url = None
    if str(proxy.get("proxy_enabled") or "").lower() in TRUE and proxy.get("proxy_url"):
        proxy_url = "http://%s:%d" % (proxy["proxy_url"], _int(proxy, "proxy_port", 8080, 1, 65535))
    ceiling = _int(limits, "maxrows_ceiling", 10000, 1, 1000000)
    return {
        "api_key": (typesafe.get("api_key") or "").strip().strip("\"'"),
        "url": jev_client.endpoint(typesafe.get("base_url")),
        "model": typesafe.get("model") or jev_client.DEFAULT_MODEL,
        "proxy_url": proxy_url,
        "maxrows": min(_int(limits, "maxrows", 1000, 1, 1000000), ceiling),
        "maxrows_ceiling": ceiling,
        "workers": _int(limits, "workers", 8, 1, 32),
        "cache": str(limits.get("cache", "1")).lower() in TRUE,
        "cache_days": _int(limits, "cache_days", 30, 1, 3650),
    }


def has_capability(current_context, name=CAPABILITY):
    """current_context: the parsed JSON of GET authentication/current-context."""
    entries = current_context.get("entry") or [{}]
    return name in (entries[0].get("content") or {}).get("capabilities", [])


def plan(options, conf, config):
    """options: what the search said. conf: jev.conf as {stanza: {key: value}}. config: settings().
    Returns a jev_engine.Plan with two more attributes: use_cache and warnings."""
    if not config["api_key"]:
        raise ValueError("jev: no TypeSafe API key is configured. An administrator stores it under "
                         "Apps, Jev for Splunk, Configuration, Account.")
    if not config["url"].lower().startswith("https://"):
        # The configuration page enforces this too, but a hand-edited conf file does not pass through it,
        # and over http the API key and the state would travel in the clear.
        raise ValueError("jev: the base URL on the configuration page must start with https://")
    inline = [k for k in ("noul", "choice", "score") if options.get(k)]
    labels, rename, warnings = {}, None, []
    if options.get("questions"):
        if inline or options.get("options") or options.get("levels") or options.get("as"):
            raise ValueError("jev: questions= cannot be combined with noul=, choice=, score=, options=, levels= or as=")
        sets = jev_client.parse_question_sets(conf)
        questions = sets.get(options["questions"])
        if not questions:
            known = ", ".join(sorted(sets)) or "none are visible from this app"
            raise ValueError("jev: no question set named %r in jev.conf (sets: %s)" % (options["questions"], known))
        labels = jev_client.score_labels(conf, options["questions"])
    else:
        questions = jev_client.inline_question(options.get("noul"), options.get("choice"), options.get("score"),
                                               options.get("options"), options.get("levels"))
        rename = options.get("as")
    jev_client.validate_questions(questions)

    fields = [f.strip() for f in (options.get("state") or "").split(",") if f.strip()]
    if not fields:
        raise ValueError('jev: state= must name at least one field, for example state="_raw"')

    # The command's option validators refuse these first; this is the layer that is tested, so it refuses too.
    maxrows = config["maxrows"] if options.get("maxrows") is None else int(options["maxrows"])
    if maxrows < 1:
        raise ValueError("jev: maxrows= must be 1 or more")
    if maxrows > config["maxrows_ceiling"]:
        warnings.append("jev: maxrows=%d is above the ceiling an administrator set; using %d"
                        % (maxrows, config["maxrows_ceiling"]))
        maxrows = config["maxrows_ceiling"]
    workers = config["workers"] if options.get("workers") is None else int(options["workers"])
    if not 1 <= workers <= 32:
        raise ValueError("jev: workers= must be between 1 and 32")
    result = jev_engine.Plan(questions, fields, config["model"], labels=labels, maxrows=maxrows,
                             workers=workers, rename=rename)
    result.use_cache = config["cache"] and options.get("cache") is not False
    result.warnings = warnings
    return result

import import_declare_test  # noqa: F401  (UCC path bootstrap — must stay first)

from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from ransomleak_client import (
    GRAFANA_METRICS, RansomleakClient, collect_grafana_metrics, event_payload,
    grafana_range, parse_grafana_metrics, should_verify_tls)

ADDON_NAME = "TA-ransomleak"
CHECKPOINT_COLLECTION = "TA_ransomleak_checkpoints"

# The server rejects a daily series spanning more than 1000 UTC days
# (`MAX_TREND_DAYS`), and the window is inclusive at both ends, so 999 days back
# from `now` is exactly the widest window that can be asked for. A larger value
# would 400 on every time-series metric while the table metrics kept working --
# a half-dead input, which is worse than a rejected form.
MAX_LOOKBACK_DAYS = 999


def logger_for_input(input_name):
    return log.Logs().get_logger("{}_{}".format(ADDON_NAME.lower(), input_name))


def get_account(session_key, account_name):
    """Read one configured account, decrypting the stored API token."""
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-ta-ransomleak_account".format(ADDON_NAME),
    )
    return cfm.get_conf("ta-ransomleak_account").get(account_name)


def validate_grafana_input(definition, default_metrics):
    """Reject configuration Splunk would otherwise accept and fail on later.

    Worth stating plainly, because it is the reason the `globalConfig.json`
    validator regexes carry the real load: **this function never runs for an
    input created through the add-on's UI.** UCC's generated REST handler writes
    `inputs.conf` directly, so the only gate on that path is the regex, and its
    `errorMsg` must therefore describe exactly what the pattern accepts. A
    mismatch between the two was a real defect on this branch.
    """
    params = definition.parameters
    metrics = parse_grafana_metrics(params.get("metrics") or default_metrics)
    if not metrics:
        raise ValueError(
            "Select at least one metric. Valid metrics: %s." % (", ".join(GRAFANA_METRICS),))
    unknown = sorted(
        set(part.strip() for part in (params.get("metrics") or "").split(",") if part.strip())
        - set(GRAFANA_METRICS))
    if unknown:
        raise ValueError(
            "Unknown metric(s): %s. Valid metrics: %s."
            % (", ".join(unknown), ", ".join(GRAFANA_METRICS)))
    lookback = int(params.get("lookback_days", "30"))
    if not 1 <= lookback <= MAX_LOOKBACK_DAYS:
        raise ValueError("Lookback (days) must be between 1 and %d." % (MAX_LOOKBACK_DAYS,))
    channel = (params.get("channel") or "").strip()
    if channel and channel not in ("email", "sms"):
        raise ValueError("Channel must be email or sms, or left blank.")


def stream_grafana_events(inputs, event_writer, scheme, sourcetype, default_metrics,
                          default_lookback_days, error_code, error_message):
    """The body shared by `risk_helper` and `metrics_helper`.

    Two inputs, one implementation. The alternative was a fourth and fifth copy
    of the ~60-line helper boilerplate, and docs/follow-ups.md records what
    happened the last time it was copied: the copies dropped the rationale
    comments below, which are the only thing standing between a future
    "cleanup" and a silent regression. Keeping it here also means the shared
    `ransomleak_input_base.py` extraction that file calls for has one call site
    to absorb rather than three.
    """
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)

        # Namespace the checkpoint by scheme. `normalized_input_name` strips the
        # scheme off the stanza, so `ransomleak_risk://acme` and
        # `ransomleak_metrics://acme` -- distinct Splunk stanzas, and naming
        # every input after the tenant is the obvious operator action -- collide
        # on one key in a shared collection. solnlib's `update()` REPLACES the
        # document rather than merging, so one input's write would erase the
        # other's `tracked` map and both would re-emit their whole window every
        # interval; the account/base_url re-baseline guard below never fires,
        # because both inputs legitimately share an account and a base URL.
        # Only `phishing_events` keeps a bare key, and only because it shipped
        # first: re-keying it would orphan an existing install's high-water mark
        # and re-ingest its entire history.
        checkpoint_key = scheme + "/" + normalized_input_name
        try:
            session_key = inputs.metadata["session_key"]
            logger.setLevel(
                conf_manager.get_log_level(
                    logger=logger, session_key=session_key,
                    app_name=ADDON_NAME, conf_name="ta-ransomleak_settings")
            )
            log.modular_input_start(logger, normalized_input_name)

            account_name = input_item.get("account")
            account = get_account(session_key, account_name)
            base_url = account.get("base_url")

            # Fail-closed TLS: a DENY-LIST, never an allow-list. The rationale --
            # where an unrecognised value comes from and what is in flight if it
            # silently disables verification -- lives once, in
            # `ransomleak_client.should_verify_tls`. Read it before changing this.
            client = RansomleakClient(
                base_url=base_url,
                api_token=account.get("api_token"),
                verify_tls=should_verify_tls(account.get("verify_tls")),
            )

            store = checkpointer.KVStoreCheckpointer(
                CHECKPOINT_COLLECTION, session_key, ADDON_NAME)
            state = store.get(checkpoint_key) or {}

            # The checkpoint is only meaningful for the tenant that produced it.
            # Repointing an input at a different account, or editing an
            # account's base_url, would otherwise apply one tenant's digests to
            # another's aggregates: identical values would be suppressed as
            # "unchanged" and never indexed at all, with the input still
            # reporting success. Bind identity into the checkpoint and
            # re-baseline whenever it changes. (The team/channel facets need no
            # equivalent guard: they are part of every digest key, so editing
            # one changes every key and the whole window is re-emitted once.)
            if state.get("account") != account_name or state.get("base_url") != base_url:
                if state:
                    logger.warning(
                        "Input %s now points at account=%s base_url=%s (was account=%s "
                        "base_url=%s); re-baselining from scratch to avoid a silent data gap.",
                        normalized_input_name, account_name, base_url,
                        state.get("account"), state.get("base_url"))
                state = {}

            metrics = parse_grafana_metrics(input_item.get("metrics") or default_metrics)
            if not metrics:
                logger.warning(
                    "Input %s selects no valid metric; nothing to collect.",
                    normalized_input_name)
                continue
            lookback_days = int(input_item.get("lookback_days", default_lookback_days))
            team = (input_item.get("team") or "").strip() or None
            channel = (input_item.get("channel") or "").strip() or None

            range_from, range_to = grafana_range(lookback_days)
            collection = collect_grafana_metrics(
                client, metrics, range_from, range_to, state.get("tracked", {}),
                team=team, channel=channel,
            )

            for warning in collection.warnings:
                logger.warning("Input %s: %s", normalized_input_name, warning)
            if collection.tracking_disabled:
                logger.warning(
                    "Input %s produced more than the tracked-bucket ceiling; change "
                    "detection is off and every bucket is emitted each run. Narrow "
                    "Lookback (days) or the metric selection.", normalized_input_name)
            if collection.gaps:
                # Not a warning: a gap is ordinary in a sparse tenant. It is
                # logged because "no events for that day" and "a null the input
                # deliberately did not emit as 0" look identical in the index,
                # and an operator chasing a hole in a chart needs to be able to
                # tell them apart.
                logger.info(
                    "Input %s: %d datapoint(s) had no value for their bucket (no "
                    "denominator) and were skipped rather than indexed as 0.",
                    normalized_input_name, collection.gaps)

            # WHICH instant `epoch` is was decided per response shape, not per
            # input: a series bucket carries its own day
            # (`collect_grafana_metrics`), a table row does not and is stamped
            # with the observation instant. Collapsing the two into one "stamp
            # the time" call would silently pick one of them for both. This is
            # the ONE stanza pair serving two payload shapes, and it is where
            # the previous-event defect was first measured.
            #
            # `event_payload` writes that same epoch into `rlEventTime`, FIRST
            # in the serialized object, and props.conf extracts `_time` from
            # there -- so both shapes are extractable through one rule and
            # neither has to invent a shape-specific TIME_PREFIX. This is the
            # "table rows must carry an observation field" change the A/B said
            # arm D needed; making it the same field on both shapes is what
            # lets one anchored prefix serve them.
            #
            # It is stamped HERE, at write time, and deliberately NOT inside
            # `collect_grafana_metrics`: the change-detection digest is taken
            # over the body, and a table row's observation instant moves every
            # poll, so digesting a stamped body would re-emit every table row
            # forever.
            #
            # `time=` is passed as well. It agrees with `rlEventTime` by
            # construction but it is NOT authoritative -- see `event_payload`.
            for epoch, body in collection.events:
                event_writer.write_event(
                    smi.Event(
                        data=event_payload(body, epoch),
                        index=input_item.get("index"),
                        sourcetype=sourcetype,
                        time=epoch,
                    )
                )

            # Checkpoint only after the events are written, so a crash mid-write
            # replays the window rather than skipping it. Re-delivery is
            # recoverable — the digests make it a no-op on the next poll — while
            # a bucket dropped because its digest was recorded before its event
            # was written would never be indexed at all.
            store.update(checkpoint_key, {
                "tracked": collection.tracked,
                "account": account_name,
                "base_url": base_url,
            })

            log.events_ingested(
                logger, input_name, sourcetype, len(collection.events),
                input_item.get("index"), account=account_name)
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, error_code, msg_before=error_message)

import import_declare_test  # noqa: F401  (UCC path bootstrap — must stay first)

from datetime import datetime, timezone

from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from ransomleak_client import (
    RansomleakClient, collect_audit_events, event_epoch, event_payload,
    should_verify_tls)

ADDON_NAME = "TA-ransomleak"
SOURCETYPE = "ransomleak:audit"
CHECKPOINT_COLLECTION = "TA_ransomleak_checkpoints"

# How many individually-named bad-timestamp warnings one run may log before it
# switches to a single summary line. A tenant with a systematically broken
# column would otherwise write one WARNING per event.
MAX_BAD_TIMESTAMP_WARNINGS = 5


def logger_for_input(input_name):
    return log.Logs().get_logger("{}_{}".format(ADDON_NAME.lower(), input_name))


def get_account(session_key, account_name):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-ta-ransomleak_account".format(ADDON_NAME),
    )
    return cfm.get_conf("ta-ransomleak_account").get(account_name)


def validate_input(definition: smi.ValidationDefinition):
    params = definition.parameters
    if not 0 <= int(params.get("lookback_hours", "1")) <= 999:
        raise ValueError("Lookback (hours) must be between 0 and 999.")


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)

        # Namespace the checkpoint by scheme. `normalized_input_name` strips the
        # scheme off the stanza, so `audit_events://acme` and
        # `training_state://acme` -- distinct Splunk stanzas, and naming both
        # inputs after the tenant is the obvious operator action -- collide on
        # one key in a shared collection. solnlib's `update()` REPLACES the
        # document rather than merging, and the account/base_url re-baseline
        # guard does not catch it (same account, same base URL: one URL serves
        # every tenant), so the two inputs would silently adopt and clobber each
        # other's state -- permanent skips, with the input still reporting
        # success. `phishing_events` deliberately keeps the bare key: it has
        # shipped, and re-keying it would orphan an existing install's
        # high-water mark and re-ingest its entire history.
        checkpoint_key = "audit_events/" + normalized_input_name
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

            store = checkpointer.KVStoreCheckpointer(CHECKPOINT_COLLECTION, session_key, ADDON_NAME)
            state = store.get(checkpoint_key) or {}
            if state.get("account") != account_name or state.get("base_url") != base_url:
                if state:
                    logger.warning(
                        "Input %s now points at account=%s base_url=%s (was account=%s base_url=%s); "
                        "re-baselining from scratch to avoid a silent data gap.",
                        normalized_input_name, account_name, base_url,
                        state.get("account"), state.get("base_url"))
                state = {}

            run_epoch = datetime.now(timezone.utc).timestamp()
            written = 0
            bad_timestamps = 0

            def write_page(page_events):
                """Write one page's events, then let them be collected.

                `collect_audit_events` streams a page at a time instead of
                returning the whole feed: a full-history backfill of a busy
                tenant would otherwise materialise the entire corpus (order of
                GBs) before this loop ran once, and the forwarder OOMed.
                Nothing here may retain a reference to `page_events` or the
                bound is undone.
                """
                nonlocal written, bad_timestamps
                for event in page_events:
                    # Fall back to ingest time rather than skipping the row. A
                    # timestamp this add-on cannot parse is a defect in one row;
                    # dropping the row turns it into a silent, permanently
                    # repeating gap in a security feed, while an approximate
                    # `_time` is visible and recoverable -- the event's own JSON
                    # still carries the raw `timestamp` verbatim, so nothing is
                    # fabricated. Previously `parse_iso` raised inside the
                    # per-input `try` and one bad row aborted the whole tenant
                    # feed.
                    epoch = event_epoch(event.get("timestamp"))
                    if epoch is None:
                        bad_timestamps += 1
                        if bad_timestamps <= MAX_BAD_TIMESTAMP_WARNINGS:
                            logger.warning(
                                "Input %s: audit event %s has an unusable timestamp %r; "
                                "stamping _time with ingest time instead of dropping it.",
                                normalized_input_name, event.get("id"),
                                event.get("timestamp"))
                        epoch = run_epoch
                    # `event_payload` -- not a bare `json.dumps` -- is what puts
                    # `rlEventTime` first in the serialized object, and
                    # props.conf extracts `_time` from exactly that position.
                    # The DTO's own `timestamp` is deliberately NOT the
                    # extraction source: it is emitted LAST, behind `userAgent`
                    # and an unbounded `metadata` object which may itself carry
                    # a `"timestamp"` key. `time=` below stays, and agrees by
                    # construction, but it is not authoritative -- see
                    # `event_payload`'s docstring.
                    event_writer.write_event(
                        smi.Event(
                            data=event_payload(event, epoch),
                            index=input_item.get("index"),
                            sourcetype=SOURCETYPE,
                            time=epoch,
                        )
                    )
                    written += 1

            lookback_hours = int(input_item.get("lookback_hours", "1"))
            high_water = state.get("high_water")
            seen_ids = state.get("seen_ids", [])
            cursor = state.get("cursor")

            high_water, cursor, seen_ids, warnings = collect_audit_events(
                client, high_water, cursor, seen_ids,
                lookback_hours=lookback_hours,
                sink=write_page,
            )

            # Logged after the walk rather than before the writes, because the
            # walk is what produces them.
            for warning in warnings:
                logger.warning("Input %s: %s", normalized_input_name, warning)
            if bad_timestamps > MAX_BAD_TIMESTAMP_WARNINGS:
                logger.warning(
                    "Input %s: %d further event(s) had unusable timestamps and were "
                    "stamped with ingest time.",
                    normalized_input_name, bad_timestamps - MAX_BAD_TIMESTAMP_WARNINGS)

            # Written unconditionally, not behind `if high_water:`. On an empty
            # or newly-onboarded tenant `high_water` is None forever, and that
            # guard would skip the write on every run; `high_water`, `cursor`
            # and `seen_ids` all come back unchanged when the run found
            # nothing, so writing every run cannot lose state.
            #
            # Exactly one write, strictly after every event, even though the
            # events leave during the walk. A run that dies mid-walk leaves
            # this untouched, so the next run re-reads from the last stored
            # position and re-emits -- duplicates, never a gap.
            store.update(checkpoint_key, {
                "high_water": high_water, "seen_ids": seen_ids,
                "cursor": cursor,
                "account": account_name, "base_url": base_url,
            })

            log.events_ingested(
                logger, input_name, SOURCETYPE, written,
                input_item.get("index"), account=account_name)
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(
                logger, e, "RansomLeakAuditIngestError",
                msg_before="Exception while ingesting RansomLeak audit events: ")

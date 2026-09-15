import import_declare_test  # noqa: F401  (UCC path bootstrap — must stay first)

from datetime import timezone

from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from ransomleak_client import (
    RansomleakClient, collect_events, event_payload, parse_iso,
    should_verify_tls)

ADDON_NAME = "TA-ransomleak"
SOURCETYPE = "ransomleak:phishing"
CHECKPOINT_COLLECTION = "TA_ransomleak_checkpoints"


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


def validate_input(definition: smi.ValidationDefinition):
    """Reject configuration Splunk would otherwise accept and fail on later."""
    params = definition.parameters
    lookback = int(params.get("lookback_hours", "1"))
    if lookback < 0 or lookback > 999:
        raise ValueError("Lookback (hours) must be between 0 and 999.")
    page_size = int(params.get("page_size", "1000"))
    if page_size < 1 or page_size > 10000:
        raise ValueError("Page size must be between 1 and 10000.")


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            logger.setLevel(
                conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=ADDON_NAME,
                    conf_name="ta-ransomleak_settings",
                )
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
                CHECKPOINT_COLLECTION, session_key, ADDON_NAME
            )
            state = store.get(normalized_input_name) or {}

            # The checkpoint is only meaningful for the tenant that produced it.
            # Repointing an input at a different account, or editing an
            # account's base_url, would otherwise apply a stale high-water mark
            # to a different dataset — and since the mark only moves forward,
            # every event older than it would be skipped permanently, silently,
            # with the input still reporting success. Bind identity into the
            # checkpoint and re-baseline whenever it changes.
            if state.get("account") != account_name or state.get("base_url") != base_url:
                if state:
                    logger.warning(
                        "Input %s now points at account=%s base_url=%s (was account=%s "
                        "base_url=%s); re-baselining from scratch to avoid a silent data gap.",
                        normalized_input_name,
                        account_name,
                        base_url,
                        state.get("account"),
                        state.get("base_url"),
                    )
                state = {}

            events, high_water, seen_ids = collect_events(
                client,
                state.get("high_water"),
                state.get("seen_ids", []),
                lookback_hours=int(input_item.get("lookback_hours", "1")),
                page_size=int(input_item.get("page_size", "1000")),
            )

            for event in events:
                # `occurredAt` is when the phish event happened, and it is what
                # `_time` must be. It is NOT the field props.conf extracts from:
                # it sits well past any sane lookahead in the serialized event,
                # and its position in the DTO is not this add-on's to guarantee.
                # `event_payload` re-stamps the same instant as `rlEventTime`,
                # first in the object, and props.conf reads it from there.
                # `time=` is passed as well but is NOT authoritative on Splunk
                # 10.4.2 -- see `event_payload`'s docstring.
                epoch = (parse_iso(event["occurredAt"])
                         .replace(tzinfo=timezone.utc)
                         .timestamp())
                event_writer.write_event(
                    smi.Event(
                        data=event_payload(event, epoch),
                        time=epoch,
                        index=input_item.get("index"),
                        sourcetype=SOURCETYPE,
                    )
                )

            # Checkpoint only after the events are written, so a crash mid-write
            # replays the window rather than skipping it. Re-delivery is
            # recoverable; a gap is not.
            if high_water:
                store.update(
                    normalized_input_name,
                    {
                        "high_water": high_water,
                        "seen_ids": seen_ids,
                        "account": account_name,
                        "base_url": base_url,
                    },
                )

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE,
                len(events),
                input_item.get("index"),
                account=account_name,
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "RansomLeakPhishingIngestError",
                msg_before="Exception while ingesting RansomLeak phishing events: ",
            )

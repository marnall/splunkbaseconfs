import import_declare_test  # noqa: F401  (UCC path bootstrap — must stay first)

from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from ransomleak_client import (
    RansomleakClient, collect_training_state, event_payload, observation_epoch,
    should_verify_tls)

ADDON_NAME = "TA-ransomleak"
SOURCETYPE = "ransomleak:training"
CHECKPOINT_COLLECTION = "TA_ransomleak_checkpoints"


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
    if not 1 <= int(params.get("page_size", "1000")) <= 5000:
        raise ValueError("Page size must be between 1 and 5000.")
    # Each tracked entry costs roughly 83 bytes once JSON-encoded into the
    # KV-store document's string field, so MongoDB's 16MB document cap lands the
    # real ceiling near 150,000. Past it the checkpoint save fails AFTER the
    # events are written -- so the input re-emits everything and never
    # checkpoints. 100,000 keeps a safety margin under a limit we cannot query.
    if not 1 <= int(params.get("max_tracked", "50000")) <= 100000:
        raise ValueError("Max tracked rows must be between 1 and 100000.")


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)

        # Namespace the checkpoint by scheme. `normalized_input_name` strips the
        # scheme off the stanza, so `training_state://acme` and
        # `audit_events://acme` -- distinct Splunk stanzas, and naming both
        # inputs after the tenant is the obvious operator action -- collide on
        # one key in a shared collection. solnlib's `update()` REPLACES the
        # document rather than merging, so this input's write would erase the
        # other's `high_water` (full re-ingest every interval) while the other's
        # erased this input's `tracked` (full snapshot re-emit every interval),
        # and the account/base_url re-baseline guard never fires because both
        # inputs legitimately share an account and a base URL.
        # `phishing_events` deliberately keeps the bare key: it has shipped, and
        # re-keying it would orphan an existing install's high-water mark and
        # re-ingest its entire history.
        checkpoint_key = "training_state/" + normalized_input_name
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

            changed, tracked, tracking_disabled = collect_training_state(
                client,
                state.get("tracked", {}),
                page_size=int(input_item.get("page_size", "1000")),
                max_tracked=int(input_item.get("max_tracked", "50000")),
            )
            if tracking_disabled:
                logger.warning(
                    "Input %s exceeded max_tracked; change detection is off and every row is "
                    "emitted each run. Raise max_tracked or the interval.", normalized_input_name)

            # `_time` is OBSERVATION time -- when this input saw the row change
            # -- not `assignedAt`. See `observation_epoch`'s docstring in
            # ransomleak_client.py for the full rationale; the short version is
            # that this endpoint is a state projection, so the event's subject
            # is the observation and not the enrollment's assignment instant.
            # `assignedAt`, `completedAt` and `dueAt` all still ship verbatim
            # inside the event body.
            #
            # This also retires a whole failure mode rather than defending
            # against it. `external-compliance.controller.ts` projects
            # `assignedAt: toIso(row.enrollment.assignedAt) ?? ''`, so the empty
            # string is a documented, reachable value, and parsing it used to
            # raise inside this input's single `try` and abort the WHOLE tenant
            # feed. Nothing on the write path parses a row-supplied timestamp
            # any more, so no row's contents can abort or skew the feed.
            #
            # The row carries no field describing the observation -- it is a
            # state projection -- so `event_payload` adds one: `rlEventTime`,
            # first in the serialized object, carrying exactly the epoch stamped
            # below. That is the field props.conf extracts `_time` from, on this
            # and every other sourcetype. Without it this stanza would have no
            # extractable timestamp at all and every event would take its
            # predecessor's.
            observed_epoch = observation_epoch()
            for row in changed:
                event_writer.write_event(
                    smi.Event(
                        data=event_payload(row, observed_epoch),
                        index=input_item.get("index"),
                        sourcetype=SOURCETYPE,
                        time=observed_epoch,
                    )
                )

            store.update(checkpoint_key, {
                "tracked": tracked, "account": account_name, "base_url": base_url,
            })

            log.events_ingested(
                logger, input_name, SOURCETYPE, len(changed),
                input_item.get("index"), account=account_name)
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(
                logger, e, "RansomLeakTrainingIngestError",
                msg_before="Exception while ingesting RansomLeak training state: ")

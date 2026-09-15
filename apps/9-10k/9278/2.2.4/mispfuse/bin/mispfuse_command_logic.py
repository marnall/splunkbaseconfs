"""Implementation of the ``mispfusepush`` custom search command."""
import import_declare_test  # noqa: F401

from mispfuse_lib import config as cfg
from mispfuse_lib import templates as tmpl
from mispfuse_lib.client import MispClient
from mispfuse_lib import pusher


def _opt(command, name, default=None):
    val = getattr(command, name, None)
    return default if val is None else val


def transform(command, records):
    session_key = command.metadata.searchinfo.session_key
    logger = cfg.get_logger("mispfuse.command", session_key)

    account_name = _opt(command, "account")
    template_name = _opt(command, "template", "network_ioc")

    rows = [dict(r) for r in records]

    try:
        account = cfg.get_account(session_key, account_name)
        proxies = cfg.get_proxies(session_key)
        template = tmpl.load_template(session_key, template_name)
        client = MispClient(
            account["misp_url"], account["misp_key"],
            verify_ssl=account["verify_ssl"], proxies=proxies,
        )
    except Exception as exc:
        logger.error("setup failed: %s", exc)
        yield {"_time": None, "misp_status": "error", "misp_message": str(exc),
               "_raw": "MISPFuse setup error: {}".format(exc)}
        return

    options = pusher.Options(
        grouping=_opt(command, "grouping"),
        group_field=_opt(command, "group_field"),
        event_info=_opt(command, "event_info"),
        distribution=_opt(command, "distribution"),
        threat_level_id=_opt(command, "threat_level_id"),
        analysis=_opt(command, "analysis"),
        tags=_split(_opt(command, "tags")),
        to_ids=_opt(command, "to_ids"),
        publish=_opt(command, "publish"),
    )

    try:
        results = pusher.push(rows, template, client, options, logger)
    except Exception as exc:
        logger.error("push failed: %s", exc)
        yield {"misp_status": "error", "misp_message": str(exc),
               "_raw": "MISPFuse push error: {}".format(exc)}
        return

    if not results:
        yield {"misp_status": "noop", "misp_message": "no records to push",
               "_raw": "MISPFuse: nothing to push"}
        return

    for res in results:
        yield {
            "misp_status": "success" if res.ok else "failed",
            "misp_event_id": res.event_id,
            "misp_event_uuid": res.event_uuid,
            "misp_attributes": res.count,
            "misp_message": res.message,
            "misp_instance": account_name,
            "_raw": "MISPFuse {}: event={} attrs={} ({})".format(
                "OK" if res.ok else "FAIL", res.event_id, res.count, res.message
            ),
        }


def _split(value):
    if not value:
        return None
    return [t.strip() for t in str(value).split(",") if t.strip()]

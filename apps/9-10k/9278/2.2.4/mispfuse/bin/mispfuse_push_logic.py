"""Implementation of the MISPFuse custom alert action."""
import import_declare_test  # noqa: F401

from mispfuse_lib import config as cfg
from mispfuse_lib import templates as tmpl
from mispfuse_lib.client import MispClient
from mispfuse_lib import pusher


class _HelperLogger(object):
    def __init__(self, helper):
        self._h = helper

    def info(self, msg, *a):
        self._h.log_info(msg % a if a else msg)

    def warning(self, msg, *a):
        self._h.log_warning(msg % a if a else msg)

    def error(self, msg, *a):
        self._h.log_error(msg % a if a else msg)


def validate_params(helper):
    if not helper.get_param("account"):
        helper.log_error("account is a mandatory parameter.")
        return False
    if not helper.get_param("template"):
        helper.log_error("template is a mandatory parameter.")
        return False
    return True


def process_event(helper, *args, **kwargs):
    if not validate_params(helper):
        return 3

    session_key = helper.session_key
    account_name = helper.get_param("account")
    template_name = helper.get_param("template")

    try:
        account = cfg.get_account(session_key, account_name)
        proxies = cfg.get_proxies(session_key)
        template = tmpl.load_template(session_key, template_name)
        client = MispClient(
            account["misp_url"], account["misp_key"],
            verify_ssl=account["verify_ssl"], proxies=proxies,
        )
    except Exception as exc:
        helper.log_error("MISPFuse setup failed: {}".format(exc))
        return 4

    options = pusher.Options(
        grouping=helper.get_param("grouping") or None,
        group_field=helper.get_param("group_field") or None,
        event_info=helper.get_param("event_info") or None,
        distribution=_int(helper.get_param("distribution")),
        threat_level_id=_int(helper.get_param("threat_level_id")),
        analysis=_int(helper.get_param("analysis")),
        tags=_split(helper.get_param("tags")),
        to_ids=_bool(helper.get_param("to_ids")),
        publish=_bool(helper.get_param("publish")),
    )

    rows = list(helper.get_events())
    helper.log_info(
        "MISPFuse: pushing {} row(s) to instance '{}' using template '{}'.".format(
            len(rows), account_name, template_name
        )
    )

    try:
        results = pusher.push(rows, template, client, options, _HelperLogger(helper))
    except Exception as exc:
        helper.log_error("MISPFuse push failed: {}".format(exc))
        return 5

    ok = sum(1 for r in results if r.ok)
    failed = [r for r in results if not r.ok]
    for r in failed:
        helper.log_error("MISPFuse event failed: {}".format(r.message))
    helper.log_info("MISPFuse: {} event(s) created, {} failed.".format(ok, len(failed)))
    return 0 if not failed else 6


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool(value):
    if value is None or value == "":
        return None
    return str(value).strip().lower() in ("1", "true", "t", "yes", "y")


def _split(value):
    if not value:
        return None
    return [t.strip() for t in str(value).split(",") if t.strip()]

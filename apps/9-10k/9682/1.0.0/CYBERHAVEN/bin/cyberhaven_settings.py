"""Settings and logging helpers for CYBERHAVEN's own scripts.

CYBERHAVEN has no runtime dependency on any script under TA-CYBERHAVEN/bin --
it only reads configuration values (tenant_url, api_key, loglevel) that live
in TA-CYBERHAVEN's ta-cyberhaven_settings.conf, via the same third-party
libraries (solnlib, splunklib, splunktaucclib) vendored under this app's own
lib/ directory.
"""
import json
import logging
import logging.handlers
import time
from urllib.parse import quote

from solnlib import conf_manager
from splunk.clilib import cli_common as cli
from splunk.clilib.bundle_paths import make_splunkhome_path

APP_NAME = 'CYBERHAVEN'
SETTINGS_APP = 'TA-CYBERHAVEN'
SETTINGS_CONF = 'ta-cyberhaven_settings'
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = (
    "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s "
    "file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s"
)

# KV store collection (default/collections.conf + default/transforms.conf) that records,
# per notable rule_id, the status/owner value last successfully pushed to the Cyberhaven
# platform. rule_id is a plain field rather than the KV store's own _key, since one
# Cyberhaven incident can be linked to more than one notable over time.
SYNC_STATE_COLLECTION = 'cyberhaven_sync_state'


def get_notable_automation_settings(session_key):
    """Read the tenant URL and (decrypted) API key from TA-CYBERHAVEN's configuration.

    Returns a dict with 'tenant_url' and 'api_key', defaulting each to ''.
    """
    realm = "__REST_CREDENTIAL__#{}#configs/conf-{}".format(SETTINGS_APP, SETTINGS_CONF)
    cfm = conf_manager.ConfManager(session_key, SETTINGS_APP, realm=realm)
    conf = cfm.get_conf(SETTINGS_CONF)
    hec_settings = conf.get('hec_settings')
    notable_automation = conf.get('notable_automation')
    return {
        'tenant_url': (hec_settings.get('tenant_url') or '').strip().strip('/'),
        'api_key': (notable_automation.get('api_key') or '').strip(),
    }


def get_proxy_settings(session_key):
    """Read TA-CYBERHAVEN's [proxy] stanza and return a requests-style proxies dict.

    Returns None if proxying is disabled or Host/Port aren't configured, so callers can
    pass the result straight through to requests as `proxies=` with no None-check dance.
    """
    realm = "__REST_CREDENTIAL__#{}#configs/conf-{}".format(SETTINGS_APP, SETTINGS_CONF)
    cfm = conf_manager.ConfManager(session_key, SETTINGS_APP, realm=realm)
    conf = cfm.get_conf(SETTINGS_CONF)
    try:
        proxy = conf.get('proxy')
    except Exception:
        return None

    if str(proxy.get('proxy_enabled', '0')).strip().lower() not in ('1', 'true'):
        return None

    host = (proxy.get('proxy_url') or '').strip()
    port = (proxy.get('proxy_port') or '').strip()
    if not host or not port:
        return None

    username = (proxy.get('proxy_username') or '').strip()
    password = (proxy.get('proxy_password') or '').strip()
    userinfo = ''
    if username:
        userinfo = quote(username, safe='')
        if password:
            userinfo += f":{quote(password, safe='')}"
        userinfo += '@'

    # "http://" here is the scheme used to talk to the proxy itself (only "http" proxy_type
    # is supported), not the scheme of the request being proxied -- every call in this app
    # goes to https://<tenant_url>/public/v2/..., so the actual traffic to Cyberhaven stays
    # fully TLS-encrypted end-to-end through the CONNECT tunnel regardless of this value.
    proxy_url = f"http://{userinfo}{host}:{port}"  # NOSONAR
    return {"http": proxy_url, "https": proxy_url}


def get_log_level():
    """Read the loglevel from TA-CYBERHAVEN's [logging] stanza via a direct conf-file
    read (splunk.clilib), same as TA-CYBERHAVEN's own logger_manager.py -- no session
    key needed, so this is safe to call at module-import time.

    Also used by the alert action scripts' ModularAlertBase.get_log_level() override
    (see cyberhaven_update_status.py / cyberhaven_update_owner.py) so the framework's
    own "modalert" logger respects this same setting, instead of going through
    splunktaucclib's UCC-style Setup_Util.get_log_level(), which looks for a
    globalConfig.json this app doesn't ship (it isn't built with ucc-gen) and always
    logs "Global config JSON file not found!" before falling back to INFO.
    """
    try:
        cfg = cli.getConfStanza(SETTINGS_CONF, 'logging')
        level_name = str(cfg.get('loglevel')).upper()
        return getattr(logging, level_name, DEFAULT_LOG_LEVEL)
    except Exception:
        return DEFAULT_LOG_LEVEL


def get_logger(file_name):
    """Return a rotating-file logger under CYBERHAVEN's own log file name."""
    logger_name = f"{APP_NAME}_{file_name}"
    logger = logging.getLogger(logger_name)
    logger.propagate = False
    logger.setLevel(get_log_level())

    if not logger.handlers:
        log_file = make_splunkhome_path(["var", "log", "splunk", f"{logger_name}.log"])
        handler = logging.handlers.RotatingFileHandler(log_file, mode="a", maxBytes=25000000, backupCount=10)
        handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        logger.addHandler(handler)

    return logger


def _kvstore_path(suffix=""):
    return f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{SYNC_STATE_COLLECTION}{suffix}"


def get_sync_state(session_key, rule_id):
    """Return the stored cyberhaven_sync_state row for this notable's rule_id, or None.

    Best-effort: any REST/parse failure is treated the same as "no row yet" rather than
    raised, since a KV store hiccup here should never block a sync attempt. Logs the
    outcome either way (found / not found / query failed) so a silent KV store failure
    doesn't look identical to "no prior sync state" when reading these logs later.
    """
    import splunk.rest as rest

    logger = get_logger("sync_state")
    if not rule_id:
        return None
    try:
        _resp, content = rest.simpleRequest(
            _kvstore_path(),
            sessionKey=session_key,
            getargs={"query": json.dumps({"rule_id": rule_id})},
            method="GET",
            raiseAllErrors=True,
        )
        rows = json.loads(content)
        if rows:
            logger.info(f"get_sync_state: found existing row for rule_id={rule_id} (_key={rows[0].get('_key')}).")
            return rows[0]
        logger.info(f"get_sync_state: no existing row for rule_id={rule_id}.")
        return None
    except Exception as e:
        logger.warning(f"get_sync_state: KV store query failed for rule_id={rule_id}: {e}")
        return None


def upsert_sync_state(session_key, rule_id, cyberhaven_incident_id, **fields):
    """Record what was last successfully synced to the Cyberhaven platform for a notable.

    Updates the existing cyberhaven_sync_state row for this rule_id if one exists,
    otherwise inserts a new one. Best-effort and non-blocking: failures are logged and
    swallowed so a KV store write hiccup never fails the adaptive response action itself
    (worst case, the next run re-sends an update Cyberhaven already has). Logs the outcome
    either way so a silent write failure doesn't look identical to a successful one.
    """
    import splunk.rest as rest

    logger = get_logger("sync_state")
    if not rule_id:
        logger.warning("upsert_sync_state called with no rule_id; skipping.")
        return

    # KV store's update-by-_key POST is a full document replace, not a partial patch. Start
    # from whatever fields are already on the row (e.g. synced_status/synced_close_reason
    # written by cyberhaven_update_status) so a caller that only knows about its own fields
    # (e.g. cyberhaven_update_owner only ever passes synced_owner) doesn't wipe them out --
    # otherwise, whichever AR writes this rule_id second always erases what the other AR
    # wrote, regardless of timing.
    existing = get_sync_state(session_key, rule_id)
    body = {k: v for k, v in (existing or {}).items() if k not in ("_key", "_user")}
    body["rule_id"] = rule_id
    body["cyberhaven_incident_id"] = cyberhaven_incident_id
    body["last_synced_time"] = time.time()
    body.update(fields)

    try:
        if existing and existing.get("_key"):
            resp, content = rest.simpleRequest(
                _kvstore_path(f"/{existing['_key']}"),
                sessionKey=session_key,
                jsonargs=json.dumps(body),
                method="POST",
                raiseAllErrors=True,
            )
            logger.info(
                f"upsert_sync_state: updated existing row _key={existing['_key']} for rule_id={rule_id} "
                f"with {fields} (http_status={resp.get('status')})."
            )
        else:
            resp, content = rest.simpleRequest(
                _kvstore_path(),
                sessionKey=session_key,
                jsonargs=json.dumps(body),
                method="POST",
                raiseAllErrors=True,
            )
            logger.info(
                f"upsert_sync_state: inserted new row for rule_id={rule_id} with {fields} "
                f"(http_status={resp.get('status')}, response={content})."
            )
    except Exception as e:
        logger.warning(f"Failed to record sync state for rule_id={rule_id}: {e}")

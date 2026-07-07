#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import re
import json

import random
import time
import hashlib
import logging
import threading
import configparser
from logging.handlers import RotatingFileHandler

# Networking and URL handling imports
import requests
from requests.structures import CaseInsensitiveDict
from urllib.parse import urlencode
import urllib.parse
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))

# import Splunk libs
import splunklib.client as client
import splunklib.results as results

# import trackme libs
from trackme_libs_licensing import trackme_check_license

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces, trackme_parse_describe_flag_from_payload

# import trackme libs croniter
from trackme_libs_croniter import validate_cron_schedule

# import the per-request effective logger
from trackme_libs_logging import get_effective_logger

# logging:
# To avoid overriding the logging destination of callers, the libs do not set
# any logging definition of their own. Trace calls go through
# get_effective_logger(): in a REST-handler request this resolves to the
# calling handler's named per-handler logger (bound by RESTHandler.handle()),
# so lib traces land in that handler's log file with their tenant_id context;
# in a custom-command process it resolves to the root logger the command
# configured at startup. This replaced bare logging.<verb>() calls, which only
# reached a useful destination while REST handlers redirected the root logger
# (the leak-prone, process-global pattern removed in PR #1712).


# cd context manager
class cd:
    """Context manager for changing the current working directory"""

    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


class JSONFormatter(logging.Formatter):
    def __init__(self, *args, timestamp=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_timestamp = timestamp

    def format(self, record):

        log_record = {
            "time": self.custom_timestamp if self.custom_timestamp else time.time(),
        }

        unwanted_attrs = set(
            [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "taskName",
            ]
        )

        for key, value in record.__dict__.items():
            if (
                key not in log_record
                and not key.startswith("_")
                and key not in unwanted_attrs
            ):
                log_record[key] = value

        return json.dumps(log_record)


def trackme_parse_describe_flag(request_info):
    """
    Strict, truthy-string-safe parser for the ``describe=true`` flag on REST
    handler requests (issue #1055).

    Returns True only when the request body JSON contains ``describe`` as
    boolean ``true`` or as a string that matches ``true`` (case-insensitive,
    stripped). Any other string (including ``"false"``) or non-bool value
    yields False so ``if describe:`` is never fooled by Python string truthiness.
    """
    try:
        return trackme_parse_describe_flag_from_payload(
            str(request_info.raw_args["payload"])
        )
    except Exception:
        return False


def extract_keys_list(resp_dict, default=None):
    """
    Extract ``keys_list`` from a REST request body, accepting ``object_id``
    as an alias.

    Defensive against small-model AI assistants (concierge / advisor MCP
    tool calls, ad-hoc agent prompts) that confuse the UI-facing
    ``object_id`` field — which in TrackMe's data model already IS the
    SHA256 ``_key`` value — with the backend's ``keys_list`` parameter
    name. Without this helper, the LLM sends the right *value* under the
    wrong *field name* and the call fails the parameter check.

    Acceptance order:

      1. ``keys_list`` (preferred, explicit contract)
      2. ``object_id`` (alias; an INFO log line records the use so we
         can later measure how often the AI surface needs the alias)

    If both are present, ``keys_list`` wins (explicit beats alias).

    The returned shape **matches what was in the request body** — string
    (incl. comma-separated CSV) or list. Downstream handlers already do
    ``if not isinstance(keys_list, list): keys_list = keys_list.split(",")``
    to normalize, so we leave that contract untouched.

    Args:
        resp_dict: parsed JSON request body (dict).
        default: returned when neither ``keys_list`` nor ``object_id`` is
                 present / non-empty. Defaults to ``None`` to match the
                 current ``resp_dict.get("keys_list", None)`` idiom.

    Returns:
        The raw ``keys_list`` value (str | list), or the ``object_id``
        value when keys_list is missing, or ``default``.
    """
    raw = resp_dict.get("keys_list")
    if raw in (None, "", []):
        alias = resp_dict.get("object_id")
        if alias not in (None, "", []):
            get_effective_logger().info(
                f'function=extract_keys_list, '
                f'accepted_object_id_alias_for_keys_list="true", '
                f'value_type="{type(alias).__name__}"'
            )
            return alias
        return default
    return raw


def trackme_reqinfo(session_key, splunkd_uri):
    """
    Retrieve request info & settings with automatic retry logic.
    """

    # Ensure splunkd_uri starts with "https://"
    if not splunkd_uri.startswith("https://"):
        splunkd_uri = f"https://{splunkd_uri}"

    # Build header and target URL
    headers = CaseInsensitiveDict()
    headers["Authorization"] = f"Splunk {session_key}"
    headers["Content-Type"] = "application/json"
    target_url = f"{splunkd_uri}/services/trackme/v2/configuration/request_info"

    # Create a requests session for better performance
    session = requests.Session()
    session.headers.update(headers)

    # Retry configuration
    max_retries = 5
    base_delay = 2  # seconds
    
    for attempt in range(max_retries + 1):
        try:
            # Use a context manager to handle the request
            with session.get(target_url, verify=False) as response:
                if response.ok:
                    get_effective_logger().debug(f'Success retrieving conf on attempt {attempt + 1}, data="{response}"')
                    response_json = response.json()
                    return response_json
                else:
                    error_message = f'Failed to retrieve conf on attempt {attempt + 1}, status_code={response.status_code}, response_text="{response.text}"'
                    
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff: 2, 4, 8, 16, 32 seconds
                        get_effective_logger().warning(f'{error_message}. Retrying in {delay} seconds...')
                        time.sleep(delay)
                        continue
                    else:
                        get_effective_logger().error(f'{error_message}. Max retries ({max_retries}) exceeded.')
                        raise Exception(error_message)

        except Exception as e:
            error_message = f'Failed to retrieve conf on attempt {attempt + 1}, exception="{str(e)}"'
            
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 2, 4, 8, 16, 32 seconds
                get_effective_logger().warning(f'{error_message}. Retrying in {delay} seconds...')
                time.sleep(delay)
                continue
            else:
                get_effective_logger().error(f'{error_message}. Max retries ({max_retries}) exceeded.')
                raise Exception(error_message)


def trackme_get_server_time_info(source_tag="direct"):
    """
    Return a snapshot of the current Splunk server local time as seen by
    the Python process that invokes this function.

    This helper is deliberately *simple*: it just calls
    ``datetime.now().astimezone()`` and formats the result. The real
    correctness concern is **where** it gets invoked from, not what it
    does internally.

    Splunk propagates each authenticated user's timezone preference
    (``user-prefs.conf → general.tz``) into the REST handler's Python
    process environment. That means calling this helper *directly*
    from a REST handler executed under a user's HTTP session returns
    the caller's preferred TZ (e.g. ``BST``) instead of splunkd's
    system TZ (e.g. ``UTC``), which is the frame the decision maker
    actually uses.

    The correct way to get a system-user frame is for the REST handler
    to make an **internal HTTP call to another TrackMe endpoint** using
    the system authtoken, causing splunkd to dispatch the handler in a
    system-user context. See ``get_request_info`` in
    ``trackme_rest_handler_configuration.py`` for that indirection:
    it calls back into ``get_server_time`` on the same Configuration
    handler via ``service.get(...)``, which runs the helper in a
    clean system-user context.

    Arguments:
        source_tag: diagnostic string returned in the ``source`` field
            so callers can tell whether they invoked the helper
            directly (potentially polluted TZ) or via the internal
            system-authed path. Expected values:
                - "direct"                — called in the current
                                             REST handler's process;
                                             TZ may reflect the caller's
                                             user-prefs.
                - "system_authed_call"    — called via the internal
                                             get_server_time endpoint
                                             through a system_authtoken
                                             service.get(); TZ reflects
                                             splunkd's system frame.
                - "direct_fallback"       — caller attempted the system
                                             path, it failed, and this
                                             is the degraded fallback.
                Other values may be used for future paths.

    Returns a dict matching the ``ServerTimeInfo`` contract consumed by
    the shared ``<ServerTimeBanner>`` in ``@splunk/trackme-notifications``.
    """

    from datetime import datetime, timedelta

    now_naive = datetime.now()
    dt_aware = now_naive.astimezone()

    utc_off = dt_aware.utcoffset() or timedelta(0)
    total_seconds = int(utc_off.total_seconds())
    utc_offset_minutes = total_seconds // 60
    sign = "+" if total_seconds >= 0 else "-"
    abs_total = abs(total_seconds)
    hh = abs_total // 3600
    mm = (abs_total % 3600) // 60
    utc_offset_display = f"{sign}{hh:02d}:{mm:02d}"

    tz_name = ""
    try:
        if dt_aware.tzinfo is not None:
            tz_name = dt_aware.tzinfo.tzname(dt_aware) or ""
    except Exception:
        tz_name = ""
    # Fallback readable label for a zero offset with no tzname.
    if not tz_name and utc_offset_minutes == 0:
        tz_name = "UTC"

    return {
        "iso": dt_aware.isoformat(timespec="seconds"),
        "epoch": int(dt_aware.timestamp()),
        "tz_name": tz_name,
        "utc_offset_minutes": utc_offset_minutes,
        "utc_offset_display": utc_offset_display,
        "weekday": dt_aware.weekday(),
        "hour": dt_aware.hour,
        "source": source_tag,
    }


def trackme_getloglevel(system_authtoken, splunkd_port):
    """
    Simply get and return the loglevel with elevated privileges to avoid code duplication
    """

    # Get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=splunkd_port,
        token=system_authtoken,
        timeout=600,
    )

    # set loglevel
    loglevel = "INFO"
    conf_file = "trackme_settings"
    confs = service.confs[str(conf_file)]
    for stanza in confs:
        if stanza.name == "logging":
            for stanzakey, stanzavalue in stanza.content.items():
                if stanzakey == "loglevel":
                    loglevel = stanzavalue

    return loglevel


def trackme_getloglevel_from_service(service):
    """
    Get and return the loglevel using an existing Splunk service connection.
    This avoids creating a redundant service connection when one is already available.
    
    :param service: An existing Splunk SDK Service object already connected.
    :return: The log level string (e.g., "INFO", "DEBUG", "WARNING", "ERROR").
    """

    loglevel = "INFO"
    try:
        conf_file = "trackme_settings"
        confs = service.confs[str(conf_file)]
        for stanza in confs:
            if stanza.name == "logging":
                for stanzakey, stanzavalue in stanza.content.items():
                    if stanzakey == "loglevel":
                        loglevel = stanzavalue
                break  # Found the logging stanza, no need to continue
    except Exception as e:
        get_effective_logger().warning(
            f'trackme_getloglevel_from_service failed to read loglevel, defaulting to INFO, exception="{str(e)}"'
        )

    return loglevel


def trackme_reqinfo_from_service(service):
    """
    Retrieve TrackMe configuration directly from an existing Splunk service connection.
    This avoids the HTTP roundtrip of calling the /services/trackme/v2/configuration/request_info endpoint.
    
    Returns the same trackme_conf dict structure that the REST endpoint returns,
    enabling drop-in replacement for callers that only need trackme_conf.
    
    :param service: An existing splunklib.client.Service object connected to Splunk.
    :return: A dictionary with 'trackme_conf' key containing all trackme_settings.conf stanzas.
    """

    trackme_conf = {}

    try:
        conf_file = "trackme_settings"
        confs = service.confs[str(conf_file)]

        for stanza in confs:
            # Create a sub-dictionary for the current stanza name if it doesn't exist
            if stanza.name not in trackme_conf:
                trackme_conf[stanza.name] = {}

            # Store key-value pairs from the stanza content
            for stanzakey, stanzavalue in stanza.content.items():
                if stanzavalue:
                    trackme_conf[stanza.name][stanzakey] = stanzavalue
                else:
                    trackme_conf[stanza.name][stanzakey] = ""

    except Exception as e:
        error_message = f'trackme_reqinfo_from_service failed to read trackme_settings.conf, exception="{str(e)}"'
        get_effective_logger().error(error_message)
        raise Exception(error_message)

    return {"trackme_conf": trackme_conf}


# Default splunkd timeout in seconds, used for local splunkd REST API calls and SDK connections
SPLUNKD_TIMEOUT_DEFAULT = 300


def get_splunkd_timeout(trackme_conf=None, reqinfo=None):
    """
    Extract the splunkd_timeout value from a TrackMe configuration dictionary.
    
    Accepts either:
    - trackme_conf: the raw trackme_conf dict (e.g. from trackme_reqinfo_from_service)
    - reqinfo: the full reqinfo dict (e.g. from trackme_reqinfo), which contains trackme_conf under the key "trackme_conf"
    
    Returns an integer timeout value in seconds, defaulting to SPLUNKD_TIMEOUT_DEFAULT if not found or invalid.
    """

    conf = None
    if reqinfo is not None:
        conf = reqinfo.get("trackme_conf", {})
    elif trackme_conf is not None:
        # If trackme_conf has a nested "trackme_conf" key (from trackme_reqinfo_from_service), unwrap it
        if "trackme_conf" in trackme_conf:
            conf = trackme_conf["trackme_conf"]
        else:
            conf = trackme_conf

    if conf is not None:
        try:
            timeout_val = int(conf.get("trackme_general", {}).get("splunkd_timeout", SPLUNKD_TIMEOUT_DEFAULT))
            # Clamp to valid range
            if timeout_val < 30:
                timeout_val = 30
            elif timeout_val > 600:
                timeout_val = 600
            return timeout_val
        except (ValueError, TypeError, AttributeError):
            pass

    return SPLUNKD_TIMEOUT_DEFAULT


def trackme_vtenant_account_from_service(service, tenant_id):
    """
    Retrieve vtenant-specific settings directly from an existing Splunk service connection.
    This avoids the HTTP roundtrip of calling the /services/trackme/v2/vtenants/vtenants_accounts endpoint.
    
    Replicates the same logic as post_vtenants_accounts in trackme_rest_handler_vtenants_user.py,
    including the mloutliers allowlist processing.
    
    :param service: An existing splunklib.client.Service object connected to Splunk.
    :param tenant_id: The tenant identifier to retrieve settings for.
    :return: A dictionary with the vtenant account settings for the specified tenant_id.
    :raises Exception: If the tenant_id is not found or conf cannot be read.
    """

    try:
        conf_file = "trackme_vtenants"
        confs = service.confs[str(conf_file)]
    except Exception as e:
        error_message = f'trackme_vtenant_account_from_service failed to read trackme_vtenants.conf, exception="{str(e)}"'
        get_effective_logger().error(error_message)
        raise Exception(error_message)

    trackme_vtenant_conf = {}

    for stanza in confs:
        # Only process the requested tenant_id stanza
        if stanza.name == str(tenant_id):
            trackme_vtenant_conf[stanza.name] = {}
            for stanzakey, stanzavalue in stanza.content.items():
                trackme_vtenant_conf[stanza.name][stanzakey] = stanzavalue

            # Check that alias is defined, otherwise default to stanza.name
            if not trackme_vtenant_conf[stanza.name].get("alias"):
                trackme_vtenant_conf[stanza.name]["alias"] = stanza.name

            #
            # mloutliers processing:
            # For each component in mloutliers_allowlist, define mloutliers_<component>
            # which gets 0 if mloutliers is disabled, 0 if enabled and not in the list, 1 if enabled and in the list
            #
            mloutliers = int(
                trackme_vtenant_conf[stanza.name].get("mloutliers", 0)
            )

            outliers_allowlist = trackme_vtenant_conf[stanza.name].get(
                "mloutliers_allowlist", "dsm,dhm,flx,wlk,fqm"
            )

            outliers_components = ["dsm", "dhm", "flx", "wlk", "fqm"]
            mloutliers_set = set(outliers_allowlist.split(","))

            mloutliers_dict = {
                f"mloutliers_{comp}": (
                    1 if comp in mloutliers_set and mloutliers == 1 else 0
                )
                for comp in outliers_components
            }

            trackme_vtenant_conf[stanza.name]["mloutliers_dsm"] = mloutliers_dict["mloutliers_dsm"]
            trackme_vtenant_conf[stanza.name]["mloutliers_dhm"] = mloutliers_dict["mloutliers_dhm"]
            trackme_vtenant_conf[stanza.name]["mloutliers_flx"] = mloutliers_dict["mloutliers_flx"]
            trackme_vtenant_conf[stanza.name]["mloutliers_fqm"] = mloutliers_dict["mloutliers_fqm"]
            trackme_vtenant_conf[stanza.name]["mloutliers_wlk"] = mloutliers_dict["mloutliers_wlk"]

            break  # Found the tenant, no need to continue

    if tenant_id not in trackme_vtenant_conf:
        error_message = f'trackme_vtenant_account_from_service, tenant_id="{tenant_id}" not found in trackme_vtenants.conf'
        get_effective_logger().error(error_message)
        raise Exception(error_message)

    return trackme_vtenant_conf[tenant_id]


def trackme_get_version(service, log_context=None):
    """
    Get TrackMe version from app configuration with fallback to file-based reading.
    
    This function handles permission issues that occur when DB Connect is installed
    and the user has limited privileges. When iterating over app_confs, it tries to
    access all apps including DB Connect which requires special capabilities
    ($db_connect_read_app_conf$). Falls back to reading app.conf file directly.
    
    Args:
        service: Splunk service object (from splunklib.client)
        log_context: Optional dictionary with context for logging (e.g., {'tenant_id': '...', 'instance_id': '...'})
    
    Returns:
        str: TrackMe version string, or None if not found
    """
    trackme_version = None
    
    try:
        app_confs = service.confs["app"]
        for stanza in app_confs:
            if stanza.name == "id":
                for stanzakey, stanzavalue in stanza.content.items():
                    if stanzakey == "version":
                        trackme_version = stanzavalue
                        break
                if trackme_version:
                    break
    except Exception as e:
        # Handle permission errors when DB Connect is installed and user has limited privileges
        # When iterating over app_confs, it tries to access all apps including DB Connect which requires
        # special capabilities ($db_connect_read_app_conf$). Fall back to reading app.conf file directly.
        log_msg = "failed to retrieve trackme version via service API (likely due to DB Connect permission requirements)"
        if log_context:
            log_msg = f'{log_context.get("context_prefix", "")} {log_msg}'.strip()
        get_effective_logger().debug(f'{log_msg}, exception="{str(e)}", trying file-based fallback')
        
        try:
            # Read from the app.conf file directly as a fallback using configparser
            # This is more robust than manual parsing and handles various INI file formats
            app_conf_path = os.path.join(splunkhome, "etc", "apps", "trackme", "default", "app.conf")
            if os.path.exists(app_conf_path):
                config = configparser.ConfigParser()
                # Preserve case sensitivity for section and option names
                config.optionxform = str
                try:
                    config.read(app_conf_path)
                    # Get version from [id] section
                    if config.has_section('id') and config.has_option('id', 'version'):
                        trackme_version = config.get('id', 'version').strip()
                except (configparser.Error, ValueError) as config_error:
                    log_msg = f"failed to parse app.conf using configparser: {str(config_error)}"
                    if log_context:
                        log_msg = f'{log_context.get("context_prefix", "")} {log_msg}'.strip()
                    get_effective_logger().debug(log_msg)
            if not trackme_version:
                log_msg = "failed to retrieve trackme version from file, version will be None"
                if log_context:
                    log_msg = f'{log_context.get("context_prefix", "")} {log_msg}'.strip()
                get_effective_logger().warning(log_msg)
        except Exception as e2:
            log_msg = f'failed to retrieve trackme version via file fallback, exception="{str(e2)}", version will be None'
            if log_context:
                log_msg = f'{log_context.get("context_prefix", "")} {log_msg}'.strip()
            get_effective_logger().warning(log_msg)
            # Continue with None version - the schema_version_required function should handle this
    
    return trackme_version


def trackme_vtenant_account(session_key, splunkd_uri, tenant_id):
    """
    Retrieve vtenant specific settings.
    """

    # Ensure splunkd_uri starts with "https://"
    if not splunkd_uri.startswith("https://"):
        splunkd_uri = f"https://{splunkd_uri}"

    # Build header and target URL
    headers = CaseInsensitiveDict()
    headers["Authorization"] = f"Splunk {session_key}"
    headers["Content-Type"] = "application/json"
    target_url = f"{splunkd_uri}/services/trackme/v2/vtenants/vtenants_accounts"

    # Create a requests session for better performance
    session = requests.Session()
    session.headers.update(headers)

    try:
        # Use a context manager to handle the request
        with session.post(
            target_url, data=json.dumps({"tenant_id": tenant_id}), verify=False
        ) as response:
            if response.ok:
                get_effective_logger().debug(f'Success retrieving conf, data="{response}"')
                response_json = response.json()
                return response_json
            else:
                error_message = f'tenant_id="{tenant_id}", failed to retrieve conf, status_code={response.status_code}, response_text="{response.text}"'
                get_effective_logger().error(error_message)
                raise Exception(error_message)

    except Exception as e:
        error_message = f'tenant_id="{tenant_id}", failed to retrieve conf, exception="{str(e)}"'
        get_effective_logger().error(error_message)
        raise Exception(error_message)


def is_ai_feed_lifecycle_covering(vtenant_account, component):
    """Return True if the AI Feed Lifecycle Advisor (under the Components
    Advisor umbrella) is enabled for this tenant AND its component list
    includes the given component.

    Used to enforce a mutex between the legacy mechanical Adaptive Delay
    feature (``trackmesplkadaptivedelay``) and the AI-driven Feed Lifecycle
    Advisor — both manage DSM/DHM delay thresholds, and only one can be
    authoritative at a time. When this helper returns True the legacy
    feature is dormant:

      * Save-time hook (``trackme_rh_vtenants_handler``) flips both
        ``adaptive_delay`` and ``variable_delay_auto_review`` to 0 when
        the AI advisor is turned on for DSM or DHM.
      * Runtime gates in ``trackmesplkadaptivedelay`` and
        ``trackmesplkvariabledelayreview`` short-circuit when this
        returns True (defence-in-depth: covers direct KV pokes and any
        API path that bypasses the save-time hook).
      * Configuration Guardian check ``ai_feed_lifecycle_delay_conflict``
        raises a warning if drift between the two layers is detected.

    Mode (``ai_components_advisor_mode``) is intentionally ignored — the
    admin has signalled intent to manage delay via AI regardless of
    whether the advisor currently runs in ``inspect`` or ``act`` mode.

    Args:
        vtenant_account: dict returned by ``trackme_vtenant_account()``
            (or the equivalent payload off ``trackmeload``).
        component: ``"dsm"`` or ``"dhm"`` (lowercase short code).

    Returns:
        bool — True if AI Feed Lifecycle Advisor is the authority for
        this component on this tenant.
    """
    try:
        master = int(vtenant_account.get("ai_components_advisor_enabled", 0) or 0)
    except (TypeError, ValueError):
        master = 0
    if master != 1:
        return False
    csv = str(vtenant_account.get("ai_components_advisor_list", "") or "").strip()
    if not csv:
        return False
    covered = {c.strip().lower() for c in csv.split(",") if c.strip()}
    return component.lower() in covered


def trackme_vtenant_component_info(session_key, splunkd_uri, tenant_id):
    """
    Retrieve vtenant component information.
    """

    # Ensure splunkd_uri starts with "https://"
    if not splunkd_uri.startswith("https://"):
        splunkd_uri = f"https://{splunkd_uri}"

    # Build header and target URL
    headers = CaseInsensitiveDict()
    headers["Authorization"] = f"Splunk {session_key}"
    headers["Content-Type"] = "application/json"
    target_url = f"{splunkd_uri}/services/trackme/v2/configuration/components"

    # Create a requests session for better performance
    session = requests.Session()
    session.headers.update(headers)

    try:
        # Use a context manager to handle the request
        with session.post(
            target_url, data=json.dumps({"tenant_id": tenant_id}), verify=False
        ) as response:
            if response.ok:
                get_effective_logger().debug(f'Success retrieving conf, data="{response}"')
                response_json = response.json()
                return response_json
            else:
                error_message = f'tenant_id="{tenant_id}", failed to retrieve conf, status_code={response.status_code}, response_text="{response.text}"'
                get_effective_logger().error(error_message)
                raise Exception(error_message)

    except Exception as e:
        error_message = f'tenant_id="{tenant_id}", failed to retrieve conf, exception="{str(e)}"'
        get_effective_logger().error(error_message)
        raise Exception(error_message)


def trackme_idx_for_tenant(session_key, splunkd_uri, tenant_id):
    """
    Retrieve request info & settings.
    """

    # Ensure splunkd_uri starts with "https://"
    if not splunkd_uri.startswith("https://"):
        splunkd_uri = f"https://{splunkd_uri}"

    # Build header and target URL
    headers = CaseInsensitiveDict()
    headers["Authorization"] = f"Splunk {session_key}"
    headers["Content-Type"] = "application/json"
    target_url = f"{splunkd_uri}/services/trackme/v2/vtenants/tenant_idx_settings"

    # Create a requests session for better performance
    session = requests.Session()
    session.headers.update(headers)

    try:
        # Use a context manager to handle the request
        with session.post(
            target_url, data=json.dumps({"tenant_id": tenant_id}), verify=False
        ) as response:
            if response.ok:
                get_effective_logger().debug(f'Success retrieving conf, data="{response}"')
                response_json = response.json()
                return response_json
            else:
                error_message = f'tenant_id="{tenant_id}", failed to retrieve conf, status_code={response.status_code}, response_text="{response.text}"'
                get_effective_logger().error(error_message)
                raise Exception(error_message)

    except Exception as e:
        error_message = f'tenant_id="{tenant_id}", failed to retrieve conf, exception="{str(e)}"'
        get_effective_logger().error(error_message)
        raise Exception(error_message)


def trackme_gen_state(index, source, sourcetype, event):
    try:
        # Create a dedicated logger for state events
        state_logger = logging.getLogger("trackme.state.events")
        state_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not state_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_state_events.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            logging.Formatter.converter = time.gmtime
            filehandler.setFormatter(formatter)
            state_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            state_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in state_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_state_events.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                logging.Formatter.converter = time.gmtime
                filehandler.setFormatter(formatter)
                state_logger.addHandler(filehandler)

        # if the event is a string, convert it to a dictionary
        if isinstance(event, str):
            event = json.loads(event)

        # if the event_id is not in the event, generate it
        if "event_id" not in event:
            event["event_id"] = hashlib.sha256(json.dumps(event).encode()).hexdigest()

        # log the event
        state_logger.info(
            "TrackMe State Events",
            extra={
                "target_index": index,
                "target_sourcetype": sourcetype,
                "target_source": source,
                "event": json.dumps(event),
            },
        )

    except Exception as e:
        raise Exception(str(e))


#
# remote account connectivity
#


def is_reachable(session, url, timeout=15):
    try:
        session.get(url, timeout=timeout, verify=False)
        return True, None
    except Exception as e:
        return False, str(e)


def is_reachable_with_retry(session, url, timeout, retry_config, is_reachable_func=None):
    """
    Check if URL is reachable with retry logic and exponential backoff.
    
    retry_config should contain:
    - retry_enabled: bool (or int 0/1 or str)
    - retry_max_total_time: int/float (seconds)
    - retry_initial_delay: int/float (seconds)
    - retry_backoff_multiplier: float
    - retry_max_attempts: int
    
    is_reachable_func: Optional function to use for reachability checks.
                      If None, uses the module-level is_reachable function.
    """
    # Use provided function or default to module-level is_reachable
    if is_reachable_func is None:
        is_reachable_func = is_reachable
    
    # Check if retries are enabled (handle both bool and int 0/1)
    retry_enabled = retry_config.get('retry_enabled', True)
    if isinstance(retry_enabled, str):
        retry_enabled = retry_enabled in ('1', 'true', 'True', 'yes', 'Yes')
    elif isinstance(retry_enabled, int):
        retry_enabled = retry_enabled == 1
    
    if not retry_enabled:
        # If retries disabled, use original behavior
        return is_reachable_func(session, url, timeout)
    
    # Get retry configuration with defaults, handling empty strings and invalid values
    try:
        max_total_time_val = retry_config.get('retry_max_total_time', 30)
        max_total_time = float(max_total_time_val) if max_total_time_val and str(max_total_time_val).strip() else 30.0
    except (ValueError, TypeError):
        max_total_time = 30.0
    
    try:
        initial_delay_val = retry_config.get('retry_initial_delay', 2)
        initial_delay = float(initial_delay_val) if initial_delay_val and str(initial_delay_val).strip() else 2.0
    except (ValueError, TypeError):
        initial_delay = 2.0
    
    try:
        backoff_multiplier_val = retry_config.get('retry_backoff_multiplier', 2.0)
        backoff_multiplier = float(backoff_multiplier_val) if backoff_multiplier_val and str(backoff_multiplier_val).strip() else 2.0
    except (ValueError, TypeError):
        backoff_multiplier = 2.0
    
    try:
        max_attempts_val = retry_config.get('retry_max_attempts', 10)
        max_attempts = int(max_attempts_val) if max_attempts_val and str(max_attempts_val).strip() else 10
    except (ValueError, TypeError):
        max_attempts = 10
    
    # Ensure reasonable values
    max_total_time = max(1.0, max_total_time)
    initial_delay = max(0.1, initial_delay)
    backoff_multiplier = max(1.0, backoff_multiplier)
    max_attempts = max(1, max_attempts)
    
    start_time = time.time()
    attempt = 0
    current_delay = initial_delay
    
    while True:
        attempt += 1
        reachable, error = is_reachable_func(session, url, timeout)
        
        if reachable:
            if attempt > 1:
                get_effective_logger().info(
                    f'URL="{url}" became reachable after {attempt} attempts, '
                    f'total retry time: {time.time() - start_time:.2f}s'
                )
            return True, None
        
        # Check if we've exceeded limits
        elapsed_time = time.time() - start_time
        if elapsed_time >= max_total_time:
            error_msg = (
                f'Retry timeout after {elapsed_time:.1f}s (max: {max_total_time}s), '
                f'attempts: {attempt}/{max_attempts}, last error: {error}'
            )
            get_effective_logger().warning(f'URL="{url}" {error_msg}')
            return False, error_msg
        
        if attempt >= max_attempts:
            error_msg = (
                f'Max retry attempts ({max_attempts}) reached, '
                f'total time: {elapsed_time:.1f}s, last error: {error}'
            )
            get_effective_logger().warning(f'URL="{url}" {error_msg}')
            return False, error_msg
        
        # Log retry attempt
        get_effective_logger().debug(
            f'URL="{url}" retry attempt {attempt}/{max_attempts}, '
            f'waiting {current_delay:.2f}s before next attempt, '
            f'elapsed: {elapsed_time:.1f}s/{max_total_time}s'
        )
        
        # Wait before next retry with exponential backoff
        # Ensure we don't sleep longer than remaining time
        remaining_time = max_total_time - elapsed_time
        sleep_time = min(current_delay, remaining_time)
        if sleep_time > 0:
            time.sleep(sleep_time)
        
        # Calculate next delay with exponential backoff
        current_delay = min(
            current_delay * backoff_multiplier,
            max_total_time - elapsed_time
        )


def select_url(session, splunk_url, timeout=15, retry_config=None):
    splunk_urls = splunk_url.split(",")
    unreachable_errors = []

    reachable_urls = []
    for url in splunk_urls:
        if retry_config:
            reachable, error = is_reachable_with_retry(session, url, timeout, retry_config)
        else:
            reachable, error = is_reachable(session, url, timeout=timeout)
        
        if reachable:
            reachable_urls.append(url)
        else:
            unreachable_errors.append((url, error))

    selected_url = random.choice(reachable_urls) if reachable_urls else False
    return selected_url, unreachable_errors


def get_bearer_token(storage_passwords, account):
    # realm
    credential_realm = "__REST_CREDENTIAL__#trackme#configs/conf-trackme_account"
    credential_name = f"{credential_realm}:{account}``"

    # extract as raw json
    bearer_token_rawvalue = ""

    for credential in storage_passwords:
        if credential.content.get("realm") == str(
            credential_realm
        ) and credential.name.startswith(credential_name):
            bearer_token_rawvalue = bearer_token_rawvalue + str(
                credential.content.clear_password
            )

    # extract a clean json object
    bearer_token_rawvalue_match = re.search(
        r'\{"bearer_token":\s*"(.*)"\}', bearer_token_rawvalue
    )
    if bearer_token_rawvalue_match:
        bearer_token = bearer_token_rawvalue_match.group(1)
    else:
        bearer_token = None

    return bearer_token


def establish_sdk_remote_service(
    parsed_url, bearer_token, app_namespace, account, timeout=600
):

    # Set default port if not explicitly provided
    port = parsed_url.port or 443

    # Combine hostname and path to handle sub-root endpoints, if any.
    base_path = parsed_url.path.rstrip("/")  # Ensure no trailing slash
    host_with_path = f"{parsed_url.hostname}{base_path}"

    try:
        service = client.connect(
            host=host_with_path,
            splunkToken=str(bearer_token),
            owner="nobody",
            app=app_namespace,
            port=port,
            autologin=True,
            timeout=timeout,
        )

        remote_apps = [app.label for app in service.apps]
        if remote_apps:
            get_effective_logger().info(
                f'Remote search connectivity check to host="{parsed_url.hostname}" on port="{parsed_url.port}" was successful'
            )
            return service

    except Exception as e:
        error_msg = f'Remote search for account="{account}" has failed at connectivity check, host="{parsed_url.hostname}" on port="{parsed_url.port}", url={host_with_path}, timeout={timeout}, exception="{str(e)}"'
        raise Exception(error_msg)

    return None


# Test remote account connectivity, for a least privileges approach, this function uses a system_authtoken
def trackme_test_remote_account(reqinfo, account):
    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=reqinfo.server_rest_port,
        token=reqinfo.system_authtoken,
        timeout=600,
    )

    # Splunk credentials store
    storage_passwords = service.storage_passwords

    # get all accounts
    accounts = []
    conf_file = "trackme_account"

    # if there are no account, raise an exception, otherwise what we would do here?
    try:
        confs = service.confs[str(conf_file)]
    except Exception as e:
        error_msg = (
            "splunkremotesearch was called but we have no remote account configured yet"
        )
        raise Exception(error_msg)

    for stanza in confs:
        # get all accounts
        for name in stanza.name:
            accounts.append(stanza.name)
            break

    # account configuration
    isfound = False
    splunk_url = None
    app_namespace = None
    rbac_roles = None
    timeout_connect_check = None
    timeout_search_check = None
    token_rotation_enablement = None
    token_rotation_frequency = None

    # get account
    for stanza in confs:
        if stanza.name == str(account):
            isfound = True
            for key, value in stanza.content.items():
                if key == "splunk_url":
                    splunk_url = value
                if key == "app_namespace":
                    app_namespace = value
                if key == "rbac_roles":
                    rbac_roles = value
                if key == "timeout_connect_check":
                    timeout_connect_check = int(value)
                if key == "timeout_search_check":
                    timeout_search_check = int(value)
                if key == "token_rotation_enablement":
                    token_rotation_enablement = int(value)
                if key == "token_rotation_frequency":
                    token_rotation_frequency = int(value)

    # checks timeout
    if not timeout_connect_check:
        timeout_connect_check = 15
    if not timeout_search_check:
        timeout_search_check = 300

    # retry configuration - use defaults if not configured
    retry_config = {
        "retry_enabled": "1",
        "retry_max_total_time": "30",
        "retry_initial_delay": "2",
        "retry_backoff_multiplier": "2.0",
        "retry_max_attempts": "10",
    }
    for stanza in confs:
        if stanza.name == str(account):
            for key, value in stanza.content.items():
                if key == "retry_enabled":
                    retry_config["retry_enabled"] = value
                if key == "retry_max_total_time":
                    retry_config["retry_max_total_time"] = value
                if key == "retry_initial_delay":
                    retry_config["retry_initial_delay"] = value
                if key == "retry_backoff_multiplier":
                    retry_config["retry_backoff_multiplier"] = value
                if key == "retry_max_attempts":
                    retry_config["retry_max_attempts"] = value

    # Stop here if we cannot find the submitted account
    if not isfound:
        error_msg = f'The account="{account}" has not been configured on this instance, cannot proceed!'
        get_effective_logger().error(error_msg)
        raise Exception(
            {
                "status": "failure",
                "message": error_msg,
                "targets": account,
            }
        )

    # Create a session within the generate function
    session = requests.Session()

    # Call target selector and pass the session as an argument
    selected_url, errors = select_url(
        session, splunk_url, timeout=timeout_connect_check, retry_config=retry_config
    )

    # end of get configuration

    # If none of the endpoints could be reached
    if not selected_url:
        error_msg = f"None of the endpoints provided in the account URLs could be reached successfully, verify your network connectivity! (timeout: {timeout_connect_check}) "
        error_msg += "Errors: " + ", ".join(
            [f"{url}: {error}" for url, error in errors]
        )
        get_effective_logger().error(error_msg)
        raise Exception(
            {
                "status": "failure",
                "message": error_msg,
                "account": account,
                "targets": splunk_url,
            }
        )

    # check the license
    try:
        check_license = trackme_check_license(
            reqinfo.server_rest_uri, reqinfo.session_key
        )
        license_is_valid = check_license.get("license_is_valid")
        get_effective_logger().debug(
            f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
        )
    except Exception as e:
        license_is_valid = 0
        get_effective_logger().error(f'function check_license exception="{str(e)}"')

    # try and return
    if license_is_valid != 1 and len(accounts) >= 2 and accounts[0] != account:
        error_msg = f"This TrackMe deployment is running in Free limited edition and you have reached the maximum number of 1 remote deployment, only the first remote account ({accounts[0]}) can be used"
        raise Exception(
            {
                "status": "failure",
                "message": error_msg,
                "account": account,
            }
        )

    else:
        # Enforce https and remove trailing slash in the URL, if any
        selected_url = f"https://{selected_url.replace('https://', '').rstrip('/')}"

        # Splunk remote application namespace where searches are going to be executed, default to search if not defined
        if not app_namespace:
            app_namespace = "search"

        # else get the bearer token stored encrypted
        else:
            bearer_token = get_bearer_token(storage_passwords, account)

        if not bearer_token:
            error_msg = f'The bearer token for the account="{account}" could not be retrieved, cannot proceed!'
            raise Exception(
                {
                    "status": "failure",
                    "message": error_msg,
                    "account": account,
                    "host": parsed_url.hostname,
                    "port": parsed_url.port,
                }
            )

        else:
            # Use urlparse to extract relevant info from target
            parsed_url = urllib.parse.urlparse(selected_url)

            # Establish the remote service
            try:
                remoteservice = establish_sdk_remote_service(
                    parsed_url,
                    bearer_token,
                    app_namespace,
                    account,
                    timeout=timeout_search_check,
                )

            except Exception as e:
                error_msg = f'remote search for account="{account}" has failed at connectivity check, host="{parsed_url.hostname}" on port="{parsed_url.port}" for Splunk remote account="{account}", timeout={timeout_search_check}, exception="{str(e)}"'
                get_effective_logger().error(error_msg)
                error_info = {
                    "status": "failure",
                    "message": f"remote search check failed at connectivity verification, response: {str(e)}",
                    "account": account,
                    "host": parsed_url.hostname,
                    "port": parsed_url.port,
                    "timeout_connect_check": timeout_connect_check,
                    "timeout_search_check": timeout_search_check,
                    "rbac_roles": rbac_roles,
                    "app_namespace": app_namespace,
                    "token_rotation_enablement": token_rotation_enablement,
                    "token_rotation_frequency": token_rotation_frequency,
                }
                raise TrackMeRemoteConnectionError(error_info)

            if remoteservice:
                get_effective_logger().info(
                    f'remote search connectivity check to host="{parsed_url.hostname}" on port="{parsed_url.port}" for Splunk remote account="{account}" was successful'
                )
                return {
                    "status": "success",
                    "message": "remote search connectivity check was successful, service was established",
                    "account": account,
                    "host": parsed_url.hostname,
                    "port": parsed_url.port,
                    "timeout_connect_check": timeout_connect_check,
                    "timeout_search_check": timeout_search_check,
                    "rbac_roles": rbac_roles,
                    "app_namespace": app_namespace,
                    "token_rotation_enablement": token_rotation_enablement,
                    "token_rotation_frequency": token_rotation_frequency,
                }

            else:
                error_msg = "remote search connectivity check has failed to retrieve the list of applications on the remote system"
                get_effective_logger().error(error_msg)
                raise Exception(
                    {
                        "status": "failure",
                        "message": "remote search check failed at connectivity verification",
                        "account": account,
                        "host": parsed_url.hostname,
                        "port": parsed_url.port,
                        "timeout_connect_check": timeout_connect_check,
                        "timeout_search_check": timeout_search_check,
                        "rbac_roles": rbac_roles,
                        "app_namespace": app_namespace,
                        "token_rotation_enablement": token_rotation_enablement,
                        "token_rotation_frequency": token_rotation_frequency,
                    }
                )


# Test remote connectivity before the account is created, expects a dict account object containing required information to test the connectivity
def trackme_test_remote_connectivity(connection_info):
    splunk_url = connection_info.get("target_endpoints")
    app_namespace = connection_info.get("app_namespace", "search")
    bearer_token = connection_info.get("bearer_token")
    timeout_connect_check = connection_info.get("timeout_connect_check", 15)
    timeout_search_check = connection_info.get("timeout_search_check", 300)

    # retry configuration - use defaults if not provided
    retry_config = {
        "retry_enabled": connection_info.get("retry_enabled", "1"),
        "retry_max_total_time": connection_info.get("retry_max_total_time", "30"),
        "retry_initial_delay": connection_info.get("retry_initial_delay", "2"),
        "retry_backoff_multiplier": connection_info.get("retry_backoff_multiplier", "2.0"),
        "retry_max_attempts": connection_info.get("retry_max_attempts", "10"),
    }

    # Create a session within the generate function
    session = requests.Session()

    # Call target selector and pass the session as an argument
    selected_url, errors = select_url(
        session, splunk_url, timeout=timeout_connect_check, retry_config=retry_config
    )

    # end of get configuration

    # Stop here if none of the submitted endpoints can be reached
    if not selected_url:
        error_msg = f"None of the endpoints provided in the account URLs could be reached successfully. Verify your network connectivity! (timeout: {timeout_connect_check}) "
        error_msg += "Errors: " + ", ".join(
            [f"{url}: {error}" for url, error in errors]
        )
        get_effective_logger().error(error_msg)
        raise Exception(
            {
                "status": "failure",
                "message": error_msg,
                "targets": splunk_url,
            }
        )

    # Enforce https and remove trailing slash in the URL, if any
    selected_url = f"https://{selected_url.replace('https://', '').rstrip('/')}"

    if not bearer_token:
        error_msg = f"The bearer token was not provided, cannot proceed!"
        raise Exception(
            {
                "status": "failure",
                "message": error_msg,
                "host": parsed_url.hostname,
                "port": parsed_url.port,
            }
        )

    else:
        # Use urlparse to extract relevant info from target
        parsed_url = urllib.parse.urlparse(selected_url)

        # Establish the remote service
        try:
            remoteservice = establish_sdk_remote_service(
                parsed_url,
                bearer_token,
                app_namespace,
                "connection_test",
                timeout=timeout_search_check,
            )

        except Exception as e:
            error_msg = f'remote search has failed at connectivitity check, host="{parsed_url.hostname}" on port="{parsed_url.port}", timeout={timeout_search_check}, exception="{str(e)}"'
            get_effective_logger().error(error_msg)
            raise Exception(
                {
                    "message": "remote search check failed at connectivity verification",
                    "host": parsed_url.hostname,
                    "port": parsed_url.port,
                    "exception": str(e),
                }
            )

        if remoteservice:
            get_effective_logger().info(
                f'remote search connectivity check to host="{parsed_url.hostname}" on port="{parsed_url.port}" was successful'
            )
            return {
                "status": "success",
                "message": "remote search connectivity check was successful, service was established",
                "host": parsed_url.hostname,
                "port": parsed_url.port,
            }

        else:
            error_msg = "remote search connectivity check has failed to retrieve the list of applications on the remote system"
            get_effective_logger().error(error_msg)
            raise Exception(
                {
                    "message": error_msg,
                    "host": parsed_url.hostname,
                    "port": parsed_url.port,
                }
            )


# Get remote account credentials, designed to be used for a least privileges approach in a programmatic approach
def trackme_get_remote_account(reqinfo, account):
    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=reqinfo.server_rest_port,
        token=reqinfo.system_authtoken,
        timeout=600,
    )

    # Splunk credentials store
    storage_passwords = service.storage_passwords

    # get all accounts
    accounts = []
    conf_file = "trackme_account"

    # if there are no account, raise an exception, otherwise what we would do here?
    try:
        confs = service.confs[str(conf_file)]
    except Exception as e:
        error_msg = (
            "splunkremotesearch was called but we have no remote account configured yet"
        )
        raise Exception(error_msg)

    for stanza in confs:
        # get all accounts
        for name in stanza.name:
            accounts.append(stanza.name)
            break

    # account configuration
    isfound = False
    splunk_url = None
    app_namespace = None
    rbac_roles = None
    timeout_connect_check = None
    timeout_search_check = None
    token_rotation_enablement = None
    token_rotation_frequency = None

    # get account
    for stanza in confs:
        if stanza.name == str(account):
            isfound = True
            for key, value in stanza.content.items():
                if key == "splunk_url":
                    splunk_url = value
                if key == "app_namespace":
                    app_namespace = value
                if key == "rbac_roles":
                    rbac_roles = value
                if key == "timeout_connect_check":
                    timeout_connect_check = value
                if key == "timeout_search_check":
                    timeout_search_check = value
                if key == "token_rotation_enablement":
                    token_rotation_enablement = value
                if key == "token_rotation_frequency":
                    token_rotation_frequency = value

    # retry configuration
    retry_enabled = None
    retry_max_total_time = None
    retry_initial_delay = None
    retry_backoff_multiplier = None
    retry_max_attempts = None
    
    for stanza in confs:
        if stanza.name == str(account):
            for key, value in stanza.content.items():
                if key == "retry_enabled":
                    retry_enabled = value
                if key == "retry_max_total_time":
                    retry_max_total_time = value
                if key == "retry_initial_delay":
                    retry_initial_delay = value
                if key == "retry_backoff_multiplier":
                    retry_backoff_multiplier = value
                if key == "retry_max_attempts":
                    retry_max_attempts = value

    # end of get configuration

    # Stop here if we cannot find the submitted account
    if not isfound:
        error_msg = f'The account="{account}" has not been configured on this instance, cannot proceed!'
        raise Exception(
            {
                "status": "failure",
                "message": error_msg,
                "account": account,
            }
        )

    # check the license
    try:
        check_license = trackme_check_license(
            reqinfo.server_rest_uri, reqinfo.session_key
        )
        license_is_valid = check_license.get("license_is_valid")
        get_effective_logger().debug(
            f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
        )

    except Exception as e:
        license_is_valid = 0
        get_effective_logger().error(f'function check_license exception="{str(e)}"')

    # try and return
    if license_is_valid != 1 and len(accounts) >= 2 and accounts[0] != account:
        error_msg = f"This TrackMe deployment is running in Free limited edition and you have reached the maximum number of 1 remote deployment, only the first remote account ({accounts[0]}) can be used"
        raise Exception(
            {
                "status": "failure",
                "message": error_msg,
                "account": account,
            }
        )

    else:
        # Splunk remote application namespace where searches are going to be executed, default to search if not defined
        if not app_namespace:
            app_namespace = "search"

        # RBAC: the user must be a member of the grante roles for this account, for retro-compatibility purposes,
        # if this was not defined yet, use builtin TrackMe roles
        if not rbac_roles:
            rbac_roles = [
                "admin",
                "sc_admin",
                "trackme_user",
                "trackme_power",
                "trackme_admin",
            ]
        else:
            rbac_roles = rbac_roles.split(",")

        # timeouts
        if not timeout_connect_check:
            timeout_connect_check = 10
        if not timeout_search_check:
            timeout_search_check = 300

        # get the bearer token stored encrypted
        bearer_token = get_bearer_token(storage_passwords, account)

        if not bearer_token:
            error_msg = f'The bearer token for the account="{account}" could not be retrieved, cannot proceed!'
            raise Exception(
                {
                    "status": "failure",
                    "message": error_msg,
                    "account": account,
                    "splunk_url": splunk_url,
                }
            )

        else:
            # render
            result = {
                "status": "success",
                "message": "remote search connectivity check was successful, service was established",
                "account": account,
                "splunk_url": splunk_url,
                "app_namespace": app_namespace,
                "token": bearer_token,
                "rbac_roles": rbac_roles,
                "timeout_connect_check": timeout_connect_check,
                "timeout_search_check": timeout_search_check,
                "token_rotation_enablement": token_rotation_enablement,
                "token_rotation_frequency": token_rotation_frequency,
            }
            
            # Add retry configuration if present
            if retry_enabled is not None:
                result["retry_enabled"] = retry_enabled
            if retry_max_total_time is not None:
                result["retry_max_total_time"] = retry_max_total_time
            if retry_initial_delay is not None:
                result["retry_initial_delay"] = retry_initial_delay
            if retry_backoff_multiplier is not None:
                result["retry_backoff_multiplier"] = retry_backoff_multiplier
            if retry_max_attempts is not None:
                result["retry_max_attempts"] = retry_max_attempts
            
            return result


#
#
#


def trackme_get_report(
    session_key,
    splunkd_uri,
    tenant_id,
    report_name,
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # create a new report
    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to get report report_name="{report_name}"'
    )

    # get the report
    try:
        savedsearch = service.saved_searches[report_name]
        savedsearch_search = savedsearch.content["search"]
        savedsearch_cron_schedule = savedsearch.content["cron_schedule"]
        savedsearch_description = savedsearch.content["description"]
        savedsearch_disabled = savedsearch.content["disabled"]
        savedsearch_is_scheduled = savedsearch.content["is_scheduled"]
        savedsearch_schedule_window = savedsearch.content["schedule_window"]
        savedsearch_workload_pool = savedsearch.content["workload_pool"]
        savedsearch_earliest_time = savedsearch.content["dispatch.earliest_time"]
        savedsearch_latest_time = savedsearch.content["dispatch.latest_time"]
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", report_name="{report_name}"'
        )
        return {
            "savedsearch_search": savedsearch_search,
            "savedsearch_cron_schedule": savedsearch_cron_schedule,
            "savedsearch_description": savedsearch_description,
            "savedsearch_disabled": savedsearch_disabled,
            "savedsearch_is_scheduled": savedsearch_is_scheduled,
            "savedsearch_schedule_window": savedsearch_schedule_window,
            "savedsearch_workload_pool": savedsearch_workload_pool,
            "savedsearch_earliest_time": savedsearch_earliest_time,
            "savedsearch_latest_time": savedsearch_latest_time,
        }

    except Exception as e:
        error_msg = f'tenant_id="{tenant_id}", failed to get report report_name="{report_name}" with exception:"{str(e)}"'
        get_effective_logger().error(error_msg)
        raise Exception(error_msg)


#
#
#


def trackme_create_report(
    session_key,
    splunkd_uri,
    tenant_id,
    report_name,
    report_search,
    report_properties,
    report_acl,
    max_failures_count=24,
    sleep_time=5,
):
    """Create a saved search ("report") for a tenant.

    ``max_failures_count`` and ``sleep_time`` control the internal
    transient-failure retry loop. The defaults (24 × 5 s = 120 s) are
    tuned for the cold-start case where a saved search references a
    macro that was created moments earlier — splunkd's config-refresh
    cycle is the only legitimate transient cause and 2 minutes is the
    observed worst case. Callers in a restore context (where the same
    name was just deleted) should pass much smaller values
    (e.g. 3 × 2 s) — the only transient cause that matters there is
    Splunk's saved-searches cache eviction, which resolves in seconds,
    not minutes. See conflict-handling audit for v3 KO restore.
    """
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # create a new report
    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to create report report_name="{report_name}"'
    )

    #
    # Splunkd API needs a couple of seconds to refresh while macros were created
    # In a programmatic context, this may lead the report creation to be failing
    # the function will check the KO status, and wait if needed for a certain amount of time

    creation_success = False
    current_failures_count = 0

    while current_failures_count < max_failures_count and not creation_success:
        try:
            newtracker = service.saved_searches.create(
                str(report_name), str(report_search)
            )
            get_effective_logger().info(
                f'tenant_id="{tenant_id}", action="success", report_name="{report_name}"'
            )
            creation_success = True
            break

        except Exception as e:
            # Detect HTTP 409 Conflict (a saved search with the same name
            # already exists). This is a permanent condition — retrying cannot
            # resolve it — so fail fast instead of exhausting the retry budget
            # and flooding the logs with misleading "temporary failure" warnings.
            http_code = getattr(e, "status", None) or getattr(e, "httpcode", None)
            err_str = str(e)
            if http_code == 409 or "HTTP 409" in err_str or "already exists" in err_str:
                get_effective_logger().error(
                    f'tenant_id="{tenant_id}", conflict detected, a saved search with report_name="{report_name}" already exists, aborting creation without retry, exception="{err_str}"'
                )
                raise Exception(
                    f'tenant_id="{tenant_id}", conflict: a saved search with report_name="{report_name}" already exists (HTTP 409 Conflict)'
                )

            # We except this sentence in the exception if the API is not ready yet
            get_effective_logger().warning(
                f'tenant_id="{tenant_id}", temporary failure, the report is not yet available, will sleep and re-attempt, report report_name="{report_name}"'
            )
            time.sleep(sleep_time)
            current_failures_count += 1

            if current_failures_count >= max_failures_count:
                get_effective_logger().error(
                    f'tenant_id="{tenant_id}", max attempt reached, failure to create report report_name="{report_name}", report_search="{report_search}" with exception:"{str(e)}"'
                )
                raise Exception(
                    f'tenant_id="{tenant_id}", max attempt reached, failure to create report report_name="{report_name}", report_search="{report_search}" with exception:"{str(e)}"'
                )

    # Complete the report definition
    kwargs = report_properties

    # For optimization purposes, if the schedule is set to every 5 minutes, randomly choose an every 5 minutes schedule
    if kwargs.get("cron_schedule") == "*/5 * * * *":
        cron_random_list = [
            "*/5 * * * *",
            "1-56/5 * * * *",
            "2-57/5 * * * *",
            "3-58/5 * * * *",
            "4-59/5 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)
    elif kwargs.get("cron_schedule") == "*/10 * * * *":
        cron_random_list = [
            "*/10 * * * *",
            "1-59/10 * * * *",
            "2-59/10 * * * *",
            "3-59/10 * * * *",
            "4-59/10 * * * *",
            "5-59/10 * * * *",
            "6-59/10 * * * *",
            "7-59/10 * * * *",
            "8-59/10 * * * *",
            "9-59/10 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)
    elif kwargs.get("cron_schedule") == "*/15 * * * *":
        cron_random_list = [
            "*/15 * * * *",
            "1-59/15 * * * *",
            "2-59/15 * * * *",
            "3-59/15 * * * *",
            "4-59/15 * * * *",
            "5-59/15 * * * *",
            "6-59/15 * * * *",
            "7-59/15 * * * *",
            "8-59/15 * * * *",
            "9-59/15 * * * *",
            "10-59/15 * * * *",
            "11-59/15 * * * *",
            "12-59/15 * * * *",
            "13-59/15 * * * *",
            "14-59/15 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)

    elif kwargs.get("cron_schedule") == "*/20 * * * *":
        cron_random_list = [
            "*/20 * * * *",
            "1-59/20 * * * *",
            "2-59/20 * * * *",
            "3-59/20 * * * *",
            "4-59/20 * * * *",
            "5-59/20 * * * *",
            "6-59/20 * * * *",
            "7-59/20 * * * *",
            "8-59/20 * * * *",
            "9-59/20 * * * *",
            "10-59/20 * * * *",
            "11-59/20 * * * *",
            "12-59/20 * * * *",
            "13-59/20 * * * *",
            "14-59/20 * * * *",
            "15-59/20 * * * *",
            "16-59/20 * * * *",
            "17-59/20 * * * *",
            "18-59/20 * * * *",
            "19-59/20 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)

    elif kwargs.get("cron_schedule") == "*/20 22-23,0-6 * * *":
        cron_random_list = [
            "*/20 22-23,0-6 * * *",
            "1-59/20 22-23,0-6 * * *",
            "2-59/20 22-23,0-6 * * *",
            "3-59/20 22-23,0-6 * * *",
            "4-59/20 22-23,0-6 * * *",
            "5-59/20 22-23,0-6 * * *",
            "6-59/20 22-23,0-6 * * *",
            "7-59/20 22-23,0-6 * * *",
            "8-59/20 22-23,0-6 * * *",
            "9-59/20 22-23,0-6 * * *",
            "10-59/20 22-23,0-6 * * *",
            "11-59/20 22-23,0-6 * * *",
            "12-59/20 22-23,0-6 * * *",
            "13-59/20 22-23,0-6 * * *",
            "14-59/20 22-23,0-6 * * *",
            "15-59/20 22-23,0-6 * * *",
            "16-59/20 22-23,0-6 * * *",
            "17-59/20 22-23,0-6 * * *",
            "18-59/20 22-23,0-6 * * *",
            "19-59/20 22-23,0-6 * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)

    elif (
        kwargs.get("cron_schedule") == "*/30 * * * *"
        or kwargs.get("cron_schedule") == "30 * * * *"
    ):
        cron_random_list = [
            "*/30 * * * *",
            "1,31 * * * *",
            "2,32 * * * *",
            "3,33 * * * *",
            "4,34 * * * *",
            "5,35 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)

    elif kwargs.get("cron_schedule") == "*/60 * * * *":
        cron_random_list = [
            "*/60 * * * *",
            "1 * * * *",
            "2 * * * *",
            "3 * * * *",
            "4 * * * *",
            "5 * * * *",
            "6 * * * *",
            "7 * * * *",
            "8 * * * *",
            "9 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)

    elif kwargs.get("cron_schedule") == "0 22-23,0-6 * * *":
        cron_random_list = [
            "0 22-23,0-6 * * *",
            "1 22-23,0-6 * * *",
            "2 22-23,0-6 * * *",
            "3 22-23,0-6 * * *",
            "4 22-23,0-6 * * *",
            "5 22-23,0-6 * * *",
            "6 22-23,0-6 * * *",
            "7 22-23,0-6 * * *",
            "8 22-23,0-6 * * *",
            "9 22-23,0-6 * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)

    elif kwargs.get("cron_schedule") == "0 */12 * * *":
        cron_random_list = [
            f"{m} */12 * * *" for m in range(0, 60)
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)

    # Filter out invalid cron_schedule values
    cron_schedule = kwargs.get("cron_schedule")
    if cron_schedule in (None, "None", "null", ""):
        kwargs.pop("cron_schedule", None)
        cron_schedule = None
    
    # verify the cron schedule validity, if submitted
    if cron_schedule:
        try:
            validate_cron_schedule(cron_schedule)
        except Exception as e:
            get_effective_logger().error(str(e))
            return {
                "payload": {
                    "action": "failure",
                    "response": str(e),
                },
                "status": 500,
            }

    # Update the server and refresh the local copy of the object.
    #
    # We use splunklib's Entity methods (.update() / .post("acl")) which
    # internally use self.path that was set by splunklib via parse.unquote()
    # on the atom response href. When self.path is passed through
    # _abspath() -> UrlEncoded(skip_encode=False), splunklib encodes it
    # exactly once via parse.quote(). This means saved search names with
    # spaces or other special characters are handled correctly.
    #
    # Do NOT replace this with manually-built paths passed to service.post()
    # — those either get double-encoded (if pre-encoded) or remain unencoded
    # (if plain string), both of which fail for names with spaces.
    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to update report_name="{report_name}" with kwargs="{json.dumps(kwargs, indent=1)}"'
    )
    try:
        #
        # Splunkd API needs a couple of seconds to refresh while macros were created
        # In a programmatic context, this may lead the report creation to be failing
        # the function will check the KO status, and wait if needed for a certain amount of time

        # set max failed re-attempt
        max_failures_count = 24
        sleep_time = 5
        creation_success = False
        current_failures_count = 0
        newtracker_update = None

        while current_failures_count < max_failures_count and not creation_success:
            try:
                # Re-lookup inside the retry loop to handle eventual
                # consistency on freshly created saved searches.
                # service.saved_searches[name] wraps the key in
                # UrlEncoded(key, encode_slash=True) so names with spaces
                # are looked up correctly.
                newtracker_update = service.saved_searches[str(report_name)]
                newtracker_update.update(**kwargs).refresh()
                get_effective_logger().info(
                    f'tenant_id="{tenant_id}", action="success", report_name="{report_name}" with kwargs="{json.dumps(kwargs, indent=1)}"'
                )
                creation_success = True
                break

            except Exception as e:
                get_effective_logger().warning(
                    f'tenant_id="{tenant_id}", temporary failure, the report is not yet available, will sleep and re-attempt, report report_name="{report_name}"'
                )
                time.sleep(sleep_time)
                current_failures_count += 1

                if current_failures_count >= max_failures_count:
                    get_effective_logger().error(
                        f'tenant_id="{tenant_id}", max attempt reached, failure to create report report_name="{report_name}" with exception:"{str(e)}"'
                    )
                    raise Exception(str(e))

    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to update report report_name="{report_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))

    # Handler RBAC — use Entity.post("acl", body=urlencode(report_acl)).
    #
    # CRITICAL: Do NOT unpack report_acl as **report_acl — its "owner" and
    # "sharing" keys would collide with Entity.post's signature where those
    # are namespace parameters, not body parameters. Passing them as namespace
    # would cause splunklib to build the URL with owner=nobody/app=system
    # (since report_acl has no "app" key), but the saved search lives in
    # owner=nobody/app=trackme — resulting in a 404.
    #
    # Passing body=urlencode(report_acl) keeps all ACL fields in the request
    # body and lets splunklib use the service's own namespace (nobody/trackme)
    # for the path, matching where the saved search was actually created.
    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to update report_name="{report_name}" with kwargs="{json.dumps(report_acl, indent=1)}"'
    )
    try:
        newtracker_update.post("acl", body=urlencode(report_acl))
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", report_name="{report_name}" with kwargs="{json.dumps(report_acl, indent=1)}"'
        )

        return {
            "action": "success",
            "tenant_id": tenant_id,
            "report_name": report_name,
            "report_search": report_search,
            "report_owner": report_acl.get("owner"),
            "report_perms_read": report_acl.get("perms.read"),
            "report_perms_write": report_acl.get("perms.write"),
            "description": kwargs.get("description"),
            "is_scheduled": kwargs.get("is_scheduled"),
            "schedule_window": kwargs.get("schedule_window"),
            "dispatch.earliest_time": kwargs.get("dispatch.earliest_time"),
            "dispatch.latest_time": kwargs.get("dispatch.latest_time"),
            "cron_schedule": kwargs.get("cron_schedule"),
        }

    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to update report report_name="{report_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_manage_report_schedule(
    logger,
    session_key,
    splunkd_uri,
    tenant_id,
    report_name,
    input_report_properties=None,
    action=None,
    splunkd_timeout=None,
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    """
    This function is used to enable, disable the report schedule, or show the current schedule enablement status
    """

    # check action, allowed values are: enable, disable
    if action not in ["enable", "disable", "status"]:
        raise Exception(
            f'tenant_id="{tenant_id}", invalid action="{action}", allowed values are: enable, disable, status'
        )

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # Resolve splunkd_timeout from config if not provided
    if splunkd_timeout is None:
        try:
            splunkd_timeout = get_splunkd_timeout(trackme_conf=trackme_reqinfo_from_service(service))
        except Exception:
            splunkd_timeout = SPLUNKD_TIMEOUT_DEFAULT

    # log start
    logger.debug(
        f'tenant_id="{tenant_id}", attempting to run handle schedule management with action={action} for report report_name="{report_name}"'
    )

    # get the report object
    try:
        savedsearch_object = service.saved_searches[str(report_name)]
    except Exception as e:
        error_msg = f'tenant_id="{tenant_id}", failure to get report report_name="{report_name}" with exception:"{str(e)}"'
        get_effective_logger().error(error_msg)
        raise Exception(error_msg)

    #
    # check orphan & retrieve acl
    #

    # Build header and target URL
    headers = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }

    # url
    url = f'{splunkd_uri}/{savedsearch_object.links["alternate"]}/acl/list?output_mode=json'

    try:
        response = requests.get(url, headers=headers, verify=False, timeout=splunkd_timeout)
        response.raise_for_status()
        response_json = response.json()

        savedsearch_content = savedsearch_object.content
        savedsearch_acl = response_json.get("entry")[0]["acl"]

        # log
        logger.debug(
            f'tenant_id="{tenant_id}", action="success", report_name="{report_name}", savedsearch_content="{json.dumps(savedsearch_content, indent=2)}", savedsearch_acl="{json.dumps(savedsearch_acl, indent=2)}"'
        )

        # get the report properties
        if input_report_properties is None:
            report_properties = {
                "description": savedsearch_content.get("description"),
                "disabled": savedsearch_content.get("disabled"),
                "is_scheduled": savedsearch_content.get("is_scheduled"),
                "schedule_window": savedsearch_content.get("schedule_window"),
                "cron_schedule": savedsearch_content.get("cron_schedule"),
                "dispatch.earliest_time": savedsearch_content.get("dispatch.earliest_time"),
                "dispatch.latest_time": savedsearch_content.get("dispatch.latest_time"),
            }
        else:
            report_properties = {
                "description": savedsearch_content.get("description"),
                "disabled": savedsearch_content.get("disabled"),
                "is_scheduled": input_report_properties.get("is_scheduled"),
                "schedule_window": input_report_properties.get("schedule_window"),
                "cron_schedule": input_report_properties.get("cron_schedule"),
                "dispatch.earliest_time": input_report_properties.get("dispatch.earliest_time"),
                "dispatch.latest_time": input_report_properties.get("dispatch.latest_time"),
            }


        # get the report acl
        report_acl = {
            "owner": savedsearch_acl.get("owner"),
            "app": savedsearch_acl.get("app"),
            "sharing": savedsearch_acl.get("sharing"),
            "perms_read": ",".join(savedsearch_acl.get("perms").get("read", [])),
            "perms_write": ",".join(savedsearch_acl.get("perms").get("write", [])),
        }

    except Exception as e:
        error_msg = f'tenant_id="{tenant_id}", failure to get report report_name="{report_name}" with exception:"{str(e)}"'
        raise Exception(error_msg)

    # for now, return
    if action == "status":
        return report_properties, report_acl

    elif action in ["enable", "disable"]:

        if action == "enable":
            report_properties["is_scheduled"] = 1
        elif action == "disable":
            report_properties["is_scheduled"] = 0

        try:
            savedsearch_object.update(**report_properties).refresh()
        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failure to update report report_name="{report_name}" with exception:"{str(e)}"'
            raise Exception(error_msg)

        return report_properties, report_acl


def trackme_delete_report(session_key, splunkd_uri, tenant_id, report_name):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # Pre-delete metadata snapshot for forensic logging. Use
    # ``.get()`` with defaults instead of bracket access — Splunk
    # saved-searches occasionally lack one of the seven properties
    # below (e.g. a never-scheduled search may not carry a
    # ``cron_schedule`` key, depending on Splunk version). Bracket
    # access used to raise ``KeyError`` here, *before* the actual
    # delete call ran, so the function appeared to "fail to delete"
    # something it had not yet attempted to delete. Surfaces as
    # an HTTP 409 conflict on the subsequent restore-create. Use
    # ``.get()`` so the snapshot is best-effort and the actual
    # delete always runs.
    snapshot = {}
    try:
        savedsearch = service.saved_searches[report_name]
        content = getattr(savedsearch, "content", None) or {}
        for key in (
            "search", "cron_schedule", "description", "is_scheduled",
            "dispatch.earliest_time", "dispatch.latest_time",
        ):
            snapshot[key] = content.get(key) if hasattr(content, "get") else None
    except Exception as snapshot_err:
        # Snapshot failure is non-fatal — log debug and proceed
        # to the actual delete. We don't even know yet whether the
        # search exists; the delete will tell us.
        get_effective_logger().debug(
            f'tenant_id="{tenant_id}", report_name="{report_name}" — '
            f'pre-delete metadata snapshot skipped: {str(snapshot_err)}'
        )

    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to delete report '
        f'report_name="{report_name}", snapshot={snapshot}'
    )

    try:
        service.saved_searches.delete(str(report_name))
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", report_name="{report_name}"'
        )
        return "success"
    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to delete report report_name="{report_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_create_alert(
    session_key,
    splunkd_uri,
    tenant_id,
    alert_name,
    alert_search,
    properties,
    alert_properties,
    alert_acl,
    max_failures_count=24,
    sleep_time=5,
):
    """Create a saved search with alert actions ("alert") for a tenant.

    ``max_failures_count`` and ``sleep_time`` control the internal
    transient-failure retry loop. The defaults (24 × 5 s = 120 s) are
    tuned for the cold-start case where the alert references a macro
    or report that was created moments earlier — splunkd's config-
    refresh cycle is the only legitimate transient cause and 2 minutes
    is the observed worst case. Callers in a restore context (where
    the same name was just deleted) should pass much smaller values
    (e.g. 3 × 2 s) — the only transient cause that matters there is
    Splunk's saved-searches cache eviction, which resolves in seconds,
    not minutes. Mirrors the ``trackme_create_report`` signature
    introduced for the same v3 KO restore conflict-handling work; the
    two functions hit the same Splunk endpoint and share the same
    failure modes, so they share the same kwargs.
    """
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    # create a new alert
    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to create alert alert_name="{alert_name}"'
    )

    #
    # Splunkd API needs a couple of seconds to refresh while macros were created
    # In a programmatic context, this may lead the report creation to be failing
    # the function will check the KO status, and wait if needed for a certain amount of time

    creation_success = False
    current_failures_count = 0

    while current_failures_count < max_failures_count and not creation_success:
        try:
            newalert = service.saved_searches.create(str(alert_name), str(alert_search))
            get_effective_logger().info(
                f'tenant_id="{tenant_id}", action="success", alert_name="{alert_name}"'
            )
            creation_success = True
            break

        except Exception as e:
            # Detect HTTP 409 Conflict (a saved search with the same
            # name already exists). This is a permanent condition —
            # retrying cannot resolve it — so fail fast instead of
            # exhausting the retry budget and flooding the logs with
            # misleading "temporary failure" warnings. Mirrors the
            # equivalent fast-fail in ``trackme_create_report``.
            http_code = getattr(e, "status", None) or getattr(e, "httpcode", None)
            err_str = str(e)
            if (
                http_code == 409
                or "HTTP 409" in err_str
                or "already exists" in err_str
            ):
                get_effective_logger().error(
                    f'tenant_id="{tenant_id}", conflict detected, a saved search '
                    f'with alert_name="{alert_name}" already exists, aborting '
                    f'creation without retry, exception="{err_str}"'
                )
                raise Exception(
                    f'tenant_id="{tenant_id}", conflict: a saved search with '
                    f'alert_name="{alert_name}" already exists '
                    f'(HTTP 409 Conflict)'
                )

            # We except this sentence in the exception if the API is not ready yet
            get_effective_logger().warning(
                f'tenant_id="{tenant_id}", temporary failure, the alert is not yet available, will sleep and re-attempt, alert alert_name="{alert_name}"'
            )
            time.sleep(sleep_time)
            current_failures_count += 1

            if current_failures_count >= max_failures_count:
                error_msg = f'tenant_id="{tenant_id}", max attempt reached, failure to create alert alert_name="{alert_name}" with exception:"{str(e)}"'
                get_effective_logger().error(error_msg)
                raise Exception(error_msg)

    # update the properties
    newalert_update = service.saved_searches[str(alert_name)]

    # Complete the report definition
    get_effective_logger().debug(
        f'tenant_id="{tenant_id}", properties="{properties}", alert_properties="{alert_properties}", alert_acl="{alert_acl}"'
    )
    kwargs = {}
    kwargs.update(properties)
    kwargs.update(alert_properties)

    # For optimization purposes, if the schedule is set to every 5 minutes, randomly choose an every 5 minutes schedule
    if kwargs.get("cron_schedule") == "*/5 * * * *":
        cron_random_list = [
            "*/5 * * * *",
            "1-56/5 * * * *",
            "2-57/5 * * * *",
            "3-58/5 * * * *",
            "4-59/5 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)
    elif kwargs.get("cron_schedule") == "*/10 * * * *":
        cron_random_list = [
            "*/10 * * * *",
            "1-59/10 * * * *",
            "2-59/10 * * * *",
            "3-59/10 * * * *",
            "4-59/10 * * * *",
            "5-59/10 * * * *",
            "6-59/10 * * * *",
            "7-59/10 * * * *",
            "8-59/10 * * * *",
            "9-59/10 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)
    elif kwargs.get("cron_schedule") == "*/15 * * * *":
        cron_random_list = [
            "*/10 * * * *",
            "1-59/10 * * * *",
            "2-59/10 * * * *",
            "3-59/10 * * * *",
            "4-59/10 * * * *",
            "5-59/10 * * * *",
            "6-59/10 * * * *",
            "7-59/10 * * * *",
            "8-59/10 * * * *",
            "9-59/10 * * * *",
            "10-59/10 * * * *",
            "11-59/10 * * * *",
            "12-59/10 * * * *",
            "13-59/10 * * * *",
            "14-59/10 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)
    elif (
        kwargs.get("cron_schedule") == "*/30 * * * *"
        or kwargs.get("cron_schedule") == "30 * * * *"
    ):
        cron_random_list = [
            "*/30 * * * *",
            "1,31 * * * *",
            "2,32 * * * *",
            "3,33 * * * *",
            "4,34 * * * *",
            "5,35 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)
    elif kwargs.get("cron_schedule") == "*/60 * * * *":
        cron_random_list = [
            "*/60 * * * *",
            "2,32 * * * *",
            "3,33 * * * *",
            "4,34 * * * *",
            "5,35 * * * *",
            "6,36 * * * *",
            "7,37 * * * *",
            "8,38 * * * *",
            "9,39 * * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)

    elif kwargs.get("cron_schedule") == "0 22-23,0-6 * * *":
        cron_random_list = [
            "0 22-23,0-6 * * *",
            "1 22-23,0-6 * * *",
            "2 22-23,0-6 * * *",
            "3 22-23,0-6 * * *",
            "4 22-23,0-6 * * *",
            "5 22-23,0-6 * * *",
            "6 22-23,0-6 * * *",
            "7 22-23,0-6 * * *",
            "8 22-23,0-6 * * *",
            "9 22-23,0-6 * * *",
        ]
        kwargs["cron_schedule"] = random.choice(cron_random_list)

    # verify the cron schedule validity, if submitted
    if kwargs.get("cron_schedule"):
        try:
            validate_cron_schedule(kwargs.get("cron_schedule"))
        except Exception as e:
            get_effective_logger().error(str(e))
            return {
                "payload": {
                    "action": "failure",
                    "response": str(e),
                },
                "status": 500,
            }

    # Update the server and refresh the local copy of the object
    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to update alert_name="{alert_name}" with kwargs="{json.dumps(kwargs, indent=1)}"'
    )

    try:
        newalert_update.update(**kwargs).refresh()
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", alert_name="{alert_name}" with kwargs="{json.dumps(kwargs, indent=1)}"'
        )

    except Exception as e:
        error_msg = f'tenant_id="{tenant_id}", failure to update alert alert_name="{alert_name}", kwargs="{json.dumps(kwargs, indent=1)}" with exception:"{str(e)}"'
        get_effective_logger().error(error_msg)
        raise Exception(error_msg)

    record_url = f"{splunkd_uri}/servicesNS/nobody/trackme/saved/searches/{urllib.parse.quote(alert_name)}/acl"
    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to update alert_name="{alert_name}"'
    )

    try:
        response = requests.post(
            record_url, headers=header, data=alert_acl, verify=False, timeout=600
        )
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", alert_name="{alert_name}"'
        )
    except Exception as e:
        error_msg = f'tenant_id="{tenant_id}", failure to update alert alert_name="{alert_name}", alert_acl="{json.dumps(alert_acl, indent=1)}" with exception:"{str(e)}"'
        get_effective_logger().error(error_msg)
        raise Exception(error_msg)

    return {
        "action": "success",
        "tenant_id": tenant_id,
        "alert_name": alert_name,
        "alert_search": alert_search,
        "alert_owner": alert_acl.get("owner"),
        "report_perms_read": alert_acl.get("perms.read"),
        "report_perms_write": alert_acl.get("perms.write"),
        "description": kwargs.get("description"),
        "is_scheduled": kwargs.get("is_scheduled"),
        "schedule_window": kwargs.get("schedule_window"),
        "dispatch.earliest_time": kwargs.get("dispatch.earliest_time"),
        "dispatch.latest_time": kwargs.get("dispatch.latest_time"),
        "cron_schedule": kwargs.get("cron_schedule"),
    }


def trackme_create_kvcollection(
    session_key, splunkd_uri, tenant_id, collection_name, collection_acl
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    # create a new KVstore collection

    # if the collection is found, print it out
    # if not, then create the collection
    if collection_name not in service.kvstore:
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", attempting to create collection collection_name="{collection_name}"'
        )
        try:
            service.kvstore.create(
                collection_name, **{"app": "trackme", "owner": "nobody"}
            )
            get_effective_logger().info(
                f'tenant_id="{tenant_id}", action="success", collection_name="{collection_name}"'
            )
        except Exception as e:
            get_effective_logger().error(
                f'tenant_id="{tenant_id}", failure to create collection collection_name="{collection_name}" with exception:"{str(e)}"'
            )
            raise Exception(
                f'tenant_id="{tenant_id}", failure to create collection collection_name="{collection_name}" with exception:"{str(e)}"'
            )

    record_url = f"{splunkd_uri}/servicesNS/nobody/trackme/storage/collections/config/{collection_name}/acl"

    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to update collection collection_name="{collection_name}"'
    )
    try:
        response = requests.post(
            record_url,
            headers=header,
            data=collection_acl,
            verify=False,
            timeout=600,
        )
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", collection_name="{collection_name}"'
        )
        return "success"
    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to update collection collection_name="{collection_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_delete_kvcollection(session_key, splunkd_uri, tenant_id, collection_name):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to delete collection collection_name="{collection_name}"'
    )
    try:
        service.kvstore.delete(collection_name)
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", collection_name="{collection_name}"'
        )
        return "success"
    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to delete collection collection_name="{collection_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_create_kvtransform(
    session_key,
    splunkd_uri,
    tenant_id,
    transform_name,
    transform_fields,
    collection_name,
    transform_owner,
    transform_acl,
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    # transforms
    transforms = service.confs["transforms"]

    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to create transforms transforms_name="{transform_name}"'
    )
    try:
        transforms.create(
            name=str(transform_name),
            **{
                "app": "trackme",
                "sharing": "app",
                "external_type": "kvstore",
                "collection": str(collection_name),
                "fields_list": transform_fields,
                "owner": transform_owner,
            },
        )
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", transforms_name="{transform_name}"'
        )
    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to create transforms transforms_name="{transform_name}" with exception:"{str(e)}"'
        )
        raise Exception(
            f'tenant_id="{tenant_id}", failure to create transforms transforms_name="{transform_name}" with exception:"{str(e)}"'
        )

    record_url = f"{splunkd_uri}/servicesNS/admin/trackme/data/transforms/lookups/{transform_name}/acl"

    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to update transforms transforms_name="{transform_name}"'
    )
    try:
        response = requests.post(
            record_url,
            headers=header,
            data=transform_acl,
            verify=False,
            timeout=600,
        )
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", transforms_name="{transform_name}"'
        )
        return "success"
    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to update transforms transforms_name="{transform_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_delete_kvtransform(session_key, splunkd_uri, tenant_id, transform_name):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # transforms
    transforms = service.confs["transforms"]

    # proceed
    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to delete transform transform_name="{transform_name}"'
    )
    try:
        transforms.delete(name=str(transform_name))
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", transform_name="{transform_name}"'
        )
        return "success"
    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to delete transform transform_name="{transform_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_create_macro(
    session_key,
    splunkd_uri,
    tenant_id,
    macro_name,
    macro_definition,
    macro_owner,
    macro_acl,
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    # macros
    macros = service.confs["macros"]

    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to create macro macro_name="{macro_name}"'
    )
    try:
        macros.create(
            name=str(macro_name),
            **{
                "app": "trackme",
                "sharing": "app",
                "definition": str(macro_definition),
                "owner": str(macro_owner),
            },
        )
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", macro_name="{macro_name}"'
        )

    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to create macro macro_name="{macro_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))

    record_url = f"{splunkd_uri}/servicesNS/admin/trackme/data/macros/{macro_name}/acl"

    get_effective_logger().info(
        f'tenant_id="{tenant_id}", attempting to update macro macro_name="{macro_name}"'
    )
    try:
        #
        # Splunkd API needs a couple of seconds to refresh while macros were created
        # In a programmatic context, this may lead the report creation to be failing
        # the function will check the KO status, and wait if needed for a certain amount of time

        # set max failed re-attempt
        max_failures_count = 24
        sleep_time = 5
        creation_success = False
        current_failures_count = 0

        while current_failures_count < max_failures_count and not creation_success:
            try:
                response = requests.post(
                    record_url,
                    headers=header,
                    data=macro_acl,
                    verify=False,
                    timeout=600,
                )
                get_effective_logger().info(
                    f'tenant_id="{tenant_id}", action="success", macro_name="{macro_name}"'
                )
                new_macro = macros[str(macro_name)].get
                get_effective_logger().debug(
                    f'tenant_id="{tenant_id}", macro_name="{macro_name}", response="{new_macro}"'
                )
                creation_success = True
                break

            except Exception as e:
                get_effective_logger().warning(
                    f'tenant_id="{tenant_id}", temporary failure, the macro is not yet available, will sleep and re-attempt, macro macro_name="{macro_name}"'
                )
                time.sleep(sleep_time)
                current_failures_count += 1

                if current_failures_count >= max_failures_count:
                    get_effective_logger().error(
                        f'tenant_id="{tenant_id}", max attempt reached, failure to create macro macro_name="{macro_name}" with exception:"{str(e)}"'
                    )
                    raise Exception(str(e))

        return "success"

    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to update macro macro_name="{macro_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_delete_macro(session_key, splunkd_uri, tenant_id, macro_name):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # macros
    macros = service.confs["macros"]

    try:
        # get the definition first
        macro_definition = macros[macro_name].content["definition"]

        get_effective_logger().info(
            f'tenant_id="{tenant_id}", attempting to delete macro macro_name="{macro_name}", macro_definition="{macro_definition}"'
        )

        # delete
        macros.delete(name=str(macro_name))

        get_effective_logger().info(
            f'tenant_id="{tenant_id}", action="success", macro_name="{macro_name}"'
        )

        return "success"

    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", failure to delete macro macro_name="{macro_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_report_update_enablement(
    session_key, splunkd_uri, tenant_id, report_name, action
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    if action not in ("enable", "disable"):
        raise Exception(
            f'Invalid value for action="{action}", valid options are: enable | disable'
        )

    else:
        record_url = f"{splunkd_uri}/servicesNS/nobody/trackme/saved/searches/{urllib.parse.quote(str(report_name))}/{action}"
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", attempting to {action} report report_name="{report_name}"'
        )
        try:
            response = requests.post(
                record_url, headers=header, verify=False, timeout=600
            )
            get_effective_logger().info(
                f'tenant_id="{tenant_id}", action="success", report_name="{report_name}"'
            )
            return "success"
        except Exception as e:
            get_effective_logger().error(
                f'tenant_id="{tenant_id}", failure to update report report_name="{report_name}" with exception:"{str(e)}"'
            )
            raise Exception(str(e))


def trackme_macro_update_enablement(
    session_key, splunkd_uri, tenant_id, macro_name, action
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # get macros
    macros = service.confs["macros"]

    if action not in ("enable", "disable"):
        raise Exception(
            f'Invalid value for action="{action}", valid options are: enable | disable'
        )

    else:
        if action == "enable":
            kwargs = {"disabled": "false"}
        elif action == "disable":
            kwargs = {"disabled": "true"}

        # update the properties
        macro_update = macros[str(macro_name)]
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", attempting to update macro macro_name="{macro_name}"'
        )
        try:
            macro_update.update(**kwargs).refresh()
            get_effective_logger().info(
                f'tenant_id="{tenant_id}", action="success", macro_name="{macro_name}"'
            )
            return "success"
        except Exception as e:
            get_effective_logger().error(
                f'tenant_id="{tenant_id}", failure to update macro macro_name="{macro_name}" with exception:"{str(e)}"'
            )
            raise Exception(str(e))


def trackme_kvcollection_update_enablement(
    session_key, splunkd_uri, tenant_id, collection_name, action
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    if action not in ("enable", "disable"):
        raise Exception(
            f'Invalid value for action="{action}", valid options are: enable | disable'
        )

    else:
        record_url = f"{splunkd_uri}/servicesNS/nobody/trackme/storage/collections/config/{collection_name}/{action}"

        get_effective_logger().info(
            f'tenant_id="{tenant_id}", attempting to {action} collection collection_name="{collection_name}"'
        )
        try:
            response = requests.post(
                record_url, headers=header, verify=False, timeout=600
            )
            get_effective_logger().info(
                f'tenant_id="{tenant_id}", action="success", collection_name="{collection_name}"'
            )
            return "success"
        except Exception as e:
            get_effective_logger().error(
                f'tenant_id="{tenant_id}", failure to update collection collection_name="{collection_name}" with exception:"{str(e)}"'
            )
            raise Exception(str(e))


def trackme_transform_update_enablement(
    session_key, splunkd_uri, tenant_id, transform_name, action
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # get transforms
    transforms = service.confs["transforms"]

    if action not in ("enable", "disable"):
        raise Exception(
            f'Invalid value for action="{action}", valid options are: enable | disable'
        )

    else:
        if action == "enable":
            kwargs = {"disabled": "false"}
        elif action == "disable":
            kwargs = {"disabled": "true"}

        # update the properties
        transform_update = transforms[str(transform_name)]
        get_effective_logger().info(
            f'tenant_id="{tenant_id}", attempting to update transform="{transform_name}"'
        )
        try:
            transform_update.update(**kwargs).refresh()
            get_effective_logger().info(
                f'tenant_id="{tenant_id}", action="success", transform_name="{transform_name}"'
            )
            return "success"
        except Exception as e:
            get_effective_logger().error(
                f'tenant_id="{tenant_id}", failure to update transforms transform_name="{transform_name}" with exception:"{str(e)}"'
            )
            raise Exception(str(e))


def trackme_audit_event(
    session_key,
    splunkd_uri,
    tenant_id,
    user,
    action,
    change_type,
    object_name,
    object_category,
    object_attrs,
    result,
    comment,
    object_id=None,
):
    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    # Audit

    # set
    url = "%s/services/trackme/v2/audit/audit_events_v2" % splunkd_uri

    # set events list
    audit_events = {
        "action": action,
        "change_type": change_type,
        "object": object_name,
        "object_category": object_category,
        "object_attrs": object_attrs,
        "user": user,
        "result": result,
        "comment": comment,
    }
    if object_id:
        audit_events["object_id"] = object_id

    # set data
    data = {"tenant_id": f"{tenant_id}", "audit_events": [audit_events]}

    # Proceed
    try:
        # Validate data before sending
        try:
            json_data = json.dumps(data)
        except (TypeError, ValueError) as json_error:
            error_message = f'Failed to serialize audit data to JSON, error="{str(json_error)}", data="{data}"'
            get_effective_logger().error(error_message)
            raise Exception(error_message)
        
        response = requests.post(
            url, headers=header, data=json_data, verify=False, timeout=600
        )
        if response.ok:
            get_effective_logger().debug(f'Success audit event, data="{response}"')
            response_json = response.json()
            return response_json
        else:
            error_message = f'Failed to generate an audit event, status_code={response.status_code}, response_text="{response.text}"'
            get_effective_logger().error(error_message)
            raise Exception(error_message)

    except Exception as e:
        error_msg = f'trackme_audit_event has failed, exception="{str(e)}"'
        raise Exception(error_msg)


def trackme_resolve_entity_object_name(service, component, tenant_id, object_id):
    """Resolve the human-readable `object` field of an entity from its
    component KV collection (``kv_trackme_{component}_tenant_{tenant_id}``),
    given the entity's ``_key`` (``object_id``).

    Returns the ``object`` field as a string, or falls back to
    ``str(object_id)`` if the lookup fails or the record has no ``object``
    field. Never raises.

    Used by handlers that need to emit entity-scoped audit events via
    :func:`trackme_audit_event` with ``object=<entity_name>`` so the event
    matches the per-entity "Audit changes" tab filter
    (``object_category=splk-<component>`` AND ``object=<name>`` OR
    ``object_id=<keyid>``).
    """
    try:
        main_collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        record = service.kvstore[main_collection_name].data.query_by_id(object_id)
        if record:
            return record.get("object") or str(object_id)
    except Exception:
        pass
    return str(object_id)


def trackme_audit_flip(
    session_key,
    splunkd_uri,
    tenant_id,
    keyid,
    alias,
    object,
    object_category,
    priority,
    object_state,
    object_previous_state,
    latest_flip_time,
    latest_flip_state,
    anomaly_reason,
    result,
):
    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    # set
    url = "%s/services/trackme/v2/audit/flip_event" % splunkd_uri
    data = {
        "tenant_id": str(tenant_id),
        "keyid": str(keyid),
        "alias": str(alias),
        "object": str(object),
        "object_category": str(object_category),
        "priority": str(priority),
        "object_state": str(object_state),
        "object_previous_state": str(object_previous_state),
        "latest_flip_time": str(latest_flip_time),
        "latest_flip_state": str(latest_flip_state),
        "anomaly_reason": str(anomaly_reason),
        "result": str(result),
    }

    # Proceed
    try:
        response = requests.post(
            url,
            headers=header,
            data=json.dumps(data, indent=1),
            verify=False,
            timeout=600,
        )
        if response.ok:
            get_effective_logger().debug(f'Success flip event, data="{response}"')
            response_json = response.json()
            return response_json
        else:
            error_message = f'Failed to generate a flip event, status_code={response.status_code}, response_text="{response.text}", data="{json.dumps(data, indent=1)}"'
            get_effective_logger().error(error_message)
            raise Exception(error_message)

    except Exception as e:
        error_msg = f'trackme_audit_flip has failed, exception="{str(e)}"'
        raise Exception(error_msg)


def trackme_state_event(
    session_key, splunkd_uri, tenant_id, index, sourcetype, source, record,
    splunkd_timeout=None,
):
    """
    Generate a state event.

    Args:
        session_key: Splunk session key for authentication
        splunkd_uri: Splunkd URI (e.g., https://127.0.0.1:8089)
        tenant_id: Tenant ID
        index: Index name
        sourcetype: Sourcetype name
        source: Source name
        record: Event record data
        splunkd_timeout: Optional timeout in seconds for the splunkd REST call

    Returns:
        Response JSON from the API

    Raises:
        Exception: If the request fails
    """
    if splunkd_timeout is None:
        splunkd_timeout = SPLUNKD_TIMEOUT_DEFAULT

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    # set
    url = "%s/services/trackme/v2/audit/state_event" % splunkd_uri
    data = {
        "tenant_id": str(tenant_id),
        "index": str(index),
        "sourcetype": str(sourcetype),
        "source": str(source),
        "record": record,
    }

    # Proceed
    try:
        response = requests.post(
            url, headers=header, data=json.dumps(data), verify=False, timeout=splunkd_timeout
        )
        if response.ok:
            get_effective_logger().debug(f'Success state event, data="{response}"')
            response_json = response.json()
            return response_json
        else:
            error_message = f'Failed to generate a state event, status_code={response.status_code}, response_text="{response.text}"'
            get_effective_logger().error(error_message)
            raise Exception(error_message)

    except Exception as e:
        error_msg = f'trackme_state_event has failed, exception="{str(e)}"'
        get_effective_logger().error(error_msg)
        raise Exception(error_msg)


# Register multiple handler events at once
def trackme_handler_events(
    session_key, splunkd_uri, tenant_id, handler_events, source, sourcetype
):
    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }

    # set
    url = f"{splunkd_uri}/services/trackme/v2/audit/handler_events"
    data = {
        "tenant_id": str(tenant_id),
        "handler_events": handler_events,
        "source": str(source),
        "sourcetype": str(sourcetype),
    }

    # check if the handler_events is a list, otherwise convert it to a list
    if not isinstance(handler_events, list):
        handler_events = [handler_events]

    # Proceed
    try:
        response = requests.post(
            url, headers=header, data=json.dumps(data), verify=False, timeout=600
        )
        if response.ok:
            get_effective_logger().debug(f'Success handler event, data="{response}"')
            response_json = response.json()
            return response_json
        else:
            error_message = f'Failed to generate a handler event, status_code={response.status_code}, response_text="{response.text}"'
            get_effective_logger().error(error_message)
            raise Exception(error_message)

    except Exception as e:
        error_msg = f'trackme_handler_events has failed, exception="{str(e)}"'
        raise Exception(error_msg)


def trackme_components_register_gen_metrics(
    session_key, splunkd_uri, tenant_id, records
):
    # proceed
    try:
        # get the target index
        tenant_indexes = trackme_idx_for_tenant(
            session_key,
            splunkd_uri,
            tenant_id,
        )

        # Create a dedicated logger for component metrics
        metrics_logger = logging.getLogger("trackme.components.metrics")
        metrics_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not metrics_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_components_register_metrics.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter()
            logging.Formatter.converter = time.gmtime
            filehandler.setFormatter(formatter)
            metrics_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            metrics_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in metrics_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_components_register_metrics.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter()
                logging.Formatter.converter = time.gmtime
                filehandler.setFormatter(formatter)
                metrics_logger.addHandler(filehandler)

        for record in records:
            metrics_logger.info(
                "Metrics - group=components_register_metrics",
                extra={
                    "target_index": tenant_indexes["trackme_metric_idx"],
                    "tenant_id": tenant_id,
                    "component": record.get("component"),
                    "tracker": record.get("tracker"),
                    "metrics_event": json.dumps(record.get("metrics_event")),
                },
            )

        return True

    except Exception as e:
        raise Exception(str(e))


# register the tenant object summary status
def trackme_register_tenant_object_summary(
    session_key,
    splunkd_uri,
    tenant_id,
    component,
    report,
    last_status,
    last_exec,
    last_duration,
    last_result,
    earliest,
    latest,
    splunkd_timeout=None,
):
    """
    Register tenant object summary status.

    Args:
        session_key: Splunk session key for authentication
        splunkd_uri: Splunkd URI (e.g., https://127.0.0.1:8089)
        tenant_id: Tenant ID
        component: Component name
        report: Report name
        last_status: Last execution status
        last_exec: Last execution time
        last_duration: Last execution duration
        last_result: Last execution result
        earliest: Search earliest time
        latest: Search latest time
        splunkd_timeout: Optional timeout in seconds for the splunkd SDK connection

    Raises:
        Exception: If the connection or update fails
    """
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # Extract hostname and port, with defaults for robustness
    hostname = parsed_url.hostname or "127.0.0.1"
    port = parsed_url.port or 8089

    # get service
    try:
        service = client.connect(
            owner="nobody",
            app="trackme",
            host=hostname,
            port=port,
            token=session_key,
            timeout=splunkd_timeout if splunkd_timeout is not None else SPLUNKD_TIMEOUT_DEFAULT,
        )

        # Register the object summary in the dedicated exec summary collection
        collection_exec_summary_name = "kv_trackme_virtual_tenants_exec_summary"
        collection_exec_summary = service.kvstore[collection_exec_summary_name]
    except Exception as e:
        error_msg = f'trackme_register_tenant_object_summary connection failed, host={hostname}, port={port}, exception="{str(e)}"'
        get_effective_logger().error(error_msg)
        raise Exception(error_msg)

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().debug(
        f'Starting function trackme_register_tenant_object_summary, tenant_id="{tenant_id}", component="{component}", report="{report}", last_exec="{last_exec}", last_status="{last_status}", last_duration="{last_duration}", last_result="{last_result}", earliest="{earliest}", latest="{latest}"'
    )

    # Retrieve the exec summary record from the dedicated collection
    try:
        exec_summary_records = collection_exec_summary.data.query(query=json.dumps(query_string))
        if exec_summary_records:
            exec_summary_record = exec_summary_records[0]
            exec_summary_key = exec_summary_record.get("_key")
        else:
            exec_summary_record = None
            exec_summary_key = None
        get_effective_logger().debug(
            f'The exec_summary record lookup completed, tenant_id="{tenant_id}", found={exec_summary_key is not None}, originating_report="{report}"'
        )
    except Exception as e:
        exec_summary_record = None
        exec_summary_key = None
        get_effective_logger().debug(
            f'No exec_summary record found for tenant_id="{tenant_id}", originating_report="{report}", will create a new one'
        )

    # try to load the dict
    try:
        tenant_objects_exec_summary = json.loads(
            exec_summary_record.get("tenant_objects_exec_summary")
        ) if exec_summary_record else None
    except Exception as e:
        tenant_objects_exec_summary = None

    # logging debug
    get_effective_logger().debug(
        f'tenant_id="{tenant_id}", component="{component}", report="{report}", Retrieve tenant_objects_exec_summary="{tenant_objects_exec_summary}"'
    )

    # add to existing disct
    if tenant_objects_exec_summary and tenant_objects_exec_summary != "None":
        try:
            # log
            get_effective_logger().debug(
                f'tenant_id="{tenant_id}", component="{component}", report="{report}", Updating the existing record in the dictionary, summary_dict="{json.dumps(tenant_objects_exec_summary, indent=1)}"'
            )

            report_dict = tenant_objects_exec_summary[report]

            # Update the existing record in the dict
            report_dict["component"] = str(component)
            report_dict["last_status"] = str(last_status)
            report_dict["last_exec"] = str(last_exec)
            report_dict["last_duration"] = round(float(last_duration), 3)
            report_dict["last_result"] = str(last_result)
            report_dict["earliest"] = str(earliest)
            report_dict["latest"] = str(latest)
            # persistent
            report_dict["persistent"] = "False"

            # sort report_dict alphabetically
            tenant_objects_exec_summary[report] = dict(sorted(report_dict.items()))

        except Exception as e:
            # set the dict
            summary_dict = {
                report: {
                    "component": component,
                    "last_status": last_status,
                    "last_exec": last_exec,
                    "last_duration": last_duration,
                    "last_result": last_result,
                    "earliest": earliest,
                    "latest": latest,
                }
            }

            # log
            get_effective_logger().debug(
                f'tenant_id="{tenant_id}", component="{component}", report="{report}", Adding a new record to the dictionary, summary_dict="{json.dumps(summary_dict, indent=1)}"'
            )

            # Update with a new record
            tenant_objects_exec_summary.update(summary_dict)

    # Empty dict
    else:
        # Set the dict
        tenant_objects_exec_summary = {
            report: {
                "component": component,
                "last_status": last_status,
                "last_exec": last_exec,
                "last_duration": last_duration,
                "last_result": last_result,
                "earliest": earliest,
                "latest": latest,
            }
        }

        # log
        get_effective_logger().debug(
            f'tenant_id="{tenant_id}", component="{component}", report="{report}", Creating a new dictionary, tenant_objects_exec_summary="{json.dumps(tenant_objects_exec_summary, indent=1)}"'
        )

    # generate metrics unconditionally for every execution
    components_register_metrics_gen_start = time.time()

    if last_status == "success":
        last_status_num = 1
    elif last_status == "failure":
        last_status_num = 2
    else:
        last_status_num = 3

    if last_duration:
        try:
            last_duration = round(float(last_duration), 3)
        except Exception as e:
            last_duration = 0
    else:
        last_duration = 0

    try:
        components_register_metrics = (
            trackme_components_register_gen_metrics(
                session_key,
                splunkd_uri,
                tenant_id,
                [
                    {
                        "tenant_id": tenant_id,
                        "component": component,
                        "tracker": report,
                        "metrics_event": {
                            "status": last_status_num,
                            "runtime": last_duration,
                        },
                    }
                ],
            )
        )
        get_effective_logger().info(
            f'context="components_register_gen_metrics", tenant_id="{tenant_id}", function trackme_components_register_gen_metrics success {components_register_metrics}, run_time={round(time.time()-components_register_metrics_gen_start, 3)}'
        )
    except Exception as e:
        get_effective_logger().error(
            f'context="components_register_gen_metrics", tenant_id="{tenant_id}", function trackme_components_register_gen_metrics failed with exception {str(e)}'
        )

    # logging debug
    get_effective_logger().debug(
        f'tenant_id="{tenant_id}", component="{component}", report="{report}", Ended processing, tenant_objects_exec_summary="{tenant_objects_exec_summary}"'
    )

    try:
        exec_summary_data = {
            "tenant_id": tenant_id,
            "tenant_objects_exec_summary": json.dumps(
                tenant_objects_exec_summary, indent=2
            ),
        }
        if exec_summary_key:
            collection_exec_summary.data.update(
                str(exec_summary_key), json.dumps(exec_summary_data)
            )
        else:
            collection_exec_summary.data.insert(json.dumps(exec_summary_data))

    except Exception as e:
        get_effective_logger().error(
            f'failure while trying to update the exec summary KVstore record, exception="{str(e)}"'
        )


# register the tenant object summary status (do not gen metrics, non persistent)
def trackme_register_tenant_object_summary_gen_non_persistent(
    session_key,
    splunkd_uri,
    tenant_id,
    component,
    report,
    last_status,
    last_exec,
    last_duration,
    last_result,
    earliest,
    latest,
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # Register the object summary in the dedicated exec summary collection
    collection_exec_summary_name = "kv_trackme_virtual_tenants_exec_summary"
    collection_exec_summary = service.kvstore[collection_exec_summary_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().debug(
        f'Starting function trackme_register_tenant_object_summary, tenant_id="{tenant_id}", component="{component}", report="{report}", last_exec="{last_exec}", last_status="{last_status}", last_duration="{last_duration}", last_result="{last_result}", earliest="{earliest}", latest="{latest}"'
    )

    # Retrieve the exec summary record from the dedicated collection
    try:
        exec_summary_records = collection_exec_summary.data.query(query=json.dumps(query_string))
        if exec_summary_records:
            exec_summary_record = exec_summary_records[0]
            exec_summary_key = exec_summary_record.get("_key")
        else:
            exec_summary_record = None
            exec_summary_key = None
        get_effective_logger().debug(
            f'The exec_summary record lookup completed, tenant_id="{tenant_id}", found={exec_summary_key is not None}, originating_report="{report}"'
        )
    except Exception as e:
        exec_summary_record = None
        exec_summary_key = None
        get_effective_logger().debug(
            f'No exec_summary record found for tenant_id="{tenant_id}", originating_report="{report}", will create a new one'
        )

    # try to load the dict
    try:
        tenant_objects_exec_summary = json.loads(
            exec_summary_record.get("tenant_objects_exec_summary")
        ) if exec_summary_record else None
    except Exception as e:
        tenant_objects_exec_summary = None

    # logging debug
    get_effective_logger().debug(
        f'tenant_id="{tenant_id}", component="{component}", report="{report}", Retrieve tenant_objects_exec_summary="{tenant_objects_exec_summary}"'
    )

    # add to existing disct
    if tenant_objects_exec_summary and tenant_objects_exec_summary != "None":
        try:
            # log
            get_effective_logger().debug(
                f'tenant_id="{tenant_id}", component="{component}", report="{report}", Updating the existing record in the dictionary, summary_dict="{json.dumps(tenant_objects_exec_summary, indent=1)}"'
            )

            report_dict = tenant_objects_exec_summary[report]

            # Update the existing record in the dict
            report_dict["component"] = str(component)
            report_dict["last_status"] = str(last_status)
            report_dict["last_exec"] = str(last_exec)
            report_dict["last_duration"] = round(float(last_duration), 3)
            report_dict["last_result"] = str(last_result)
            report_dict["earliest"] = str(earliest)
            report_dict["latest"] = str(latest)
            # persistent
            report_dict["persistent"] = "False"

            # sort report_dict alphabetically
            tenant_objects_exec_summary[report] = dict(sorted(report_dict.items()))

        except Exception as e:
            # set the dict
            summary_dict = {
                report: {
                    "component": component,
                    "last_status": last_status,
                    "last_exec": last_exec,
                    "last_duration": last_duration,
                    "last_result": last_result,
                    "earliest": earliest,
                    "latest": latest,
                }
            }

            # log
            get_effective_logger().debug(
                f'tenant_id="{tenant_id}", component="{component}", report="{report}", Adding a new record to the dictionary, summary_dict="{json.dumps(summary_dict, indent=1)}"'
            )

            # Update with a new record
            tenant_objects_exec_summary.update(summary_dict)

    # Empty dict
    else:
        # Set the dict
        tenant_objects_exec_summary = {
            report: {
                "component": component,
                "last_status": last_status,
                "last_exec": last_exec,
                "last_duration": last_duration,
                "last_result": last_result,
                "earliest": earliest,
                "latest": latest,
            }
        }

        # log
        get_effective_logger().debug(
            f'tenant_id="{tenant_id}", component="{component}", report="{report}", Creating a new dictionary, tenant_objects_exec_summary="{json.dumps(tenant_objects_exec_summary, indent=1)}"'
        )

    # logging debug
    get_effective_logger().debug(
        f'tenant_id="{tenant_id}", component="{component}", report="{report}", Ended processing, tenant_objects_exec_summary="{tenant_objects_exec_summary}"'
    )

    try:
        exec_summary_data = {
            "tenant_id": tenant_id,
            "tenant_objects_exec_summary": json.dumps(
                tenant_objects_exec_summary, indent=2
            ),
        }
        if exec_summary_key:
            collection_exec_summary.data.update(
                str(exec_summary_key), json.dumps(exec_summary_data)
            )
        else:
            collection_exec_summary.data.insert(json.dumps(exec_summary_data))

    except Exception as e:
        get_effective_logger().error(
            f'failure while trying to update the exec summary KVstore record, exception="{str(e)}"'
        )


# register the tenant object summary status (persistent)
def trackme_register_tenant_object_summary_gen_persistent(
    session_key,
    splunkd_uri,
    tenant_id,
    component,
    report,
    last_status,
    last_exec,
    last_duration,
    last_result,
    earliest,
    latest,
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # Register the object summary in the dedicated exec summary collection
    collection_exec_summary_name = "kv_trackme_virtual_tenants_exec_summary"
    collection_exec_summary = service.kvstore[collection_exec_summary_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().debug(
        f'Starting function trackme_register_tenant_object_summary_from_splunkremotesearch, tenant_id="{tenant_id}", component="{component}", report="{report}", last_exec="{last_exec}", last_status="{last_status}", last_duration="{last_duration}", last_result="{last_result}", earliest="{earliest}", latest="{latest}"'
    )

    # Retrieve the exec summary record from the dedicated collection
    try:
        exec_summary_records = collection_exec_summary.data.query(query=json.dumps(query_string))
        if exec_summary_records:
            exec_summary_record = exec_summary_records[0]
            exec_summary_key = exec_summary_record.get("_key")
        else:
            exec_summary_record = None
            exec_summary_key = None
        get_effective_logger().debug(
            f'The exec_summary record lookup completed, tenant_id="{tenant_id}", found={exec_summary_key is not None}, originating_report="{report}"'
        )
    except Exception as e:
        exec_summary_record = None
        exec_summary_key = None
        get_effective_logger().debug(
            f'No exec_summary record found for tenant_id="{tenant_id}", originating_report="{report}", will create a new one'
        )

    # try to load the dict
    try:
        tenant_objects_exec_summary = json.loads(
            exec_summary_record.get("tenant_objects_exec_summary")
        ) if exec_summary_record else None
    except Exception as e:
        tenant_objects_exec_summary = None

    # logging debug
    get_effective_logger().debug(
        f'tenant_id="{tenant_id}", component="{component}", report="{report}", Retrieve tenant_objects_exec_summary="{tenant_objects_exec_summary}"'
    )

    # add to existing disct
    if tenant_objects_exec_summary and tenant_objects_exec_summary != "None":
        try:
            # log
            get_effective_logger().debug(
                f'tenant_id="{tenant_id}", component="{component}", report="{report}", Updating the existing record in the dictionary, summary_dict="{json.dumps(tenant_objects_exec_summary, indent=1)}"'
            )

            report_dict = tenant_objects_exec_summary[report]

            # Update the existing record in the dict
            report_dict["component"] = str(component)
            report_dict["last_status"] = str(last_status)
            report_dict["last_exec"] = str(last_exec)
            report_dict["last_duration"] = round(float(last_duration), 3)
            report_dict["last_result"] = str(last_result)
            report_dict["earliest"] = str(earliest)
            report_dict["latest"] = str(latest)
            # persistent
            report_dict["persistent"] = "True"

            # sort report_dict alphabetically
            tenant_objects_exec_summary[report] = dict(sorted(report_dict.items()))

        except Exception as e:
            # set the dict
            summary_dict = {
                report: {
                    "component": component,
                    "last_status": last_status,
                    "last_exec": last_exec,
                    "last_duration": last_duration,
                    "last_result": last_result,
                    "earliest": earliest,
                    "latest": latest,
                }
            }

            # log
            get_effective_logger().debug(
                f'tenant_id="{tenant_id}", component="{component}", report="{report}", Adding a new record to the dictionary, summary_dict="{json.dumps(summary_dict, indent=1)}"'
            )

            # Update with a new record
            tenant_objects_exec_summary.update(summary_dict)

    # Empty dict
    else:
        # Set the dict
        tenant_objects_exec_summary = {
            report: {
                "component": component,
                "last_status": last_status,
                "last_exec": last_exec,
                "last_duration": last_duration,
                "last_result": last_result,
                "earliest": earliest,
                "latest": latest,
            }
        }

        # log
        get_effective_logger().debug(
            f'tenant_id="{tenant_id}", component="{component}", report="{report}", Creating a new dictionary, tenant_objects_exec_summary="{json.dumps(tenant_objects_exec_summary, indent=1)}"'
        )

    # generate metrics unconditionally for every execution
    components_register_metrics_gen_start = time.time()

    if last_status == "success":
        last_status_num = 1
    elif last_status == "failure":
        last_status_num = 2
    else:
        last_status_num = 3

    if last_duration:
        try:
            last_duration = round(float(last_duration), 3)
        except Exception as e:
            last_duration = 0
    else:
        last_duration = 0

    try:
        components_register_metrics = (
            trackme_components_register_gen_metrics(
                session_key,
                splunkd_uri,
                tenant_id,
                [
                    {
                        "tenant_id": tenant_id,
                        "component": component,
                        "tracker": report,
                        "metrics_event": {
                            "status": last_status_num,
                            "runtime": last_duration,
                        },
                    }
                ],
            )
        )
        get_effective_logger().info(
            f'context="components_register_gen_metrics", tenant_id="{tenant_id}", function trackme_register_tenant_object_summary_from_splunkremotesearch success {components_register_metrics}, run_time={round(time.time()-components_register_metrics_gen_start, 3)}'
        )
    except Exception as e:
        get_effective_logger().error(
            f'context="components_register_gen_metrics", tenant_id="{tenant_id}", function trackme_register_tenant_object_summary_from_splunkremotesearch failed with exception {str(e)}'
        )

    # logging debug
    get_effective_logger().debug(
        f'tenant_id="{tenant_id}", component="{component}", report="{report}", Ended processing, tenant_objects_exec_summary="{tenant_objects_exec_summary}"'
    )

    try:
        exec_summary_data = {
            "tenant_id": tenant_id,
            "tenant_objects_exec_summary": json.dumps(
                tenant_objects_exec_summary, indent=2
            ),
        }
        if exec_summary_key:
            collection_exec_summary.data.update(
                str(exec_summary_key), json.dumps(exec_summary_data)
            )
        else:
            collection_exec_summary.data.insert(json.dumps(exec_summary_data))

    except Exception as e:
        get_effective_logger().error(
            f'failure while trying to update the exec summary KVstore record, exception="{str(e)}"'
        )


# return the tenant object summary status for the last execution registered
def trackme_return_tenant_object_summary(
    session_key, splunkd_uri, tenant_id, component, report
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # Read the object summary from the dedicated exec summary collection
    collection_exec_summary_name = "kv_trackme_virtual_tenants_exec_summary"
    collection_exec_summary = service.kvstore[collection_exec_summary_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().debug(
        f'Starting function trackme_return_tenant_object_summary, tenant_id="{tenant_id}", component="{component}", report="{report}"'
    )

    try:
        exec_summary_records = collection_exec_summary.data.query(query=json.dumps(query_string))
        if exec_summary_records:
            exec_summary_record = exec_summary_records[0]
        else:
            exec_summary_record = None
        get_effective_logger().debug(
            f'The exec_summary record lookup completed, tenant_id="{tenant_id}", found={exec_summary_record is not None}, originating_report="{report}"'
        )
    except Exception as e:
        exec_summary_record = None
        get_effective_logger().error(
            f'The exec_summary record was not found in the collection, tenant_id="{tenant_id}", originating_report="{report}"'
        )

    if exec_summary_record:
        # try to load the dict
        try:
            tenant_objects_exec_summary = json.loads(
                exec_summary_record.get("tenant_objects_exec_summary")
            )
        except Exception as e:
            tenant_objects_exec_summary = None

        # load
        if tenant_objects_exec_summary and tenant_objects_exec_summary != "None":
            # logging debug
            get_effective_logger().debug(
                f'function trackme_return_tenant_object_summary, tenant_id="{tenant_id}", component="{component}", report="{report}", Retrieve tenant_objects_exec_summary="{json.dumps(tenant_objects_exec_summary.get(report), indent=2)}"'
            )

            # return the dict
            return tenant_objects_exec_summary.get(report)

        # Empty dict
        else:
            return {
                "component": component,
                "last_status": "unknown",
                "last_exec": "unknown",
                "last_duration": "unknown",
                "last_result": "unknown",
                "earliest": "unknown",
                "latest": "unknown",
            }

    # No record found
    else:
        return {
            "component": component,
            "last_status": "unknown",
            "last_exec": "unknown",
            "last_duration": "unknown",
            "last_result": "unknown",
            "earliest": "unknown",
            "latest": "unknown",
        }


# delete a tenant object summary record
def trackme_delete_tenant_object_summary(
    session_key, splunkd_uri, tenant_id, component, report
):
    parsed_url = urllib.parse.urlparse(splunkd_uri)

    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )

    # Delete the object summary from the dedicated exec summary collection
    collection_exec_summary_name = "kv_trackme_virtual_tenants_exec_summary"
    collection_exec_summary = service.kvstore[collection_exec_summary_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().debug(
        f'Starting function trackme_delete_tenant_object_summary, tenant_id="{tenant_id}", component="{component}", report="{report}"'
    )

    try:
        exec_summary_records = collection_exec_summary.data.query(query=json.dumps(query_string))
        if exec_summary_records:
            exec_summary_record = exec_summary_records[0]
            exec_summary_key = exec_summary_record.get("_key")
        else:
            exec_summary_record = None
            exec_summary_key = None
        get_effective_logger().debug(
            f'The exec_summary record lookup completed, tenant_id="{tenant_id}", found={exec_summary_key is not None}, originating_report="{report}"'
        )
    except Exception as e:
        exec_summary_record = None
        exec_summary_key = None
        get_effective_logger().error(
            f'The exec_summary record was not found in the collection, tenant_id="{tenant_id}", originating_report="{report}"'
        )

    if exec_summary_record and exec_summary_key:
        # try to load the dict
        try:
            tenant_objects_exec_summary = json.loads(
                exec_summary_record.get("tenant_objects_exec_summary")
            )
        except Exception as e:
            tenant_objects_exec_summary = None

        # load
        if tenant_objects_exec_summary and tenant_objects_exec_summary != "None":
            # logging debug
            get_effective_logger().debug(
                f'function trackme_delete_tenant_object_summary, tenant_id="{tenant_id}", component="{component}", report="{report}", Retrieve tenant_objects_exec_summary="{json.dumps(tenant_objects_exec_summary.get(report), indent=2)}"'
            )

            # delete the record from the dict
            tenant_objects_exec_summary.pop(report, None)

            # update the exec summary record
            exec_summary_data = {
                "tenant_id": tenant_id,
                "tenant_objects_exec_summary": json.dumps(
                    tenant_objects_exec_summary, indent=2
                ),
            }

            # update the KVstore record
            try:
                collection_exec_summary.data.update(
                    str(exec_summary_key), json.dumps(exec_summary_data)
                )
                get_effective_logger().info(
                    f'function trackme_delete_tenant_object_summary, tenant_id="{tenant_id}", report="{report}", register summary record was successfully purged'
                )
                return "success"

            except Exception as e:
                get_effective_logger().error(
                    f'function trackme_delete_tenant_object_summary, tenant_id="{tenant_id}", report="{report}", Failure to remove the register summary record, exception="{str(e)}"'
                )
                return "failure"

        # Empty dict
        else:
            get_effective_logger().info(
                f'function trackme_delete_tenant_object_summary, found no record to be purged in the register object summary for tenant_id="{tenant_id}"'
            )


# Return the Elastic Source search to be executed depending on the various options
def trackme_return_elastic_exec_search(
    search_mode,
    search_constraint,
    object,
    data_index,
    data_sourcetype,
    tenant_id,
    register_component,
    wrapper_name,
):

    # init remote
    remote = False

    # init core_search
    core_search = None

    # if search_mode starts by remote_
    if search_mode.startswith("remote_"):

        # set remote to True
        remote = True

        # extract using rex
        get_effective_logger().debug(f'search_constraint="{search_constraint}"')
        remote_matches = re.match(
            r"(account\=\s{0,}\"{0,1}[^\|]+\"{0,1})\s{0,}\|\s{0,}(.*)",
            search_constraint,
        )
        if remote_matches:
            remote_target = remote_matches.group(1).replace('\\"', '"')
            search_constraint = remote_matches.group(2)
        else:
            get_effective_logger().error(
                f'invalid search, account or search constraint could not be extracted, search_constraint="{search_constraint}"'
            )
            raise Exception(
                f'invalid search, account or search constraint could not be extracted, search_constraint="{search_constraint}"'
            )

    if search_mode in ("tstats", "remote_tstats"):
        core_search = remove_leading_spaces(
            f"""\
            | tstats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, count as data_eventcount, dc(host) as dcount_host where {search_constraint} by _time, index, sourcetype span=30s
            | eval data_last_ingestion_lag_seen=data_last_ingest-data_last_time_seen
            | eval spantime=data_last_ingest | eventstats max(data_last_time_seen) as data_last_time_seen, max(dcount_host) as global_dcount_host | eval spantime=if(spantime>=(now()-300), spantime, null())
            | eventstats sum(data_eventcount) as eventcount_5m, avg(data_last_ingestion_lag_seen) as latency_5m, avg(dcount_host) as dcount_host_5m by spantime
            | stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m,
            latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m,
            latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, 
            max(data_last_ingest) as data_last_ingest, min(data_first_time_seen) as data_first_time_seen, max(data_last_time_seen) as data_last_time_seen, avg(data_last_ingestion_lag_seen) as data_last_ingestion_lag_seen, sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host
            | eval dcount_host=round(global_dcount_host, 0)
            | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)                
            | eval object="{object}", data_index="{data_index}", data_sourcetype="{data_sourcetype}"
            """
        )

    elif search_mode in ("raw", "remote_raw"):
        core_search = remove_leading_spaces(
            f"""\
            {search_constraint}
            | eval ingest_lag=_indextime-_time
            | eventstats max(_indextime) as data_last_ingest, max(_time) as data_last_time_seen
            | eval spantime=data_last_ingest | eval spantime=if(spantime>=(now()-300), spantime, null())
            | eventstats count as eventcount_5m, avg(ingest_lag) as latency_5m, dc(host) as dcount_host_5m by spantime
            | stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m,
            latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m,
            latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, 
            max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, avg(ingest_lag) as data_last_ingestion_lag_seen, count as data_eventcount, dc(host) as global_dcount_host
            | eval dcount_host=round(global_dcount_host, 0)
            | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)
            | eval object="{object}", data_index="{data_index}", data_sourcetype="{data_sourcetype}"
            """
        )

    elif search_mode in ("mpreview", "remote_mpreview"):
        core_search = remove_leading_spaces(
            f"""\
            | mpreview {search_constraint}
            | eventstats max(_time) as data_last_time_seen
            | eval spantime=data_last_time_seen | eval spantime=if(spantime>=(now()-300), spantime, null())
            | eventstats count as eventcount_5m, dc(host) as dcount_host_5m by spantime
            | stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m,
            latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m,
            latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m, 
            max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, count as data_eventcount, dc(host) as global_dcount_host
            | eval data_last_ingest=data_last_time_seen
            | eval dcount_host=round(global_dcount_host, 0)
            | eval object="{object}", data_index="{data_index}", data_sourcetype="{data_sourcetype}"
            """
        )

    elif search_mode in ("from", "remote_from"):

        if re.match("datamodel:", str(search_constraint)):
            core_search = remove_leading_spaces(
                f"""\
                | from {search_constraint}
                | eval ingest_lag=_indextime-_time
                | eventstats max(_indextime) as data_last_ingest, max(_time) as data_last_time_seen
                | eval spantime=data_last_ingest | eval spantime=if(spantime>=(now()-300), spantime, null())
                | eventstats count as eventcount_5m, avg(ingest_lag) as latency_5m, dc(host) as dcount_host_5m by spantime
                | stats latest(eventcount_5m) as latest_eventcount_5m, avg(eventcount_5m) as avg_eventcount_5m, stdev(eventcount_5m) as stdev_eventcount_5m, perc95(eventcount_5m) as perc95_eventcount_5m,
                latest(latency_5m) as latest_latency_5m, avg(latency_5m) as avg_latency_5m, stdev(latency_5m) as stdev_latency_5m, perc95(latency_5m) as perc95_latency_5m,
                latest(dcount_host_5m) as latest_dcount_host_5m, avg(dcount_host_5m) as avg_dcount_host_5m, stdev(dcount_host_5m) as stdev_dcount_host_5m, perc95(dcount_host_5m) as perc95_dcount_host_5m,
                max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, avg(ingest_lag) as data_last_ingestion_lag_seen, count as data_eventcount, dc(host) as global_dcount_host
                | eval dcount_host=round(global_dcount_host, 0)
                | eval data_last_ingestion_lag_seen=round(data_last_ingestion_lag_seen, 0)
                | eval object="{object}", data_index="{data_index}", data_sourcetype="{data_sourcetype}"
                """
            )

        if re.match("lookup:", str(search_constraint)):
            core_search = remove_leading_spaces(
                f"""\
                | from {search_constraint}
                | eventstats max(_time) as indextime | eval _indextime=if(isnum(_indextime), _indextime, indextime) | fields - indextime
                | eval host=if(isnull(host), "none", host)
                | stats max(_indextime) as data_last_ingest, min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, count as data_eventcount, dc(host) as dcount_host
                | eval latest_eventcount_5m=data_eventcount
                | eval object="{object}", data_index="{data_index}", data_sourcetype="{data_sourcetype}"
                """
            )

    elif search_mode in ("mstats", "remote_mstats"):

        core_search = remove_leading_spaces(
            f"""\
            | mstats latest(_value) as value where {search_constraint} by host, metric_name span=1m 
            | stats min(_time) as data_first_time_seen, max(_time) as data_last_time_seen, dc(metric_name) as data_eventcount, dc(host) as global_dcount_host
            | eval data_last_ingest=data_last_time_seen, data_last_ingestion_lag_seen=now()-data_last_time_seen
            | eval object="{object}", data_index="{data_index}", data_sourcetype="{data_sourcetype}"
            """
        )

    # Conditional components based on register_component
    register_component_part = (
        f' register_component="True" tenant_id="{tenant_id}" component="splk-dsm" report="{wrapper_name}"'
        if register_component == "True"
        else ""
    )

    # Final assembly of the query, including handling for remote mode
    if remote:
        # escape double quotes in core_search
        core_search = core_search.replace('"', '\\"')
        query = remove_leading_spaces(
            f"""\
            | splunkremotesearch {remote_target} search="{core_search}" {register_component_part}
            | `trackme_elastic_dedicated_tracker("{tenant_id}")` 
            | eval tenant_id="{tenant_id}" 
            | stats count as report_entities_count by tenant_id 
            | `register_tenant_component_summary({tenant_id}, dsm)`                
            """
        )

    else:
        # Standard query format for non-remote mode
        query = remove_leading_spaces(
            f"""\
            {core_search}
            | `trackme_elastic_dedicated_tracker("{tenant_id}")`
            | eval tenant_id="{tenant_id}"
            | stats count as report_entities_count by tenant_id
            | `register_tenant_component_summary({tenant_id}, dsm)`
            """
        )

    if not core_search:
        error_msg = f'search_mode="{search_mode}", search_constraint="{search_constraint}", data_index="{data_index}", data_sourcetype="{data_sourcetype}", wrapper_name="{wrapper_name}", register_component="{register_component}", failed to generate a valid search'
        get_effective_logger().error(error_msg)
        raise Exception(error_msg)

    return query


def trackme_register_tenant_component_summary(
    session_key, splunkd_uri, tenant_id, component
):

    # if the component is submitted with a prefix, extract the component name
    component_segments = component.split("-")
    if len(component_segments) >= 2:
        extracted_component = component_segments[1]
    else:
        extracted_component = component

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }

    # data
    data = {
        "tenant_id": tenant_id,
        "component": extracted_component,
    }

    # Add the vtenant account
    url = f"{splunkd_uri}/services/trackme/v2/component/write/component_summary_update"

    # Proceed
    try:
        response = requests.post(
            url,
            headers=header,
            data=json.dumps(data),
            verify=False,
            timeout=600,
        )

        if response.status_code not in (200, 201, 204):
            msg = f'tenant_id="{tenant_id}", component="{extracted_component}", function trackme_register_tenant_component_summary has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
            raise Exception(msg)

        else:
            get_effective_logger().info(
                f'tenant_id="{tenant_id}", component="{extracted_component}", function trackme_register_tenant_component_summary has succeeded, response.status_code="{response.status_code}", response.json="{json.dumps(response.json(), indent=2)}"'
            )
            return response.json()

    except Exception as e:
        error_msg = f'tenant_id="{tenant_id}", component="{extracted_component}", function trackme_register_tenant_component_summary has failed, exception="{str(e)}"'
        raise Exception(error_msg)


def trackme_refresh_component_summary_async(
    session_key, splunkd_uri, tenant_id, component, object_id=None, logger_=None,
):
    """
    Asynchronously refresh the cached <component>_extended_stats blob in
    kv_trackme_virtual_tenants_entities_summary. The blob drives the Single
    Value cards on Tenant Home and is read by `trackmegetcoll mode=cachedstats`.

    Score-only mutations (false positive, manual score influence, outlier
    false positive) do not update entity KV records — they only write a
    score event and the score cache. Without an explicit refresh here, the
    cached summary stays stale until the next per-tenant per-component
    scheduled tracker fires (or the 15-minute staleness fallback in
    trackmegetcoll), causing the SVs to disagree with the entity table.

    Runs in a daemon thread; non-blocking; fail-open (logs a warning on
    error). Returns the started thread; callers may ignore it.
    """
    log = logger_ if logger_ is not None else logging

    def _runner():
        try:
            trackme_register_tenant_component_summary(
                session_key, splunkd_uri, tenant_id, component,
            )
        except Exception as ex:
            log.warning(
                f'task="refresh_component_summary_after_score_change" failed, '
                f'tenant_id="{tenant_id}", component="{component}", '
                f'object_id="{object_id}", exception="{str(ex)}"'
            )

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return t


def trackme_send_to_tcm(session_key, splunkd_uri, resp_dict, http_mode, http_service):
    """
    Send the transaction to TrackMe Configuration Manager
    """

    # Ensure splunkd_uri starts with "https://"
    if not splunkd_uri.startswith("https://"):
        splunkd_uri = f"https://{splunkd_uri}"

    # Build header and target URL
    headers = CaseInsensitiveDict()
    headers["Authorization"] = f"Splunk {session_key}"
    headers["Content-Type"] = "application/json"
    target_url = f"{splunkd_uri}/services/trackme_conf_manager/v1/conf_manager_receiver"

    # Create a requests session for better performance
    session = requests.Session()
    session.headers.update(headers)

    data = {
        "transaction_request": resp_dict,
        "transaction_http_mode": http_mode,
        "transaction_http_service": http_service,
    }

    try:
        # Use a context manager to handle the request
        with session.post(target_url, data=json.dumps(data), verify=False) as response:
            if response.ok:
                get_effective_logger().debug(
                    f'Success sending the transaction to TCM, data="{response}"'
                )
                response_json = response.json()
                return response_json
            else:
                error_message = f'Failed to send the transaction to TCM, status_code={response.status_code}, response_text="{response.text}"'
                get_effective_logger().error(error_message)
                raise Exception(error_message)

    except Exception as e:
        error_message = f'Failed to send the transaction to TCM, exception="{str(e)}"'
        get_effective_logger().error(error_message)
        raise Exception(error_message)


def run_splunk_search(service, search_query, search_params, max_retries, sleep_time=5, sample_ratio=None):
    """
    Executes a Splunk search with a retry mechanism and progressive backoff.

    :param search_query: The Splunk search query to execute.
    :param search_params: Parameters for the search query.
    :param max_retries: Maximum number of retries for the search.
    :param sleep_time: Base time to wait between retries in seconds.
    :param sample_ratio: The sample ratio to use for the search.
    :return: A reader object with the search results.
    """

    # ensure preview is set to False in search_params or results may appear to be duplicated
    search_params["preview"] = False

    # Enforce JSON output mode. This function always wraps the response in a
    # splunklib.results.JSONResultsReader, so the underlying export stream MUST
    # be JSON. Splunk's jobs/export endpoint defaults to XML when output_mode
    # is not provided, which causes JSONResultsReader to raise
    # "Expecting value: line 1 column 1 (char 0)" on the first XML line.
    # Forcing it here protects all callers from that latent failure mode.
    search_params["output_mode"] = "json"

    # if sample_ratio is provided, set the sample_ratio in search_params
    if sample_ratio:
        search_params["sample_ratio"] = sample_ratio

    current_retries = 0
    total_wait_time = 0  # Track total time spent waiting
    max_total_wait_time = 900  # 15 minutes in seconds
    last_exception = None  # Track the last exception that occurred

    while current_retries < max_retries:
        try:
            search_results = service.jobs.export(search_query, **search_params)
            return results.JSONResultsReader(search_results)
        except Exception as e:
            last_exception = str(e)  # Store the exception message
            if "maximum number of concurrent historical searches" in str(
                e
            ) or "This search could not be dispatched because the role-based concurrency limit of historical searches" in str(
                e
            ):
                current_retries += 1

                # Calculate progressive backoff sleep time
                # Use linear progression to maximize attempts within 15-minute limit
                # Target: 24 attempts within 900 seconds, starting at 10s, ending at ~50s
                progressive_sleep_time = (
                    10 + (current_retries - 1) * 1.8
                )  # Linear progression
                progressive_sleep_time = min(progressive_sleep_time, 120)  # Cap at 120s

                # Check if this sleep would exceed the 15-minute total wait time limit
                if total_wait_time + progressive_sleep_time > max_total_wait_time:
                    get_effective_logger().error(
                        f'function run_splunk_search, would exceed 15-minute total wait time limit, stopping after {current_retries} retries, total wait time={total_wait_time:.1f}s, search_query="{search_query}"'
                    )
                    raise Exception(
                        f'function run_splunk_search, would exceed 15-minute total wait time limit, stopping after {current_retries} retries, total wait time={total_wait_time:.1f}s, search_query="{search_query}"'
                    )

                get_effective_logger().warning(
                    f'function run_splunk_search, temporary search failure, retry {current_retries}/{max_retries} for Splunk search due to error="{str(e)}", will re-attempt in {progressive_sleep_time:.1f} seconds (progressive backoff), total wait time so far={total_wait_time:.1f}s.'
                )
                time.sleep(progressive_sleep_time)
                total_wait_time += progressive_sleep_time
            else:
                get_effective_logger().error(
                    f'function run_splunk_search, permanent search failure, search failed with exception="{str(e)}", search_query="{search_query}", search_params="{search_params}"'
                )
                raise

    raise Exception(
        f'function run_splunk_search, permanent search failure after reaching max retries, last_exception="{last_exception}", attempt="{current_retries}", max_retries="{max_retries}", total_wait_time="{total_wait_time:.1f}s", search_query="{search_query}", search_params="{search_params}"'
    )


def get_kv_collection(collection, collection_name):
    """
    Get all records from a KVstore collection.

    :param collection: The KVstore collection object.
    :param collection_name: The name of the collection to query.

    :return: A tuple containing the records, keys, and a dictionary of the records.

    """
    start_time = time.time()
    collection_records = []
    collection_records_keys = set()
    collection_dict = {}

    try:
        end = False
        skip_tracker = 0
        while not end:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if len(process_collection_records) == 0:
                end = True

            else:
                for item in process_collection_records:
                    if item.get("_key") not in collection_records_keys:
                        collection_records.append(item)
                        collection_records_keys.add(item["_key"])
                        collection_dict[item["_key"]] = item
                skip_tracker += len(process_collection_records)

        get_effective_logger().info(
            f'context="perf", KVstore select terminated, no_records="{len(collection_records)}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}"'
        )

        return collection_records, collection_records_keys, collection_dict

    except Exception as e:
        get_effective_logger().error(
            f"failed to call get_kv_collection, args={collection_name}, exception={str(e)}"
        )
        raise Exception(str(e))


# Get emails delivery account credentials, designed to be used for a least privileges approach in a programmatic approach
def trackme_get_emails_account(reqinfo, account):
    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=reqinfo.server_rest_port,
        token=reqinfo.system_authtoken,
        timeout=600,
    )

    # Splunk credentials store
    storage_passwords = service.storage_passwords

    # get all accounts
    accounts = []
    conf_file = "trackme_emails"

    # if there are no account, raise an exception, otherwise what we would do here?
    try:
        confs = service.confs[str(conf_file)]
    except Exception as e:
        error_msg = "We have no emails delivery account configured yet"
        raise Exception(error_msg)

    for stanza in confs:
        # get all accounts
        for name in stanza.name:
            accounts.append(stanza.name)
            break

    # email account configuration
    isfound = False
    email_server = None
    email_username = None
    email_password = None
    email_security = None
    allowed_email_domains = None
    sender_email = None
    email_format = None
    email_footer = None

    # get account
    for stanza in confs:
        if stanza.name == str(account):
            isfound = True
            for key, value in stanza.content.items():
                if key == "email_server":
                    email_server = value
                if key == "email_username":
                    email_username = value
                if key == "email_security":
                    email_security = value
                if key == "allowed_email_domains":
                    allowed_email_domains = value
                if key == "sender_email":
                    sender_email = value
                if key == "email_format":
                    email_format = value
                if key == "email_footer":
                    email_footer = value

    # end of get configuration

    # Stop here if we cannot find the submitted account
    if not isfound:
        error_msg = f'The account="{account}" has not been configured on this instance, cannot proceed!'
        raise Exception(
            {
                "status": "failure",
                "message": error_msg,
                "account": account,
            }
        )

    # get the email password, if any
    if email_username and email_server != "localhost:25":
        try:
            credential_realm = "__REST_CREDENTIAL__#trackme#configs/conf-trackme_emails"
            credential_name = f"{credential_realm}:{account}``"

            for credential in storage_passwords:
                if (
                    credential.content.get("realm") == str(credential_realm)
                    and credential.name.startswith(credential_name)
                    and "email_password" in credential.content.clear_password
                ):
                    email_password = json.loads(credential.content.clear_password).get(
                        "email_password"
                    )
        except Exception as e:
            email_password = None

    # render
    return {
        "account": account,
        "email_server": email_server,
        "email_username": email_username,
        "email_password": email_password,
        "email_security": email_security,
        "allowed_email_domains": allowed_email_domains,
        "sender_email": sender_email,
        "email_format": email_format,
        "email_footer": email_footer,
    }


def trackme_check_report_exists(session_key, splunkd_uri, tenant_id, report_name):
    """
    Check if a report exists in Splunk.
    
    :param session_key: Splunk session key
    :param splunkd_uri: Splunkd URI
    :param tenant_id: Tenant ID
    :param report_name: Name of the report to check
    :return: True if report exists, False otherwise
    """
    parsed_url = urllib.parse.urlparse(splunkd_uri)
    
    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )
    
    try:
        savedsearch = service.saved_searches[report_name]
        get_effective_logger().info(f'tenant_id="{tenant_id}", report exists, report_name="{report_name}"')
        return True
    except Exception as e:
        get_effective_logger().info(f'tenant_id="{tenant_id}", report does not exist, report_name="{report_name}", exception="{str(e)}"')
        return False


def trackme_verify_report_available(session_key, splunkd_uri, tenant_id, report_name, max_attempts=12, sleep_time=5):
    """
    Verify that a report is available and ready for execution in Splunk.
    This function retries checking for the report's existence to handle propagation delays
    in large SHC environments where knowledge objects may take time to become available.
    
    :param session_key: Splunk session key
    :param splunkd_uri: Splunkd URI
    :param tenant_id: Tenant ID
    :param report_name: Name of the report to verify
    :param max_attempts: Maximum number of verification attempts (default: 12)
    :param sleep_time: Time to sleep between attempts in seconds (default: 5)
    :return: True if report is available, False otherwise
    """
    get_effective_logger().info(
        f'tenant_id="{tenant_id}", verifying report availability, report_name="{report_name}", max_attempts={max_attempts}, sleep_time={sleep_time}'
    )
    
    for attempt in range(1, max_attempts + 1):
        if trackme_check_report_exists(session_key, splunkd_uri, tenant_id, report_name):
            get_effective_logger().info(
                f'tenant_id="{tenant_id}", report verified as available, report_name="{report_name}", attempt={attempt}/{max_attempts}'
            )
            return True
        
        if attempt < max_attempts:
            get_effective_logger().info(
                f'tenant_id="{tenant_id}", report not yet available, will retry, report_name="{report_name}", attempt={attempt}/{max_attempts}, sleeping {sleep_time}s'
            )
            time.sleep(sleep_time)
        else:
            get_effective_logger().warning(
                f'tenant_id="{tenant_id}", report verification failed after {max_attempts} attempts, report_name="{report_name}"'
            )
    
    return False


def trackme_check_kvcollection_exists(session_key, splunkd_uri, tenant_id, collection_name):
    """
    Check if a KVstore collection exists in Splunk.
    
    :param session_key: Splunk session key
    :param splunkd_uri: Splunkd URI
    :param tenant_id: Tenant ID
    :param collection_name: Name of the collection to check
    :return: True if collection exists, False otherwise
    """
    parsed_url = urllib.parse.urlparse(splunkd_uri)
    
    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )
    
    try:
        collection = service.kvstore[collection_name]
        # Try to access the collection to verify it exists
        collection.data.query()
        get_effective_logger().info(f'tenant_id="{tenant_id}", collection exists, collection_name="{collection_name}"')
        return True
    except Exception as e:
        get_effective_logger().info(f'tenant_id="{tenant_id}", collection does not exist, collection_name="{collection_name}", exception="{str(e)}"')
        return False


def trackme_check_kvtransform_exists(session_key, splunkd_uri, tenant_id, transform_name):
    """
    Check if a KVstore transform exists in Splunk.
    
    :param session_key: Splunk session key
    :param splunkd_uri: Splunkd URI
    :param tenant_id: Tenant ID
    :param transform_name: Name of the transform to check
    :return: True if transform exists, False otherwise
    """
    parsed_url = urllib.parse.urlparse(splunkd_uri)
    
    # get service
    service = client.connect(
        owner="nobody",
        app="trackme",
        port=parsed_url.port,
        token=session_key,
        timeout=600,
    )
    
    try:
        transforms = service.confs["transforms"]
        transform = transforms[transform_name]
        get_effective_logger().info(f'tenant_id="{tenant_id}", transform exists, transform_name="{transform_name}"')
        return True
    except Exception as e:
        get_effective_logger().info(f'tenant_id="{tenant_id}", transform does not exist, transform_name="{transform_name}", exception="{str(e)}"')
        return False


#
# Lookup-based policy shared utilities
#


class TrackMeRemoteConnectionError(Exception):
    def __init__(self, error_info):
        self.error_info = error_info
        super().__init__(str(error_info))

# -*- coding: utf-8 -*-
"""Provide a set of methods for configuration manipulation."""

import json
from typing import Any, Dict, List

from requests import HTTPError

from rfes_menu import Menu
from recordedfuture.api.asi_client import AsiClient
from recordedfuture.api.base_client import PROXY_PASSWORD_DUMMY, ProxyError
from recordedfuture.api.rfclient import RFClient
from recordedfuture.api.splunk_api import SplunkClient, IndicatorSetting, KvCollection
from recordedfuture.core.app_env import RfesAppEnv
from recordedfuture.core.constants import (
    ASI_API_KEY_NAME,
    AUTOMATIC_THREAT_HUNT_FIELD,
    CACHED_NO_SHARE,
    CACHED,
    CLASSIC_ALERT_INGESTED_AGE_OUT_STANZA,
    CLASSIC_INDEX_PROPERTY,
    CONF_CHECKPOINT,
    CONFIG_FILENAME,
    CORRELATION_CACHE_AGE_OUT_STANZA,
    CORRELATION_PROFILE_COLLECTION,
    CORRELATION_VIEW_ID,
    CORRELATION_CATEGORIES,
    DEFAULT_INDICATOR_TYPES,
    PORTAL_PLATFORM_STANZA,
    OLD_SHARE_INTELLIGENCE_FLAG_NAME,
    PLAYBOOK_ALERT_INGESTED_AGE_OUT_STANZA,
    PLAYBOOK_INDEX_PROPERTY,
    REALTIME,
    RFCLIENT_TIMEOUT,
    SAVEDSEARCHES_FILENAME,
    SAVED_SEARCH_CORRELATION,
    SIGMA_DETECTION_AGE_OUT_STANZA,
    SIGMA_RULES_NOTABLES_SAVED_SEARCH,
    THREAT_HUNT_PROFILE_COLLECTION,
    THREAT_HUNT_RESULT_AGE_OUT,
    THREAT_HUNTS_NOTABLES_SAVED_SEARCH,
    MAX_RETENTION_DAYS,
    MAX_RETENTION_ROWS,
    HUNT_MODE,
    CORRELATION_MODE,
    ATO_DM_DELAY_SECONDS_FIELD,
    TARGET_TYPE_PORTAL,
)

from recordedfuture.correlation.searches import CorrelationQueryBuilder, IocMapping
from recordedfuture.correlation.ato import pick_config_type_indicator_map
from recordedfuture.core.dict_validation import validate_dict, OptionalField, ListField
from recordedfuture.core.exceptions import (
    ValidationError,
    InvalidUrlError,
    NotPriviligedError,
)
from recordedfuture.threathunt.threathunt import get_default_indicators
from recordedfuture.correlation.usecases import sync_usecases
from rfes_ui_sync import sync_ui_elements
from recordedfuture.core.utils import (
    SplunkConf,
    get_instance_guid,
    get_property_from_usecases,
    endpoint_requires_payload,
    check_asi_configured,
)
from recordedfuture.core.version import StrictVersion
from urllib3 import __version__ as urllib3_version


#######################################################################
#
# Connection related configuration methods
#
#######################################################################
def user_permission(in_dict, app_env):
    user_perm = app_env.has_user_perm(in_dict)
    if user_perm is False:
        warning = ""
    else:
        warning = "hidden"
    return 200, {
        "links": {},
        "entry": [],
        "warning": warning,
        "has_user_perm": user_perm,
    }


def verify_connection(configuration, app_env):
    """Verify that proxy and API URL settings are valid and working."""
    proxy_entries = [
        "proxy_enabled",
        "proxy_username",
        "proxy_password",
        "proxy_url",
        "proxy_port",
        "ssl_verify_proxy",
        "proxy_proto",
    ]
    client = RFClient(app_env)
    # Check proxy if any
    app_env.logger.debug("Checking if proxy is enabled")
    if configuration.get("proxy", {}).get("proxy_enabled") == "1":
        app_env.logger.debug("Proxy enabled, checking that all fields are present.")
        for pe in proxy_entries:
            if pe not in configuration["proxy"].keys():
                raise ValidationError(
                    "Missing configuration %s in proxy configuration." % pe
                )
        try:
            client.check_proxy_access(configuration)
        except ProxyError as e:
            raise ValidationError(e)

    # Check API URL
    app_env.logger.debug("Checking API URL.")
    if not configuration["api_url"].lower().startswith("https://"):
        raise ValidationError("Only HTTPS is allowed in API URL.")
    try:
        client.check_api_access(configuration)
    except InvalidUrlError as e:
        raise ValidationError(e)


def save_connection(configuration, app_env):
    """Save proxy and API URL settings."""
    client = SplunkClient(app_env)
    if not configuration["api_url"].endswith("/"):
        configuration["api_url"] = configuration["api_url"] + "/"
    data = {
        "recorded_future_api_url": configuration["api_url"],
        "ssl_verify": app_env.is_splunk_cloud or configuration["ssl_verify"],
        # Old setting, remove together with changes in utils once everyone
        # has upgraded to 2.x. Setting verify_ssl to true ensures it is ignored
        # as we only listen to verify_ssl if it is false.
        "verify_ssl": True,
    }
    client.config.post_config("recordedfuture_settings", stanza="settings", data=data)
    if configuration["proxy"]:
        proxy_password = configuration["proxy"].pop("proxy_password")
        client.config.post_config(
            "recordedfuture_settings", stanza="proxy", data=configuration["proxy"]
        )
        if proxy_password != PROXY_PASSWORD_DUMMY:
            app_env.logger.debug("Updating Proxy Password")
            app_env.set_proxy_password(proxy_password)


#######################################################################
#
# Token related configuration methods
#
#######################################################################


def verify_token(configuration, app_env):
    """Verify that the API Token is valid."""
    if configuration["api_token"] != "api_token":
        check_api_token(app_env, configuration["api_token"])
        return
    check_api_token(app_env, app_env.api_key)


def check_api_token(app_env, token):
    """Check if API Token is valid by asking the API."""
    client = RFClient(app_env, token)
    try:
        client.config.info()
    except HTTPError:
        app_env.logger.exception("Trying to validate token")
        raise ValidationError("API token is not valid.")
    return True


def verify_asi_key(configuration, app_env):
    """Verify that the ASI API key is valid."""
    if "asi_ssl_verify" not in configuration:
        raise ValidationError('"asi_ssl_verify" must be defined in payload.')

    if configuration["asi_api_key"] != "api_key":
        check_asi_api_key(
            app_env, configuration["asi_api_key"], configuration["asi_ssl_verify"]
        )
        return
    check_asi_api_key(app_env, app_env.asi_api_key, app_env.asi_ssl_verify)


def check_asi_api_key(app_env, api_key: str, ssl_verify: bool):
    """Check if ASI API key is valid by asking the API."""
    client = AsiClient(app_env, api_key)
    try:
        client.ping(ssl_verify=ssl_verify)
    except HTTPError:
        app_env.logger.exception("Trying to validate token")
        raise ValidationError("API token is not valid.")
    return True


def get_share_intelligence(app_env, enrichment_mode):
    share_intelligence = app_env.privacy.get_bool("share_intelligence")
    if share_intelligence is None and enrichment_mode != CACHED_NO_SHARE:
        # privacy setting not set, and user hadn't selected to not share.
        return "on"
    elif enrichment_mode == CACHED_NO_SHARE:
        return "off"

    if enrichment_mode == REALTIME:
        # If they selected realtime-data share_intelligence is always on.
        return "on"
    return "on" if share_intelligence else "off"


def save_token(configuration, app_env):
    """Save API Token and a couple of other settings."""
    if configuration["api_token"] != "api_token":
        app_env.logger.debug("Updating API Token")
        app_env.set_api_key(configuration["api_token"])


def save_asi_api_key(configuration, app_env):
    """Save API key and a couple of other settings."""
    if "asi_ssl_verify" not in configuration:
        raise ValidationError('"asi_ssl_verify" must be provided in the payload.')

    if configuration["asi_api_key"] != "api_key":
        app_env.logger.debug("Updating ASI API key")
        app_env.set_asi_api_key(configuration["asi_api_key"])
    client = SplunkClient(app_env)
    data = {"asi_ssl_verify": configuration["asi_ssl_verify"]}
    client.config.post_config("recordedfuture_settings", stanza="settings", data=data)


#######################################################################
#
# Timeout related configuration methods
#
#######################################################################


def verify_timeout(timeout_to_verify):
    """Verify that the timeout value is valid."""
    try:
        timeout = int(timeout_to_verify)
        if timeout <= 0:
            raise ValidationError("API Timeout must be a positive integer")
        # set max timeout value
        if timeout > 360:
            raise ValidationError("API Timeout cannot exceed 360 seconds")
    except ValueError:
        raise ValidationError("Invalid API Timeout value")


def save_timeout(timeout, setting_name, app_env):
    """Save timeout settings."""
    client = SplunkClient(app_env)
    data = {setting_name: str(timeout)}
    client.config.post_config("recordedfuture_settings", stanza="settings", data=data)


def write_conf_file(in_dict, app_env):
    """
    Write data to a single conf-file.

    The payload consists of the following structure:
    {
        "query": {
            "filename": "recordedfuture_settings",
            "stanza": "settings",
            "data": {
                "key1": "value1",
                "key2": "value2"
            }
        }
    }
    """
    client = SplunkClient(app_env)
    data = dict(in_dict.get("query", [])) or json.loads(in_dict.get("payload", {}))

    filename = data.get("filename")
    stanza = data.get("stanza")
    data = data.get("data", "{}")
    data = json.loads(data)

    if not filename or not data:
        raise ValidationError("Missing filename and/or data")
    client.config.post_config(filename, stanza=stanza, data=data)
    return 200, {"entry": [{"name": "write_conf_file", "content": "Data written"}]}


def read_configuration(in_dict, app_env):
    """A utility endpoint that allows you to read configuration files through SPL"""
    client = SplunkClient(app_env)
    conf_file = dict(in_dict["query"]).get("conf_file")
    if not conf_file:
        return 400, {}

    data = client.config.get_config(conf_file)
    return 200, data


def write_configuration(in_dict, app_env):
    """Write the new configuration to the configuration file."""
    try:
        full_configuration = json.loads(in_dict["payload"])["entry"][0]  # type: dict
        configuration = SplunkConf(full_configuration["content"])  # type: SplunkConf
    except Exception as err:
        raise Exception("Could not extract configuration from POST request: %s" % err)

    client = SplunkClient(app_env)
    if configuration.get("api_url"):
        verify_connection(configuration, app_env)
        app_env.logger.debug("Validating connection config successful.")
        save_connection(configuration, app_env)
        app_env.logger.debug("Saving connection config successful.")

    elif configuration.get("api_token") or configuration.get("api_token") == "":
        verify_token(configuration, app_env)
        app_env.logger.debug("Validating token successful.")
        save_token(configuration, app_env)
        app_env.logger.debug("Saving token successful.")
        app_env.logger.debug("Resyncing app data...")
        sync_usecases(in_dict, app_env)
        sync_ui_elements(in_dict, app_env)
        # After we verified token make sure to disable TI data sharing.
        disable_ti_data_sharing_for_multiorg(app_env)
        set_configured(app_env)

    elif configuration.get("asi_api_key") is not None:
        verify_asi_key(configuration, app_env)
        app_env.logger.debug("Validating ASI API key successful.")
        save_asi_api_key(configuration, app_env)
        app_env.logger.debug("Saving ASI API key successful.")
        app_env.logger.debug("Resyncing app data...")
        sync_ui_elements(in_dict, app_env)
    elif configuration.get("logging"):
        client.config.post_config(
            "recordedfuture_settings",
            stanza="logging",
            data={"loglevel": configuration["logging"].upper()},
        )
        app_env.logger.debug("Saving log level successful.")

    elif configuration.get("enrichment_mode"):
        enrichment_mode = configuration["enrichment_mode"]
        client.config.post_config(
            "recordedfuture_settings",
            stanza="settings",
            data={
                "enrichment_mode": enrichment_mode,
            },
        )
        app_env.logger.debug("Saving enrichment mode successful.")
        share_intelligence = get_share_intelligence(app_env, enrichment_mode)
        app_env.logger.debug("Modifying share data setting...")
        client = SplunkClient(app_env)
        client.config.post_config(
            "recordedfuture_settings",
            stanza="privacy",
            data={"share_intelligence": share_intelligence},
        )
        app_env.logger.debug("Saving data setting successful.")
    elif configuration.get("rfclient_timeout"):
        # This timeout is used for all API clients including the splunk client.
        verify_timeout(configuration["rfclient_timeout"])
        app_env.logger.debug("Validating timeout config successful.")
        save_timeout(configuration["rfclient_timeout"], "rfclient_timeout", app_env)
        app_env.logger.debug("Saving timeout config successful.")
    elif configuration.get("es_enabled"):
        # This config option is valid, but needs to be evaluated
        # outside this IF statement
        pass
    else:
        raise Exception("Unknown configuration type")

    if configuration.get("es_enabled"):
        client.config.post_config(
            "recordedfuture_settings",
            stanza="settings",
            data={
                "es_enabled": configuration["es_enabled"],
            },
        )
        app_env.logger.debug("Saving es_enabled successful.")
        # create_alert_actions_conf() removed - alert actions now use static configuration in alert_actions.conf
        # RFPD-87335 Dynamic creation was replaced with static config
        # Therefore we also update the env before proceeding.
        app_env.es = configuration.get_bool("es_enabled", None)
        known_es_version = app_env.splunk_es_version != "version_undisclosed"
        if (app_env.es and known_es_version) or app_env.settings.get(
            "force_es", "0"
        ) == "1":
            toggle_disabled_property(app_env, "rfes_ar_links", 0)
            if not app_env.check_alert_actions_conf():
                app_env.logger.info(
                    "Alert actions now configured statically in alert_actions.conf"
                )
            elif not app_env.check_alert_actions_prefix():
                # Alert action exist, but does it have prefix (2.1.2)
                add_prefix_property_to_alert_action(app_env)
        else:
            toggle_disabled_property(app_env, "rfes_ar_links", 1)
        # Always rebuild the menu when toggling ES.
        menu = Menu(app_env)
        menu.setup()

    app_env.logger.info("Done saving new configuration.")

    client.config.reload()
    config = {
        "message": "Configuration saved successfully",
        "error": False,
    }
    config.update(**full_configuration)
    return config


def toggle_disabled_property(app_env, stanza, value):
    """Toggled the enabled/disabled property of a stanza."""
    client = SplunkClient(app_env)
    data = {"disabled": value}
    client.config.set_properties(conf="alert_actions", stanza=stanza, data=data)


def set_configured(app_env):
    """Update stanza in configuration file."""
    app_env.logger.debug("Updating is_configured to true")
    client = SplunkClient(app_env)
    client.config.post_config("app", stanza="install", data={"is_configured": "true"})
    app_env.logger.debug("is_configured set to True.")


def asi_can_connect(app_env, client: AsiClient):
    if not check_asi_configured(app_env):
        return "0"

    try:
        client.ping()
    except HTTPError as err:
        if err.response is not None:
            message = f"ASI connectivity check failed: {err.response.text}"
        else:
            message = f"ASI connectivity check failed: {err}"
        app_env.logger.warning(message)
        return "0"
    else:
        return "1"


def get_configuration(app_env):
    """Fetch configuration and return a configuration dict."""

    client = RFClient(app_env)
    splunk_client = SplunkClient(app_env)
    asi_client = AsiClient(app_env)

    def can_connect():
        try:
            res = client.config.helo()
            if res.ok:
                return "1"
        except Exception as err:
            app_env.logger.warning(
                "Connectitivity check failed: %s", err, exc_info=True
            )

        return "0"

    def fix_data(rl_dict, name):
        rl_dict["name"] = name
        rl_dict.pop("disabled", "")
        return rl_dict

    payload = dict()

    # Get correlation settings per category
    for category in CORRELATION_CATEGORIES:
        stanza = f"{CORRELATION_CACHE_AGE_OUT_STANZA}:{category}"
        # Get existing settings from .conf
        category_settings = splunk_client.config.get_config(
            CONFIG_FILENAME, stanza=stanza
        )

        if (
            category_settings
            and "entry" in category_settings
            and category_settings["entry"]
        ):
            entry = category_settings["entry"][0]
            payload[stanza] = {
                "days": entry.get("content", {}).get("days"),
                "rows": entry.get("content", {}).get("rows"),
            }

    # NOTE, this endpoint is also used when listing alerts in alerts config
    payload["alerts"] = sorted(
        [fix_data(v, k) for k, v in app_env.alerts.items()], key=lambda x: x["name"]
    )
    payload["playbook_alerts"] = sorted(
        [fix_data(v, k) for k, v in app_env.playbook_alerts.items()],
        key=lambda x: x["name"],
    )
    payload["api_url"] = app_env.api_url
    payload["api_token"] = "api_token" if app_env.api_key else ""
    payload["es_enabled"] = "1" if app_env.es else "0"
    payload["connectivity_ensured"] = can_connect()
    payload["rfclient_timeout"] = app_env.settings.get(
        "rfclient_timeout", RFCLIENT_TIMEOUT
    )
    payload["asi_api_url"] = app_env.asi_api_url
    payload["asi_api_key"] = "api_key" if app_env.asi_api_key else ""
    payload["asi_connectivity_ensured"] = asi_can_connect(app_env, asi_client)
    payload["proxy"] = {
        "proxy_username": app_env.proxy_settings.get("proxy_username", ""),
        "proxy_url": app_env.proxy_settings.get("proxy_url", ""),
        "proxy_port": app_env.proxy_settings.get("proxy_port", ""),
        "proxy_enabled": app_env.proxy_settings.get("proxy_enabled", ""),
        "proxy_password": PROXY_PASSWORD_DUMMY if app_env.get_proxy_password() else "",
        "ssl_verify_proxy": app_env.proxy_settings.get("ssl_verify_proxy", "1"),
        "proxy_proto": app_env.proxy_settings.get("proxy_proto", "https"),
    }
    payload["enrichment_mode"] = app_env.settings.get("enrichment_mode", "")
    payload["logging"] = app_env.log_level
    payload["ssl_verify"] = "1" if app_env.verify else "0"
    payload["asi_ssl_verify"] = "1" if app_env.asi_ssl_verify else "0"
    payload["is_splunk_cloud"] = "1" if app_env.is_splunk_cloud else "0"
    payload["es_installed"] = (
        "1"
        if app_env.splunk_es_version != "version_undisclosed"
        or app_env.settings.get("force_es", "0") == "1"
        else "0"
    )
    payload["https_proxy_support"] = StrictVersion(urllib3_version) >= StrictVersion(
        "1.26"
    )
    app_env.logger.debug("Fetched configuration without problems.")
    return payload


def request_stanza(in_dict, app_env):
    try:
        query = dict(in_dict["query"])
        config_file = query["config_file"]
        stanza_name = query["stanza_name"]
    except KeyError:
        return 400, "Missing parameters"
    client = SplunkClient(app_env)
    stanza = client.config.get_config(config_file, stanza=stanza_name)
    return 200, stanza


def add_prefix_property_to_alert_action(app_env):
    """Add the 'param.prefix' property to alert action stanza"""
    if not app_env.es:
        return
    client = SplunkClient(app_env)
    data = {"param.prefix": "Threat Activity Enriched"}
    client.config.set_properties(
        conf="alert_actions", stanza="rfes_ar_enrichment", data=data
    )
    app_env.logger.debug(
        "Adding 'param.prefix' property to alert action 'rfes_ar_enrichment'."
    )


# Views
def set_force_es(app_env, state):
    """Update stanza in configuration file."""
    app_env.logger.debug("Updating force_es to %s" % state)
    client = SplunkClient(app_env)
    client.config.post_config(
        "recordedfuture_settings", stanza="settings", data={"force_es": state}
    )
    client.config.reload()


def disable_ti_data_sharing_for_multiorg(app_env):
    """Method that checks if a client is multiorg; and if yes then it disabled the third-party TI feed sharing."""
    if not (app_env.privacy.share_ti_data_model_matches and app_env.es_available):
        # If the feature is already disabled there is no need to go through the motion; return early.
        return
    client = SplunkClient(app_env)
    client_metadata = get_property_from_usecases(client, app_env, "client_metadata", {})
    if client_metadata.get("is_multi_org"):
        app_env.logger.debug("Client is multiorg, disabling TI model sharing.")
        client.config.post_config(
            "recordedfuture_settings",
            stanza="privacy",
            data={"share_ti_data_model_matches": "off"},
        )
    toggle_ti_share_saved_search(app_env)


def send_last_config_blob(app_env, client, rf_client):
    """Send the final configuration blob when Collective Insights is disabled."""
    guid = get_instance_guid(app_env)
    conf_data = clean_conf(client.config.get_config("recordedfuture_settings")["entry"])
    conf_to_send = {"guid": guid, "conf": conf_data}
    conf_to_send["conf"].append(
        {"name": "privacy", "content": {"share_intelligence": "off"}}
    )
    rf_client.config.track(conf_to_send)
    app_env.logger.info("Sent last config blob with Collective Insights disabled")


def post_intelligence(in_dict, app_env):
    if in_dict["method"] != "POST":
        return 405, {"error": "Not a valid method"}

    keys = ["share_intelligence", "share_ti_data_model_matches"]
    conf = json.loads(in_dict["payload"])
    conf = {key: conf.get(key, "off") for key in keys}

    changed_property, changed_value = intelligence_sharing_conf_diff(app_env, conf)
    client = SplunkClient(app_env)

    client.config.post_config("recordedfuture_settings", stanza="privacy", data=conf)
    toggle_ti_share_saved_search(app_env)

    enrichment_mode = app_env.settings.get("enrichment_mode", REALTIME)
    settings = dict(app_env.settings)
    if enrichment_mode == CACHED_NO_SHARE and conf["share_intelligence"] == "on":
        # AR_NO_SHARE is deprecated, so we force to use AR_REALTIME
        settings["enrichment_mode"] = REALTIME
        client.config.post_config(
            "recordedfuture_settings", stanza="settings", data=settings
        )

    rf_client = RFClient(app_env)

    if conf["share_intelligence"] == "off":
        settings["enrichment_mode"] = CACHED
        client.config.post_config(
            "recordedfuture_settings", stanza="settings", data=settings
        )
        send_last_config_blob(app_env, client, rf_client)

    shared_int = conf.get("share_intelligence")
    shared_third_party_int = conf.get("share_ti_data_model_matches")
    props = {
        "es_enabled": app_env.es,
        "share_intelligence": shared_int,
        "share_ti_data_model_matches": shared_third_party_int,
    }
    rf_client.track(
        {
            "action": "privacychange/{property}/{state}".format(
                property=changed_property, state=changed_value
            ),
            "properties": props,
        }
    )

    return 200, conf


def get_intelligence(in_dict, app_env):
    privacy = app_env.privacy
    # Removing the old name of the flag that comes from v2.0
    privacy.pop(OLD_SHARE_INTELLIGENCE_FLAG_NAME, None)
    return 200, privacy


def get_third_party_intelligence(in_dict, app_env):
    privacy = app_env.privacy_third_party
    return 200, privacy


def enable_force_es(_, app_env):
    """Force enable Splunk ES support."""
    app_env.logger.debug("Entering enable_force_es")
    set_force_es(app_env, "1")


def disable_force_es(_, app_env):
    """Force disable Splunk ES support."""
    app_env.logger.debug("Entering disable_force_es")
    set_force_es(app_env, "0")


def handle_asi_configuration(in_dict, app_env):
    # Wrapper to track ASI configuration separately
    return handle_configuration(in_dict, app_env)


def handle_configuration(in_dict, app_env):
    method = in_dict["method"]
    if method not in ["POST", "GET"]:
        return 405, {"error": "Not a valid method"}

    if method == "GET":
        app_env.logger.info("handle_config_get entered.")
        return 200, get_configuration(app_env)

    try:
        app_env.logger.info("handle_config_post entered.")
        return 200, write_configuration(in_dict, app_env)
    except ValidationError as err:
        return 400, {"message": str(err)}
    except NotPriviligedError:
        return 400, {"message": "This is not a valid api token"}
    except HTTPError as err:
        response = err.response
        app_env.logger.error("Failed to save config: %s" % response.text, exc_info=True)
        return 500, {"message": "Failed due to: %s" % err}
    except Exception as err:
        app_env.logger.error("Failed to save config: %s" % err, exc_info=True)
        return 500, {"message": "Failed due to: %s" % err}


def delete_api_token(in_dict, app_env):
    method = in_dict["method"]
    if method != "DELETE":
        return 405, {"error": "Method not supported"}

    client = SplunkClient(app_env)
    client.storage.remove_password("api_key")
    return 200, {"status": "ok"}


def delete_asi_api_token(in_dict: dict, app_env: RfesAppEnv):
    method = in_dict["method"]
    if method != "DELETE":
        return 405, {"error": "Method not supported"}

    client = SplunkClient(app_env)
    client.storage.remove_password(ASI_API_KEY_NAME)
    return 200, {"status": "ok"}


def clean_conf(conf):
    modified_conf = []

    for stanza in conf:
        content = stanza["content"]
        for key, value in dict(content).items():
            if key.startswith("eai:") or key == "disabled":
                content.pop(key)
            if "." in key:  # INTEGR-3472: MongoDB keys cannot contain dots
                content.pop(key)
                # Replacing not allowed dots in the key
                content[key.replace(".", "-")] = value

        data = {"name": stanza["name"], "content": content}
        modified_conf.append(data)

    return modified_conf


def store_config(in_dict, app_env):
    client = SplunkClient(app_env)
    conf = client.config.get_config("recordedfuture_settings")

    conf_data = clean_conf(conf["entry"])
    hashed_conf = hash(json.dumps(conf_data))

    saved_conf = client.storage.get_checkpoint(CONF_CHECKPOINT)
    if saved_conf:
        saved_conf = saved_conf[0]["data"]
    saved_hashed_conf = hash(json.dumps(saved_conf))

    guid = get_instance_guid(app_env)

    if hashed_conf == saved_hashed_conf:
        app_env.logger.debug("Config not updated, not sending response")
        # nothing to do
        return 200, {"status": "ok"}

    client.storage.set_checkpoint(
        CONF_CHECKPOINT, key=CONF_CHECKPOINT, data={"data": conf_data}
    )

    privacy = ""
    for stanza in conf_data:
        if stanza["name"] == "privacy":
            privacy = stanza["content"].get("share_intelligence", "off")

    if privacy != "on":
        # check whether they actually are ok with tracking.
        app_env.logger.debug("Collective Insights is off, not sending config")
        return 200, {"status": "ok"}

    app_env.logger.debug("Sending updated configuration")
    rf_client = RFClient(app_env)
    conf_to_send = {"guid": guid, "conf": conf_data}
    rf_client.config.track(conf_to_send)
    return 200, {"status": "ok"}


def toggle_ti_share_saved_search(app_env):
    """Method that either add or remove third-party saved search for TI model writeback"""
    client = SplunkClient(app_env)
    search_name = "Recorded Future - Third-party Intelligence Sharing"
    third_party_config_status = app_env.privacy.share_ti_data_model_matches
    if (
        third_party_config_status
        and app_env.privacy.share_intelligence
        and app_env.es_available
    ):
        app_env.logger.debug("Adding saved search for TI data sharing.")
        search = "| rest splunk_server=local /services/TA-recordedfuture/share_third_party_correlations earliest=$dispatch.earliest_time$ latest=$dispatch.latest_time$"
        saved_search = client.searches.generate_saved_search(
            description="Batch job that collects third-party correlation from the TI model.",
            search=search,
            kwargs={
                "cron_schedule": "20 * * * *",
                "dispatch.earliest_time": "-65m@m",
                "dispatch.latest_time": "-5m@m",
                "enableSched": 1,
            },
        )
        client.config.post_config(
            SAVEDSEARCHES_FILENAME, search_name, data=saved_search
        )
    else:
        app_env.logger.debug("Removing saved search for TI data sharing.")
        client.config.delete_config(SAVEDSEARCHES_FILENAME, stanza=search_name)


def intelligence_sharing_conf_diff(app_env, new_change):
    """Given app_env with old settings, and then ew changes, determine which property has changed.

    Args:
        app_env: application_environment
        new_change (dict): Dictionary with the new configuration to be written.
    """
    old = set(app_env.privacy.items())
    new = set(new_change.items())
    return list(new - old)[0]


@endpoint_requires_payload
def update_purge_settings(in_dict: dict, app_env: RfesAppEnv):
    payload = json.loads(in_dict["payload"])
    _validate_purge_settings_payload(payload)

    client = SplunkClient(app_env)
    data = {}
    if payload.get("days"):
        data["days"] = payload["days"]
    if payload.get("rows"):
        data["rows"] = payload["rows"]
    client.config.post_config(CONFIG_FILENAME, payload["stanza"], data)
    return 200, {}


def _validate_purge_settings_payload(payload: dict):
    schema = {
        "days": OptionalField(int),
        "rows": OptionalField(int),
        "stanza": str,
    }
    validate_dict(payload, schema)

    optional_int_fields = [
        key
        for key, value in schema.items()
        if isinstance(value, OptionalField) and value.type_or_nested is int
    ]

    stanza = payload["stanza"]
    if ":" in stanza:
        base_stanza, category = stanza.split(":", 1)
        if base_stanza != CORRELATION_CACHE_AGE_OUT_STANZA:
            raise ValidationError(f'Unknown stanza "{stanza}"')
        if category not in CORRELATION_CATEGORIES:
            raise ValidationError(f'Invalid correlation category "{category}"')
    elif stanza not in [
        SIGMA_DETECTION_AGE_OUT_STANZA,
        CLASSIC_ALERT_INGESTED_AGE_OUT_STANZA,
        PLAYBOOK_ALERT_INGESTED_AGE_OUT_STANZA,
        THREAT_HUNT_RESULT_AGE_OUT,
    ]:
        raise ValidationError(f'Unknown stanza "{stanza}"')

    if all([payload.get(field) is None for field in optional_int_fields]):
        raise ValidationError(f"At least one of {optional_int_fields} must be set.")

    for field in optional_int_fields:
        if payload.get(field) is not None and payload[field] <= 0:
            raise ValidationError(f'"{field}" must be positive integer.')

    # Add hard limit validation
    if payload.get("days") is not None and payload["days"] > MAX_RETENTION_DAYS:
        raise ValidationError(
            f'"days" must not exceed {MAX_RETENTION_DAYS}. '
            f"Maximum retention period is {MAX_RETENTION_DAYS} days (1 year)."
        )

    if payload.get("rows") is not None and payload["rows"] > MAX_RETENTION_ROWS:
        raise ValidationError(
            f'"rows" must not exceed {MAX_RETENTION_ROWS:,}. '
            f"Maximum retention limit is {MAX_RETENTION_ROWS:,} records."
        )


@endpoint_requires_payload
def update_index_settings(in_dict: dict, app_env: RfesAppEnv):
    payload = json.loads(in_dict["payload"])
    _validate_index_settings_payload(payload)

    setting_to_savesearch_map = {
        PLAYBOOK_INDEX_PROPERTY: "Recorded Future - Index Playbook Alerts",
        CLASSIC_INDEX_PROPERTY: "Recorded Future - Index Alerts",
    }

    indexing_enabled = payload.get("value")
    alert_type = payload.get("alert_type")

    client = SplunkClient(app_env)
    client.config.post_config(
        CONFIG_FILENAME, "alert_index_settings", data={alert_type: indexing_enabled}
    )
    client.config.post_config(
        SAVEDSEARCHES_FILENAME,
        setting_to_savesearch_map[alert_type],
        data={"disabled": not indexing_enabled},
    )
    return 200, {}


def _validate_index_settings_payload(payload):
    schema = {
        "alert_type": str,
        "value": bool,
    }
    validate_dict(payload, schema)

    if payload.get("alert_type") not in {
        CLASSIC_INDEX_PROPERTY,
        PLAYBOOK_INDEX_PROPERTY,
    }:
        raise ValidationError(f"Invalid alert_type {payload.get('alert_type')}")


def get_modules_info(in_dict: dict, app_env: RfesAppEnv):
    client = SplunkClient(app_env)
    client_metadata = get_property_from_usecases(client, app_env, "client_metadata", {})
    return 200, {
        "links": {},
        "entry": [{"content": module} for module in client_metadata.get("modules", [])],
    }


def verify_asi_connection_after_migration_from_old_app(
    in_dict: dict, app_env: RfesAppEnv
):
    response: Dict[str, Any] = {"links": {}, "entry": []}
    if _verify_asi_connection(app_env):
        msg = (
            "ASI connection verified successfully after migration from old application."
        )
        app_env.logger.info(msg)
        response["entry"].append(
            {
                "name": "status",
                "content": {"status_code": 200, "message": msg},
            },
        )
    else:
        # Rolling back saved config for ASI
        client = SplunkClient(app_env)
        client.storage.remove_password(ASI_API_KEY_NAME)
        msg = (
            "Rolled back saved config for ASI due to failed verification of connection."
        )
        app_env.logger.info(msg)
        response["entry"].append(
            {
                "name": "status",
                "content": {"status_code": 400, "message": msg},
            },
        )
    return 200, response


def _verify_asi_connection(app_env):
    client = AsiClient(app_env)
    try:
        client.ping()
    except HTTPError as exc:
        app_env.logger.warning(f"Could not verify connection to ASI: {exc}")
        return False
    return True


SAVED_SEARCH_ENABLED = "true"
SAVED_SEARCH_DISABLED = "false"
ALLOWED_ENABLED_VALUES = [SAVED_SEARCH_ENABLED, SAVED_SEARCH_DISABLED]


def toggle_sigma_rules_notables_creation(in_dict: dict, app_env: RfesAppEnv):
    enabled = dict(in_dict.get("query", {})).get("enabled")
    if enabled not in ALLOWED_ENABLED_VALUES:
        raise ValidationError(
            f'Bad query parameter "enabled". Possible values are: {ALLOWED_ENABLED_VALUES}.'
        )
    client = SplunkClient(app_env)
    client.searches.post_search(
        SIGMA_RULES_NOTABLES_SAVED_SEARCH,
        {"disabled": enabled == SAVED_SEARCH_DISABLED},
    )
    return 200, {}


def toggle_threat_hunts_notables_creation(in_dict: dict, app_env: RfesAppEnv):
    enabled = dict(in_dict.get("query", {})).get("enabled")
    if enabled not in ALLOWED_ENABLED_VALUES:
        raise ValidationError(
            f'Bad query parameter "enabled". Possible values are: {ALLOWED_ENABLED_VALUES}.'
        )
    client = SplunkClient(app_env)
    client.searches.post_search(
        THREAT_HUNTS_NOTABLES_SAVED_SEARCH,
        {"disabled": enabled == SAVED_SEARCH_DISABLED},
    )
    return 200, {}


def save_default_indicator_settings(in_dict: dict, app_env: RfesAppEnv):
    """Save the default indicator settings"""
    payload = json.loads(in_dict["payload"])
    query = dict(in_dict.get("query", []))
    indicator_type = query.get("mode", HUNT_MODE)
    payload["indicator_type"] = indicator_type

    setting = IndicatorSetting.from_dict(payload)

    splunk_client = SplunkClient(app_env)
    profile_collection = THREAT_HUNT_PROFILE_COLLECTION
    if indicator_type == CORRELATION_MODE:
        profile_collection = CORRELATION_PROFILE_COLLECTION
        formatted = _formatted_indicator_data(payload)
        if not formatted["third_level"]:
            msg = "The event field needs to filled in for correlation targets."
            return 400, {"message": msg, "title": "Indicator was not saved"}

    collection = KvCollection(app_env)
    msg = "Indicator settings were not saved as configuration setting was incomplete."
    indicator_searches = collection.indicator_searches(
        query={"indicator_type": indicator_type}
    )
    config_type = list(set([i["config_type"] for i in indicator_searches]))

    if config_type and config_type[0] != setting.config_type:
        msg = f"All Detection Targets need to be either Index or Datamodel, you already have {config_type[0].title()} configured. "
        return 400, {
            "title": msg,
            "message": "Reset the default indicators, and then save again.",
        }

    if not setting.mapping:
        return 400, {"message": msg}

    collection.store_indicator_search(data=[setting.to_dict()])
    rf_client = RFClient(app_env=app_env)

    capability = "detect" if indicator_type == CORRELATION_MODE else "hunt"
    rf_client.config.update_capability([capability])

    def correlation_profile_update():
        """
        Update data related correlation profiles
        NOTE future performance optimization could be to execute this is parallel
        """
        profiles = splunk_client.storage.get_collection_data(profile_collection)
        if not profiles:
            return 200, {}

        selection_map = {"index": "portal_index", "datamodel": "portal_datamodel"}
        indicator_rules = KvCollection(app_env).indicator_searches(
            query={"indicator_type": CORRELATION_MODE}
        )
        for profile in profiles:
            _id = profile["_key"]
            ioc_types = splunk_client.searches.search(
                query="""
                    | inputlookup {id}.csv
                    | dedup ioc_type
                    | table ioc_type
                """.format(id=_id)
            )
            ioc_types = [d["ioc_type"] for d in ioc_types.get("results", [])]
            config_type, indicator_map = pick_config_type_indicator_map(
                app_env, ioc_types, indicator_rules
            )

            payload = {
                "selection": selection_map[config_type],
                "id": _id,
                "label": profile["name"],
                "use_case": _id,
            }
            builder = CorrelationQueryBuilder.from_payload(
                payload=payload, ioc_mapping=IocMapping.from_dict(indicator_map)
            )
            saved_search = splunk_client.searches.generate_saved_search(
                description="Saved search used by the cached correlations view.",
                search=builder.output(),
                ui_view=CORRELATION_VIEW_ID,
            )

            splunk_client.config.post_config(
                SAVEDSEARCHES_FILENAME,
                SAVED_SEARCH_CORRELATION.format(id=_id),
                data=saved_search,
            )

        return 200, {}

    def threathunt_profile_update():
        """Update existing profiles with new default detection targets."""
        # fetch detection targets again to keep them fresh
        profiles = splunk_client.storage.get_collection_data(
            profile_collection,
            params={"query": json.dumps({"target_type": TARGET_TYPE_PORTAL})},
        )
        if not profiles:
            return 200, {}
        indicator_searches = collection.indicator_searches(
            query={"indicator_type": HUNT_MODE}
        )
        config_type, field_map_key, field_map = get_default_indicators(
            app_env, fetched_indicators=indicator_searches
        )
        for profile in profiles:
            profile["config_type"] = config_type
            profile[field_map_key] = json.dumps(field_map)

        splunk_client.storage.batch_save(THREAT_HUNT_PROFILE_COLLECTION, profiles)
        return 200, {}

    if indicator_type == CORRELATION_MODE:
        return correlation_profile_update()
    return threathunt_profile_update()


def _formatted_indicator_data(indicator_data, field_map=None):
    data: Dict[str, Any] = {
        "first_level": [],
        "second_level": [],
        "third_level": [],
    }
    setting = IndicatorSetting.from_dict(indicator_data)
    data["type"] = setting.ioc_type
    data["config_type"] = setting.config_type

    indexes = setting.mapping
    for first_level, second_levels in indexes.items():
        data["first_level"].append(first_level)
        for second_level, third_levels in second_levels.items():
            data["second_level"].append(f"{first_level}>>{second_level}")
            for level in third_levels:
                data["third_level"].append(f"{first_level}>>{second_level}>>{level}")
    return data


def read_default_indicator_settings(in_dict: dict, app_env: RfesAppEnv):
    """Read the default indicator settings"""
    query = dict(in_dict.get("query", []))
    ioc_type = query["type"]
    indicator_type = query.get("mode", "")
    try:
        result = KvCollection(app_env).indicator_searches(
            query={"indicator_type": indicator_type, "ioc_type": ioc_type}
        )
    except HTTPError as e:
        if e.response.status_code != 404:
            raise
        else:
            return 200, {}

    if len(result) == 0:
        return 200, {}
    result = result[0]
    data = _formatted_indicator_data(result)
    data["type"] = result["ioc_type"]
    return 200, data


def reset_indicators(in_dict: dict, app_env: RfesAppEnv):
    """Reset Detection Targets, in effect removing all them"""
    if in_dict["method"] != "DELETE":
        return 405, {"error": "Not a valid method"}

    indicators = [
        "ip",
        "domain",
        "hash",
        "url",
        "vulnerability",
    ]
    query = dict(in_dict["query"])
    indicator_type = HUNT_MODE
    if query.get("mode") == CORRELATION_MODE:
        indicator_type = CORRELATION_MODE

    for indicator in indicators:
        try:
            KvCollection(app_env).delete_indicator_search(
                ioc_type=indicator, indicator_type=indicator_type
            )
        except Exception:
            pass
            # failure is 404.
    return 200, {}


def get_configured_indicators(app_env: RfesAppEnv, indicator_type: str) -> List[str]:
    """Get list of configured default indicators."""
    default_stanzas = KvCollection(app_env).indicator_searches(
        query={"indicator_type": indicator_type}
    )
    default_stanzas = [entry["ioc_type"] for entry in default_stanzas]
    return [key for key in DEFAULT_INDICATOR_TYPES if key in default_stanzas]


@endpoint_requires_payload
def toggle_auto_threat_hunt_enabled(in_dict, app_env):
    """Save auto threat hunt toggle - affects NEW profiles only"""
    payload = json.loads(in_dict["payload"])
    enabled = payload.get(AUTOMATIC_THREAT_HUNT_FIELD, "0") == "1"

    # Check what default indicators are configured
    configured = get_configured_indicators(app_env, HUNT_MODE)

    client = SplunkClient(app_env)

    client.config.post_config(
        CONFIG_FILENAME,
        PORTAL_PLATFORM_STANZA,
        {AUTOMATIC_THREAT_HUNT_FIELD: "1" if enabled else "0"},
    )

    if enabled:
        if len(configured) < len(DEFAULT_INDICATOR_TYPES):
            return 200, {
                "status": "warning",
                "message": f"Only {', '.join(configured)} default indicators configured. Automatic Threat Hunt Execution will apply to newly imported profiles.",
            }
        else:
            return 200, {
                "status": "success",
                "message": "Automatic threat hunts enabled, the setting will apply to newly imported profiles.",
            }
    else:
        # Disabled successfully
        return 200, {
            "status": "success",
            "message": "Automatic threat hunts disabled, the setting will apply to newly imported profiles.",
        }


@endpoint_requires_payload
def update_ato_dm_correlation_delay(in_dict, app_env):
    """Save ATO Datamodel Correlations delay."""
    payload = json.loads(in_dict["payload"])
    _validate_ato_dm_correlation_delay_payload(payload)
    new_value = payload["value"] * 60  # convert minutes to seconds

    client = SplunkClient(app_env)
    client.config.post_config(
        CONFIG_FILENAME,
        PORTAL_PLATFORM_STANZA,
        {ATO_DM_DELAY_SECONDS_FIELD: new_value},
    )
    return 200, {}


def _validate_ato_dm_correlation_delay_payload(payload: dict):
    schema = {
        "value": int,
    }
    validate_dict(payload, schema)

    if payload["value"] < 0:
        raise ValidationError('"value" must be a non-negative integer.')


def update_sigma_hunt_timeout(in_dict, app_env):
    """Save Sigma Threat Hunt timeout."""
    payload = json.loads(in_dict["payload"])
    _validate_sigma_hunt_timeout_payload(payload)

    client = SplunkClient(app_env)
    client.config.post_config(
        CONFIG_FILENAME,
        PORTAL_PLATFORM_STANZA,
        {"sigma_hunt_timeout_seconds": payload["value"]},
    )
    return 200, {}


def _validate_sigma_hunt_timeout_payload(payload: dict):
    schema = {
        "value": int,
    }
    validate_dict(payload, schema)

    if payload["value"] <= 0:
        raise ValidationError('"value" must be a positive integer.')


def get_auto_threat_hunt_settings(in_dict, app_env):
    client = SplunkClient(app_env)

    # Get toggle state
    try:
        config = client.config.get_config(
            CONFIG_FILENAME, stanza=PORTAL_PLATFORM_STANZA
        )
        enabled = config["entry"][0]["content"].get(AUTOMATIC_THREAT_HUNT_FIELD, "0")
    except HTTPError:
        enabled = "0"

    # Check if any defaults exist
    configured = get_configured_indicators(app_env, HUNT_MODE)

    return 200, {
        "entry": [
            {
                "content": {
                    "enabled": enabled,
                    "defaults_configured": "1" if configured else "0",
                }
            }
        ]
    }


@endpoint_requires_payload
def enable_ato_capabilities(in_dict: dict, app_env: RfesAppEnv):
    payload = json.loads(in_dict["payload"])
    _validate_enable_ato_capabilities_payload(payload)

    rf_client = RFClient(app_env)
    rf_client.config.update_capability(payload["capabilities"])
    return 200, {}


def _validate_enable_ato_capabilities_payload(payload: dict):
    schema = {
        "capabilities": ListField(str),
    }
    validate_dict(payload, schema)

    if len(payload["capabilities"]) == 0:
        raise ValidationError("At least one capability must be provided.")

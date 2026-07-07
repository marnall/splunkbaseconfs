#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import json
import logging
import random
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Optional, Sequence, Any, Callable
from urllib import parse

import httplib2
import requests
import socks
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as grequests
from google.oauth2 import service_account
from solnlib import conf_manager, log

APP_NAME = "Splunk_TA_Google_Workspace"

DIRECTORY_USER_SCOPE = "https://www.googleapis.com/auth/admin.directory.user.readonly"
ACTIVITY_REPORT_SCOPE = "https://www.googleapis.com/auth/admin.reports.audit.readonly"
ALERT_CENTER_SCOPE = "https://www.googleapis.com/auth/apps.alerts"
USAGE_REPORT_SCOPE = "https://www.googleapis.com/auth/admin.reports.usage.readonly"

ACTIVITY_REPORT_CHECKPOINT_COLLECTION_PREFIX = "activity_report_checkpoint_"
ACTIVITY_REPORT_CHECKPOINT_COLLECTION_KEY = "checkpoint"

ACTIVITY_REPORT_UNSUCCESSFUL_RUNS_COLLECTION_PREFIX = (
    "activity_report_unsuccessful_runs_"
)
ACTIVITY_REPORT_UNSUCCESSFUL_RUNS_COLLECTION_KEY = "unsuccessful_runs"


def _get_input_name_from_full_name(full_input_name: str):
    # Full input name is in form of "<input_type>://<input_name>"
    return full_input_name.split("/")[-1]


def get_activity_report_unsuccessful_runs_collection_name_from_input_name(
    input_name: str,
) -> str:
    # Input name is an actual name of the input, exactly how user entered it.
    return f"{ACTIVITY_REPORT_UNSUCCESSFUL_RUNS_COLLECTION_PREFIX}{input_name}"


def get_activity_report_unsuccessful_runs_collection_name_from_full_name(
    full_input_name: str,
) -> str:
    # Full input name is in form of "<input_type>://<input_name>"
    input_name = _get_input_name_from_full_name(full_input_name)
    return get_activity_report_unsuccessful_runs_collection_name_from_input_name(
        input_name
    )


def get_activity_report_checkpoint_collection_name_from_input_name(
    input_name: str,
) -> str:
    # Input name is an actual name of the input, exactly how user entered it.
    return f"{ACTIVITY_REPORT_CHECKPOINT_COLLECTION_PREFIX}{input_name}"


def get_activity_report_checkpoint_collection_name_from_full_name(
    full_input_name: str,
) -> str:
    # Full input name is in form of "<input_type>://<input_name>"
    input_name = _get_input_name_from_full_name(full_input_name)
    return get_activity_report_checkpoint_collection_name_from_input_name(input_name)


def logger_for_input(full_input_name: str) -> logging.Logger:
    # This function should be used to initialize logger for any modular input.
    input_name = _get_input_name_from_full_name(full_input_name)
    return log.Logs().get_logger(f"{APP_NAME.lower()}_{input_name}")


def build_http_connection(proxy_config: Optional[Dict[str, Any]]) -> httplib2.Http:
    """
    Returns a httplib2.Http object with optional proxy.
    """
    if proxy_config is not None:
        proxy_url = proxy_config["proxy_url"]
        proxy_port = proxy_config["proxy_port"]
        if proxy_config["proxy_username"] is not None:
            proxy_username = parse.unquote(proxy_config["proxy_username"])
        else:
            proxy_username = None
        if proxy_config["proxy_password"] is not None:
            proxy_password = parse.unquote(proxy_config["proxy_password"])
        else:
            proxy_password = None
        proxy_info = httplib2.ProxyInfo(
            proxy_type=socks.PROXY_TYPE_HTTP,
            proxy_host=proxy_url,
            proxy_port=proxy_port,
            proxy_user=proxy_username,
            proxy_pass=proxy_password,
        )
        return httplib2.Http(proxy_info=proxy_info)
    return httplib2.Http(proxy_info=None)


def build_proxies_from_proxy_config(
    proxy_config: Optional[Dict[str, Any]]
) -> Optional[Dict[str, str]]:
    """
    Returns a dictionary that can be used by some of the functions in the add-on.
    """
    if proxy_config is None:
        return None
    return {
        "http": _convert_proxy_config_to_string(proxy_config),
        "https": _convert_proxy_config_to_string(proxy_config),
    }


def _convert_proxy_config_to_string(proxy_config: Dict[str, Any]) -> str:
    """
    Returns a string representation that can be used when setting up environment
    variables for some of the inputs.
    """
    proxy_type = proxy_config["proxy_type"]
    proxy_url = proxy_config["proxy_url"]
    proxy_port = proxy_config["proxy_port"]
    proxy_username = proxy_config["proxy_username"]
    proxy_password = proxy_config["proxy_password"]
    if proxy_username and proxy_password:
        return "{}://{}:{}@{}:{}".format(
            proxy_type,
            proxy_username,
            proxy_password,
            proxy_url,
            proxy_port,
        )
    else:
        return f"{proxy_type}://{proxy_url}:{proxy_port}"


def _get_settings(session_key: str) -> Dict[str, Any]:
    """
    Returns settings stored in the .conf file.
    """
    settings_cfm = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-splunk_ta_google_workspace_settings",
    )
    conf = settings_cfm.get_conf("splunk_ta_google_workspace_settings").get_all()
    return conf


def get_proxy_settings(
    logger: logging.Logger, session_key: str
) -> Optional[Dict[str, Any]]:
    """
    This function reads proxy settings if any, otherwise returns None.
    Only HTTPS proxies are supported.
    :param logger: Logger object instance.
    :param session_key: Session key for particular modular input.
    """
    try:
        conf = _get_settings(session_key)
        proxy_stanza = {}
        for k, v in conf["proxy"].items():
            proxy_stanza[k] = v

        proxy_enabled = proxy_stanza.get("proxy_enabled", 0)
        if proxy_enabled is None or int(proxy_enabled) == 0:
            logger.info("Proxy is disabled")
            return None
        proxy_type = "http"
        proxy_url = proxy_stanza.get("proxy_url")
        proxy_port = int(proxy_stanza.get("proxy_port"))
        proxy_username_from_config = proxy_stanza.get("proxy_username")
        if proxy_username_from_config is None:
            proxy_username = None
        else:
            proxy_username = parse.quote(proxy_username_from_config.encode(), safe="")
        proxy_password_from_config = proxy_stanza.get("proxy_password")
        if proxy_password_from_config is None:
            proxy_password = None
        else:
            proxy_password = parse.quote(proxy_password_from_config.encode(), safe="")
        logger.info("Successfully fetched configured proxy details")
        return {
            "proxy_type": proxy_type,
            "proxy_url": proxy_url,
            "proxy_port": proxy_port,
            "proxy_username": proxy_username,
            "proxy_password": proxy_password,
        }
    except Exception as e:
        log.log_exception(
            logger,
            e,
            "Proxy Error",
            msg_before=f"Failed to fetch proxy details from configuration. {traceback.format_exc()}",
            log_level=logging.CRITICAL,
        )
        sys.exit(1)


def get_advanced_settings(
    logger: logging.Logger, session_key: str
) -> Optional[Dict[str, Any]]:
    try:
        conf = _get_settings(session_key)
        advanced_settings_raw = {}
        for k, v in conf["advanced_settings"].items():
            advanced_settings_raw[k] = v
        activity_report_interval_size_str = advanced_settings_raw.get(
            "activity_report_interval_size"
        )
        activity_report_interval_size = int(activity_report_interval_size_str)
        advanced_settings = {
            "activity_report_interval_size": activity_report_interval_size,
        }
        logger.info(f"Advanced settings: {advanced_settings}")
        return advanced_settings
    except Exception as e:
        log.log_exception(
            logger,
            e,
            "Settings Error",
            msg_before=f"Failed to fetch advanced settigns. Error: {e}",
        )
        return None


def get_account_details(session_key: str, account_name: str) -> Dict[str, str]:
    """
    Returns username and certificate for a specific account_name.
    :param session_key: session key for particular modular input.
    :param account_name: account name configured in the addon.
    """
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-splunk_ta_google_workspace_account",
        )
        account_conf_file = cfm.get_conf("splunk_ta_google_workspace_account")
        stanza = account_conf_file.get(account_name)
        username = stanza.get("username")
        certificate = stanza.get("certificate")
        if certificate is None:
            log.Logs().get_logger(APP_NAME.lower()).error(
                f"Certificate for account '{account_name}' is None. "
                "This indicates a corrupted or unreadable credential in Splunk's storage/passwords. "
                "To resolve: re-save the account in the add-on Configuration tab, or identify and "
                f"delete the corrupted entry at /servicesNS/nobody/{APP_NAME}/storage/passwords."
            )
        return {"username": username, "certificate": certificate}
    except Exception as e:
        log.Logs().get_logger(APP_NAME.lower()).error(
            f"Failed to load account details for '{account_name}': {e}. "
            "This may be caused by a corrupted credential (clear_password=None) in storage/passwords "
            "after an app data migration or architecture change. "
            f"Check /servicesNS/nobody/{APP_NAME}/storage/passwords for entries with no clear_password value.",
            exc_info=True,
        )
        return {}


class CouldNotRefreshCredentialsException(Exception):
    pass


def _get_credentials_transport(
    proxies: Optional[Dict[str, str]] = None
) -> grequests.Request:
    if proxies is not None:
        session = requests.Session()
        session.proxies.update(proxies)
        return grequests.Request(session)
    return grequests.Request()


def _retry_credentials_refresh(
    logger: logging.Logger,
    credentials: service_account.Credentials,
    num_retries: int = 5,
    proxies: Optional[dict] = None,
    sleep: Callable[[float], Any] = time.sleep,
    rand: Callable[[], float] = random.random,
) -> service_account.Credentials:
    # Refreshes service account credentials.
    for retry_num in range(num_retries):
        if retry_num > 0:
            sleep_time = rand() + retry_num
            logger.warning(
                f"Sleeping {sleep_time} seconds before retry {retry_num} of {num_retries}"
            )
            sleep(sleep_time)
        try:
            credentials.refresh(_get_credentials_transport(proxies))
            return credentials
        except google_auth_exceptions.RefreshError as e:
            if "unauthorized_client" in str(e):
                # This is a permanent configuration failure — retrying will not help.
                # The service account does not have domain-wide delegation, or the
                # delegated "Administrator email" does not have the required OAuth scopes
                # authorised in Google Admin Console.
                logger.error(
                    f"Token refresh failed with 'unauthorized_client' for account credentials: {e}. "
                    "This is a permanent authorization failure — domain-wide delegation is either "
                    "not configured for this service account, or the delegated 'Administrator email' "
                    "account has not been granted the required OAuth scopes. "
                    "Fix: in Google Admin Console → Security → API controls → Domain-wide delegation, "
                    "verify the service account client ID is present and authorised for all required "
                    "scopes (e.g. https://www.googleapis.com/auth/admin.reports.audit.readonly)."
                )
                raise CouldNotRefreshCredentialsException from e
            log.log_exception(
                logger,
                e,
                "Credentials error",
                msg_before=f"Could not refresh service account credentials because of {e}",
            )
            continue
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Credentials error",
                msg_before=f"Could not refresh service account credentials because of {e}",
            )
            continue
    raise CouldNotRefreshCredentialsException


def get_service_account_credentials(
    logger: logging.Logger,
    session_key: str,
    account_name: str,
    scopes: Sequence[str],
    proxies: Optional[dict] = None,
    num_retries: int = 5,
) -> Optional[service_account.Credentials]:
    """
    Returns authenticated service account credentials.
    :param logger: Logger object.
    :param session_key: Splunk session key.
    :param account_name: Account name to use for this input.
    :param scopes: Scopes to authenticate service account against.
    :param proxies: HTTPS proxy connection string.
    :param num_retries: Number of retries.
    """
    account_details = get_account_details(session_key, account_name)
    certificate = account_details.get("certificate")
    if certificate is None:
        logger.error(
            f"Could not obtain certificate for account '{account_name}'. "
            "The certificate value is None — this typically means the credential was not decrypted "
            "correctly, or the storage/passwords entry was corrupted (e.g. after an app data migration). "
            "Re-save the account in the add-on Configuration tab to restore the credential."
        )
        return None
    try:
        loaded_certificate = json.loads(certificate)
    except json.decoder.JSONDecodeError:
        logger.error(f"Cannot decode certificate for {account_name}")
        return None
    creds_service = service_account.Credentials.from_service_account_info(
        loaded_certificate,
        scopes=scopes,
    )
    creds = creds_service.with_subject(account_details["username"])
    logger.info(f"Refresh token at {datetime.utcnow()} UTC")
    return _retry_credentials_refresh(logger, creds, num_retries, proxies)

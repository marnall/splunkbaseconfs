#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import datetime
import json
import time
import traceback
import threading
import remedy_consts as c
import requests
from logger_manager import get_logger
from solnlib import conf_manager, utils

_LOGGER = get_logger("rest_api")

API_VERSION = "v1.0"

INCIDENT_FORM = "HPD:IncidentInterface"
INCIDENT_CREATE_FORM = "HPD:IncidentInterface_Create"

JWT_LOGIN_ENDPOINT = "{ar_server_url}/api/jwt/login"
JWT_LOGOUT_ENDPOINT = "{ar_server_url}/api/jwt/logout"
FORM_ENDPOINT = "{{ar_server_url}}/api/arsys/{api_version}/entry/{{form_name}}".format(
    api_version=API_VERSION
)
INCIDENT_FORM_ENDPOINT = (
    "{{ar_server_url}}/api/arsys/{api_version}/entry/{form_name}".format(
        api_version=API_VERSION, form_name=INCIDENT_FORM
    )
)

UNREACHABLE_URL_MSG = (
    "Unable to reach server at '{url}'. Check configurations and network settings"
)

RESPONSE_CODE_WISE_MSG = {
    requests.codes.UNAUTHORIZED: "Authentication failed",
    requests.codes.NOT_FOUND: "URL Not Found",
    requests.codes.FORBIDDEN: "Insufficient permissions",
    requests.codes.BAD_REQUEST: "Bad request",
}

MAX_RETRIES = 5
INITIAL_DELAY = 0.5  # Initial wait time in seconds
BACKOFF_FACTOR = 2  # Exponential backoff multiplier
TIMEOUT = 120  # Timeout for the request
NON_RETRYABLE_STATUS_CODES = [200, 201, 204, 400, 401, 403, 404]

TOKEN_LOCK = threading.Lock()
TOKEN_REGENERATED = threading.Event()


def set_logger(new_logger):
    """Call this to use the existing logger in this file"""
    global _LOGGER
    _LOGGER = new_logger


def execute_with_retries(method, url, logger=_LOGGER, **kwargs):
    """
    Executes an HTTP request with retry logic for handling transient failures.

    This function attempts to send an HTTP request using the specified method (`GET`, `POST`, or `PUT`)
    and retries the request up to `MAX_RETRIES` times in case of failures, with an increasing delay.

    Args:
        method (str): The HTTP method to use ('GET', 'POST', or 'PUT').
        url (str): The target URL for the request.
        event_number (int): The event number for tracking purposes.
        logger (Logger): Logger instance used for logging messages.
        **kwargs: Additional request parameters including:
            - json (dict, optional): JSON payload for POST/PUT requests.
            - data (dict, optional): Form data for POST/PUT requests.
            - params (dict, optional): Query parameters for GET requests.
            - headers (dict, optional): HTTP headers to include in the request.
            - proxies (dict, optional): Proxy settings for the request.
            - verify (bool, optional): Whether to verify SSL certificates.
            - timeout (int, optional): Request timeout in seconds.

    Returns:
        requests.Response: The HTTP response object.
    """
    delay = INITIAL_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Send the appropriate HTTP request based on the method
            response = requests.request(
                method=method.upper(),
                url=url,
                timeout=TIMEOUT,
                **kwargs,  # Pass all kwargs directly
            )

            if response.status_code in NON_RETRYABLE_STATUS_CODES:
                return response
            msg = "Attempt {attempt} failed. Error occured, status_code={status_code}, url='{url}'".format(
                attempt=attempt,
                status_code=response.status_code,
                url=url,
            )
            logger.debug(msg + ", response={}".format(response.text))
        except Exception as e:
            if attempt < MAX_RETRIES:
                logger.debug(
                    f"Attempt {attempt} failed: {e}, retrying in {delay} seconds..."
                )
            else:
                raise
        time.sleep(delay)  # Wait before retrying
        delay *= BACKOFF_FACTOR  # Increase delay exponentially

    return response


def get_remedy_fields(session_key, stanza):
    CONF_FILE = "remedy_fields"

    cm = conf_manager.ConfManager(
        session_key,
        c.APP_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(c.APP_NAME, CONF_FILE),
    )

    conf = cm.get_conf(CONF_FILE, True)
    conf.reload()

    IGNORE_FIELDS = {
        "required",
        "disabled",
        "eai:appName",
        "eai:userName",
        "eai:access",
        "name",
    }

    settings = conf.get(stanza)
    required_str = settings.get("required")
    required_fields = set()
    # get required args information from conf file.
    if required_str:
        tmp_lst = required_str.split(",")
        for field in tmp_lst:
            if not field:
                continue
            if settings.get(field):
                continue
            required_fields.add(field.strip())

    # get default field and it's value
    default_fields = {}
    for k, v in settings.items():
        if k in IGNORE_FIELDS:
            continue
        default_fields[k] = v

    return required_fields, default_fields


def get_proxy_config(session_key):
    settings_cfm = conf_manager.ConfManager(
        session_key,
        c.APP_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_remedy_settings".format(
            c.APP_NAME
        ),
    )

    splunk_ta_remedy_settings_conf = settings_cfm.get_conf(
        "splunk_ta_remedy_settings"
    ).get_all()

    proxies = {
        key: value for key, value in splunk_ta_remedy_settings_conf["proxy"].items()
    }

    if utils.is_true(proxies.get("proxy_enabled", "")):
        _LOGGER.info("Proxy is enabled")
        proxy_type = proxies.get("proxy_type")
        proxy_url = proxies.get("proxy_url")
        proxy_port = proxies.get("proxy_port")
        proxy_username = proxies.get("proxy_username", "")
        proxy_password = proxies.get("proxy_password", "")

        if proxy_username and proxy_password:
            proxy_username = requests.compat.quote_plus(proxy_username)
            proxy_password = requests.compat.quote_plus(proxy_password)
            proxy_uri = "%s://%s:%s@%s:%s" % (
                proxy_type,
                proxy_username,
                proxy_password,
                proxy_url,
                proxy_port,
            )
        else:
            proxy_uri = "%s://%s:%s" % (proxy_type, proxy_url, proxy_port)

        return {"http": proxy_uri, "https": proxy_uri}

    return None


def create_jwt_token(account_info, verify_ssl, proxy_config=None):
    """
    Generate a new JWT token

    Args:
        account_info (Object): Remedy Account details
        verify_ssl (String): SSL check configuration (True/False or ssl certificate path)
        proxy_config (Object, optional): Proxy configuration. Defaults to None.

    Returns:
        String: Newly created JWT token
    """
    jwt_url = JWT_LOGIN_ENDPOINT.format(ar_server_url=account_info.get("server_url"))
    payload = {
        "username": account_info.get("username"),
        "password": account_info.get("password"),
    }
    _LOGGER.debug("Generating jwt token, url='{}'".format(jwt_url))
    try:
        response = execute_with_retries(
            "POST",
            jwt_url,
            logger=_LOGGER,
            data=payload,
            proxies=proxy_config,
            verify=verify_ssl,
        )
    except Exception:
        msg = UNREACHABLE_URL_MSG.format(url=jwt_url)
        _LOGGER.exception(msg)
        raise Exception(msg)

    if response.status_code == requests.codes.OK:
        _LOGGER.info("Successfully generated a new jwt token")
        return response.text

    temp_err_msg = RESPONSE_CODE_WISE_MSG.get(response.status_code, "Error occured")
    msg = "{msg}, status_code={status_code}, url='{url}'".format(
        msg=temp_err_msg, status_code=response.status_code, url=jwt_url
    )
    (
        _LOGGER.warning(msg + ", response={}".format(response.text))
        if response.status_code == 401
        else _LOGGER.error(msg + ", response={}".format(response.text))
    )
    raise Exception(msg)


def update_token_in_conf_file(jwt_token, account_info, account_name, session_key):
    _LOGGER.debug("Saving the newly generated jwt token...")
    try:
        account_cfm = conf_manager.ConfManager(
            session_key,
            c.APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_remedy_account".format(
                c.APP_NAME
            ),
        )

        splunk_ta_remedy_account_conf = account_cfm.get_conf(
            "splunk_ta_remedy_account", refresh=True
        )

        encrypt_fields = {"jwt_token": jwt_token}

        if account_info.get("password"):
            encrypt_fields["password"] = account_info["password"]

        splunk_ta_remedy_account_conf.update(
            account_name, encrypt_fields, encrypt_fields.keys()
        )
    except Exception as err:
        _LOGGER.exception("Failure occurred while saving jwt token in conf file")
        raise err
    _LOGGER.info("Saved jwt token successfully")


def fetch_form_data(account_info, form_name, params, verify_ssl, proxy_config=None):
    """
    Fetch form data from the Remedy using Rest API

    Args:
        account_info (Object): Remedy Account details
        form_name (String): Form name to fetch the data
        params (Object): API request parameters
        verify_ssl (String): SSL check configuration (True/False or ssl certificate path)
        proxy_config (Object, optional): Proxy configuration. Defaults to None.

    Returns:
        Object: data fetched from the Remedy in Json format
    """
    form_url = FORM_ENDPOINT.format(
        ar_server_url=account_info.get("server_url"), form_name=form_name
    )
    _LOGGER.debug("Fetching data, url='{}', params={}".format(form_url, params))
    headers = {"Authorization": "AR-JWT {}".format(account_info.get("jwt_token"))}
    try:
        response = execute_with_retries(
            "GET",
            form_url,
            logger=_LOGGER,
            params=params,
            headers=headers,
            proxies=proxy_config,
            verify=verify_ssl,
        )
    except Exception:
        msg = UNREACHABLE_URL_MSG.format(url=form_url)
        _LOGGER.exception(msg)
        raise Exception(msg)

    if response.status_code == requests.codes.OK:
        _LOGGER.info(
            "Successfully fetched data for url='{}', params={}".format(form_url, params)
        )
        return json.loads(response.text)

    temp_err_msg = RESPONSE_CODE_WISE_MSG.get(response.status_code, "Error occured")
    msg = "{msg}, status_code={status_code}, url='{url}', params={params}, response={response}".format(
        msg=temp_err_msg,
        status_code=response.status_code,
        url=form_url,
        params=params,
        response=response.text,
    )
    _LOGGER.warning(msg) if response.status_code == 401 else _LOGGER.error(msg)
    raise Exception(msg)


def create_incident(
    account_info,
    form_name,
    params,
    payload,
    verify_ssl,
    proxy_config=None,
    event_number=1,
):
    """
    Create a new Incident using Rest API

    Args:
        account_info (Object): Remedy Account details
        form_name (String): Form name to fetch the data
        params (Object): API request parameters
        payload (Object): API request payload(incident data)
        verify_ssl (String): SSL check configuration (True/False or ssl certificate path)
        proxy_config (Object, optional): Proxy configuration. Defaults to None.

    Returns:
        Object: Details of the Incident created
    """
    url = FORM_ENDPOINT.format(
        ar_server_url=account_info.get("server_url"), form_name=form_name
    )
    headers = {"Authorization": "AR-JWT {}".format(account_info.get("jwt_token"))}

    _LOGGER.debug(
        "[event_number= {}], Incident post request, url='{}', params={}, payload={}".format(
            event_number, url, params, payload
        )
    )
    # jscpd:ignore-start
    try:
        response = execute_with_retries(
            "POST",
            url,
            logger=_LOGGER,
            json=payload,
            params=params,
            headers=headers,
            proxies=proxy_config,
            verify=verify_ssl,
        )
    except Exception:
        msg = UNREACHABLE_URL_MSG.format(url=url)
        _LOGGER.exception("[event_number= {}] {}".format(event_number, msg))
        raise Exception(msg)

    if response.status_code in (requests.codes.OK, requests.codes.CREATED):
        data = json.loads(response.text)
        return data["values"]
    # jscpd:ignore-end

    # jscpd:ignore-start
    temp_err_msg = RESPONSE_CODE_WISE_MSG.get(response.status_code, "Error occured")
    msg = "{msg}, status_code={status_code}, url='{url}', params={params}, response={response}".format(
        msg=temp_err_msg,
        status_code=response.status_code,
        url=url,
        params=params,
        response=response.text,
    )
    (
        _LOGGER.warning("[event_number= {}] {}".format(event_number, msg))
        if response.status_code == 401
        else _LOGGER.error("[event_number= {}] {}".format(event_number, msg))
    )
    raise Exception(msg)


def update_incident(
    # jscpd:ignore-end
    account_info,
    request_id,
    incident_number,
    payload,
    verify_ssl,
    proxy_config=None,
    event_number=1,
):
    """
    Create a new Incident using Rest API

    Args:
        account_info (Object): Remedy Account details
        request_id (String): Request ID of the incident to be updated
        incident_number (String): Incident Number of the incident to be updated
        payload (Object): API request payload(incident data)
        verify_ssl (String): SSL check configuration (True/False or ssl certificate path)
        proxy_config (Object, optional): Proxy configuration. Defaults to None.
    """
    url = (
        INCIDENT_FORM_ENDPOINT.format(ar_server_url=account_info.get("server_url"))
        + "/"
        + request_id
    )
    headers = {"Authorization": "AR-JWT {}".format(account_info.get("jwt_token"))}
    params = {"fields": "values(Incident Number)"}

    # jscpd:ignore-start
    _LOGGER.debug(
        "[event_number={}], Updating Incident '{}', url='{}', params={}, payload={}".format(
            event_number, incident_number, url, params, payload
        )
    )
    try:
        response = execute_with_retries(
            "PUT",
            url,
            logger=_LOGGER,
            json=payload,
            params=params,
            headers=headers,
            proxies=proxy_config,
            verify=verify_ssl,
        )
    except Exception:
        msg = UNREACHABLE_URL_MSG.format(url=url)
        _LOGGER.exception("[event_number= {}] {}".format(event_number, msg))
        raise Exception(msg)
    # jscpd:ignore-end

    # jscpd:ignore-start
    if response.status_code == requests.codes.NO_CONTENT:
        _LOGGER.info(
            "[event_number= {}], Successfully Updated Incident '{}'".format(
                event_number, incident_number
            )
        )
        return

    temp_err_msg = RESPONSE_CODE_WISE_MSG.get(response.status_code, "Error occured")
    msg = "{msg}, status_code={status_code}, url='{url}', params={params}, response={response}".format(
        msg=temp_err_msg,
        status_code=response.status_code,
        url=url,
        params=params,
        response=response.text,
    )
    (
        _LOGGER.warning("[event_number= {}] {}".format(event_number, msg))
        if response.status_code == 401
        else _LOGGER.error("[event_number= {}] {}".format(event_number, msg))
    )
    raise Exception(msg)


def relate_ci_to_incident(
    # jscpd:ignore-end
    account_info,
    payload,
    verify_ssl,
    proxy_config=None,
):
    """
    Relate a CI Name to a given Incident using Rest API

    Args:
        account_info (Object): Remedy Account details
        payload (Object): API request payload(incident data)
        verify_ssl (String): SSL check configuration (True/False or ssl certificate path)
        proxy_config (Object, optional): Proxy configuration. Defaults to None.
    """
    url = FORM_ENDPOINT.format(
        ar_server_url=account_info.get("server_url"),
        form_name="HPD:ServiceInterface",
    )
    headers = {"Authorization": "AR-JWT {}".format(account_info.get("jwt_token"))}
    params = {"fields": "values(Incident Number)"}

    # jscpd:ignore-start
    _LOGGER.debug(
        "Relating CI {} to Incident '{}', url='{}', params={}, payload={}".format(
            payload["values"]["HPD_CI"],
            payload["values"]["Incident Number"],
            url,
            params,
            payload,
        )
    )
    try:
        response = execute_with_retries(
            "POST",
            url,
            logger=_LOGGER,
            json=payload,
            params=params,
            headers=headers,
            proxies=proxy_config,
            verify=verify_ssl,
        )
    except Exception:
        msg = UNREACHABLE_URL_MSG.format(url=url)
        _LOGGER.exception(msg)
        raise Exception(msg)
    # jscpd:ignore-end

    # jscpd:ignore-start
    if response.status_code in (200, 201):
        _LOGGER.info(
            "Successfully related CI='{}' to incident '{}'".format(
                payload["values"]["HPD_CI"],
                payload["values"]["Incident Number"],
            )
        )
        return

    temp_err_msg = RESPONSE_CODE_WISE_MSG.get(response.status_code, "Error occured")
    msg = "{msg}, status_code={status_code}, url='{url}', params={params}, response={response}".format(
        msg=temp_err_msg,
        status_code=response.status_code,
        url=url,
        params=params,
        response=response.text,
    )
    _LOGGER.warning(msg) if response.status_code == 401 else _LOGGER.error(msg)
    raise Exception(msg)


def get_current_time():
    return int(time.time())
    # jscpd:ignore-end


def get_epoch_time(time_string):
    try:
        d = datetime.datetime.strptime(
            time_string, "%m/%d/%Y %H:%M:%S"
        ) - datetime.datetime(1970, 1, 1)
        return int(d.total_seconds())
    except Exception:
        raise Exception(
            "time_string '{}' must be in '%m/%d/%Y %H:%M:%S' format".format(time_string)
        )


def get_sevendaysago_time():
    prev_time = (
        datetime.datetime.utcnow() - datetime.timedelta(7)
    ) - datetime.datetime(1970, 1, 1)
    return int(prev_time.total_seconds())


def get_sslconfig(session_key, disable_ssl_certificate_validation, _LOGGER):
    """
    Fetches the ca_certs_path from the conf file and return
    1) True - If disable_ssl_certificate_validation is false
    2) ca_certs_path - If disable_ssl_certificate_validation is false and ca_certs_path is present

    :param session_key: Session key for splunk
    :param disable_ssl_certificate_validation: The ssl verification is on or off
    :param _LOGGER: Logger to write events in the validation log file.
    """
    try:
        # Default value will be used for ca_certs_path if there is any error
        _LOGGER.debug("Proceeding to fetch ssl configuration")
        sslconfig = False
        ca_certs_path = ""
        cfm = conf_manager.ConfManager(
            session_key,
            c.APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                c.APP_NAME, c.REMEDY_CONF
            ),
        )

        ca_certs_path = (
            cfm.get_conf(c.REMEDY_CONF, refresh=True)
            .get("additional_parameters")
            .get("ca_certs_path")
            or ""
        ).strip()

    except Exception:
        msg = f"Error while fetching ca_certs_path from '{c.REMEDY_CONF}' conf. Traceback: {traceback.format_exc()}"
        _LOGGER.error(msg)

    if disable_ssl_certificate_validation is False:
        if ca_certs_path != "":
            sslconfig = ca_certs_path
        else:
            sslconfig = True

    return sslconfig


class Retry:
    def __init__(
        self,
        session_key,
        account_name,
        proxy_config,
        account_manager,
        verify_ssl,
        store_token=True,
    ):
        self.session_key = session_key
        self.account_name = account_name
        self.proxy_config = proxy_config
        self.account_manager = account_manager
        self.verify_ssl = verify_ssl
        self.store_token = store_token

    def retry(self, func, *arg, **kwargs):
        # No need to pass the account_info param
        global TOKEN_REGENERATED
        account_info = self.account_manager.get_account_details(self.account_name)
        try:
            return func(account_info, *arg, **kwargs)
        except Exception as err:
            if str(err).startswith(RESPONSE_CODE_WISE_MSG[requests.codes.UNAUTHORIZED]):
                TOKEN_REGENERATED.clear()
                with TOKEN_LOCK:
                    if not TOKEN_REGENERATED.is_set():
                        new_jwt_token = create_jwt_token(
                            account_info,
                            self.verify_ssl,
                            proxy_config=self.proxy_config,
                        )
                        if self.store_token:
                            update_token_in_conf_file(
                                new_jwt_token,
                                account_info,
                                self.account_name,
                                self.session_key,
                            )

                            self.account_manager.fetch_accounts()
                        else:
                            # store the new_jwt_token in the memory
                            self.account_manager.set_jwt_token_in_memory(
                                self.account_name, new_jwt_token
                            )
                        TOKEN_REGENERATED.set()
                account_info = self.account_manager.get_account_details(
                    self.account_name
                )

                return func(account_info, *arg, **kwargs)
            else:
                raise err

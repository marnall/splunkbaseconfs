import json
import time
from urllib.parse import quote

import ta_securityscorecard_declare
import splunk.rest as rest
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.utils import is_true

from scorecard import Portfolio
from scorecard_exceptions import InvalidJSONError, ServerError


def build_proxy_dict(proxy_settings):
    """This method is used to create a dictionary with the proxy details."""
    if proxy_settings:
        proxy_type = proxy_settings['proxy_type']
        if proxy_settings.get('proxy_username') and proxy_settings.get('proxy_password'):
            proxy = {
                'http': '{proxy_type}://{user}:{password}@{host}:{port}'.format(
                    proxy_type=proxy_type,
                    user=quote(proxy_settings['proxy_username'], safe=""),
                    password=quote(proxy_settings['proxy_password'], safe=""),
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
                'https': '{proxy_type}://{user}:{password}@{host}:{port}'.format(
                    proxy_type=proxy_type,
                    user=quote(proxy_settings['proxy_username'], safe=""),
                    password=quote(proxy_settings['proxy_password'], safe=""),
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
            }
        else:
            proxy = {
                'http': '{proxy_type}://{host}:{port}'.format(
                    proxy_type=proxy_type,
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
                'https': '{proxy_type}://{host}:{port}'.format(
                    proxy_type=proxy_type,
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
            }
    else:
        proxy = {}

    return proxy


def format_portfolio_ids(portfolio_ids):
    """This method is used to format the portfolio ids."""
    try:
        # Python 2.7
        is_string = isinstance(portfolio_ids, unicode)
    except NameError:
        # Python 3
        is_string = isinstance(portfolio_ids, str)

    if is_string and portfolio_ids.strip().strip(',').lower() == 'all':
        portfolio_ids = 'all'
    elif is_string:
        portfolio_ids = portfolio_ids.strip().strip(',')
        portfolio_ids = portfolio_ids.split(',') if portfolio_ids else None

    return portfolio_ids


def extract_input_fields(helper, fields):
    """This method is used to extract the input fields."""
    inputs = {}
    for field in fields:
        inputs[field] = helper.get_arg(field)

    proxy_settings = helper.get_proxy()
    inputs['proxy'] = build_proxy_dict(proxy_settings)
    message = 'Proxy settings found' if inputs['proxy'] else 'No proxy settings found'
    helper.log_info(message)

    inputs['portfolio_ids'] = format_portfolio_ids(inputs.get('portfolio_ids'))

    if not inputs['portfolio_ids']:
        helper.log_warning('No portfolio ids received. Fetching data from portfolio companies will be skipped')
    elif inputs['portfolio_ids'] == 'all':
        helper.log_info('Data from all portfolio companies will be fetched')
    else:
        helper.log_info('Data from following portfolios will be fetched.\n{}'.format(inputs['portfolio_ids']))

    return inputs


def build_portfolio(api_url, helper, access_key, ids, **config):
    """This method is used to create a portfolio object."""
    try:
        portfolio = Portfolio(api_url, helper, access_key, ids, **config)
    except InvalidJSONError:
        helper.log_error("Data received from API is not in JSON format.")
        helper.log_error("No portfolios to proceed. Stopping...")
        raise
    except ServerError:
        helper.log_error("Sever error occurred while calling the API")
        helper.log_error("No portfolios to proceed. Stopping...")
        raise
    except Exception:
        helper.log_error("Error in finding portfolios")
        raise

    for invalid_id in portfolio.invalid_ids:
        helper.log_error("The Portfolio ID {} invalid. "
                         "Please validate that your portfolio ID is entered correctly".format(invalid_id))

    return portfolio


def wait_for_kvstore(session_key, helper):
    """Wait for KV store to initialize.

    Raises:
        Exception: when kv store is not in ready state
    """
    retries = 0

    def get_status(uri):
        _, content = rest.simpleRequest(
            uri,
            sessionKey=session_key,
            method="GET",
            getargs={"output_mode": "json"},
            raiseAllErrors=True,
        )
        data = json.loads(content)["entry"]
        return data[0]["content"]["current"].get("status")

    uri = "/services/kvstore/status"
    status = get_status(uri)
    if status != "ready":
        while retries < 3:
            retries += 1
            helper.log_info("KV Store status is not ready. Checking again in 60 seconds. retry={}".format(retries))
            time.sleep(60)
            retry_status = get_status(uri)

            if retry_status == "ready":
                break

        if retry_status != "ready":
            raise Exception("KV store is not in ready state. Current state: " + str(status))


def get_proxy_uri(session_key, proxy_settings=None):
    """
    Generate proxy uri from provided configurations.

    :param session_key: Splunk Session Key
    :param proxy_settings: Proxy configuration dict. Defaults to None.
    :return: if proxy configuration available returns uri string else None.
    """
    if not proxy_settings:
        proxy_settings = get_proxy_configuration(session_key)

    if proxy_settings.get("proxy_enabled") == "0":
        return None

    if proxy_settings.get("proxy_password"):
        if proxy_settings.get("proxy_username") == "" or proxy_settings.get("proxy_username") is None:
            raise ValueError(
                "Proxy Username is not provided. Please provide the proxy username to perform the data collection."
            )

    if proxy_settings.get("proxy_username"):
        if proxy_settings.get("proxy_password") == "" or proxy_settings.get("proxy_password") is None:
            raise ValueError(
                "Proxy Password is not provided. Please provide the proxy password to perform the data collection."
            )
        proxy_settings["proxy_password"] = get_proxy_clear_password(session_key)

    if all(
        [
            proxy_settings,
            is_true(proxy_settings.get("proxy_enabled")),
            proxy_settings.get("proxy_url"),
            proxy_settings.get("proxy_type"),
        ]
    ):
        http_uri = proxy_settings["proxy_url"]

        if proxy_settings.get("proxy_port"):
            http_uri = "{}:{}".format(http_uri, proxy_settings.get("proxy_port"))

        if proxy_settings.get("proxy_username") and proxy_settings.get(
            "proxy_password"
        ):
            http_uri = "{}:{}@{}".format(
                quote(proxy_settings["proxy_username"], safe=""),
                quote(proxy_settings["proxy_password"], safe=""),
                http_uri,
            )

        http_uri = "{}://{}".format(proxy_settings['proxy_type'], http_uri)

        proxy_data = {"http": http_uri, "https": http_uri}

        return proxy_data
    else:
        return None


def get_proxy_configuration(session_key):
    """
    Get proxy configuration settings.

    :return: proxy configuration dict.
    """
    rest_endpoint = "/servicesNS/nobody/{}/TA_securityscorecard_settings/proxy".format(ta_securityscorecard_declare.ta_name)

    _, content = rest.simpleRequest(
        rest_endpoint,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    return json.loads(content)["entry"][0]["content"]


def get_proxy_clear_password(session_key):
    """
    Get clear password from splunk passwords.conf.

    :return: str/None: proxy password if available else None.
    """
    try:
        manager = CredentialManager(
            session_key,
            app=ta_securityscorecard_declare.ta_name,
            realm="__REST_CREDENTIAL__#{0}#{1}".format(
                ta_securityscorecard_declare.ta_name, "configs/conf-ta_securityscorecard_settings"
            ),
        )
        return json.loads(manager.get_password("proxy")).get("proxy_password")
    except CredentialNotExistException:
        return None


def get_global_account_credential(session_key, account_name):
    """
    Get global account credential.

    :param session_key: Splunk Session Key
    :param account_name: str, global account name configured in the input
    :return: password of the global account credential
    """
    manager = CredentialManager(
        session_key,
        app=ta_securityscorecard_declare.ta_name,
        realm="__REST_CREDENTIAL__#{0}#{1}".format(
            ta_securityscorecard_declare.ta_name, "configs/conf-ta_securityscorecard_account"
        ),
    )
    credential = manager.get_password(account_name)
    return json.loads(credential).get("password")

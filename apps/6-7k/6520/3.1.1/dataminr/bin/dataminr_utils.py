import json

import import_declare_test  # noqa: F401
import splunk.rest as rest
from import_declare_test import ta_name
from requests.compat import quote_plus
from solnlib import conf_manager
from solnlib.utils import is_true


class IntervalConvertor:
    """Interval convertor for Inputs."""

    def encode(self, interval, _):
        """Minutes -> Seconds."""
        return int(interval) * 60

    def decode(self, interval, _):
        """Seconds -> Minutes."""
        return int(int(interval) / 60)


def get_proxy_info(session_key, logger):
    """Get proxy information.

    :param session_key: Splunk session key
    :return: dictionary containing proxy details or None
    """
    proxy_info_dict = {}
    # Retrieve proxy configurations
    try:
        resp, content = rest.simpleRequest(
            f"/servicesNS/nobody/{ta_name}/{ta_name}_settings/proxy",
            sessionKey=session_key,
            method="GET",
            getargs={"output_mode": "json", "--cred--": "1"},
            raiseAllErrors=True,
        )
        # Parse response
        content = json.loads(content)

    except Exception:
        raise

    for item in content["entry"]:
        proxy_info_dict = item["content"]
        break

    # Return None if proxy_enabled is false or proxy hostname or proxy port is not found
    if (
        not is_true(proxy_info_dict.get("proxy_enabled"))
        or not proxy_info_dict.get("proxy_port")  # noqa: W503
        or not proxy_info_dict.get("proxy_url")  # noqa: W503
    ):
        logger.info("Proxy is disabled")
        return None

    proxy_user_pass = ""
    # Quote username and password if available
    if proxy_info_dict.get("proxy_username") and proxy_info_dict.get("proxy_password"):
        proxy_username = quote_plus(proxy_info_dict["proxy_username"], safe="")
        proxy_password = quote_plus(proxy_info_dict["proxy_password"], safe="")
        proxy_user_pass = f"{proxy_username}:{proxy_password}@"

    logger.info("Proxy is enabled")
    # Prepare proxy string
    proxy = "{proxy_type}://{proxy_user_pass}{proxy_host}:{proxy_port}".format(
        proxy_type=proxy_info_dict["proxy_type"],
        proxy_user_pass=proxy_user_pass,
        proxy_host=proxy_info_dict["proxy_url"],
        proxy_port=proxy_info_dict["proxy_port"],
    )
    proxies = {
        "http": proxy,
        "https": proxy,
    }

    return proxies


def get_credentials(account_name, session_key):
    """
    Get credentials from API Query.

    :param account_name: Account name to fetch credentials for.
    :param session_key: Splunk session key

    :return: dictionary containing account details.
    """
    resp, content = rest.simpleRequest(
        f"/servicesNS/nobody/{ta_name}/{ta_name}_account/{account_name}",
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json", "--cred--": "1"},
        raiseAllErrors=True,
    )
    content = json.loads(content)
    return content["entry"][0]["content"]


def get_hec_tokens(session_key):
    """
    Get configured HEC tokens from API Query.

    :param session_key: Splunk session key

    :return: List containing HEC Tokens.
    """
    hec_url = "/servicesNS/nobody/-/data/inputs/http"
    tokens_list = []
    try:
        resp, content = rest.simpleRequest(
            hec_url, sessionKey=session_key, method="GET", getargs={"output_mode": "json"}, raiseAllErrors=True
        )
        content = json.loads(content)
        for http_stanza in content["entry"]:
            tokens_list.append(http_stanza["content"]["token"])
        return tokens_list
    except Exception:
        raise


def update_access_token(account_name, account, new_access_token, session_key):
    """
    Update the token values in the account configuration file.

    :param account_name: Account Name.
    :param account: dictionary containing account details.
    :param new_access_token: Regenerated access token.
    :param account_name: Splunk session key
    """
    account_cfm = conf_manager.ConfManager(
        session_key, ta_name, realm=f"__REST_CREDENTIAL__#{ta_name}#configs/conf-{ta_name}_account"
    )
    encrypt_fields = {
        "access_token": new_access_token,
        "refresh_token": account.get("refresh_token"),
        "client_secret": account.get("client_secret"),
    }
    account_conf = account_cfm.get_conf(f"{ta_name}_account", refresh=True)
    account_conf.update(account_name, encrypt_fields, encrypt_fields.keys())


def get_watchlist_ids(all_watchlists, configured_watchlists):
    """
    Get parsed watchlist Ids.

    :param all_watchlists: All watchlists available in account.
    :param configured_watchlists: Watchlists configured in input.
    """
    input_watchlists = configured_watchlists.split("~")
    if "All" in input_watchlists:
        input_watchlist_ids = [wl["id"] for wl in all_watchlists]
    else:
        input_watchlist_ids = [wl["id"] for wl in all_watchlists if wl["name"] in input_watchlists]
    return input_watchlist_ids


def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager.

    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza,
                    otherwise return all stanza
    """
    conf_file = conf_manager.ConfManager(
        session_key,
        ta_name,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(ta_name, conf_file),
    ).get_conf(conf_file)

    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all()

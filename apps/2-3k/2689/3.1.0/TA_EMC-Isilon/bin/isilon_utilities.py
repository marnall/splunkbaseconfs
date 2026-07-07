from builtins import str
import requests
import traceback
import os
import json
import sys
import re
from solnlib.credentials import CredentialManager
from splunk import rest
from splunk.clilib import cli_common as cli
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from solnlib import conf_manager
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import const
try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]


# Write meta info
def _write_meta_info(data, filename, logger, file_path=None):
    """Updates pos file with the latest token values."""
    path = file_path if file_path is not None else sys.path[0]
    pos_file_path = os.path.join(path, filename)
    try:
        logger.debug("message=updating_pos_file | Updating the pos file with latest values.")
        pos_file = open(pos_file_path, "w")
        pos_file.truncate()
        data = json.dumps(data)
        pos_file.write(data)
        pos_file.close()
        logger.debug("message=updated_pos_file | pos file updated with latest values.")
    except Exception:
        logger.error("message=error_updating_pos_file | Error updating pos file.\n{}".format(traceback.format_exc()))
        raise


# Read meta info
def _read_meta_info(filename, logger, file_path=None):
    """Reads pos file for the token values if file exists."""
    path = file_path if file_path is not None else sys.path[0]
    pos_file_path = os.path.join(path, filename)
    file_data = {}
    try:
        if os.path.exists(pos_file_path):
            pos_file = open(pos_file_path, "r")
            file_data = pos_file.read().strip()
            file_data = json.loads(file_data)
            pos_file.close()
            logger.debug("message=read_pos_file_data | Successfully fetched the latest data from pos file.")
            return file_data
        else:
            logger.debug("message=error_reading_pos_file | Unable to fetch latest data as data is not available.")
            return -1
    except Exception:
        logger.error("message=error_reading_pos_file_data | Error occured while fetching latest "
                     "data from pos file.\n{}".format(traceback.format_exc()))
        raise


def get_conf_file(session_key, app_name, conf_file):
    """This method returns content present in conf file."""
    try:
        conf_file = conf_manager.ConfManager(
            session_key,
            app_name,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(app_name, conf_file),
        ).get_conf(conf_file)
        file_content = conf_file.get_all(only_current_app=True)
        return file_content
    except Exception:
        return None


def create_proxy_uri_dict(proxy_dict):
    """
    This is utility method which returns proxy dict with composed uri in a format which requests package accepts.

    :param proxy_dict: dict containing proxy details
    :return proxies: proxy dict (for ex.: {'http': '<uri>', https: '<uri>'} and empty
                                 dict object is returned when proxy is disabled)
    """
    proxies = {}
    if proxy_dict.get("proxy_enabled", "0").lower() in ["true", "1", "yes"]:
        uri = proxy_dict["proxy_url"]
        if proxy_dict.get("proxy_port"):
            uri = "{}:{}".format(uri, proxy_dict["proxy_port"])
        if proxy_dict.get("proxy_username") and proxy_dict.get("proxy_password"):
            uri = "{}://{}:{}@{}/".format(
                proxy_dict["proxy_type"],
                requests.compat.quote_plus(str(proxy_dict["proxy_username"])),
                requests.compat.quote_plus(str(proxy_dict["proxy_password"])),
                uri,
            )
        else:
            uri = "{}://{}".format(proxy_dict["proxy_type"], uri)
        proxies = {"http": uri, "https": uri}
    return proxies


def get_proxy_data(session_key, app_name, logger):
    """Returns the details of proxies if enabled else returns None."""
    try:
        logger.debug("message=proxy_details | Fetching proxy details with splunk's internal method.")
        proxy_stanza = cli.getConfStanza("ta_emc_isilon_settings", "proxy")
        if proxy_stanza.get("proxy_enabled") == "1":
            logger.info("message=proxy_details | Proxy is enabled.")
            proxy_pwd = unencrypted_password(session_key, app_name, logger)
            if proxy_pwd:
                proxy_stanza["proxy_password"] = proxy_pwd.get("proxy_password")
            proxies = create_proxy_uri_dict(proxy_stanza)
            logger.debug("message=proxy_details | Returning required proxy details.")
            return proxies
        else:
            logger.info("message=proxy_details | Proxy is disabled.")
            return None
    except Exception:
        logger.error("message=proxy_error | Error occured while fetching proxy details.\n{}"
                     .format(traceback.format_exc()))
        return None


def unencrypted_password(session_key, app_name, logger):
    """Converts encrypted proxy password into an unencrypted one."""
    manager = CredentialManager(
        session_key,
        app=app_name,
        realm="__REST_CREDENTIAL__#{}#configs/conf-ta_emc_isilon_settings".format(app_name),
    )
    unencrypted_passwd = None
    try:
        logger.debug("message=proxy_details | Trying to decrypt proxy password if provided")
        unencrypted_passwd = json.loads(manager.get_password("proxy"))
        logger.debug("message=proxy_details | Proxy password decrypted successfully")
    except Exception:
        logger.debug("message=decryption_failure | Can not decrypt "
                     "proxy password.\n{}".format(traceback.format_exc()))
    return unencrypted_passwd


def retry_session():
    """Create and returns a session object."""
    session = requests.Session()
    retry = Retry(
        total=const.RETRY_ATTEMPTS,
        read=const.RETRY_ATTEMPTS,
        connect=const.RETRY_ATTEMPTS,
        backoff_factor=const.BACKOFF_FACTOR,
        allowed_methods=const.ALLOWED_METHODS,
        status_forcelist=const.STATUS_FORCELIST,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def reload_stanza(session_key, logger):
    """Reload the inputs present under data/inputs/monitor."""
    try:
        rest.simpleRequest(
            "/servicesNS/nobody/{}/data/inputs/monitor/_reload".format(APP_NAME),
            sessionKey=session_key,
            method="POST",
            raiseAllErrors=True,
        )
    except Exception:
        logger.error("message=error_reloading_stanza | Error occured while reloading stanza.\n{}"
                     .format(traceback.format_exc()))


def splunk_rest_call(method, conf_file, each, session_key, postargs=None):
    """Splunk internal rest call."""
    encoded_stanza = quote(each, safe="")
    rest.simpleRequest(
        "/servicesNS/nobody/{}/configs/conf-{}/{}".format(APP_NAME, conf_file, encoded_stanza),
        sessionKey=session_key,
        method=method,
        getargs={"output_mode": "json"},
        postargs=postargs,
        raiseAllErrors=True,
    )


def file_exist(file_name, ta_name):
    """
    Check if the file exists or not.

    :param file_name: Name of the file which is to be checked if it exists or not.
    :param ta_name: Name of the app.
    :return boolean value after checking if the file exists or not.
    """
    file_path = make_splunkhome_path(["etc", "apps", ta_name, "local", file_name])
    file_name = "".join([file_path, ".conf"])
    if os.path.exists(file_name):
        return True
    else:
        return False


def get_release_version(host, cookies, verify, logger, proxy):
    """Returns the oneFs version."""
    try:
        session = retry_session()
        csrf = cookies.get('isicsrf')
        sessid = cookies.get('isisessid')
        url = "https://" + host + ":" + const.ISILON_PORT + "/platform/1/cluster/config"
        if csrf:
            headers = {
                'X-CSRF-Token': str(csrf),
                'Cookie': "isisessid=" + str(sessid),
                'Referer': 'https://' + str(host) + ':' + const.ISILON_PORT
            }
            r = session.get(verify=verify, url=url, proxies=proxy, headers=headers)
            return r.json().get('onefs_version', None).get('release', None)
        else:
            r = session.get(verify=verify, url=url, proxies=proxy, cookies=cookies)
            return r.json().get('onefs_version', None).get('release', None)
    except Exception:
        logger.error("message=error_while_getting_version | Error occured while getting product version.\n{}"
                     .format(traceback.format_exc()))
        return None


def get_cookie(host, username, password, verify, proxy, logger):
    """Generates the cookies."""
    logger.debug("message=generating_cookies | Generating cookies.")
    try:
        url = (
            "https://" + host + ":" + const.ISILON_PORT + "/session/1/session"
        )
        headers = {"Content-Type": "application/json"}
        body = json.dumps(
            {
                "username": username,
                "password": password,
                "services": ("platform", "namespace"),
            }
        )
        session = retry_session()
        r = session.post(
            verify=verify,
            url=url,
            headers=headers,
            data=body,
            proxies=proxy,
        )
        r.raise_for_status()
        logger.debug("message=cookies_generated_successfully | Cookies generated successfully.")
        return dict(r.cookies)
    except Exception:
        logger.error(
            "message=error_while_generating_cookie | Error occured while generating cookies.\n{}"
            .format(traceback.format_exc())
        )
        return None


def get_management_port(session_key, logger):
    """Get Management Port."""
    try:
        mgmt_port = const.DEFAULT_MANAGEMENT_PORT
        _, content = rest.simpleRequest(
            "/services/configs/conf-web/settings",
            method="GET",
            sessionKey=session_key,
            getargs={"output_mode": "json"},
            raiseAllErrors=True,
        )
        content = json.loads(content)
        mgmt_port = re.findall(r':(\d+)', content["entry"][0]["content"]["mgmtHostPort"])[0]
        logger.debug("message=management_port_details | Management port is {}".format(mgmt_port))
    except Exception:
        logger.error("message=error_getting_port | Error occured while getting port from web.conf file."
                     " Considering default value of 8089.\n{}".format(traceback.format_exc()))
    return mgmt_port

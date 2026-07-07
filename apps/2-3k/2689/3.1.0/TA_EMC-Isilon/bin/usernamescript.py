import ta_emc_isilon_declare  # noqa: F401
import splunklib.client as client
import splunk.Intersplunk
import sys
import json
import traceback
import isilon_utilities as utility
import isilon_logger_manager as log
import const


def users_call(endpoint, cookie, host, req_args, proxy, logger):
    """This method calls the single user endpoint using UID."""
    csrf = cookie.get("isicsrf")
    sessid = cookie.get("isisessid")
    session = utility.retry_session()
    if csrf:
        headers = {
            "X-CSRF-Token": str(csrf),
            "Cookie": "isisessid=" + str(sessid),
            "Referer": "https://" + str(host) + ":8080",
        }
        logger.debug("message=requesting_endpoint | Sending the request to endpoint.")
        response = session.get(endpoint, headers=headers, proxies=proxy, **req_args)
    else:
        response = session.get(endpoint, cookies=cookie, proxies=proxy, **req_args)
    return response


if __name__ == "__main__":
    logger = log.setup_logging("ta_emc_isilon_username_script")
    try:
        results, d_results, settings = splunk.Intersplunk.getOrganizedResults()
        if not results:
            logger.info("message=nothing_to_update | Nothing to update in lookup.")
            sys.exit(0)
        session_key = str(settings.get('sessionKey'))
        port = str(utility.get_management_port(session_key, logger))
        headers = {
            "Content-type": "application/json",
            "Accept": "text/plain",
            "Authorization": "Splunk {}".format(session_key),
        }
        ac_file = utility.get_conf_file(session_key, const.TA_NAME, const.ACCOUNTS_CONF_FILE)
        if ac_file:
            req_args = {"verify": False, "timeout": float(const.REQUEST_TIMEOUT), }
            proxy = utility.get_proxy_data(session_key, const.TA_NAME, logger)
            for entry in results:
                cookies = None
                host = entry.get("host")
                unique_key_field = entry.get("unique_key_field")
                uid = entry.get("uid")
                for key in ac_file:
                    if ac_file[key].get("ip_address") == host:
                        user_name = ac_file[key].get("username")
                        password = ac_file[key].get("password")
                        verify = const.VERIFY_SSL
                        cookies = utility.get_cookie(host, user_name, password, verify, proxy, logger)
                        if verify:
                            req_args["verify"] = verify
                        endpoint = const.UID_TO_USERNAME_ENDPOINT.format(host, const.ISILON_PORT, uid)
                        break
                else:
                    logger.error("message=account_does_not_exist | Account does not exist for the"
                                 " host = {}. Please configure the account from UI".format(host))
                    break
                if cookies:
                    uid_response = users_call(endpoint, cookies, host, req_args, proxy, logger)
                    res = json.loads(uid_response.text)
                    try:
                        username = res.get('users')[0].get('uid').get('name')
                    except Exception:
                        username = None
                        logger.error("message=error_while_fetching_username | Error occured for fetching username"
                                     " for host = {}".format(host))
                    if username:
                        searchquery = '| makeresults | eval host="{}", uid="{}", username="{}", unique_key_field="{}" \
                                    | outputlookup "dell_isilon_username" \
                                    key_field=unique_key_field'.format(host, uid, username, unique_key_field)
                        service = client.connect(
                            host="localhost",
                            port=port,
                            scheme="https",
                            app=const.TA_NAME,
                            token=session_key
                        )
                        oneshot_results = service.jobs.oneshot(searchquery)
        else:
            logger.info("message=accounts_do_not_exist | Accounts do not exists. Please configure the"
                        " accounts from UI.")
    except Exception:
        logger.error("message=error_on_updating_lookup | Error occured while updating username to lookup.\n{}"
                     .format(traceback.format_exc()))

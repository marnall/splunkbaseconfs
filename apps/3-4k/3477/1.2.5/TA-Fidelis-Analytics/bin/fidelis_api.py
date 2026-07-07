import json
import sys

import requests

from splunk.clilib import cli_common as cli

from fidelis_utility import get_logger, get_credentials,resource


logger = get_logger("FIDELIS_API")


def print_to_splunk(data_results, key, host):
    print "{ \"CommandPostURL\":\"%s\", \"%s\": %s }\n" % (host, key, json.dumps(data_results))


def call_api(host, uname, password, allow_ssl):
    session = requests.session()
    try:
        login_data = {'j_username': uname, 'j_password': password}
        session.post(host + resource.get('login'), login_data, verify = allow_ssl)
    except Exception as e:
        logger.error("TA Fidelis Error : Cannot Connect to  %s : Error : %s" % (host, str(e)))
        sys.exit(5)

    try:
        result = session.get(host + resource.get('selection_values'), verify = allow_ssl)
        res_text = result.content

    except Exception as e:
        logger.error("TA Fidelis Error : Unable to get selection value from  %s : Error : %s" % (host, str(e)))
        sys.exit(10)

    try:
        print_to_splunk(json.loads(res_text)['SEVERITY'], 'SEVERITY', host)
        print_to_splunk(json.loads(res_text)['RULE_NAME'], 'RULE_NAME', host)
        print_to_splunk(json.loads(res_text)['POLICY_NAME'], 'POLICY_NAME', host)
    except Exception as e:
        logger.error("TA Fidelis Error : Unable to parse response data : Error : %s" % (str(e)))
        sys.exit(15)


if __name__ == "__main__":
    session_key = sys.stdin.readline().strip()
    if len(session_key) == 0:
        logger.error("TA Fidelis Error: Did not receive a session key from splunkd.")
        sys.exit()

    try:
        input_args = cli.getConfStanza('fidelissetup', 'setupentity')
        allow_ssl = not (bool(int(input_args["ALLOW_SSL"])))

        url = input_args["RESTSERVER"]
        password, username = get_credentials(session_key, "FIDELIS_API")
        if not allow_ssl:
            call_api(url, username, password, allow_ssl)
        else:
            cert_loc = input_args["SSL_CERT_LOC"]
            call_api(url, username, password, cert_loc)

    except Exception as e:
        logger.error("Error in __main__ ", exc_info = True)
        sys.exit(3)

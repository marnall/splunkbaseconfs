import sys

import requests
from requests.auth import HTTPBasicAuth
from splunk.clilib import cli_common as cli

from CMXUtil import *


logger = get_logger('REST_MAP')
sessionKey = sys.stdin.readline().strip()

protocol = "https://"


def load_data(loginurl, username, password, verify_cert = True):
    try:
        url = protocol + loginurl
        r = requests.get(url = url, auth = HTTPBasicAuth(username, password), verify = verify_cert,
                         allow_redirects = True)

        if len(r.content) > 0:
            print json.dumps(json.loads(r.content))
        return r.status_code

    except Exception:
        logger.error("Error in login", exc_info = True)
        print "STATUS UNKNOWN-In valid web proxy IP or Web proxy is not responding."
        sys.exit(3)


if __name__ == '__main__':
    user_name, password = get_credentials(sessionKey)
    inputargs = cli.getConfStanza('cmxsetup', 'setupentity')

    if inputargs["RESTSERVER"] == '' or user_name == '' or password == '':
        logger.error("No REST Server configuration available, please complete the setup")
        sys.exit(3)

    if inputargs["RESTPORT"] == '':
        url = inputargs["RESTSERVER"] + resource['MAP']
    else:
        url = inputargs["RESTSERVER"] + ":" + inputargs["RESTPORT"] + resource['MAP']

    verify_cert = not (bool(int(inputargs["ALLSSC"])))

    logger.debug("REST Call status " + str(load_data(url, user_name, password, verify_cert)))
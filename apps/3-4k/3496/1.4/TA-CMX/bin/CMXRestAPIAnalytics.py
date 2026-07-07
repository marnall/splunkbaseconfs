import sys

import requests
from requests.auth import HTTPBasicAuth
from splunk.clilib import cli_common as cli

from CMXUtil import *


logger = get_logger('RESTANAYLTICS')

sessionKey = sys.stdin.readline().strip()
protocol = "https://"


def load_data(loginurl, username, password, verify_cert = True):
    try:

        url = protocol + loginurl

        r = requests.get(url = url, auth = HTTPBasicAuth(username, password), verify = verify_cert,
                         allow_redirects = True)

        if 200 <= r.status_code <= 300 and len(r.content) > 0:
            print json.dumps(json.loads(r.content))
        return r.status_code

    except Exception:
        logging.error("Error in login", exc_info = True)
        sys.exit(3)


if __name__ == '__main__':
    userName, password = get_credentials(sessionKey)
    inputargs = cli.getConfStanza('cmxsetup', 'setupentity')

    if not inputargs["RESTSERVER"] or not userName or not password:
        logger.error("No REST Server configuration available, please complete the setup")
        sys.exit(3)

    if inputargs["RESTPORT"]:
        url = inputargs["RESTSERVER"] + ":" + inputargs["RESTPORT"] + resource['ANALYTICS']
    else:
        url = inputargs["RESTSERVER"] + resource['ANALYTICS']

    verify_cert = not (bool(int(inputargs["ALLSSC"])))

    logger.debug("REST Call status " + str(load_data(url, userName, password, verify_cert)))
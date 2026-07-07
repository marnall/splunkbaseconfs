import sys

import requests
from requests.auth import HTTPBasicAuth
from splunk.clilib import cli_common as cli
import splunk.search as splunk_search

from CMXUtil import *


logger = get_logger('REST_ACTIVE')

inputargs = {}
session_key = sys.stdin.readline().strip()
protocol = "https://"


def load_data(user_name = "", password = "", verify_cert = True, index = "main"):
    try:
        if inputargs["RESTPORT"] == '':
            resturl = inputargs["RESTSERVER"] + resource['ACTIVE']
        else:
            resturl = inputargs["RESTSERVER"] + ":" + inputargs["RESTPORT"] + resource['ACTIVE']

        url = protocol + resturl

        query = '|search index=' + index + \
                ' sourcetype=cmxmap | spath path=campuses{} output=campus | head 1  | fields - _raw | ' \
                'fields campus  | mvexpand campus | spath input=campus path=name output=CampusName | dedup CampusName | ' \
                'spath input=campus path=buildingList{} output=buildingList | mvexpand buildingList | ' \
                'spath input=buildingList path=name output=BuildingName | dedup CampusName BuildingName| ' \
                'spath input=buildingList path=floorList{} output=floorList | mvexpand floorList | ' \
                'spath input=floorList path=name output=FloorName | dedup CampusName BuildingName  FloorName | ' \
                'spath input=floorList path=aesUid output=FloorID | dedup CampusName BuildingName FloorName FloorID ' \
                '| table CampusName BuildingName FloorName FloorID'

        results = splunk_search.searchAll(query, earliest_time = "-24h@h", latest_time = "+5m",
                                          sessionKey = session_key)

        # Need to set the sessionKey (input.submit() doesn't allow passing the sessionKey)
        if results is not None:
            for i, x in enumerate(results):

                url = url + "?floorid=" + str(x['FloorID'])

                r = requests.get(url = url, auth = HTTPBasicAuth(user_name, password), verify = verify_cert,
                                 allow_redirects = True)

                if 200 <= r.status_code <= 300 and len(r.content) > 0:
                    for data in json.loads(r.content):
                        if data["dot11Status"] == 'ASSOCIATED':
                            print json.dumps(data)

        else:
            r = requests.get(url = url, auth = HTTPBasicAuth(user_name, password), verify = verify_cert,
                             allow_redirects = True)

            if 200 <= r.status_code <= 300 and len(r.content) > 0:
                for data in json.loads(r.content):
                    if data["dot11Status"] == 'ASSOCIATED':
                        print json.dumps(data)
            else:
                logger.error("Couldn't retrive data from CMX ")
                logger.error(r)
    except Exception:
        logger.error("Error in login", exc_info = True)
        sys.exit(3)


if __name__ == '__main__':
    userName, password = get_credentials(session_key)

    inputargs = cli.getConfStanza('cmxsetup', 'setupentity')

    if not inputargs["RESTSERVER"] or not userName or not password:
        logger.error("No REST Server configuration available, please complete the setup")
        sys.exit(3)

    index = inputargs["INDEX"] if inputargs["INDEX"] else "main"

    verify_cert = not (bool(int(inputargs["ALLSSC"])))

    load_data(userName, password, verify_cert, index)

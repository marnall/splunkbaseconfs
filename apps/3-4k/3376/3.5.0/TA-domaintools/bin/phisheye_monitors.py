import splunk
import json
import requests
import traceback
import urllib
from Utils.dtools_logger import DToolsLogger


class PhishEye(splunk.rest.BaseRestHandler):

    def handle_GET(self):
        logger = DToolsLogger.setup("ImportPhishEyeMonitors", "dt_import_phisheye_monitors.log")
        logger.info("starting import phisheye monitors script.")

        sessionKey = self.sessionKey

        headers, response = splunk.rest.simpleRequest(
            '/services/domaintools_credentials',
            method='POST',
            sessionKey=sessionKey,
            postargs={}
        )

        credentials = json.loads(response)

        url = "https://api.domaintools.com/v1/phisheye/term-list/?api_username={0}&api_key={1}".format(
            credentials['username'],
            credentials['password']
        )
        response = requests.get(url)
        data = response.json()

        logger.info("phisheye api data: {0}".format(data))
        monitors = map(lambda x: {"_key": x["term"], "term": x["term"], "enabled": False}, data['response']['terms'])

        # splunk supports a limited subset of mongo search operations (not including "IN")
        archived_monitors = map(lambda x: {"_key": {"$ne": x["_key"]}}, monitors)
        query = {"$and": archived_monitors}
        query_string = urllib.quote(json.dumps(query))

        headers, data = splunk.rest.simpleRequest(
            '/servicesNS/nobody/TA-domaintools/storage/collections/data/phisheye_monitors?query={0}'.format(query_string),
            sessionKey=sessionKey
        )
        logger.info("deleting archived monitors: {0}".format(data))

        for monitor in json.loads(data):
            response = splunk.rest.simpleRequest(
                '/servicesNS/nobody/TA-domaintools/storage/collections/data/phisheye_monitors/{0}'.format(monitor["_key"]),
                method='DELETE',
                sessionKey=sessionKey
            )

        for monitor in monitors:
            response = splunk.rest.simpleRequest(
                '/servicesNS/nobody/TA-domaintools/storage/collections/data/phisheye_monitors',
                method='POST',
                sessionKey=sessionKey,
                jsonargs=json.dumps(monitor)
            )

        self.response.write("phisheye monitor import completed successfully.")
        logger.info("completed import phisheye monitors script.")

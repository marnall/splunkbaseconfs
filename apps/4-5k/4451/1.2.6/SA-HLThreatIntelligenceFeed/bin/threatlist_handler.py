"""
Generates the Threatlists
"""
import sys
import os
import shutil
import logging
import logging.handlers
import requests
from threatintelligence import Helpers, Errors
from splunk.clilib import cli_common as cli


# Setup the handler
logger = logging.getLogger('SA-HLThreatIntelligenceFeed')
logger.setLevel(logging.INFO)

helpers = Helpers()
errors = Errors()
threat_file_path = helpers.get_lookup_path()
session_key = sys.stdin.readline().strip()
api_key = helpers.get_credentials(session_key)
errors.set_session_key(session_key)
cfg = cli.getConfStanza('feed_proxy', 'proxy')
http_proxy_path = cfg.get('http')
https_proxy_path = cfg.get('https')
proxy_dict = {
    'http': http_proxy_path,
    'https': https_proxy_path
}


def get_feed(_api_key):
    """
    Loops through API endpoints and pulls down the data
    :param _api_key:
    :return:
    """

    logger.info("Starting the threatlist_handler.py scripted input.")

    base_url = "https://threats.hurricanelabs.com/api/hlget-threats/"

    endpoints = [
        {"file_name": "misp_Domains.csv", "url": base_url + "misp_Domains.csv"},
        {"file_name": "misp_IPDST.csv", "url": base_url + "misp_IPDST.csv"},
        {"file_name": "misp_MD5SUMs.csv", "url": base_url + "misp_MD5SUMs.csv"},
        {"file_name": "misp_SHA1SUMs.csv", "url": base_url + "misp_SHA1SUMs.csv"},
        {"file_name": "misp_SHA256SUMs.csv", "url": base_url + "misp_SHA256SUMs.csv"},
        {"file_name": "misp_URLs.csv", "url": base_url + "misp_URLs.csv"},
        {"file_name": "hl-current-threats.csv", "url": base_url + "hl-current-threats.csv"}
    ]

    urls = [item['url'] for item in endpoints]

    for url in urls:
        logger.info("Scripted Input (threatlist_handler.py) is attempting to pull from %s", str(url))

        headers = {'x-api-key': _api_key}
        try:
            response = requests.get(url, headers=headers, proxies=proxy_dict, timeout=360)
            logger.info("Response from API %s when requesting %s", str(response), str(url))
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            logger.error("SA-HLThreatIntelligenceFeed returned an HTTP error: %s", str(errh))
        except requests.exceptions.ConnectionError as errc:
            logger.error("Error connecting to SA-HLThreatIntelligenceFeed. Details: %s", str(errc))
        except requests.exceptions.Timeout as errt:
            logger.error("SA-HLThreatIntelligenceFeed timed out. Details: %s", str(errt))
        except requests.exceptions.RequestException as err:
            logger.error("An error occurred when attempting to connect to SA-HLThreatIntelligenceFeed. "
                         "Details: %s", str(err))

        output_file_name = url.rsplit('/', 1)[-1]

        try:
            if not os.path.exists(threat_file_path):
                logger.info("Lookup directory did not exist, creating it now.")
                os.makedirs(threat_file_path)
        except OSError as e:
            logger.error("Could not create lookup directory. Reason: %s", str(e))
            errors.throw_cannot_create_lookup_path(e)

        report_file_path = os.path.join(threat_file_path, output_file_name)

        try:
            logger.info("Attempting to create Threat Intelligence lookup files.")
            tmp_file_path = report_file_path + ".tmp"
            with open(tmp_file_path, 'wb') as fd:
                fd.write(response.content)
            shutil.move(tmp_file_path, report_file_path)
        except OSError as e:
            logger.error("Failed to create Threat Intelligence lookup files. Reason: %s", str(e))
            errors.throw_could_not_download_threatlist(e)


get_feed(api_key)

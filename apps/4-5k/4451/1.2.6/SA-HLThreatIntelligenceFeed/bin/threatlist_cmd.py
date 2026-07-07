"""
Generates the Threatlists using hlthreatintel command. Useful for Splunk Cloud.
"""
import os
import sys
import shutil
import logging.handlers
import requests
import splunk.Intersplunk
from splunk import entity
from splunk.clilib import cli_common as cli

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
from threatintelligence import Helpers, Errors


class HLThreatIntel:
    """
    Class for hlthreatintel custom command
    """
    my_app = 'SA-HLThreatIntelligenceFeed'
    helpers = Helpers()
    errors = Errors()
    threat_file_path = helpers.get_lookup_path()
    cfg = cli.getConfStanza('feed_proxy', 'proxy')
    http_proxy_path = cfg.get('http')
    https_proxy_path = cfg.get('https')
    proxy_dict = {
        'http': http_proxy_path,
        'https': https_proxy_path
    }

    base_url = "https://threats.hurricanelabs.com/api/hlget-threats/"

    endpoints = [
        {"file_name": "misp_Domains.csv",
         "url": base_url + "misp_Domains.csv"},
        {"file_name": "misp_IPDST.csv", "url": base_url + "misp_IPDST.csv"},
        {"file_name": "misp_MD5SUMs.csv",
         "url": base_url + "misp_MD5SUMs.csv"},
        {"file_name": "misp_SHA1SUMs.csv",
         "url": base_url + "misp_SHA1SUMs.csv"},
        {"file_name": "misp_SHA256SUMs.csv",
         "url": base_url + "misp_SHA256SUMs.csv"},
        {"file_name": "misp_URLs.csv", "url": base_url + "misp_URLs.csv"},
        {"file_name": "hl-current-threats.csv",
         "url": base_url + "hl-current-threats.csv"}
    ]
    urls = [item['url'] for item in endpoints]


    # Setup the handler
    logger = logging.getLogger('SA-HLThreatIntelligenceFeed')
    logger.setLevel(logging.INFO)

    def get_feed(self, api_key, session_key):
        """
        Loops through API endpoints and pulls down the data
        :param api_key:
        :param session_key:
        :return:
        """

        self.errors.set_session_key(session_key)
        headers = {'x-api-key': api_key}

        for url in self.urls:

            self.logger.info("Custom Command (threatlist_cmd.py) is attempting to pull from %s", str(url))

            try:
                response = requests.get(url, headers=headers, proxies=self.proxy_dict, timeout=120)
                self.logger.info("Response from API %s when requesting %s", str(response), str(url))
                response.raise_for_status()
            except requests.exceptions.HTTPError as errh:
                self.logger.error("SA-HLThreatIntelligenceFeed returned an HTTP error: %s", str(errh))
            except requests.exceptions.ConnectionError as errc:
                self.logger.error("Error connecting to SA-HLThreatIntelligenceFeed. Details: %s", str(errc))
            except requests.exceptions.Timeout as errt:
                self.logger.error("SA-HLThreatIntelligenceFeed timed out. Details: %s", str(errt))
            except requests.exceptions.RequestException as err:
                self.logger.error("An error occurred when attempting to connect to SA-HLThreatIntelligenceFeed. "
                                  "Details: %s", str(err))

            output_file_name = url.rsplit('/', 1)[-1]

            try:
                if not os.path.exists(self.threat_file_path):
                    self.logger.info("Lookup directory did not exist, creating it now.")
                    os.makedirs(self.threat_file_path)
            except OSError as e:
                self.logger.error("Could not create lookup directory. Reason: %s", str(e))
                self.errors.throw_cannot_create_lookup_path(e)

            report_file_path = os.path.join(self.threat_file_path, output_file_name)

            try:
                self.logger.info("Attempting to create Threat Intelligence lookup files.")
                tmp_file_path = report_file_path + ".tmp"
                with open(tmp_file_path, 'wb') as fd:
                    fd.write(response.content)
                shutil.move(tmp_file_path, report_file_path)
            except OSError as e:
                self.logger.error("Failed to create Threat Intelligence lookup files. Reason: %s", str(e))
                self.errors.throw_could_not_download_threatlist(e)

    def get_credentials(self, session_key):
        """
        Retrieves credentials from encrypted credential store.
        :return:
        """

        try:
            # list all credentials
            entities = entity.getEntities(
                ['admin', 'passwords', 'api_key'], namespace=self.my_app, owner='nobody', sessionKey=session_key
            )
        except Exception as unknown_exception:
            message = "Could not get %s credentials from splunk. Error: %s" % (self.my_app, str(unknown_exception)) # pylint: disable=consider-using-f-string
            self.logger.error("Could not get %s credentials from splunk. Error: %s",
                              self.my_app, str(unknown_exception))
            self.helpers.make_error_message(message, session_key, 'threatlist_cmd.py')
            return splunk.Intersplunk.generateErrorResults(message)

        # grab first set of credentials
        last = None
        for stanza in entities.values():
            if stanza['eai:acl']['app'] == self.my_app:
                last = stanza['username'], stanza['clear_password']
        if last:
            # username is not needed
            api_key = last[1]
        else:
            message = 'No credentials have been found. Please configure ' + self.my_app + ' first.'
            self.logger.error('No credentials have been found. Please configure %s first.', self.my_app)
            self.helpers.make_error_message(message, session_key, 'threatlist_cmd.py')
            return splunk.Intersplunk.generateErrorResults(message)
        return api_key

def main():
    """ Main function """
    results, dummy_results, settings = splunk.Intersplunk.getOrganizedResults() # pylint: disable=unused-variable
    session_key = settings.get("sessionKey")
    hlthreatintel = HLThreatIntel()
    api_key = hlthreatintel.get_credentials(session_key)
    hlthreatintel.get_feed(api_key, session_key)
    splunk.Intersplunk.outputResults([{"result": "Successfully updated MISP feeds"}])

if __name__ == "__main__":
    main()

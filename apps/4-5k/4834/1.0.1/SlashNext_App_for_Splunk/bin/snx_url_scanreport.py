import sys
sys.path.append('../lib')

import requests
import snx_utils
import traceback
import time

import splunk.Intersplunk
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration()
class SnxURLScanReportCommand(GeneratingCommand):
    # Class variables
    # Scan ID against which Scan Report is to be fetched
    scan_id = Option(require=True)

    # If user wants extended info as well (Screenshot, HTML and Text)
    extended_info = Option(require=False, validate=validators.Boolean())

    # Internal variables
    api_key = None
    base_url = None
    snx_logger = None

    def _download_forensics(self, event, scanId):
        actions_failed = 0

        # --------------------------- Downloading Screenshot ---------------------------
        self.snx_logger.info('Downloading Screenshot')
        # Make a call to SlashNext - OTI Endpoint
        download_sc_api = self.base_url + '/oti/v1/download/screenshot'
        ep_params = {
            'authkey': self.api_key,
            'scanid': scanId,
            'resolution': 'medium'
        }

        response = requests.post(download_sc_api, ep_params)
        if response.ok:
            data = response.json()
            if data.get('errorNo') == 0:
                msg = 'Download Screenshot Successful.'
                self.snx_logger.info(msg)
                event['url_scBase64'] = data.get('scData').get('scBase64')
            else:
                actions_failed += 1
                msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                self.snx_logger.error(msg)
        else:
            actions_failed += 1
            msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(response.reason)
            self.snx_logger.error(msg)

        # --------------------------- Downloading HTML ---------------------------
        self.snx_logger.info('Downloading HTML')
        # Make a call to SlashNext - OTI Endpoint
        download_html_api = self.base_url + '/oti/v1/download/html'
        ep_params = {
            'authkey': self.api_key,
            'scanid': scanId
        }

        response = requests.post(download_html_api, ep_params)
        if response.ok:
            data = response.json()
            if data.get('errorNo') == 0:
                msg = 'Download HTML Successful.'
                self.snx_logger.info(msg)
                event['url_htmlBase64'] = data.get('htmlData').get('htmlBase64')
            else:
                actions_failed += 1
                msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                self.snx_logger.error(msg)
        else:
            actions_failed += 1
            msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(response.reason)
            self.snx_logger.error(msg)

        # --------------------------- Downloading Text ---------------------------
        self.snx_logger.info('Downloading Text')
        # Make a call to SlashNext - OTI Endpoint
        download_text_api = self.base_url + '/oti/v1/download/text'
        ep_params = {
            'authkey': self.api_key,
            'scanid': scanId
        }

        response = requests.post(download_text_api, ep_params)
        if response.ok:
            data = response.json()
            if data.get('errorNo') == 0:
                msg = 'Download Text Successful.'
                self.snx_logger.info(msg)
                event['url_textBase64'] = data.get('textData').get('textBase64')
            else:
                actions_failed += 1
                msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                self.snx_logger.error(msg)
        else:
            actions_failed += 1
            msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(response.reason)
            self.snx_logger.error(msg)

        if actions_failed == 3:
            msg = 'Failed to download Screenshot, HTML and Text data.'
            self.snx_logger.error(msg)
        else:
            msg = 'Successful in either downloading Screenshot, HTML or/and Text data'
            self.snx_logger.info(msg)

    def generate(self):
        # Initial Settings for logging and credentials
        try:
            # Accquire the logger
            self.snx_logger = snx_utils.setup_logging()
            self.snx_logger.info('Running "snxurlscanreport" Command')

            # Get API information
            api_config = snx_utils.get_config("slashnext.conf", "api-setup")
            self.base_url = api_config['base_url']
            self.api_key = api_config['api_key']

            if self.scan_id is not None:
                # Let's first create an empty event
                output_keys = ['url', 'url_scanId', 'url_verdict', 'url_threatStatus', 'url_threatType',
                               'url_threatName', 'url_firstSeen', 'url_lastSeen', 'url_scBase64', 'url_htmlBase64',
                               'url_textBase64', 'finalUrl', 'landingUrl', 'landingUrl_scanId', 'landingUrl_verdict',
                               'landingUrl_threatStatus', 'landingUrl_threatName', 'landingUrl_threatType',
                               'landingUrl_firstSeen', 'landingUrl_lastSeen', '_time', '_raw']
                event = dict.fromkeys(output_keys)

                # First add event metadata (necessary for Splunk internal initialization)
                event['_time'] = time.time()

                # Now we add data from different actions
                # ------------------ URL Scan Report ------------------ #
                # Make a call to SlashNext - OTI Endpoint
                url_scan_api = self.base_url + '/oti/v1/url/scan'
                ep_params = {
                    'authkey': self.api_key,
                    'scanid': self.scan_id
                }

                response = requests.post(url_scan_api, ep_params)
                if response.ok:
                    data = response.json()
                    if data.get('errorNo') == 0:
                        msg = 'URL Scan Successful'
                        self.snx_logger.info(msg)

                        # Add URL Scan data
                        event['url'] = data.get('urlData').get('url')
                        event['url_scanId'] = data.get('urlData').get('scanId')
                        event['url_verdict'] = data.get('urlData').get('threatData').get('verdict')
                        event['url_threatStatus'] = data.get('urlData').get('threatData').get('threatStatus')
                        event['url_threatType'] = data.get('urlData').get('threatData').get('threatType')
                        event['url_threatName'] = data.get('urlData').get('threatData').get('threatName')
                        event['url_firstSeen'] = data.get('urlData').get('threatData').get('firstSeen')
                        event['url_lastSeen'] = data.get('urlData').get('threatData').get('lastSeen')

                        forensics_scanId = None
                        if 'landingUrl' in data.get('urlData'):
                            event['landingUrl'] = data.get('urlData').get('landingUrl').get('url')
                            event['landingUrl_scanId'] = data.get('urlData').get('landingUrl').get('scanId')
                            # We use the scanId of Landing URL for forensics
                            forensics_scanId = data.get('urlData').get('landingUrl').get('scanId')
                            event['landingUrl_verdict'] = data.get('urlData').get('landingUrl').get(
                                'threatData').get('verdict')
                            event['landingUrl_threatStatus'] = data.get('urlData').get('landingUrl').get(
                                'threatData').get('threatStatus')
                            event['landingUrl_threatName'] = data.get('urlData').get('landingUrl').get(
                                'threatData').get('threatName')
                            event['landingUrl_threatType'] = data.get('urlData').get('landingUrl').get(
                                'threatData').get('threatType')
                            event['landingUrl_firstSeen'] = data.get('urlData').get('landingUrl').get(
                                'threatData').get('firstSeen')
                            event['landingUrl_lastSeen'] = data.get('urlData').get('landingUrl').get(
                                'threatData').get('lastSeen')

                        elif 'finalUrl' in data.get('urlData'):
                            # We use the scanId of Scanned URL for forensics
                            forensics_scanId = data.get('urlData').get('scanId')
                            event['finalUrl'] = data.get('urlData').get('finalUrl')

                        # Finally, add the complete JSON response as raw data
                        event['_raw'] = data

                        # ------------------ Forensics Data ------------------ #
                        # Calling the function to collectively download screenshot, HTML and text data
                        if self.extended_info and data.get('swlData') is None:
                            self.snx_logger.info('Downloading Forensics for Scan ID: {0}'.format(forensics_scanId))
                            self._download_forensics(event, self.scan_id)
                            event['_raw'] = "Raw data too long to show."

                    elif data.get('errorNo') == 1:
                        msg = 'Your URL Scan request is submitted to the cloud and may take up-to 60 ' \
                              'seconds to complete. Please check back later using "snxurlscanreport" ' \
                              'action with scan_id = {0}'.format(self.scan_id)
                        self.snx_logger.error(msg)
                        yield {'ERROR': msg}
                        return

                    else:
                        msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                        self.snx_logger.error(msg)
                        # Return Error
                        yield {'ERROR': msg}
                        return

                    # Finally, we yield the event back to the Search
                    yield event

                else:
                    msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(response.reason)
                    self.snx_logger.error(msg)
                    # Return Error
                    yield {'ERROR': msg}
                    return

            else:
                yield {'ERROR': 'No Parameter value specified. Please specify host or url value.'}

        except Exception as e:
            stack = traceback.format_exc()
            # splunk.Intersplunk.generateErrorResults(str(e))
            self.snx_logger.error(str(e) + ". Traceback: " + str(stack))


dispatch(SnxURLScanReportCommand, sys.argv, sys.stdin, sys.stdout, __name__)

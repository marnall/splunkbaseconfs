import sys
sys.path.append('../lib')

import requests
import snx_utils
import traceback
import time
import splunk.Intersplunk
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


@Configuration()
class SnxHostReportCommand(GeneratingCommand):
    # Class variables
    # Host against which Forensics are to be fetched
    host = Option(require=True)

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
                event['latestUrl_scBase64'] = data.get('scData').get('scBase64')
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
                event['latestUrl_htmlBase64'] = data.get('htmlData').get('htmlBase64')
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
                event['latestUrl_textBase64'] = data.get('textData').get('textBase64')
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
            self.snx_logger.info('Running "snxhostreport" Command')

            # Get API information
            api_config = snx_utils.get_config("slashnext.conf", "api-setup")
            self.base_url = api_config['base_url']
            self.api_key = api_config['api_key']

            if self.host is not None:
                # Let's first create an empty event
                output_keys = ['host_verdict', 'host_threatStatus', 'host_threatName', 'host_threatType',
                               'host_firstSeen', 'latestUrl', 'latestUrl_scanId', 'latestUrl_verdict', 'latestUrl_threatStatus',
                               'latestUrl_threatName', 'latestUrl_threatType', 'latestUrl_firstSeen',
                               'latestUrl_lastSeen', 'latestUrl_scBase64', 'latestUrl_htmlBase64',
                               'latestUrl_textBase64', 'finalUrl', 'landingUrl', 'landingUrl_scanId',
                               'landingUrl_verdict', 'landingUrl_threatStatus', 'landingUrl_threatName',
                               'landingUrl_threatType', 'landingUrl_firstSeen', 'landingUrl_lastSeen',
                               '_time', '_raw']
                event = dict.fromkeys(output_keys)

                # First add event metadata (necessary for Splunk internal initialization)
                event['_time'] = time.time()

                # Now we add data from different actions

                # ------------------ Host Reputation ------------------ #
                self.snx_logger.info('Checking Host Reputation for Host: {0}'.format(self.host))
                # Make a call to SlashNext - OTI Endpoint
                host_repute_api = self.base_url + '/oti/v1/host/reputation'
                ep_params = {
                    'authkey': self.api_key,
                    'host': self.host
                }

                response = requests.post(host_repute_api, ep_params)
                if response.ok:
                    data = response.json()
                    if data.get('errorNo') == 0:
                        msg = 'Host Reputation Successful'
                        self.snx_logger.info(msg)
                        # Add Host Reputation data
                        event['host_verdict'] = data.get('threatData').get('verdict')
                        event['host_threatStatus'] = data.get('threatData').get('threatStatus')
                        event['host_threatType'] = data.get('threatData').get('threatType')
                        event['host_threatName'] = data.get('threatData').get('threatName')
                        event['host_firstSeen'] = data.get('threatData').get('firstSeen')
                        event['host_lastSeen'] = data.get('threatData').get('lastSeen')

                        # Finally, add the complete JSON response as raw data
                        event['_raw'] = data

                        # if there is no Intel Found, simply return whatever we have
                        if event['host_verdict'].startswith('Unrated'):
                            msg = 'Host Reputation Returned: {0}'.format(event['host_verdict'])
                            self.snx_logger.info(msg)
                            yield event
                            return
                    else:
                        msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                        self.snx_logger.error(msg)
                        # Yield and error and return
                        yield {'ERROR': msg}
                        return
                else:
                    msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(response.reason)
                    self.snx_logger.error(msg)
                    # Yield and error and return
                    yield {'ERROR': msg}
                    return

                # ------------------ Host Report (Latest URL) ------------------ #
                self.snx_logger.info('Checking Host Report for Host: {0}'.format(self.host))
                # Make a call to SlashNext - OTI Endpoint
                host_report_api = self.base_url + '/oti/v1/host/report'
                ep_params = {
                    'authkey': self.api_key,
                    'host': self.host,
                    'page': 1,
                    'rpp': 1
                }

                response = requests.post(host_report_api, ep_params)
                if response.ok:
                    data = response.json()
                    if data.get('errorNo') == 0:
                        msg = 'Host Report Successful'
                        self.snx_logger.info(msg)

                        # Extract the Latest URL
                        first_url = data.get('urlDataList')[0]
                        latest_url = first_url.get('url')
                        latest_url_scanId = str(first_url.get('scanId'))

                        # Perform a URL Scan if there exists no Scan ID for the URL
                        if latest_url_scanId == 'N/A':
                            url_scansync_api = self.base_url + '/oti/v1/url/scansync'
                            ep_params = {
                                'authkey': self.api_key,
                                'url': latest_url
                            }

                            response = requests.post(url_scansync_api, ep_params)
                            if response.ok:
                                scan_data = response.json()
                                if scan_data.get('errorNo') == 0:
                                    msg = 'URL Scan Sync Successful'
                                    self.snx_logger.info(msg)

                                    event['latestUrl'] = scan_data.get('urlData').get('url')
                                    event['latestUrl_scanId'] = scan_data.get('urlData').get('scanId')
                                    event['latestUrl_verdict'] = scan_data.get('urlData').get('threatData').get('verdict')
                                    event['latestUrl_threatStatus'] = scan_data.get('urlData').get('threatData').get('threatStatus')
                                    event['latestUrl_threatName'] = scan_data.get('urlData').get('threatData').get('threatName')
                                    event['latestUrl_threatType'] = scan_data.get('urlData').get('threatData').get('threatType')
                                    event['latestUrl_firstSeen'] = scan_data.get('urlData').get('threatData').get('firstSeen')
                                    event['latestUrl_lastSeen'] = scan_data.get('urlData').get('threatData').get('lastSeen')

                                    # If there is a landing URL, we use its Scan ID
                                    # else we just use the scanned URL's Scan ID
                                    if 'landingUrl' in scan_data:
                                        latest_url_scanId = scan_data.get('urlData').get('landingUrl').get('scanId')
                                        event['landingUrl'] = scan_data.get('urlData').get('landingUrl').get('url')
                                        event['landingUrl_scanId'] = scan_data.get('urlData').get('landingUrl').get('scanId')
                                        event['landingUrl_verdict'] = scan_data.get('urlData').get('landingUrl').get('threatData').get('verdict')
                                        event['landingUrl_threatStatus'] = scan_data.get('urlData').get('landingUrl').get('threatData').get('threatStatus')
                                        event['landingUrl_threatName'] = scan_data.get('urlData').get('landingUrl').get('threatData').get('threatName')
                                        event['landingUrl_threatType'] = scan_data.get('urlData').get('landingUrl').get('threatData').get('threatType')
                                        event['landingUrl_firstSeen'] = scan_data.get('urlData').get('landingUrl').get('threatData').get('firstSeen')
                                        event['landingUrl_lastSeen'] = scan_data.get('urlData').get('landingUrl').get('threatData').get('lastSeen')

                                    elif 'finalUrl' in scan_data:
                                        latest_url_scanId = scan_data.get('urlData').get('scanId')
                                        event['finalUrl'] = scan_data.get('urlData').get('finalUrl')

                                    else:
                                        latest_url_scanId = scan_data.get('urlData').get('scanId')

                                else:
                                    msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                                    self.snx_logger.error(msg)
                                    # Return Error
                                    yield {'ERROR': msg}
                            else:
                                msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(
                                    response.reason)
                                self.snx_logger.error(msg)
                                # Return Error
                                yield {'ERROR': msg}

                        # Scan ID exists
                        else:
                            event['latestUrl'] = first_url.get('url')
                            event['latestUrl_scanId'] = first_url.get('scanId')
                            event['latestUrl_verdict'] = first_url.get('threatData').get('verdict')
                            event['latestUrl_threatStatus'] = first_url.get('threatData').get('threatStatus')
                            event['latestUrl_threatName'] = first_url.get('threatData').get('threatName')
                            event['latestUrl_threatType'] = first_url.get('threatData').get('threatType')
                            event['latestUrl_firstSeen'] = first_url.get('threatData').get('firstSeen')
                            event['latestUrl_lastSeen'] = first_url.get('threatData').get('lastSeen')

                            if 'landingUrl' in first_url:
                                latest_url_scanId = first_url.get('landingUrl').get('scanId')
                                event['landingUrl'] = first_url.get('landingUrl').get('url')
                                event['landingUrl_scanId'] = first_url.get('landingUrl').get('scanId')
                                event['landingUrl_verdict'] = first_url.get('landingUrl').get('threatData').get('verdict')
                                event['landingUrl_threatStatus'] = first_url.get('landingUrl').get('threatData').get('threatStatus')
                                event['landingUrl_threatName'] = first_url.get('landingUrl').get('threatData').get('threatName')
                                event['landingUrl_threatType'] = first_url.get('landingUrl').get('threatData').get('threatType')
                                event['landingUrl_firstSeen'] = first_url.get('landingUrl').get('threatData').get('firstSeen')
                                event['landingUrl_lastSeen'] = first_url.get('landingUrl').get('threatData').get('lastSeen')

                            elif 'finalUrl' in first_url:
                                latest_url_scanId = first_url.get('scanId')
                                event['finalUrl'] = first_url.get('finalUrl')

                            else:
                                latest_url_scanId = first_url.get('scanId')

                        # ------------------ Forensics Data ------------------ #
                        # Calling the function to collectively download screenshot, HTML and text data
                        if data.get('swlData') is None:
                            self.snx_logger.info('Downloading Forensics for Scan ID: {0}'.format(latest_url_scanId))
                            self._download_forensics(event, latest_url_scanId)
                    else:
                        msg = 'Failed. Error Reason: {0}'.format(data.get('errorMsg'))
                        self.snx_logger.error(msg)
                        # Return Error
                        yield {'ERROR': msg}
                else:
                    msg = 'Error Connecting to SlashNext Cloud due to reason: {0}'.format(response.reason)
                    self.snx_logger.error(msg)
                    # Return Error
                    yield {'ERROR': msg}

                # Finally, we yield the event back to the Search
                yield event

            else:
                yield {'ERROR': 'No Parameter value specified. Please specify host parameter value.'}

        except Exception as e:
            stack = traceback.format_exc()
            # splunk.Intersplunk.generateErrorResults(str(e))
            self.snx_logger.error(str(e) + ". Traceback: " + str(stack))


dispatch(SnxHostReportCommand, sys.argv, sys.stdin, sys.stdout, __name__)

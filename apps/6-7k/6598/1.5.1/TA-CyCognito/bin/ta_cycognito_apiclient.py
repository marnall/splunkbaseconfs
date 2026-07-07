"""This file is used to define api methods."""
import json
import traceback

import requests

import ta_cycognito_constants as constants
import ta_cycognito_declare  # noqa F401
import ta_cycognito_utils as utils


class CycognitoClient(object):
    """A Cycognito class which contains base methods."""

    def __init__(self, helper, ew, logger, input_type):
        """
        Initialize object with given parameters.

        :param ew: object of EventWriter class
        :param helper: object of BaseModInput class
        :param logger: logger object
        :input_type: specifies the type of input(assets/issues)
        """
        self.cycognito_account = helper.get_arg('cycognito_account')
        self.index = helper.get_arg('index')
        self.platform_url = self.cycognito_account["platform_url"]
        self.api_token = self.cycognito_account["api_token"]
        self.input_name = helper.get_arg('name')
        self.input_type = input_type
        self.session_key = helper.context_meta['session_key']
        self.proxy = utils.get_proxy(self.session_key)
        # session object for making rest call
        self.session_object = utils.requests_retry_session()
        # headers to pass in REST call
        self.headers = {
            'Authorization': self.api_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.helper = helper
        self.logger = logger
        self.ew = ew

    def collect_cycognito_data(self, url, page, data=[]):
        """Make api call to cycognito platform to collect data."""
        try:
            params = {'count': constants.PAGE_LIMIT, 'offset': page}
            response = self.session_object.post(
                url,
                headers=self.headers,
                params=params,
                json=data,
                verify=constants.SSL_VERIFY,
                timeout=constants.REQ_TIMEOUT,
                proxies=self.proxy
            )
            if response and response.status_code == 200:
                self.logger.debug(
                    "CyCognito Rest API: Successful Response")
                return response.json()
            elif response.status_code == 400:
                self.logger.error(
                    "CyCognito Rest API: Error occurred while fetching {} data. "
                    " input_name={}, Status code=400 and Response={}".format(
                        self.input_type, self.input_name, response.text))
            elif response.status_code == 401:
                self.logger.error(
                    "CyCognito Rest API: Error occurred while fetching {} data. "
                    "input_name={}, Status code=401 and Response={}".format(
                        self.input_type, self.input_name, response.text))
                self.logger.debug("CyCognito Rest API: Please verify that API key token is expired or not"
                                  " for account={}.".format(self.cycognito_account["name"]))
            else:
                self.logger.error("CyCognito Rest API: Error occurred while fetching {} data. "
                                  " input_name={}, Status code={} and "
                                  "Response={}".format(
                                      self.input_type, self.input_name, response.status_code, response.text))
        except (requests.HTTPError, requests.exceptions.ConnectionError) as e:
            self.logger.error(
                "CyCognito Rest API: HTTPError or ConnectionError occurred while fetching {} data."
                " input_name={}, Error=\"{}\"".format(self.input_type, self.input_name, str(e)))
            self.logger.error(
                "CyCognito Rest API: HTTPError or ConnectionError occurred while fetching {} data."
                " input_name={}, Error=\"{}\"".format(self.input_type, self.input_name, traceback.format_exc()))
        except Exception as e:
            self.logger.error(
                "CyCognito Rest API: Exception occurred while fetching {} data."
                " input_name={}, Error=\"{}\"".format(self.input_type, self.input_name, str(e)))
            self.logger.error(
                "CyCognito Rest API: Unexpected error occurred. "
                "input_name={}, Error=\"{}\"".format(self.input_name, traceback.format_exc()))
        return None

    def write_events_to_splunk(self, response, sourcetype=None):
        """Ingest the data in specified index."""
        event_count = 0
        try:
            # iterate through all events of response
            for event in response:
                event_count += 1
                new_event = self.helper.new_event(
                    json.dumps(event, ensure_ascii=False),
                    index=self.index,
                    source=self.helper.get_input_type(),
                    host=self.platform_url,
                    sourcetype=sourcetype if sourcetype else self.helper.get_sourcetype()
                )
                self.ew.write_event(new_event)
        except Exception as e:
            self.logger.error(
                "CyCognito Events: Error occurred while writing event to Splunk."
                "input_name={}, Error=\"{}\"".format(self.input_name, str(e)))
            self.logger.error(
                "CyCognito Events: Error occurred while writing event to Splunk."
                "input_name={}, Error=\"{}\"".format(self.input_name, traceback.format_exc()))
        return event_count
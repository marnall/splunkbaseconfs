import json
from datetime import datetime, timezone

from fnc import FncClient, FncClientError, FncClientLogger
from fnc.api import FncApiClient, FncRestClient
from fnc.errors import ErrorMessages, ErrorType
from fnc.metastream import FncMetastreamClient
from global_variables import INTEGRATION_NAME
from IPy import IP

default_timeout = 30
default_verify = True


class FncSplunkRestClient(FncRestClient):
    def __init__(self, helper):
        self.helper = helper

    def validate_request(self, req_args: dict):
        if not req_args or 'url' not in req_args:
            raise FncClientError(
                error_type=ErrorType.REQUEST_VALIDATION_ERROR,
                error_message=ErrorMessages.REQUEST_URL_NOT_PROVIDED
            )

        if 'method' not in req_args:
            raise FncClientError(
                error_type=ErrorType.REQUEST_VALIDATION_ERROR,
                error_message=ErrorMessages.REQUEST_METHOD_NOT_PROVIDED
            )

    def send_request(self, req_args: dict = None):
        url = req_args['url']
        method = req_args['method']
        headers = req_args.get('headers', {})
        timeout = req_args.get('timeout', 70)
        verify = req_args.get('verify', True)
        parameters = req_args.get('params', {})
        json = req_args.get('json', None)
        data = req_args.get('data', None)
        payload = json or data

        return self.helper.send_http_request(url,
                                             method=method,
                                             parameters=parameters,
                                             payload=payload,
                                             headers=headers,
                                             timeout=timeout,
                                             verify=verify
                                             )


class FncSplunkLogger(FncClientLogger):
    def __init__(self, helper):
        self.helper = helper

    def set_helper(self, helper):
        self.helper = helper

    def get_level(self, level):
        if not self.helper:
            return None
        return self.helper.get_log_level()

    def set_level(self, level):
        if not self.helper:
            return
        self.helper.set_log_level(level.upper())

    def critical(self, log: str):
        if not self.helper:
            return
        self.helper.log_critical(log)

    def error(self, log: str):
        if not self.helper:
            return
        self.helper.log_error(log)

    def warning(self, log: str):
        if not self.helper:
            return
        self.helper.log_warning(log)

    def info(self, log: str):
        if not self.helper:
            return
        self.helper.log_info(log)

    def debug(self, log: str):
        if not self.helper:
            return
        self.helper.log_debug(log)


class FncSplunkClientManager(object):
    helper = None
    api_client: FncApiClient = None
    metastream_client: FncMetastreamClient = None
    logger: FncSplunkLogger = None
    rest_client: FncSplunkRestClient = None

    def __init__(self, helper, ew):
        self.helper = helper
        self.ew = ew
        self.logger = FncSplunkLogger(helper)
        self.rest_client = FncSplunkRestClient(helper)

    def initialize_api_client(self, api_token: str, domain: str):
        # get user agent from global variables
        user_agent = INTEGRATION_NAME
        self.api_client = FncClient.get_api_client(
            name=user_agent, api_token=api_token, domain=domain, rest_client=self.rest_client, logger=self.logger)

    def initialize_metastream_client(self,
                                     account_code: str = None,
                                     access_key: str = None,
                                     secret_key: str = None,
                                     bucket: str = None
                                     ):
        # get user agent from global variables
        user_agent = INTEGRATION_NAME
        self.metastream_client = FncClient.get_metastream_client(
            name=user_agent,
            access_key=access_key,
            secret_key=secret_key,
            account_code=account_code,
            bucket=bucket,
            logger=self.logger
        )

    def get_api_client(self):
        if not self.api_client:
            self.logger.warning("API Client was requested before initialized.")

        return self.api_client

    def get_metastream_client(self):
        if not self.metastream_client:
            self.logger.warning(
                "Metastream Client was requested before initialized.")
        return self.metastream_client

    def get_logger(self):
        return self.logger

    def create_splunk_event(
            self,
            timestamp=None,
            source_type=None,
            data=None):
        if not data:
            self.logger.warning(
                "Ignoring empty event that was sent to Splunk.")

        now = datetime.now(tz=timezone.utc)
        timestamp = timestamp or now
        event_timestamp = "{:.3f}".format(timestamp.timestamp())

        splunk_event = self.helper.new_event(time=event_timestamp,
                                             source=self.helper.get_input_type(),
                                             index=self.helper.get_output_index(),
                                             sourcetype=source_type or self.helper.get_sourcetype(),
                                             data=json.dumps(data))

        # Write the splunk event
        self.ew.write_event(splunk_event)

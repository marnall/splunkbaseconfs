import os
import cloudknox_consts
import cloudknox_common_utils as utils
from filelock import Timeout, FileLock

from solnlib.utils import is_true
from log_manager import setup_logging
from splunk_aoblib.rest_helper import TARestHelper


_LOGGER = setup_logging("cloudknox_mod_input")


class CloudKnoxCollect(object):
    """A class to establish connection with Cloudknox and get data using REST API."""

    def __init__(self, session_key, app_name):
        """Intialize ColudKnoxCollect object to get data from cloudknox platform.

        Args:
            session_key (object): Splunk session key
            app_name (str): Name of the App
        """
        self.session_key = session_key

        try:
            self.PROXY_URI = utils.get_proxy_uri(app_name, self.session_key)
            self.CLOUDKNOX_CONFIGS = utils.get_cloudknox_configs()
        except Exception as e:
            _LOGGER.error(
                "Unexpected error occured while generating or saving new token: {}".format(e)
            )
            exit()

        if self.PROXY_URI:
            _LOGGER.info("Proxy is enabled on the instance.")

        self.APP_NAME = app_name
        self.VERIFY_SSL = is_true(self.CLOUDKNOX_CONFIGS.get("verify_cert", "true"))

    @staticmethod
    def request_ck_access_token(ck_url, account_id, access_key, secret_key, verify_cert, proxy_uri):
        """Generate new access token with CloudKnox credentials.

        Args:
            ck_url (str): CloudKnox base URL
            account_id (str): Service account ID
            access_key (str): Access Key
            secret_key (str): Secret Key
            verify_cert (bool): SSL certificate validation flag
            proxy_uri (str): Proxy URI

        Returns:
            object: requests.Response object
        """
        request_data = {
            "serviceAccountId": account_id,
            "accessKey": access_key,
            "secretKey": secret_key,
        }

        request_url = "{scheme}{url}{endpoint}".format(
            scheme="https://", url=ck_url, endpoint=cloudknox_consts.AUTH_ENDPOINT
        )
        response = TARestHelper().send_http_request(
            request_url, "post", payload=request_data, verify=verify_cert, proxy_uri=proxy_uri,
        )
        return response

    def get_and_update_access_token(self):
        """Get new access token and store it in passwords.conf.

        Returns:
            str: cloudknox access token
        """
        _LOGGER.info("CloudKnox access token expired. Fetching new access token.")
        # # Acquire Lock
        ck_access_token_lock = FileLock(
            os.path.join(os.path.dirname(__file__), "..", "local", "ck_access_token.lock")
        )
        try:
            with ck_access_token_lock.acquire(
                timeout=cloudknox_consts.LOCK_TIMEOUT,
                poll_intervall=cloudknox_consts.LOCK_POLLING_INTERVAL,
            ):
                _LOGGER.info("Acquired lock. Access token validation and generation in progress.")
                ck_url = self.CLOUDKNOX_CONFIGS.get("cloudknox_url", "").strip("/")
                account_id = self.CLOUDKNOX_CONFIGS.get("account_id", "")
                access_key = self.CLOUDKNOX_CONFIGS.get("access_key", "")

                # Validate existing access token
                request_url = "{scheme}{url}{endpoint}".format(
                    scheme="https://", url=ck_url, endpoint=cloudknox_consts.LIST_AUTH_SYSTEMS
                )

                # # Get stored access token
                secret_key, access_token = utils.get_ck_clear_tokens(
                    self.APP_NAME, self.session_key
                )
                request_headers = {"X-CloudKnox-Access-Token": access_token}
                dummy_response = TARestHelper().send_http_request(
                    request_url,
                    "get",
                    headers=request_headers,
                    verify=self.VERIFY_SSL,
                    proxy_uri=self.PROXY_URI,
                    timeout=(cloudknox_consts.CONNECT_TIMEOUT, cloudknox_consts.READ_TIMEOUT),
                )
                if dummy_response.status_code == 401:
                    _LOGGER.info("Access token is invalid, generating new access token...")
                    response = self.request_ck_access_token(
                        ck_url, account_id, access_key, secret_key, self.VERIFY_SSL, self.PROXY_URI
                    )
                    if response.ok:
                        access_token = response.json()["accessToken"]
                        utils.save_ck_credentials(self.APP_NAME, self.session_key, access_token)
                        _LOGGER.info("Access token generated and updated.")
                    else:
                        reason = self.get_error_message(response)
                        _LOGGER.error(
                            "Some error occured while regenerating the Access token: Status Code: {},Reason: {}."
                            " Exiting the data collection".format(
                                response.status_code, reason
                            )
                        )
                        ck_access_token_lock.release(force=True)
                        exit()
                    return None
        except Timeout:
            _LOGGER.error("Failed to acquire lock in given timeout.")
            ck_access_token_lock.release(force=True)
            exit()
        except Exception as e:
            _LOGGER.error(
                "Unexpected error occured while generating or saving new token: {}".format(e)
            )
            ck_access_token_lock.release(force=True)
            exit()

    def _call_endpoint(self, ck_url, endpoint, payload={}, method="post"):
        """Make REST call to the provided CloudKnox endpoints.

        Args:
            ck_url (str): CloudKnox base URL
            endpoint (str): CloudKnox endpoint
            payload (str): Request body
            method (str): HTTP method

        Returns:
            object: requests.Response object
        """
        request_url = "{scheme}{url}{endpoint}".format(
            scheme="https://", url=ck_url, endpoint=endpoint
        )

        _LOGGER.debug("Executing REST call: {}".format(request_url))

        retry = 0
        while retry <= cloudknox_consts.GLOBAL_RETRY:
            try:
                # # Get stored access token
                secret_key, access_token = utils.get_ck_clear_tokens(
                    self.APP_NAME, self.session_key
                )
                request_headers = {"X-CloudKnox-Access-Token": access_token}
                response = TARestHelper().send_http_request(
                    request_url,
                    method,
                    headers=request_headers,
                    verify=self.VERIFY_SSL,
                    proxy_uri=self.PROXY_URI,
                    payload=payload,
                    timeout=(cloudknox_consts.CONNECT_TIMEOUT, cloudknox_consts.READ_TIMEOUT),
                )
                if response.ok:
                    _LOGGER.info("Successfully obtained response from: {}".format(request_url))
                    return response
                if response.status_code == 401:
                    self.get_and_update_access_token()
                else:
                    reason = self.get_error_message(response)
                    message = "Failed to collect data from CloudKnox! URL:{} Payload: {}\
                            Status Code: {}, Reason: {}".format(
                        request_url, payload, response.status_code, reason
                    )
                    _LOGGER.error(message)
                    break
                retry += 1
            except Exception as e:
                _LOGGER.error(
                    "Unexpected Error while calling {} endpoint: {}".format(request_url, str(e))
                )
                break
        return None

    def cloudknox_get_all_auth_systems(self):
        """Get auth systems from cloudknox platform.

        Returns:
            object: requests.Response object
        """
        ck_url = self.CLOUDKNOX_CONFIGS.get("cloudknox_url", "").strip("/")

        response = self._call_endpoint(ck_url, cloudknox_consts.LIST_AUTH_SYSTEMS, method="get")
        return response

    def _generate_par_payload(self, name, sub_category, auth_system, auth_type, page_id, dataSummary, reportSummary):
        """Generate payload for PAR enpoint request.

        Args:
            name (str): CloudKnox Dashboad category name
            sub_category (str): CloudKnox sub category
            auth_system (dict/list of dict): Auth system dict/list of dict
            auth_type (str): Auth system type
            page_id (int): request page id
            dataSummary (boolean): Indicates if the data to be collected is Summary data
            reportSummary (boolean): Indicates if the data to be collected is aws Report Summary data

        Returns:
            dict: payload
        """
        payload = {"authSystemType": auth_type}
        if reportSummary:
            # payload for AWS REPORT_SUMMARY
            payload.update({
                "authSystemIds": [auth_system.get("id")],
                "findingType": "{}.{}".format(name, sub_category)
            })
        elif dataSummary:
            # payload for summary endpoint
            payload.update({
                "authSystemIds": [each.get("id") for each in auth_system],
                "findingType": "{}.{}".format(name, sub_category),
                "aggregation": {
                    "authSystem": True
                }
            })
        else:
            # payload for data endpoint
            payload.update({
                "authSystemIds": [each.get("id") for each in auth_system],
                "findingType": "{}.{}".format(name, sub_category),
                "pageInfo": {
                    "pageSize": cloudknox_consts.PAGE_SIZE,
                    "pageId": page_id
                }
            })
        return payload

    def cloudknox_collect_par_data(
        self, name, sub_category, auth_system, auth_sys_type, endpoint,
        dataSummary=False, reportSummary=False
    ):
        """Collect cloudknox PAR data.

        Args:
            ck_url(str): Cloudknox URL
            name(str): Name of category
            sub_category (str): CloudKnox sub category
            auth_system (dict/list of dict): Auth system dict/list of dict
            auth_sys_type (str): Auth system type
            endpoint (str): The endpoint to collect data from
            dataSummary (boolean): Indicates if the data to be collected is Summary data
            reportSummary (boolean): Indicates if the data to be collected is aws Report Summary data

        Returns:
            object: requests.Response object
        """
        ck_url = self.CLOUDKNOX_CONFIGS.get("cloudknox_url", "").strip("/")
        page_id = 0
        flag = True
        while flag:
            payload = self._generate_par_payload(
                name, sub_category, auth_system, auth_sys_type, page_id, dataSummary, reportSummary
            )
            response = self._call_endpoint(ck_url, endpoint, payload)
            if (
                not response or reportSummary
                or (response.ok and len(response.json().get("data")) < cloudknox_consts.PAGE_SIZE)
                or dataSummary
            ):
                flag = False
            yield response
            page_id += 1

    def cloudknox_collect_audit_trail_data(self, start_time, input_name, end_time):
        """
        Collect cloudknox auditlogs data.

        Args:
            start_time(str): Start time from that time data should be fetched from platform.
            input_name(str): Input name for which data will be collected.
            end_time(int): Epoch seconds till now.

        Returns:
            object: LIST object
        """
        audit_payload = cloudknox_consts.AUDIT_PAYLOAD
        yield self.collect_data_in_chunked_of_hour(start_time,
                                                   end_time,
                                                   audit_payload, input_name,
                                                   cloudknox_consts.AUDITLOG_DATA_ENDPOINT,
                                                   "auditlogs",
                                                   cloudknox_consts.SECONDS_OF_FIVE_MIN)

    def cloudknox_collect_alert_data(self, start_time, input_name, end_time, alert_type):
        """
        Collect cloudknox alerts data.

        Args:
            start_time(str): Start time from that time data should be fetched from platform.
            input_name(str): Input name for which data will be collected.
            end_time(int): Epoch seconds till now.

        Returns:
            object: LIST object
        """
        alert_payload = cloudknox_consts.ALERT_PAYLOAD
        yield self.collect_data_in_chunked_of_hour(start_time,
                                                   end_time,
                                                   alert_payload, input_name,
                                                   cloudknox_consts.ALERT_DATA_ENDPOINT.format(alert_type),
                                                   "alerts")

    def collect_data_in_chunked_of_hour(self, start_time, end_time, payload,
                                        input_name, api_endpoint, field, offset=None):
        """
        Collect data from mentioned endpoint in chunked of hours.

        Args:
            start_time(str): Start time from that time data should be fetched from platform.
            end_time(str): End time till that time data should be fetched from platform.
            payload(dict): HTTP request payload.
            input_name(str): Input name for which data will be collected.
            api_endpoint(str): From this endpoint dat will be collected.
            field(str): Field name.
            offset(int): Offset seconds which will be added in start_time.

        Returns:
            object: LIST object
        """
        ck_url = self.CLOUDKNOX_CONFIGS.get("cloudknox_url", "").strip("/")
        start_time = start_time + offset if offset else start_time
        add_minutes = False
        # Flag set to False when no response is obtained and used to break from the the data collection loop
        continue_flag = True

        # Loop to iterate through the entire time range in chunks
        while (True and continue_flag):
            # Start collection from 0th page
            page_number = 0

            # Terminate while loop since the provided time range is scanned
            if end_time - start_time <= 0:
                _LOGGER.info("Completed scanning entire time range for {} input".format(input_name))
                break

            # Break time range into chunks of 60 minutes if needed, else execute with same range
            if end_time - start_time > cloudknox_consts.SECONDS_OF_HR:
                _LOGGER.info("Range for {} input is greater than 60 minutes. Breaking into chunks.".format(input_name))

                # Add offset for audit logs only if add_minutes flag is True
                # This flag will be False in case of empty response which will avoid data miss
                if add_minutes:
                    start_time = start_time + offset if offset else start_time
                    add_minutes = False

                chunked_endtime = start_time + cloudknox_consts.SECONDS_OF_HR
                payload['from'] = start_time
                payload['to'] = chunked_endtime

            else:
                _LOGGER.info("Range for {} input is less than / equal to 60 minutes.".format(input_name))

                # Add offset for audit logs only if add_minutes flag is True
                # This flag will be False in case of empty response which will avoid data miss
                if add_minutes:
                    start_time = start_time + offset if offset else start_time
                    add_minutes = False

                payload['from'] = start_time
                payload['to'] = end_time
                chunked_endtime = end_time

            # Loop to iterate through all the pages within each chunk
            while True:
                endpoint = "{}/{}".format(api_endpoint, page_number)

                _LOGGER.info("Requesting {} data for input {}. Parameters: from: {}, to: {}, page: {}.".format(
                    field, input_name, payload['from'], payload['to'], page_number))
                response = self._call_endpoint(ck_url, endpoint, payload)

                if response:
                    response_data = response.json()
                    total_events = len(response_data)

                    if response_data:
                        _LOGGER.info(
                            "{} {} events found for input {}. Parameters: from: {}, to: {}, page: {}.".format(
                                total_events, field, input_name, payload['from'], payload['to'], page_number))
                        # Adding 1000 milliseconds to the maximum value of timestamp obtained in response.
                        # This is needed since both the parameters are inclusive
                        # i.e. API provides response of events in time range:  ">=from and <=to"
                        if field == "auditlogs":
                            max_timestamp = response_data[-1]["dateStartedOn"] + 1000

                        elif field == "alerts":
                            max_timestamp = response_data[-1]["dateModifiedOn"] + 1000

                        # Convert milliseconds into seconds since API expects it only in seconds.
                        chunked_endtime = int(max_timestamp / 1000)
                        # Set the add_minutes flag since we have received data for the calculated endtime
                        add_minutes = True
                        yield response_data
                        page_number = page_number + 1

                    else:
                        _LOGGER.info(
                            "No {} data found for input {}. Parameters: from: {}, to: {}, page: {}.".format(
                                field, input_name, payload['from'], payload['to'], page_number))
                        break

                else:
                    continue_flag = False
                    break

            start_time = chunked_endtime

    def check_credentials(self):
        """
        Check the configuration is done before creating inputs.

        raise ValueError: When configuration is not completed.
        """
        # get cloudknox url, access_key and access key from conf
        ck_url = self.CLOUDKNOX_CONFIGS.get("cloudknox_url", "").strip("/")
        ck_account_id = self.CLOUDKNOX_CONFIGS.get("account_id", "")
        ck_access_key = self.CLOUDKNOX_CONFIGS.get("access_key", "")

        # if any of them are None then the account is not configured
        if not all([ck_url, ck_account_id, ck_access_key]):
            message = "CloudKnox credentials are not configured."
            raise ValueError(message)

    @staticmethod
    def get_error_message(response):
        """Return error reason from response.

        Args:
            response(Response Object): Response from cloudknox Rest endpoint.
        Returns:
            str: error message from response.
        """
        if "errorCode" in response.json():
            return response.json().get("errorCode")
        else:
            return response.reason

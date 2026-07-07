"""This module contains class and methods related to collection\
 of findings,assets and sources."""
import import_declare_test  # noqa F401
import time
from typing import List, Union
from google.oauth2 import service_account
from googleapiclient import discovery
import google.auth
from google.auth import aws
from google.auth import identity_pool
from google_auth_httplib2 import AuthorizedHttp
import httplib2
import ssl
from googleapiclient.errors import HttpError
from TA_GoogleSCC_consts import constants
from TA_GoogleSCC_utils import get_vm_details, get_proxy_settings # noqa F401
from splunklib import modularinput as smi
import splunk.admin as admin
import traceback
import base64
import json


ERROR_MESSAGES = {
    "BAD_REQUEST_ERROR": "An error occurred while fetching/submitting the data. Reason: {}",
    "AUTHENTICATION_ERROR": "Unauthenticated. Check the configured Service Account JSON. Reason: {}",
    "AUTHORIZATION_ERROR": "Request has insufficient privileges. Reason: {}",
    "NOT_FOUND_ERROR": "Not found. Reason: {}",
    "TOO_MANY_REQUESTS_ERROR": "Too many requests please try after sometime. Reason: {}",
    "CONFLICT_ERROR": "Conflict. Reason: {}",
    "UNKNOWN_ERROR": "Unknown error occurred. Reason: {}",
}


class GetSessionKey(admin.MConfigHandler):
    """Session key."""

    def __init__(self):
        """Initialize Session Key."""
        self.session_key = self.getSessionKey()


class GoogleClient:
    """A Google Client class which contain base methods."""

    def __init__(
        self,
        service_name: str,
        service_version: str,
        service_account_json,
        credential_configuration_file,
        scopes: list,
        logger,
        organization_id,
        timeout,
        session_key=None,
    ):
        """Initialize Google SCC client."""
        try:
            if session_key is None:
                session_key = GetSessionKey().session_key
                proxy = get_proxy_settings(logger, session_key)
            else:
                proxy = get_proxy_settings(logger, session_key)
        except Exception:
            logger.error("message=proxy_error | Error Occured while fetching proxy.\n{}".format(traceback.format_exc()))

        try:
            is_gcp, is_aws, is_azure = get_vm_details(logger, session_key)
            if is_gcp:
                credentials, project_id = google.auth.default()
            elif is_aws:
                credential_configuration_file = json.loads(credential_configuration_file)
                credentials = aws.Credentials.from_info(
                    info=credential_configuration_file, scopes=constants.SCOPES)
            elif is_azure:
                credential_configuration_file = json.loads(credential_configuration_file)
                credentials = identity_pool.Credentials.from_info(
                    credential_configuration_file, scopes=constants.SCOPES)
            else:
                credentials = service_account.Credentials.from_service_account_info(
                    info=service_account_json, scopes=constants.SCOPES
                )
            http_client = AuthorizedHttp(credentials=credentials, http=proxy)
            self.logger = logger
            self.organization_id = organization_id
            self.service = discovery.build(
                service_name,
                service_version,
                http=http_client,
                cache_discovery=False
                )
        except ssl.SSLError as ex:
            logger.error("message=ssl_error | SSL Error occurred while initializing GoogleClient.\n{0}"
                         .format(traceback.format_exc()))
            raise ex
        except httplib2.socks.HTTPError:
            logger.error("message=proxy_error | Proxy error occurred while executing request.\n{0}"
                         .format(traceback.format_exc()))
            self.put_msg("Invalid Proxy credentials. Please recheck your\
             Proxy settings.")
        except Exception:
            logger.error("message=client_initialization_error | Error occurred while initializing GoogleClient.\n{0}"
                         .format(traceback.format_exc()))

    @staticmethod
    def process_http_error(status, reason, count, logger):
        """Process http error response and return retry needed or not."""
        if status >= 500:
            logger.error(
                "message=server_error |"
                "The server encountered an internal error with status {0} and reason: {1}".format(status, reason)
            )
            if count < constants.RETRY_COUNT:
                logger.error("message=retry_mechanism |"
                             "The server Retrying for {0} time after sleeping\
                             for {1} Seconds.".format(count, constants.TIME_TO_SLEEP_ON_RETRY))
                time.sleep(constants.TIME_TO_SLEEP_ON_RETRY)
                return True
            return False
        status_code_message_map = {
            400: ERROR_MESSAGES["BAD_REQUEST_ERROR"],
            401: ERROR_MESSAGES["AUTHENTICATION_ERROR"],
            403: ERROR_MESSAGES["AUTHORIZATION_ERROR"],
            404: ERROR_MESSAGES["NOT_FOUND_ERROR"],
            409: ERROR_MESSAGES["CONFLICT_ERROR"],
            429: ERROR_MESSAGES["TOO_MANY_REQUESTS_ERROR"],
        }
        err_msg = ERROR_MESSAGES["UNKNOWN_ERROR"]
        if status in status_code_message_map:
            err_msg = status_code_message_map[status]
        logger.error(
            "message=http_error |"
            " HttpError occurred while executing request with status {0}. {1}".format(status, err_msg.format(reason))
        )
        return False

    @staticmethod
    def execute_request(request, logger):
        """Execute request and handle error scenario."""
        count = 0
        while count < constants.RETRY_COUNT:
            count = count + 1
            try:
                return request.execute()
            except HttpError as e:
                status = e.resp.status
                reason = e._get_reason()
                if GoogleClient.process_http_error(status, reason, count, logger):
                    continue
            except httplib2.socks.HTTPError:
                logger.error("message=proxy_error | Proxy error occurred while executing request.\n{0}"
                             .format(traceback.format_exc()))
            except httplib2.ServerNotFoundError:
                logger.error("message=server_error | ServerNotFoundError occurred while executing "
                             "request.\n{0}".format(traceback.format_exc()))
            except Exception:
                logger.error("message=unexpected_error | Unexpected error occurred.\n{0}"
                             .format(traceback.format_exc()))
            break
        return False


class GoogleSccClient(GoogleClient):
    """A Google SCC client contains method for validation and collection."""

    def __init__(self, **kwargs):
        """Class init."""
        super().__init__(**kwargs)

    def get_resource_assets(self, parent: str, page_size: Union[str, int], index, ew, org):
        """Get an organization's assets and ingest them into Splunk.

        Args:
            parent (str): Name of the organization assets should belong to.
            page_size (Union[str, int]): Maximum number of assets in single call.
        """
        assets_object = self.service.assets()
        request = assets_object.list(parent=parent, assetTypes=constants.DEFAULT_ASSET_TYPES,
                                     contentType=constants.CONTENT_TYPE_RESOURCE, pageSize=page_size)
        resource_event_count = 0
        try:
            while request:
                result = self.execute_request(request, self.logger)
                if not result:
                    self.logger.error("message=data_fetching_error | Error occurred while fetching assets.")
                    break
                if result.get('assets'):
                    for res_obj in result.get('assets'):
                        try:
                            ancestor_project_id = ""
                            for anc in res_obj.get('ancestors'):
                                if anc.startswith("projects/"):
                                    ancestor_project_id = anc
                            res_obj["ancestor_project_id"] = ancestor_project_id
                            res_obj['orgID'] = org
                            event = smi.Event(
                                data=json.dumps(res_obj),
                                sourcetype='google:scc:assets',
                                index=index,
                                source='google_scc_assets_input'
                            )
                            ew.write_event(event)
                            resource_event_count += 1
                        except Exception:
                            self.logger.error("message = data_ingestion_error |"
                                              " Error occured while writing event into splunk.\n{}"
                                              .format(traceback.format_exc()))
                request = assets_object.list_next(request, result)
        except Exception:
            self.logger.error("message=data_fetching_error |"
                              " Error occurred while fetching assets.\n{0}".format(traceback.format_exc()))
        return resource_event_count

    def get_iam_assets(self, parent: str, page_size: Union[str, int], index, ew, org):
        """Get an organization's assets and ingest them into Splunk.

        Args:
            parent (str): Name of the organization assets should belong to.
            page_size (Union[str, int]): Maximum number of assets in single call.
        """
        assets_object = self.service.assets()
        request = assets_object.list(parent=parent, assetTypes=constants.DEFAULT_IAM_ASSET_TYPES,
                                     contentType=constants.CONTENT_TYPE_IAM, pageSize=page_size)

        iam_event_count = 0
        try:
            while request:
                result = self.execute_request(request, self.logger)
                if not result:
                    self.logger.info("message=data_fetching_details |"
                                     " Empty response received while fetching assets.")
                    return result
                if result.get('assets'):
                    for res_obj in result.get('assets'):
                        try:
                            ancestor_project_id = ""
                            for anc in res_obj.get('ancestors'):
                                if anc.startswith("projects/"):
                                    ancestor_project_id = anc
                            res_obj["ancestor_project_id"] = ancestor_project_id
                            res_obj['orgID'] = org
                            event = smi.Event(
                                data=json.dumps(res_obj),
                                sourcetype='google:scc:iam:assets',
                                index=index,
                                source='google_scc_assets_input'
                            )
                            ew.write_event(event)
                            iam_event_count += 1
                        except Exception:
                            self.logger.error("message = data_ingestion_error |"
                                              " Error occured while writing event into splunk: {}"
                                              .format(traceback.format_exc()))
                request = assets_object.list_next(request, result)
        except Exception:
            self.logger.error("message=data_fetching_error |"
                              " Error occurred while fetching assets.\n{0}".format(traceback.format_exc()))
        return iam_event_count

    def get_sources_data(self, logger, parent, page_size):
        """Get an organization's source from API."""
        sources_object = self.service.organizations().sources()
        request = sources_object.list(parent=parent, pageSize=page_size)
        response = []
        while request:
            result = self.execute_request(request, logger)
            if not result:
                logger.info("message=data_fetching_details |"
                            " Empty response received while fetching sources.")
                break
            response.append(result)
            request = sources_object.list_next(request, result)
        return response

    def update_findings_state(self, logger, name, body):
        """Update the findings state and return the response."""
        request = self.service.organizations().sources().findings().setState(name=name, body=body)
        result = self.execute_request(request, logger)
        if not result:
            logger.error("message=finding_state_error |"
                         " Error occurred while updating the finding state to {} for Finding ID - {}."
                         "\n{}"
                         .format(body.get('state'), name, traceback.format_exc()))
            return False
        logger.info("message=finding_state_updated |"
                    " Updated the finding state to {} for Finding ID - {}.".format(body.get('state'), name))
        return result


class GooglePubSubClient(GoogleClient):
    """A Google Client class which contain methods related pub/sub."""

    def __init__(self, project_id, subscription_id, service_account_json, credential_configuration_file, **kwargs):
        """Class init."""
        super().__init__(
            service_account_json=service_account_json,
            credential_configuration_file=credential_configuration_file,
            **kwargs
        )
        self.project_id = project_id
        self.subscription_id = subscription_id

    def pull_messages(self, max_messages, ret_immediately=False):
        """Pull message from pubsub api."""
        subscription = "projects/{0}/subscriptions/{1}".format(self.project_id, self.subscription_id)
        body = {"max_messages": max_messages, "return_immediately": ret_immediately}
        request = self.service.projects().subscriptions().pull(subscription=subscription, body=body)
        result = self.execute_request(request, self.logger)
        return result

    def acknowledge_messages(self, acks_list: List):
        """Acknowledges message that are fetched."""
        subscription = "projects/{0}/subscriptions/{1}".format(self.project_id, self.subscription_id)
        body = {"ack_ids": acks_list}
        request = self.service.projects().subscriptions().acknowledge(subscription=subscription, body=body)
        result = self.execute_request(request, self.logger)
        return result

    def fetch_assets(self, maximum_fetching, index, ew, org):
        """
        Fetch asset updates from pub/sub and ingest them into Splunk.

        Args:
        maximum_fetching: maximum number of asset updates to pull.
        """
        acknowledges = []
        resource_event_count = 0
        iam_event_count = 0
        while True:
            try:
                messages = self.pull_messages(max_messages=maximum_fetching)
            except Exception:
                self.logger.error("message=data_fetching_error |"
                                  " Error occurred while pulling the messages.\n{}".format(traceback.format_exc()))
                break
            if messages == {}:
                self.logger.info("message=data_fetched_successfully | All data is fetched from the service.")
                break

            data_list = messages.get("receivedMessages", [])
            for data in data_list:

                ack_id = data.get("ackId")
                try:
                    encoded_data = data.get("message", {}).get("data", "")
                    decoded_data = base64.b64decode(encoded_data).decode()
                    try:
                        json_response = json.loads(decoded_data)
                    except json.JSONDecodeError:
                        json_response = {}
                    except Exception:
                        json_response = {}
                        self.logger.error("message=json_error |"
                                          " Error occured while jsonifying data.\n{0}"
                                          .format(traceback.format_exc()))
                    if json_response.get("asset"):
                        if json_response.get('asset', {}).get('resource'):
                            try:
                                ancestor_project_id = ""
                                for anc in json_response.get('asset', {}).get('ancestors'):
                                    if anc.startswith("projects/"):
                                        ancestor_project_id = anc
                                json_response["ancestor_project_id"] = ancestor_project_id
                                json_response['orgID'] = org
                                event = smi.Event(
                                    data=json.dumps(json_response),
                                    sourcetype='google:scc:assets',
                                    index=index,
                                    source='google_scc_assets_input'
                                )
                                ew.write_event(event)
                                resource_event_count += 1
                            except Exception:
                                self.logger.error("message=data_ingestion_error |"
                                                  " Error occured while writing event into splunk.\n{}"
                                                  .format(traceback.format_exc()))
                        elif json_response.get('asset', {}).get('iamPolicy'):
                            try:
                                ancestor_project_id = ""
                                for anc in json_response.get('asset', {}).get('ancestors'):
                                    if anc.startswith("projects/"):
                                        ancestor_project_id = anc
                                json_response["ancestor_project_id"] = ancestor_project_id
                                json_response['orgID'] = org
                                event = smi.Event(
                                    data=json.dumps(json_response),
                                    sourcetype='google:scc:iam:assets',
                                    index=index,
                                    source='google_scc_assets_input'
                                )
                                ew.write_event(event)
                                iam_event_count += 1
                            except Exception:
                                self.logger.error("message=data_ingestion_error |"
                                                  " Error occured while writing event into splunk.\n{}"
                                                  .format(traceback.format_exc()))

                except Exception:
                    self.logger.error("message=decoding_error |"
                                      " Error decoding Exception while processing assets data."
                                      " Asset={0}\n{1}".format(data, traceback.format_exc()))  # noqa: E501
                acknowledges.append(ack_id)

            if acknowledges:
                self.acknowledge_messages(acknowledges)
                self.logger.debug("message=acknowledged_assets_count |"
                                  " Acknowledged assets count = {0}.".format(len(acknowledges)))
                acknowledges = []
        return resource_event_count, iam_event_count


def init_google_cai_client(**kwargs) -> GoogleSccClient:
    """Provide GoogleCAIClient instance."""
    client = GoogleSccClient(
        service_name=constants.CAI_SERVICE_NAME,
        service_version=constants.CAI_SERVICE_VERSION,
        scopes=constants.SCOPES,
        **kwargs
    )
    return client


def init_google_pubsub_client(**kwargs) -> GooglePubSubClient:
    """Provide GooglePubSubClient instance."""
    client = GooglePubSubClient(
        service_name=constants.PUBSUB_SERVICE_NAME,
        service_version=constants.PUBSUB_SERVICE_VERSION,
        scopes=constants.SCOPES,
        **kwargs
    )
    return client


def init_google_scc_client(**kwargs) -> GoogleSccClient:
    """Provide GoogleSccClient instance."""
    client = GoogleSccClient(
        service_name=constants.SERVICE_NAME,
        service_version=constants.SERVICE_VERSION,
        scopes=constants.SCOPES,
        **kwargs
    )
    return client


def get_findings_data(logger, max_findings, index, ew, org, client: GooglePubSubClient):
    """Get findings data from google scc api."""
    acknowledges = []
    event_count = 0
    while True:
        try:
            messages = client.pull_messages(max_messages=max_findings)
        except Exception:
            logger.error("message=data_fetching_error |"
                         " Error occurred while pulling the messages.\n{}".format(traceback.format_exc()))
            break
        if messages == {}:
            logger.info("message=data_fetched_successfully | All data is fetched from the service.")
            break
        data_list = messages.get("receivedMessages", [])

        for data in data_list:
            ack_id = data.get("ackId")

            try:
                encoded_data = data.get("message", {}).get("data", "")
                decoded_data = base64.b64decode(encoded_data).decode()
                try:
                    json_response = json.loads(decoded_data)
                except json.JSONDecodeError:
                    json_response = {}
                except Exception:
                    json_response = {}
                    logger.error("message=json_error |"
                                 " Error occured while jsonifying data.\n{0}".format(traceback.format_exc()))

                if json_response.get("finding"):
                    try:
                        json_response['orgID'] = org
                        event = smi.Event(
                            data=json.dumps(json_response),
                            sourcetype='google:scc:findings',
                            index=index,
                            source="google_scc_findings_input"
                        )
                        ew.write_event(event)
                        event_count += 1
                    except Exception:
                        logger.error("message = data_ingestion_error |"
                                     " Error occured while writing event into splunk: {}"
                                     .format(traceback.format_exc()))
            except Exception:
                logger.error("message=decoding_error |"
                             " Error Decoding Exception while processing finding data."
                             " Finding={0}\n{1}".format(data, traceback.format_exc()))  # noqa: E501

            acknowledges.append(ack_id)
        if acknowledges:
            client.acknowledge_messages(acknowledges)
            logger.debug("message=acknowledged_findings_count |"
                         " Acknowledged findings count = {0}.".format(len(acknowledges)))
            acknowledges = []
    return event_count


def get_auditlog_data(logger, max_fetch, index, ew, org, client: GooglePubSubClient):
    """Get findings data from google scc api."""
    acknowledges = []
    event_count = 0
    while True:
        try:
            messages = client.pull_messages(max_messages=max_fetch)
        except Exception:
            logger.error("message=data_fetching_error |"
                         " Error occurred while pulling the messages.\n{}".format(traceback.format_exc()))
            break
        if messages == {}:
            logger.info("message=data_fetched_successfully | All data is fetched from the service.")
            break
        data_list = messages.get("receivedMessages", [])

        for data in data_list:
            ack_id = data.get("ackId")

            try:
                encoded_data = data.get("message", {}).get("data", "")
                decoded_data = base64.b64decode(encoded_data).decode()
                try:
                    json_response = json.loads(decoded_data)
                except json.JSONDecodeError:
                    json_response = {}
                except Exception:
                    json_response = {}
                    logger.error("message=json_error |"
                                 " Error occured while jsonifying data.\n{0}".format(traceback.format_exc()))

                log_types = ('data_access', 'policy', 'system_event', 'activity')
                if json_response.get('logName') and json_response.get('logName').endswith(log_types):
                    try:
                        json_response['orgID'] = org
                        event = smi.Event(
                            data=json.dumps(json_response),
                            sourcetype='google:scc:auditlogs',
                            index=index,
                            source="google_scc_auditlog_input"
                        )
                        ew.write_event(event)
                        event_count += 1
                    except Exception:
                        logger.error("message=data_ingestion_error |"
                                     " Error occured while writing event into splunk.\n{}"
                                     .format(traceback.format_exc()))

            except Exception:
                logger.error("message=decoding_error |"
                             " Error in Decoding while processing audit log data."
                             " log={0}\n{1}".format(data, traceback.format_exc()))  # noqa: E501

            acknowledges.append(ack_id)
        if acknowledges:
            client.acknowledge_messages(acknowledges)
            logger.debug("message=acknowledged_audit_logs_count |"
                         " Acknowledged Audit logs count = {0}.".format(len(acknowledges)))
            acknowledges = []
    return event_count

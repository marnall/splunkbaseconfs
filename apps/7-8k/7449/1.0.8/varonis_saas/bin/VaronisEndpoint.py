from splunk.persistconn.application import PersistentServerConnectionApplication
import json
import traceback
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client
from SplunkSettings import SplunkSettings
from HttpClient import HttpClient
from HttpClientMock import HttpClientMock
from Constants import app_name, THREAT_MODEL_ENUM_ID
from Utils import argToList
from SplunkLogging import setup_logging
from SearchAlertObjectMapper import SearchAlertObjectMapper
from QueryBuilder import QueryBuilder
from Constants import CLOSE_REASONS, ALERT_STATUSES
from AlertAttributes import AlertAttributes

logger = setup_logging("varonis_endpoint.log")


class VaronisEndpoint(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()
        self.logger = logger

    @staticmethod
    def get_service(request_body):
        session = json.loads(request_body)['session']
        session_key = session['authtoken']
        return client.connect(token=session_key)

    def get_client(self, request_body):
        service = self.get_service(request_body)
        url, api_key, log_level = SplunkSettings.get_app_settings(service)
        return HttpClient(url, api_key)

    def handle(self, request_body):
        try:
            log_level = SplunkSettings.get_app_settings(self.get_service(request_body))[2]
            self.logger.setLevel(log_level)

            payload = json.loads(json.loads(request_body)['payload'])
            self.logger.debug(f"Start of VaronisEndpoint: command = {payload['command']}")
            result = None

            if payload['command'] == "test-connection":
                url = payload['url']
                api_key = payload['api_key']
                self.logger.debug(f"[TestConnection]: url = {url}, api_key = {'*' * len(api_key)}")
                http_client = HttpClient(url, api_key)
                result = json.dumps(http_client.get_auth_token())

            if payload['command'] == "update-alert":
                self.logger.debug(f"[UpdateAlert]: payload = {payload}")
                http_client = self.get_client(request_body)

                alert_ids = argToList(payload['alert_id'])
                status_id = None
                close_reason_id = None

                if not payload['status'] and not payload['note']:
                    raise ValueError(f'At least one of status, note or close_reason is required.')

                if payload['status']:
                    if payload['status'].lower() == 'closed' and not payload['closeReasonId']:
                        raise ValueError(f'close_reason is required when status is closed.')
                    elif payload['status'].lower() == 'closed':
                        if payload['closeReasonId'].lower() not in CLOSE_REASONS.keys():
                            raise ValueError(f'close_reason must be one of {CLOSE_REASONS.keys()}.')
                        else:
                            close_reason_id = CLOSE_REASONS[payload['closeReasonId'].lower()]
                    else:
                        close_reason_id = CLOSE_REASONS['other']

                    if payload['status'].lower() not in ALERT_STATUSES.keys():
                        raise ValueError(f'status must be one of {ALERT_STATUSES.keys()}.')
                    else:
                        status_id = ALERT_STATUSES[payload['status'].lower()]

                update_status_result = None
                add_note_result = None

                if status_id:
                    update_status_query = {
                        "AlertGuids": alert_ids,
                        "CloseReasonId": close_reason_id,
                        "StatusId": status_id
                    }
                    self.logger.debug(f"[UpdateAlert]: update_status_query = {update_status_query}")
                    update_status_result = http_client.alert_update_status(update_status_query)

                if payload['note']:
                    add_note_query = {
                        "AlertGuids": alert_ids,
                        "Note": payload['note']
                    }
                    self.logger.debug(f"[UpdateAlert]: add_note_query = {add_note_query}")
                    add_note_result = http_client.add_note_to_alerts(add_note_query)

                result = f'update_status_result={update_status_result}, add_note_result={add_note_result}'

            if payload['command'] == "load-alert":
                self.logger.debug(f"[LoadAlert]: payload = {payload}")
                http_client = self.get_client(request_body)
                query = QueryBuilder().build_alert_query(threat_model_names=None, threat_model_ids=None,
                                                         alertIds=argToList(payload['alertId']),
                                                         start_time=None, end_time=None,
                                                         device_names=None, user_names=None, last_days=180,
                                                         ingest_time_from=None,
                                                         ingest_time_to=None,
                                                         alert_statuses=None, alert_severities=None,
                                                         alert_category_ids=None,
                                                         extra_fields=None,
                                                         descending_order=False)

                self.logger.debug(f'[LoadAlert] Executing search query: {json.dumps(query)}')
                results = http_client.execute_search_query(query)
                mapper = SearchAlertObjectMapper()
                alert = mapper.map(results)[0]
                alert['url'] = f"{http_client.url}/analytics/entity/Alert/{alert['Alert ID']}"
                result = json.dumps(alert)
                self.logger.debug(f'[LoadAlert] Response: {result}')

        except Exception as e:
            self.logger.error(traceback.format_exc());
            return {'payload': traceback.format_exc(), 'status': 500}

        return {'payload': result, 'status': 200}

    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")

    def done(self):
        pass

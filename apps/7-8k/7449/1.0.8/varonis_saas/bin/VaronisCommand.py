import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import traceback
from datetime import datetime
import pytz
from tzlocal import get_localzone
from splunklib.searchcommands import dispatch, Configuration, Option
from VaronisBaseCommand import VaronisBaseCommand
from QueryBuilder import QueryBuilder
from Constants import CLOSE_REASONS, ALERT_STATUSES, THREAT_MODEL_ENUM_ID, ALERT_CATEGORIES
from EventAttributes import EventAttributes
from SearchEventObjectMapper import SearchEventObjectMapper
from AlertAttributes import AlertAttributes
from SearchAlertObjectMapper import SearchAlertObjectMapper
from Utils import argToList
from SplunkSettings import SplunkSettings


# @Configuration(type='reporting')
@Configuration()
class VaronisCommand(VaronisBaseCommand):

    def __init__(self):
        super().__init__()
        self.start_time = None
        self.end_time = None

    command = Option(doc='Name of the command to execute', require=False, default='')
    alert_id = Option(doc='Pipe-separated list of alerts', require=False, default='')
    status = Option(doc='Alert status', require=False, default='')
    category = Option(doc='Alert Category', require=False, default='')
    threat_model = Option(doc='Pipe-separated list of requested threat model names', require=False, default='')
    severity = Option(doc='Alert severity', require=False, default='')
    note = Option(doc='Note to add to the alert', require=False, default='')
    close_reason = Option(doc='Note to add to the alert', require=False, default='')
    extra_fields = Option(doc='Pipe-separated list of Extra fields to include in the output', require=False, default='')

    def stream(self, records):
        try:
            self.log.debug(f"Start of Setup Logging: ")

            # log_level = SplunkSettings.get_app_settings(self.get_service())[2]
            self.client = self.get_client()
            # self.log.setLevel(log_level)

            if not self.start_time and not self.end_time:
                self.start_time = datetime.fromtimestamp(int(self.search_results_info.search_et))
                self.end_time = datetime.fromtimestamp(int(self.search_results_info.search_lt))

            self.log.debug(f"End of Setup Logging: ")

            if not self.command or self.command.lower() == 'get_alerts':
                return self.get_alerts()
            elif self.command.lower() == 'get_alerted_events':
                return self.get_alerted_events()
            elif self.command.lower() == 'update_alert':
                return self.update_alert()
            elif self.command.lower() == 'threat_model':
                return self.get_threat_model()
            else:
                raise ValueError(f'Invalid command: {self.command}')

        except Exception as e:
            traceback.print_exc()
            self.log.error(f"Error occurred while executing command: {e} {traceback.format_exc()}")
            print(e)
            raise

    def get_alerts(self):
        threat_models = argToList(self.threat_model)
        alert_statuses = argToList(self.status)
        alert_severities = argToList(self.severity)
        alert_ids = argToList(self.alert_id)
        alert_categories = argToList(self.category)
        extra_fields = argToList(self.extra_fields)

        self.log.debug(f"Start of VaronisGetAlertsCommand: "
                       f"start_time={self.start_time}, "
                       f"end_time = {self.end_time}, "
                       f"threat_models = {threat_models}, "
                       f"alert_statuses = {alert_statuses}, "
                       f"alert_severities = {alert_severities}, "
                       f"alert_ids = {alert_ids}, "
                       f"extra_fields = {extra_fields}")

        # self.client = self.get_client()

        self.log.debug(f"End of get client")

        threat_model_ids = self.get_threat_model_ids(threat_models)

        alert_category_ids = []
        if alert_categories:
            for category in alert_categories:
                if category.lower() not in ALERT_CATEGORIES.keys():
                    raise ValueError(f'alert_category must be one of {ALERT_CATEGORIES.keys()}.')
                else:
                    alert_category_ids.append(ALERT_CATEGORIES[category.lower()])

        query = QueryBuilder().build_alert_query(threat_model_names=None, threat_model_ids=threat_model_ids,
                                                 alertIds=alert_ids,
                                                 start_time=self.start_time, end_time=self.end_time,
                                                 device_names=None, user_names=None, last_days=None,
                                                 ingest_time_from=None,
                                                 ingest_time_to=None,
                                                 alert_statuses=alert_statuses, alert_severities=alert_severities,
                                                 alert_category_ids=alert_category_ids,
                                                 extra_fields=extra_fields,
                                                 descending_order=False)
        results = self.client.execute_search_query(query, max_fetch=1000)
        mapper = SearchAlertObjectMapper()
        alerts = mapper.map(results)

        count = 0
        local_tz = get_localzone()
        for item in alerts:
            utc_time = datetime.fromisoformat(item['Alert Time UTC'])
            _time = utc_time.replace(tzinfo=pytz.utc).astimezone(local_tz).timestamp()
            item['Url'] = f"{self.client.url}/analytics/entity/Alert/{item['Alert ID']}"
            raw_summary = item
            output_item = {'_raw': raw_summary, '_time': _time, **item}
            yield output_item
            count += 1

        self.log.debug(f'End of VaronisGetAlertsCommand: {count} alerts returned.')

    def update_alert(self):
        if not self.alert_id:
            raise ValueError(f'alert_id is required.')

        alert_ids = argToList(self.alert_id)

        self.log.debug(f"Start of VaronisAlertUpdateCommand: "
                       f"alert_ids = {alert_ids},"
                       f"status = {self.status}, "
                       f"note = {self.note}, "
                       f"close_reason = {self.close_reason}"
                       )

        status_id = None
        close_reason_id = None

        if not self.status and not self.note:
            raise ValueError(f'At least one of status, note or close_reason is required.')

        if self.status:
            if self.status.lower() == 'closed' and not self.close_reason:
                raise ValueError(f'close_reason is required when status is closed.')
            elif self.status.lower() == 'closed':
                if self.close_reason.lower() not in CLOSE_REASONS.keys():
                    raise ValueError(f'close_reason must be one of {CLOSE_REASONS.keys()}.')
                else:
                    close_reason_id = CLOSE_REASONS[self.close_reason.lower()]
            else:
                close_reason_id = CLOSE_REASONS['other']

            if self.status.lower() not in ALERT_STATUSES.keys():
                raise ValueError(f'status must be one of {ALERT_STATUSES.keys()}.')
            else:
                status_id = ALERT_STATUSES[self.status.lower()]

        # self.client = self.get_client()

        update_status_result = None
        add_note_result = None

        if status_id:
            update_status_query = {
                "AlertGuids": alert_ids,
                "CloseReasonId": close_reason_id,
                "StatusId": status_id
            }
            update_status_result = self.client.alert_update_status(update_status_query)

        if self.note:
            add_note_query = {
                "AlertGuids": alert_ids,
                "Note": self.note
            }
            add_note_result = self.client.add_note_to_alerts(add_note_query)

        unix_timestamp = int(datetime.now().timestamp())
        if update_status_result or add_note_result:
            output_item = {'_raw': f"Alerts: {alert_ids} updated", '_time': unix_timestamp}
        else:
            output_item = {'_raw': f"Alerts: {alert_ids} NOT updated", '_time': unix_timestamp}

        query = QueryBuilder().build_alert_query(threat_model_names=None, threat_model_ids=None, alertIds=alert_ids,
                                                 start_time=None, end_time=None,
                                                 device_names=None, user_names=None, last_days=180,
                                                 ingest_time_from=None,
                                                 ingest_time_to=None,
                                                 alert_statuses=None, alert_severities=None,
                                                 alert_category_ids=None,
                                                 extra_fields=None,
                                                 descending_order=False)
        results = self.client.execute_search_query(query, max_fetch=1000)
        mapper = SearchAlertObjectMapper()
        alerts = mapper.map(results)

        count = 0
        local_tz = get_localzone()
        for item in alerts:
            utc_time = datetime.fromisoformat(item['Alert Time UTC'])
            _time = utc_time.replace(tzinfo=pytz.utc).astimezone(local_tz).timestamp()
            item['Url'] = f"{self.client.url}/analytics/entity/Alert/{item['Alert ID']}"
            raw_summary = item
            output_item = {'_raw': raw_summary, '_time': _time, **item}
            yield output_item
            count += 1

        self.log.debug(f'End of VaronisAlertUpdateCommand.')

    def get_alerted_events(self):
        if not self.alert_id:
            raise ValueError(f'alert_id is required.')
        alert_ids = argToList(self.alert_id)
        extra_fields = argToList(self.extra_fields)
        self.log.debug(f"Start of VaronisGetAlertedEventsCommand: "
                       f"start_time={self.start_time}, "
                       f"end_time = {self.end_time}, "
                       f"alert_ids = {alert_ids},"
                       f"extra_fields = {extra_fields}")

        # self.client = self.get_client()

        query = QueryBuilder().build_event_query(alertIds=alert_ids,
                                                 start_time=self.start_time, end_time=self.end_time,
                                                 last_days=None, extra_fields=extra_fields,
                                                 descending_order=True)

        results = self.client.execute_search_query(query, max_fetch=1000)
        mapper = SearchEventObjectMapper()
        events = mapper.map(results)

        count = 0
        for item in events:
            unix_timestamp = int(
                datetime.fromisoformat(item["Generation Time (UTC)"].rstrip('Z')).timestamp())
            raw_summary = item
            output_item = {'_raw': raw_summary, '_time': unix_timestamp, **item}
            yield output_item
            count += 1

        self.log.debug(f'End of VaronisGetAlertedEventsCommand: {count} alerts returned.')

    def get_threat_model(self):
        self.log.debug(f"Start of VaronisGetThreatModelsCommand")

        # self.client = self.get_client()

        results = self.client.get_enum(THREAT_MODEL_ENUM_ID)

        count = 0
        for item in results:
            raw_summary = item["displayField"]
            output_item = {'_raw': raw_summary, **item}
            yield output_item
            count += 1

        self.log.debug(f'End of VaronisGetThreatModelsCommand: {count} models returned.')


if __name__ == "__main__":
    dispatch(VaronisCommand, sys.argv, sys.stdin, sys.stdout, __name__)

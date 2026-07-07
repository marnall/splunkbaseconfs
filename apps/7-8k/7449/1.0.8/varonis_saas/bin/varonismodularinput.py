import os
import sys

from VaronisModularInputBase import VaronisModularInputBase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import json
from datetime import datetime, timedelta
import traceback
import pytz
from tzlocal import get_localzone
from Constants import app_name, THREAT_MODEL_ENUM_ID
from AlertAttributes import AlertAttributes
from QueryBuilder import QueryBuilder
from SearchAlertObjectMapper import SearchAlertObjectMapper
from HttpClient import HttpClient
from HttpClientMock import HttpClientMock

from SplunkSettings import SplunkSettings

from splunklib.modularinput import *
import splunklib.client as client


class varonismodularinput(VaronisModularInputBase):

    def __init__(self):
        super().__init__()
        self.input_name = None

        self.api_key = None
        self.url = None

        self.threat_model_names = None
        self.alert_statuses = None
        self.alert_severities = None
        self.max_fetch = None
        self.first_fetch = None
        self.reset_on_next_run = None

        self.client = None

    def get_scheme(self):
        scheme = Scheme("Varonis SaaS")
        scheme.description = "Pull alerts data from Varonis SaaS"
        scheme.use_external_validation = True

        scheme.add_argument(
            Argument(
                name="threat_model_names",
                title="Threat Models",
                data_type=Argument.data_type_string,
                required_on_create=False,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            Argument(
                name="alert_statuses",
                title="Alert Status",
                data_type=Argument.data_type_string,
                required_on_create=False,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            Argument(
                name="alert_severities",
                title="Alert Severity",
                data_type=Argument.data_type_string,
                required_on_create=False,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            Argument(
                name="max_fetch",
                title="Maximum number of alert per fetch",
                data_type=Argument.data_type_number,
                required_on_create=False,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            Argument(
                name="first_fetch",
                title="First fetch time",
                data_type=Argument.data_type_string,
                required_on_create=False,
                required_on_edit=False,
            )
        )

        scheme.add_argument(
            Argument(
                name="reset_on_next_run",
                title="Reset on next run",
                data_type=Argument.data_type_boolean,
                required_on_create=False,
                required_on_edit=False,
            )
        )

        return scheme

    def stream_events(self, inputs, ew):
        try:
            self.inputs = inputs

            self.url, self.api_key, log_level = self.get_app_params()
            self.logger.setLevel(log_level)

            self.input_name = self.get_input_name()
            self.max_fetch = int(self.get_input_param("max_fetch"))
            self.first_fetch = int(self.get_input_param("first_fetch"))
            self.threat_model_names = self.get_input_param("threat_model_names")
            self.alert_statuses = self.get_input_param("alert_statuses")
            self.alert_severities = self.get_input_param("alert_severities")
            self.reset_on_next_run = self.get_input_param("reset_on_next_run")

            self.logger.info(f"[{self.input_name}] Starting execution with input parameters: "
                             f"url = {self.url}, "
                             f"api_key = {'*' * len(self.api_key)}, "
                             f"max_fetch = {self.max_fetch}, "
                             f"first_fetch = {self.first_fetch}, "
                             f"threat_model_names = {self.threat_model_names}, "
                             f"alert_statuses = {self.alert_statuses}, "
                             f"alert_severities = {self.alert_severities}, "
                             f"reset_on_next_run = {self.reset_on_next_run}")

            self.load_checkpoint()

            results = self.stream_events_internal()

            local_tz = get_localzone()
            self.logger.debug(f'Local TZ is {local_tz}')
            count = 0
            for item in results:
                event = Event()
                event.stanza = self.input_name
                event.data = json.dumps(item)
                utc_time = datetime.fromisoformat(item['Alert Time UTC'])
                event.time = utc_time.replace(tzinfo=pytz.utc).astimezone(local_tz).timestamp()
                ew.write_event(event)
                count = count + 1

            self.logger.info(f"[{self.input_name}] Ending execution: fetched {count} alerts")

        except Exception as e:
            traceback.print_exc()
            self.logger.error(f"Error occured while executing modular input script: {e} {traceback.format_exc()}")

    def stream_events_internal(self):
        try:
            self.client = HttpClient(self.url, self.api_key)

            from Utils import argToList
            self.threat_model_names = argToList(self.threat_model_names)
            self.alert_statuses = argToList(self.alert_statuses)
            self.alert_severities = argToList(self.alert_severities)

            checkpoint = self.load_checkpoint()
            last_fetched_ingest_time = datetime.fromisoformat(checkpoint['last_fetched_ingest_time'])
            ingest_time_to = datetime.now()
            threat_model_ids = self.get_threat_model_ids(self.threat_model_names)
            query = QueryBuilder().build_alert_query(threat_model_names=None, threat_model_ids=threat_model_ids,
                                                     alertIds=None,
                                                     start_time=None, end_time=None,
                                                     device_names=None, user_names=None, last_days=None,
                                                     ingest_time_from=last_fetched_ingest_time,
                                                     ingest_time_to=ingest_time_to,
                                                     alert_statuses=None, alert_severities=self.alert_severities,
                                                     alert_category_ids=None,
                                                     extra_fields=None,
                                                     descending_order=False)

            results = self.client.execute_search_query(query, max_fetch=self.max_fetch,
                                                       last_fetched_ingest_time=last_fetched_ingest_time)
            mapper = SearchAlertObjectMapper()
            alerts = mapper.map(results)

            for item in alerts:
                item['url'] = f"{self.client.url}/analytics/entity/Alert/{item['Alert ID']}"
                self.logger.debug(f"[{self.input_name}] Fetched item: {json.dumps(item)}")
                yield item

            if alerts[-1:]:
                last_fetched_ingest_time_str = \
                max(alerts, key=lambda alert: datetime.fromisoformat(alert['Ingest Time']))[
                    'Ingest Time']
                last_fetched_ingest_time = datetime.fromisoformat(last_fetched_ingest_time_str) + timedelta(seconds=1)
                self.save_checkpoint({'last_fetched_ingest_time': last_fetched_ingest_time.isoformat()})

        except Exception as e:
            print(e)
            raise

    def get_threat_model_ids(self, threat_model_names):
        if threat_model_names:
            threat_models = self.client.get_enum(THREAT_MODEL_ENUM_ID)
            threat_model_ids = [threat_model["dataField"] for threat_model in threat_models
                                if any(
                    substring.lower() in threat_model["displayField"].lower() for substring in threat_model_names)]
            return threat_model_ids
        else:
            return None

    def load_checkpoint(self):
        default_checkpoint = {
            'last_fetched_ingest_time': (datetime.now() - timedelta(days=self.first_fetch)).isoformat()}
        checkpoint_file_location = self.get_checkpoint_file_location()
        try:
            with open(checkpoint_file_location, "r") as f:
                checkpoint = json.load(f)
        except:
            checkpoint = default_checkpoint
            with open(checkpoint_file_location, "w") as f:
                json.dump(checkpoint, f)

        if self.reset_on_next_run == '1':
            service = self.get_service()
            serv_inputs = service.inputs
            for input_item in serv_inputs:
                if f"{self.__class__.__name__.lower()}://{input_item.name}" in self.inputs.inputs:
                    self.logger.warning(f"[{self.input_name}][load_checkpoint] reset_on_next_run is called")

                    with open(checkpoint_file_location, "w") as f:
                        json.dump(default_checkpoint, f)

                    self.logger.warning(
                        f"[{self.input_name}][load_checkpoint] checkpoint was reset to: {default_checkpoint}")
                    self.logger.warning(f"[{self.input_name}][load_checkpoint] script will be re-executed")
                    input_item.update(reset_on_next_run=0, max_fetch=self.max_fetch)
        else:
            self.logger.debug(f"[{self.input_name}][load_checkpoint] checkpoint loaded: {checkpoint}")

        return checkpoint

    def save_checkpoint(self, checkpoint):
        checkpoint_file_location = self.get_checkpoint_file_location()
        with open(checkpoint_file_location, "w") as f:
            json.dump(checkpoint, f)

    # def validate_input(self, validation_definition):
    #     max_fetch = str(validation_definition.parameters.get("max_fetch"))
    #     if (len(max_fetch) < 1):
    #         raise ValueError("Provide Max Fetch")
    #
    #     if not max_fetch.isdecimal():
    #         raise ValueError(f"Max Fetch is not decimal {max_fetch}")
    #     returnbuild_alert_query
    #     # raise ValueError("max_fetch is not decimal")
    #     text = ''
    #     text += f"validation_definition.parameters[max_fetch] = {str(validation_definition.parameters['max_fetch'])}"
    #     text += f"{type(str(validation_definition.parameters['max_fetch']))}"
    #
    #     for p in validation_definition.parameters:
    #         text += f"[Varonis][Logger] validation_definition.parameter = {json.dumps(p)}"
    #     max_fetch = str(validation_definition.parameters["max_fetch"])
    #     if not max_fetch.isdecimal():
    #         raise ValueError(f"max_fetch is not decimal. max_fetch = {text}")


if __name__ == "__main__":
    input = varonismodularinput()
    sys.exit(varonismodularinput().run(sys.argv))

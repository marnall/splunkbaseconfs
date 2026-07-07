"""This module contains the data collection logic for insights."""
import ta_safebreach_declare  # noqa: F401

import json
import time
import datetime

from ta_safebreach_api_client import APIClient
from ta_safebreach_errors import APIError, StopExecutionError

remediation_mapping = {
    "Protocol": "protocol",
    "Port": "port",
    "Command": "command",
    "SHA256": "sha256",
    "FQDN/IP": "fqdn_ip",
    "URI": "uri",
    "Attack": "attack",
}


class InsightsCollector(object):
    """Insights collector."""

    def __init__(self, helper, ew):
        """Initialize Env."""
        self.helper = helper
        self.event_writer = ew
        self.input = helper.get_input_stanza_names()
        self.index = helper.get_arg('index')
        self.account = helper.get_arg('safebreach_account')
        self.account_id = self.account.get('account_id')
        self.api_key = self.account.get('api_token')
        self.account_name = self.account.get('name')
        self.start_time = helper.get_arg('start_date_time')
        self.check_point_key = "{}_{}_".format(self.account_name, self.input) + "insights"
        self.check_point = helper.get_check_point(self.check_point_key)

        self.session_key = self.helper.context_meta["session_key"]
        self.insights_client = APIClient(self.session_key, self.helper)
        self.header = {
            'x-apitoken': self.api_key,
            'accept': 'application/json',
            'content-type': 'application/json'
        }

    def get_parameters(self, plun_run_id):
        """Return parameter required for the request."""

        params = {
            "type": "actionBased",
            "filters":[{"key":"runId","value":[str(plun_run_id)]}],
        }
        return json.dumps(params)

    def get_epoch_time(self, date_time):
        """Convert datetime object to epoch time."""
        try:
            utc_time = datetime.datetime.strptime(date_time, r"""%Y-%m-%dT%H:%M:%S.%fZ""")
            epoch_time = (utc_time - datetime.datetime(1970, 1, 1)).total_seconds()
            return epoch_time
        except Exception:
            return None

    def get_plan_run_id(self, response_summaries, starttime, endtime):
        """Return runid for the testsummaries response."""
        runIds = []
        starttime = self.get_epoch_time(starttime)
        endtime = self.get_epoch_time(endtime)
        for response in response_summaries:
            time_ = response["endTime"]
            time_ = time_ / 1000
            if (time_ > starttime and time_ <= endtime):
                runIds.append(response["runId"])
            else:
                break
        return runIds

    def get_test_name(self, response_summaries, run_id):
        """Return testName for given test summaries run id."""
        for response in response_summaries:
            if response["runId"] == run_id:
                return response["planName"]


    def extract_fields(self, event):
        """Extract reemediation data fields."""
        if len(event.get("remediationInfo", {}).get("remediationData", {})) == 0:
            return event
        for data in event["remediationInfo"]["remediationData"].keys():
            if not (remediation_mapping.get(data)):
                continue
            event[remediation_mapping.get(data)] = list(event["remediationInfo"]["remediationData"][data].keys())
        return event

    def get_test_end_time(self, response_summaries, run_id):
        """Return testName for given test summaries run id."""
        for response in response_summaries:
            if response["runId"] == run_id:
                dt = datetime.datetime.utcfromtimestamp(response["endTime"]/1000)
                iso_format = dt.isoformat() + 'Z'
                return iso_format

    def collect_data(self):
        """Collect and ingest insights data to the splunk."""
        start_time = self.start_time
        end_time = ((datetime.datetime.utcnow()).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))[:-4] + "Z"
        checkpoint = self.helper.get_check_point(self.check_point_key)
        start_time = checkpoint or start_time
        self.helper.log_info(
            "Start_time: {} and end time: {} before data collection  ".format(
                start_time, end_time
            )
        )
        self.helper.log_info("Data Collection Started")
        self.helper.log_info("Insights collector checkpoint value is :{}".format(checkpoint))

        self.params_summaries = {
            "status": "canceled|completed",
        }
        response_summaries = self.insights_client.get_summaries(self.params_summaries, self.header, self.account_id)

        events = 0
        elapsed_time_event_collection = 0

        try:
            start_event_collection_time = time.time()
            plan_run_ids = self.get_plan_run_id(response_summaries, start_time, end_time)
            if len(plan_run_ids) <= 0:
                raise StopExecutionError()
            for plan_run_id in plan_run_ids:
                params = self.get_parameters(plan_run_id)
                self.helper.log_debug("Parameters before api call is {}".format(params))
                response_insights = self.insights_client.get_insights_data(params, self.header, self.account_id)  # noqa: E501

                for response_insight in response_insights:
                    ruler_id = response_insight["ruleId"]
                    remediation_payload = {"planRunIds": [plan_run_id]}
                    response_remediation = self.insights_client.get_remediation_data(json.dumps(remediation_payload), self.header, self.account_id, ruler_id)  # noqa: E501
                    self.helper.log_debug(f"Fetched remedaiton data for {plan_run_id}")
                    response_insight["remediationInfo"] = response_remediation
                    response_insight = self.extract_fields(response_insight)
                    response_insight['test_name'] = self.get_test_name(response_summaries, plan_run_id)
                    response_insight['test_id'] = plan_run_id
                    remediation_data_type = response_insight.get('mitigationPoints').get('key').lower()
                    response_insight['remediationDataType'] = remediation_data_type
                    response_insight['remediationDataCount'] = response_insight.get('mitigationPoints').get('value')
                    response_insight['remediationData'] = response_insight.get(remediation_data_type)
                    response_insight['affectedTargetCount'] = len(response_insight.get('targets', 0))
                    response_insight['testEndTime'] = self.get_test_end_time(response_summaries, plan_run_id)
                    response_data = json.dumps(response_insight)
                    event = self.helper.new_event(
                        source=self.helper.get_input_type(),
                        index=self.index,
                        sourcetype=self.helper.get_sourcetype(),
                        data=response_data
                    )
                    self.event_writer.write_event(event)
                    events += 1

            checkpoint = end_time
            self.helper.save_check_point(self.check_point_key, checkpoint)
            elapsed_time_event_collection = (time.time() - start_event_collection_time)
        except StopExecutionError:
            pass
        except APIError as e:
            self.helper.log_error("Exception occured while calling API: {}".format(e))
        except Exception as e:
            import traceback
            self.helper.log_error(traceback.format_exc(e))
        finally:
            self.helper.save_check_point(self.check_point_key, checkpoint)
            self.helper.log_info("Data collection completed")
            self.helper.log_info("Total events collected are {}".format(events))
            self.helper.log_info("Time elapsed in data collection is {}".format(elapsed_time_event_collection))
            self.helper.log_info("Checkpointvalue is {}".format(checkpoint))

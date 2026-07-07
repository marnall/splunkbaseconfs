"""This module contains the data collection logic for audit."""
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


class AuditCollector(object):
    """Audit collector."""

    def __init__(self, helper, ew):
        """Initialize Env."""
        self.helper = helper
        self.event_writer = ew
        self.input = helper.get_input_stanza_names()
        self.index = helper.get_arg('index')
        self.account = helper.get_arg('safebreach_account')
        self.api_key = self.account.get('api_token')
        self.account_name = self.account.get('name')
        self.start_time = helper.get_arg('start_date_time')
        self.check_point_key = "{}_{}_".format(self.account_name, self.input) + "audit"
        self.check_point = helper.get_check_point(self.check_point_key)

        self.session_key = self.helper.context_meta["session_key"]
        self.audit_client = APIClient(self.session_key, self.helper)
        self.header = {
            'x-apitoken': self.api_key,
            'accept': 'application/json',
            'content-type': 'application/json'
        }

    def get_epoch_time(self, date_time):
        """Convert datetime object to epoch time."""
        try:
            utc_time = datetime.datetime.strptime(date_time, r"""%Y-%m-%dT%H:%M:%S.%fZ""")
            epoch_time = (utc_time - datetime.datetime(1970, 1, 1)).total_seconds()
            return int(epoch_time)
        except Exception:
            return None

    def try_parse(self, obj, path):
        if not obj[path]:
            return
        try:
            obj[path] = json.loads(obj[path])
        except Exception as e:
            import traceback
            self.helper.log_error(traceback.format_exc(e))

    def collect_data(self):
        """Collect and ingest audit data to the splunk."""
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
        self.helper.log_info("Audit collector checkpoint value is :{}".format(checkpoint))

        self.params_audit = {
            "timestamp_from": self.get_epoch_time(start_time),
            "timestamp_to": self.get_epoch_time(end_time),
        }
        response = self.audit_client.get_audit_log(self.params_audit, self.header)

        events = 0
        elapsed_time_event_collection = 0

        try:
            start_event_collection_time = time.time()
            for log in response["data"]:
                self.try_parse(log, "metadata")
                self.try_parse(log, "originalParams")
                response_data = json.dumps(log)
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

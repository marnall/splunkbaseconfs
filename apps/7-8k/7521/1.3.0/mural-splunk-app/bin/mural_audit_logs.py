import sys
import os
import json
import base64
import requests
import time
from datetime import datetime, timedelta
import configparser
import splunklib.client as client
import splunklib.modularinput as smi

MURAL_AUDIT_LOG_API_URL = "https://api.mural.co/enterprise/v1/audit-log"
TIME_RANGE_HOURS = 48
MAX_RESULTS = 10000
RATE_LIMIT_INTERVAL = 20
ISO_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
LOG_PREFIX = "mural_audit_logs: "
LAST_EVENT_TIME = "last_event_time"
RUN_LIMIT_MINUTES = 55
LEGACY_CHECKPOINT_FILE_NAME = "checkpoint.json"
CHECKPOINT_FILE_PREFIX = "checkpoint"


def get_app_info():
    """Read information from the app.conf file.

    Returns:
        tuple: A tuple of (app_id, app_version) from app.conf, or (None, None) if not found.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(script_dir)
    app_conf_path = os.path.join(app_dir, "default", "app.conf")

    config = configparser.ConfigParser()
    if os.path.exists(app_conf_path):
        config.read(app_conf_path)
        try:
            app_id = config.get("package", "id")
            app_version = config.get("launcher", "version")
            return (app_id, app_version)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return (None, None)
    return (None, None)


class MuralModularInput(smi.Script):
    """All modular inputs should inherit from the abstract base class Script
    from splunklib.modularinput.script.
    They must override the get_scheme and stream_events functions, and,
    if the scheme returned by get_scheme has Scheme.use_external_validation
    set to True, the validate_input function.
    """

    def __init__(self):
        super().__init__()
        self.app_id, self.app_version = get_app_info()

    def get_scheme(self):
        """When Splunk starts, it looks for all the modular inputs defined by
        its configuration, and tries to run them with the argument --scheme.
        Splunkd expects the modular inputs to print a description of the
        input in XML on stdout. The modular input framework takes care of all
        the details of formatting XML and printing it. The user need only
        override get_scheme and return a new Scheme object.

        :return: scheme, a Scheme object
        """
        scheme = smi.Scheme("Mural Audit Logs")
        scheme.description = "A modular input for retrieving audit logs from Mural."
        scheme.use_external_validation = True
        scheme.use_single_instance = (
            True  # Set to True so we just have one instance of the modular input running with one interval
        )
        # https://docs.splunk.com/Documentation/Splunk/9.4.1/AdvancedDev/ModInputsStream
        scheme.streaming_mode = smi.Scheme.streaming_mode_xml

        desc_arg = smi.Argument("description")
        desc_arg.title = "Description"
        desc_arg.data_type = smi.Argument.data_type_string
        desc_arg.description = ""
        desc_arg.required_on_create = False
        scheme.add_argument(desc_arg)
        return scheme

    def validate_input(self, validation_definition):
        """When using external validation, after splunkd calls the modular input with
        --scheme to get a scheme, it calls it again with --validate-arguments for
        each instance of the modular input in its configuration files, feeding XML
        on stdin to the modular input to do validation. It is called the same way
        whenever a modular input's configuration is edited.

        :param validation_definition: a ValidationDefinition object

        """
        ## Make sure API Key is set and is valid
        session_key = validation_definition.metadata["session_key"]
        service = client.connect(token=session_key)
        api_key = self.get_api_key(service)
        if api_key is None:
            raise ValueError(LOG_PREFIX + "No API KEY set, set API Key for the Mural app")

    def stream_events(self, inputs, ew):
        """This function handles all the action: splunk calls this modular input
        without arguments, streams XML describing the inputs to stdin, and waits
        for XML on stdout describing events.

        Since we used single instance, it will pass all the instances of this input to a single instance of this
        script.

        :param inputs: an InputDefinition object
        :param event_writer: an EventWriter object
        """

        input_configs = inputs.inputs
        ew.log("INFO", LOG_PREFIX + "Started with the following metadata: %s" % inputs.metadata)
        ew.log("INFO", LOG_PREFIX + "Started with the following input: %s" % input_configs.items())

        # If there are no inputs, return
        # This is just to make sure we don't fetch logs without creation of inputs
        if not list(inputs.inputs.items()):
            ew.log("INFO", LOG_PREFIX + "No inputs found! Exiting.")
            return

        checkpoint_dir = inputs.metadata["checkpoint_dir"]

        try:
            ## Get API Key
            service = self.service
            api_key = self.get_api_key(service)
            if api_key is None:
                ew.log("ERROR", LOG_PREFIX + "API key not found. Please set the API key in the Mural app.")
                return
            ew.log("INFO", LOG_PREFIX + "API key retrieved successfully.")

            ## Fetch and send logs (main function)
            self.fetch_and_send_logs(ew, input_configs, api_key, checkpoint_dir)

        except Exception as e:
            ew.log("ERROR", LOG_PREFIX + f"An error occurred: {str(e)}")

    def get_api_key(self, service):
        storage_passwords = service.storage_passwords
        api_key = None
        for storage_password in storage_passwords.list():
            if storage_password.username == "api_key" and storage_password.realm == "mural_realm":
                api_key = storage_password.clear_password
                break
        return api_key

    def fetch_and_send_logs(self, ew, inputs, api_key, checkpoint_dir):
        start_time = datetime.utcnow()

        for input_name, input_item in inputs.items():
            ew.log("INFO", LOG_PREFIX + "Processing input: %s" % input_name)

            last_event_time = self.get_checkpoint(checkpoint_dir, input_name, ew)
            ew.log("INFO", LOG_PREFIX + "Input %s last checkpoint time is: %s" % (input_name, last_event_time))

            since, until = self.get_time_range(last_event_time)
            next_token = None

            updated_last_event_time = None

            while True:
                if (datetime.utcnow() - start_time).total_seconds() / 60 > RUN_LIMIT_MINUTES:
                    ew.log("INFO", LOG_PREFIX + "Script run time limit reached, exiting.")
                    return

                ew.log(
                    "INFO",
                    LOG_PREFIX
                    + "Input %s: Fetching Mural audit logs with time range: since=%s, until=%s"
                    % (input_name, since, until),
                )

                logs_data = self.fetch_audit_logs(api_key, MAX_RESULTS, since, until, next_token)
                logs = logs_data.get("data", [])

                if logs:
                    ew.log(
                        "INFO", LOG_PREFIX + "Input %s: Fetched %d logs. Sending to Splunk." % (input_name, len(logs))
                    )
                    self.send_to_splunk(ew, logs, input_name, input_item)

                    # Save checkpoint as the date of the first returned event (the most recent event)
                    if updated_last_event_time is None:
                        updated_last_event_time = logs[0]["date"]
                        self.save_checkpoint(checkpoint_dir, input_name, updated_last_event_time)

                next_token = logs_data.get("nextToken")

                if not next_token:
                    break
                ew.log(
                    "INFO",
                    LOG_PREFIX
                    + "Input %s: Next token found. Waiting for rate limit interval (%d seconds) before fetching next batch."
                    % (input_name, RATE_LIMIT_INTERVAL),
                )
                time.sleep(RATE_LIMIT_INTERVAL)

    def fetch_audit_logs(self, api_key, max_result, since=None, until=None, next_token=None):
        headers = {
            "Accept": "application/json",
            "Authorization": f"apikey {api_key}",
        }

        if self.app_id is not None and self.app_version is not None:
            headers["User-Agent"] = f"{self.app_id}/{self.app_version}"

        params = {
            "maxResults": max_result,
            **({"nextToken": next_token} if next_token else {}),
            **({"filter[date][since]": since} if since else {}),
            **({"filter[date][until]": until} if until else {}),
        }

        try:
            response = requests.get(MURAL_AUDIT_LOG_API_URL, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            raise ValueError(LOG_PREFIX + f"HTTP error occurred while fetching audit logs: {http_err}")
        except Exception as err:
            raise ValueError(LOG_PREFIX + f"An error occurred while fetching audit logs: {err}")

    def get_time_range(self, last_event_time):
        until = datetime.utcnow()
        if last_event_time:
            # adding 1 second to the last event time to avoid fetching the same event again
            since = datetime.strptime(last_event_time, ISO_TIMESTAMP_FORMAT) + timedelta(milliseconds=1000)
            # audit logs can't fetch date older than 30 days. If since is older than 30 days, set it to 30 days ago
            if since < until - timedelta(days=29):
                since = until - timedelta(days=29)
        else:
            since = until - timedelta(hours=TIME_RANGE_HOURS)
        return since.strftime(ISO_TIMESTAMP_FORMAT), until.strftime(ISO_TIMESTAMP_FORMAT)

    def send_to_splunk(self, ew, logs, input_name, input_item):
        ew.log("INFO", LOG_PREFIX + "Input %s: Writing fetched logs to Splunk." % input_name)
        index = input_item.get("index", None)
        host = input_item.get("host", None)
        sourcetype = input_item.get("sourcetype", None)

        for log in logs:
            event = smi.Event(
                stanza=input_name,
                data=json.dumps(log),
            )
            # Only set these if they are defined by user at the input
            if host and not host.startswith("$"):
                event.host = host
            if index:
                event.index = index
            if sourcetype:
                event.sourceType = sourcetype

            ew.write_event(event)

    def _encode_input_name(self, input_name):
        """Encode the input name to be used as a file name."""
        return base64.urlsafe_b64encode(input_name.encode()).decode().rstrip("=")

    def checkpoint_filename(self, checkpoint_dir, input_name):
        encoded_input_name = self._encode_input_name(input_name)
        filename = os.path.join(checkpoint_dir, f"{CHECKPOINT_FILE_PREFIX}-{encoded_input_name}.json")
        return filename

    def get_checkpoint(self, checkpoint_dir, input_name, ew):
        checkpoint_filename = self.checkpoint_filename(checkpoint_dir, input_name)

        # Backwards compatibility for old app versions:
        # Rename the legacy checkpoint file according to the new convention
        legacy_checkpoint_filename = os.path.join(checkpoint_dir, LEGACY_CHECKPOINT_FILE_NAME)
        if os.path.exists(legacy_checkpoint_filename) and not os.path.exists(checkpoint_filename):
            try:
                os.rename(legacy_checkpoint_filename, checkpoint_filename)
                ew.log("INFO", LOG_PREFIX + "Renamed legacy checkpoint file to for input: %s" % input_name)
            except Exception as e:
                ew.log("WARN", LOG_PREFIX + "Failed to rename legacy checkpoint file: %s" % str(e))

        if not os.path.exists(checkpoint_filename):
            return None

        with open(checkpoint_filename, "r") as f:
            data = json.load(f)
            return data.get(LAST_EVENT_TIME)

    def save_checkpoint(self, checkpoint_dir, input_name, last_event_time):
        checkpoint_filename = self.checkpoint_filename(checkpoint_dir, input_name)
        with open(checkpoint_filename, "w") as f:
            json.dump({LAST_EVENT_TIME: last_event_time}, f)


if __name__ == "__main__":
    sys.exit(MuralModularInput().run(sys.argv))

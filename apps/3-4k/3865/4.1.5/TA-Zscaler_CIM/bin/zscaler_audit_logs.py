import import_declare_test
import zsutils
import time
import json
import zscaler
import sys
from splunklib import modularinput as smi
from solnlib.modular_input import checkpointer
import solnlib.utils as sutils
import re
import pytz
from datetime import datetime
import os



def check_if_legacy_checkpoint_exists(input_name: str, session_key, server_uri, logger):
    """
    Replaces old checkpoint (if it exists) with new checkpoint format

    :param input_name:  Input stanza name
    :param session_key: Splunk session key
    :param server_uri:  URI of Splunk server
    :param logger:      Logger object
    """

    try:
        sscheme, shost, sport = sutils.extract_http_scheme_host_port(server_uri)
        checkpoint = checkpointer.KVStoreCheckpointer(zsutils.APP_NAME + "_checkpointer", session_key, zsutils.APP_NAME, scheme=sscheme, host=shost, port=sport)

        #legacy method was to create checkpoint with name "checkpoint".
        legacy_checkpoint = checkpoint.get("checkpoint")
        if legacy_checkpoint:
            logger.info(f"Legacy checkpoint detected at 'checkpoint'.")
            checkpoint.update(key=f"{input_name}_obj_checkpoint", state=legacy_checkpoint)
            checkpoint.delete(key="checkpoint")
            logger.info(f"Replaced legacy checkpoint 'checkpoint' with {input_name}_obj_checkpoint value: {legacy_checkpoint}")
        else:
            logger.debug("Legacy checkpoint does not exist")
    except Exception as ex:
        logger.debug(f"Legacy checkpoint does not exist")
        return


def get_checkpoint_starttime(input_name: str, server_uri, session_key, logger):
    """
    Gets the checkpoint value for starttime or if there is no checkpoint data,
    returns 7 days ago

    :param input_name: input stanza name
    :param server_uri: URI of Splunk server
    :param session_key: Splunk session key
    :param logger: logger object for logging messages
    :returns: epoch timestamp with in milliseconds
    """

    # If checkpoint key is in older format, upgrade
    check_if_legacy_checkpoint_exists(input_name, session_key, server_uri, logger)
    dscheme, dhost, dport = sutils.extract_http_scheme_host_port(server_uri)
    checkpoint = checkpointer.KVStoreCheckpointer(zsutils.APP_NAME + "_checkpointer", session_key, zsutils.APP_NAME, scheme=dscheme, host=dhost, port=dport)
    checkpoint_key = f"{input_name}_obj_checkpoint"
    starttime = checkpoint.get(checkpoint_key)

     #if we get no time for checkpoint default to 1 week ago
    if (not starttime):
        #set starttime a week ago, end time now
        logger.debug("Cant determine last execution time, using default [1 week ago]")
        startOffset = 604800
        starttime = int(round(time.time() * 1000)-startOffset)-1000
    else:
        # Check if checkpoint exceeds 30 days (API limit)
        thirtyDaysOffset = 2592000000  # 30 days in milliseconds
        thirtyDaysAgo = int(round(time.time() * 1000)) - thirtyDaysOffset

        if starttime < thirtyDaysAgo:
            logger.debug("Checkpoint starttime exceeds 30 day API limit. Resetting to 7 days ago.")
            sevenDaysOffset = 604800000  # 7 days in milliseconds
            starttime = int(round(time.time() * 1000)) - sevenDaysOffset - 1000

    return starttime


def get_endtime():
    """
    Retrieve the current time in milliseconds offset by 1 second

    :returns: current time offset by 1s in ms (int)
    """
    endtime = int(round(time.time() * 1000)) - 1000
    return endtime


def check_is_audit_report_ready(z, statusId, logger):
    """
    Polls the Zscaler API to check if the audit report is ready.   Checks the status of the
    report every 30 seconds until the report status changes from "EXECUTING" to another state

    :param z:        zscaler API object
    :param statusId: status ID from report generation response
    :param logger:   logger object for logging messages
    """

    status = z.check_audit_status(statusId)

    while status == "EXECUTING":
        logger.info(f"Looping.  Audit report still generating.   ServerSideStatus is {status}")
        time.sleep(30)
        status = z.check_audit_status(statusId)
    logger.info(f"Audit report generated.  ServerSideStatus is {status}")
    return


def get_timestamp(logger, input_text, timezone_mapping):
    """
    Extracts timestamp from input text.

    :param logger: logger object
    :param input_text: input text string
    :param timezone_mapping: dict of timezone mappings

    :returns: timestamp in epoch format or None if an error occurs
    """

    match = re.search(r'"Time": "([^"]+)"', input_text)
    if not match:
        return None

    date_string = match.group(1)

    try:
        # Split date from tz
        date_part, tz_abbr = date_string.rsplit(', ', 1)

        # Parse the date part into a datetime object
        dt = datetime.strptime(date_part, "%d %b %Y %H:%M:%S")

        # Convert the timezone abbreviation to a pytz timezone

        if tz_abbr in timezone_mapping:
            tz_name = timezone_mapping[tz_abbr]
            try:
                tz = pytz.timezone(tz_name)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.error(f"Unknown timezone: {tz_name}.   Using UTC")
        else:
            logger.warning("Timezone not found in timezone mapping (timezone.list).   Using UTC")

        if not tz:
            tz = pytz.timezone("UTC")

        # Localize the datetime object with the correct timezone
        dt = tz.localize(dt)

        # Convert the datetime object to a timestamp
        timestamp = dt.timestamp()

    except Exception as ex:
        return None

    return timestamp


def get_timezone_mappings(logger, filename="timezone.list"):
    """
    Reads timezone mappings from a timezone.list file

    :param logger: logger object
    :param filepath: path to timezone.list file

    :returns: dict of timezone mappings or None if an error occurs
    """

    try:
        timezone_mappings = {}
        filepath = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), filename)
        with open (filepath, "r") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split(":")
                    if len(parts) == 2:
                        abbr = parts[0].strip()
                        tz_name = parts[1].strip()
                        timezone_mappings[abbr] = tz_name
        logger.debug(f"Successfully loaded timezone mapping: {timezone_mappings}")
        return timezone_mappings
    except FileNotFoundError:
        logger.error(f"Timezone mapping file '{filepath}' not found")
        return None
    except Exception as e:
        logger.error(f"Error reading timezone mappings: {e}")
        return None


def process_audit_report(logger, ew, report_json, index, input_name):
    """Processes the audit report creating events in the Splunk index

    :param logger:      Logger object
    :param ew:          Splunk Event Writer object
    :param report_json: JSON from zscaler report
    :param index:       Target Splunk index
    :param input_name:  Input stanza name

    :returns:           count of events ingested
    """

    count = 0
    logger.debug(f"Loading report: {report_json} to JSON logs")
    logs = json.loads(report_json)

    TIMEZONE_MAPPING  = get_timezone_mappings(logger)
    if TIMEZONE_MAPPING is None:
        # If no TIMEZONE_MAPPING is found, use a default mapping
        TIMEZONE_MAPPING = {
            "PST": "US/Pacific",
            "PDT": "US/Pacific",
            "EST": "US/Eastern",
            "EDT": "US/Eastern",
            "CST": "US/Central",
            "CDT": "US/Central",
            "MST": "US/Mountain",
            "MDT": "US/Mountain",
            "UTC": "UTC",
            "GMT": "GMT",
        }
    logger.debug(f"Loaded JSON logs: {logs}")
    for log in logs:

        try:
            eventdata = json.dumps(log)
            timestamp = get_timestamp(logger=logger, input_text=eventdata, timezone_mapping=TIMEZONE_MAPPING)

            event = smi.Event(data=eventdata, time=timestamp, stanza=input_name, index=index,
                            sourcetype="zscalerapi-zia-audit")
            ew.write_event(event)
            count += 1
        except Exception as ex:
            logger.error(f"Error processing event: {ex}")
            continue
    return count


def write_checkpoint(endtime, input_name, session_key, server_uri, logger):
    """Writes checkpoint value to Splunk KVstore checkpoint

    :param endtime:        epoch date in milliseconds (int)
    :param input_name:     input stanza name (str)
    :param session_key:    Splunk session key (str)
    :param server_uri:     Splunk server uri (str)
    :param logger:         logger object (logging.logger)
    :returns: True on success, False on failure
    """

    checkpoint_key = f"{input_name}_obj_checkpoint"
    dscheme, dhost, dport = sutils.extract_http_scheme_host_port(server_uri)
    checkpoint = checkpointer.KVStoreCheckpointer(zsutils.APP_NAME + "_checkpointer", session_key, zsutils.APP_NAME, scheme=dscheme, host=dhost, port=dport)

    try:
        checkpoint.update(key=checkpoint_key, state=endtime)
        logger.info(f"Checkpoint key {checkpoint_key} updated with value {endtime}")
        return True
    except Exception as ex:
        logger.error(f"Failed to write checkpoint key.   {ex}")
        return False


class ZSCALER_AUDIT_LOGS(smi.Script):
    """ Splunk Modular input script to retrieve audit events from the Zscaler API """

    def get_app_name(self):
        return "zscaler_audit_logs"


    def validate_input(helper, definition):
        """
        Input validation is done on the globalConfig.json field definitions
        and is not required here.
        """
        pass


    def __init__(self):
        super(ZSCALER_AUDIT_LOGS, self).__init__()


    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        """
        Collect events from the Zscaler Audit API.  This function:
              - Gets the last checkpoint value from Splunk and sets it as starttime (or
                 sets the starttime to 7 days ago if no checkpoint exists).
              - Opens a connection to the Zscaler API and retrieves all audit logs from
                 the starttime to the current time
              - Ingests the returned logs as Splunk events into the "zscalerapi-zia-audit"
                 sourcetype

        :param self:    ZSCALER_AUDIT_LOGS class instance
        :param inputs:  Input definition object (modularinput.inputdefinition)
        :param ew:      Splunk Eventwriter (modularinput.EventWriter)
        """

        #Retrieve Splunk Session Key from input definition metadata
        meta_configs = self._input_definition.metadata
        session_key = meta_configs["session_key"]

        # Get input name and input items
        input_name, input_items = zsutils.get_input_name_and_items(inputs)
        script_path = sys.argv[0]
        script_dir = os.path.dirname(script_path)

        # Create logger object
        logger = zsutils.create_logger(input_name, session_key)
        logger.debug("zscaler_audit_logs -- modular input invoked.")

        # Retrieve input item values
        cloud = input_items.get("cloud")
        index = input_items.get("index")
        global_account = input_items.get("global_account")
        account_config = zsutils.get_account_config(session_key, global_account, logger)
        username = account_config['username']
        password = account_config['password']
        api_key = account_config['api_key']

        # Create Zscaler API object
        z = zscaler.zscaler()

        #Set Proxies, if set in the TA UI
        proxies = zsutils.get_proxy_config(session_key, logger)
        if proxies['proxy_url']:
            logger.debug("setting proxy: " + json.dumps(proxies))
            z.proxies = {
                "http": proxies['proxy_url'] + ":" + proxies['proxy_port'],
                "https": proxies['proxy_url'] + ":" + proxies['proxy_port']
            }

        #load starttime from checkpoint file
        starttime = get_checkpoint_starttime(input_name, meta_configs["server_uri"], session_key, logger)
        endtime = get_endtime()

        if not zsutils.zscaler_api_login(z, username, password, api_key, cloud, logger):
            return
        else:
            logger.info(f"Zscaler Login Success to cloud {cloud}")

        try:
            # Get Audit Report

            #Generate Report
            logger.info("Generating Zscaler Audit Report: " + str(starttime) + "-" + str(endtime))
            generate = z.generate_audit_report(starttime, endtime)
            logger.debug(f"Request sent to create zscaler audit report status: {generate.status_code}")
            if generate.status_code == 429:
                retry_after_seconds = int(json.loads(generate.text)["Retry-After"].split()[0])
                logger.info(f"Rate limited.  Waiting {retry_after_seconds} seconds before retrying")
                time.sleep(retry_after_seconds + 2)
                generate = z.generate_audit_report(starttime, endtime)

            if not (generate.status_code >= 200 and generate.status_code < 300):
                logger.error("Error generating ZScaler audit report.   Status code: " + str(generate.status_code))
                return

            logger.info("ZScaler audit report generated status(" + str(generate.status_code) + ") :" + str(generate.text))

            # Extract statusId from response
            generate_json = json.loads(generate.text)
            statusId = generate_json.get('statusId')
            if not statusId:
                logger.error("statusId not found in report generation response")
                return
            logger.debug(f"Captured statusId: {statusId}")

            check_is_audit_report_ready(z, statusId, logger)
            audit_report = z.get_audit_report(statusId, "json")
            logger.info(f"Audit report retrieved.   {len(audit_report)} events found")

            events_processed = process_audit_report(logger, ew, audit_report, index, input_name)
            logger.info(f"Audit report processed.   There were {events_processed} created")
            if write_checkpoint(endtime, input_name, session_key, meta_configs["server_uri"], logger):
                logger.debug("Complete.  Checkpoint saved.")
            else:
                logger.error(f"Error writing to checkpoint")

        finally:
            if z.logout():
                logger.info("Zscaler audit logs session closed successfully")
            else:
                logger.warning("Zscaler logout returned non-200 status, but session cleared locally")

        return


    def get_scheme(self):
        """
        Returns a Splunk Modular Input scheme object.

        This function defines the configuration schema for a Splunk Modular Input
        that pulls audit logs from the ZScaler API.

        Returns:
            smi.Scheme: A Splunk Modular Input scheme object.
        """

        scheme = smi.Scheme("Splunk Add on for ZScaler Audit Logs")
        scheme.description = "Modular input to pull audit logs from the ZScaler API"

        # Enable external validation for the input
        scheme.use_external_validation = True

        # Enable streaming mode for the input
        scheme.streaming_mode_xml = True

        # Allow multiple instances of this input to run simultaneously
        scheme.use_single_instance = False

        # Add required arguments to the scheme
        scheme.add_argument(smi.Argument('name',
                                        title='Name',
                                        description='Input Name',
                                        required_on_create=True))

        scheme.add_argument(smi.Argument('cloud',
                                        title='cloud',
                                        description='Zscaler cloud',
                                        required_on_create=True,
                                        required_on_edit=True))

        scheme.add_argument(smi.Argument('global_account',
                                        title='global_account',
                                        description='Global Account',
                                        required_on_create=True,
                                        required_on_edit=True))

        return scheme


if __name__ == '__main__':
    exit_code = ZSCALER_AUDIT_LOGS().run(sys.argv)
    sys.exit(exit_code)
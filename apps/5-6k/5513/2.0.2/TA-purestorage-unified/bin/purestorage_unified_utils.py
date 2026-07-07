import os
import io
import json
import time
import calendar
import requests
from solnlib.utils import is_true
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import six.moves.configparser
from splunk.clilib.bundle_paths import make_splunkhome_path
from ta_purestorage_unified_declare import ta_name
from solnlib import conf_manager

UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
UTC_FORMAT_WITHOUT_FLOAT = "%Y-%m-%dT%H:%M:%SZ"

LIMIT = 1000
MAX_WORKER_THREADS = 4
REQUEST_TIMEOUT = 180  # in seconds
PURE1_COLLECT_DATA_OF = ["flasharray", "flashblade"]
APP_NAME = os.path.basename(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
SETTING_CONF_FILE = "ta_purestorage_unified_settings"
PURESTORAGE_ADDITIONAL_PARAMETERS = "purestorage_additional_parameters"


def requests_retry_session(
    retries=3,
    backoff_factor=5,
    status_forcelist=list(range(500, 600)) + [429, ]
):
    """
    Create and return a session object with retry mechanism.

    :param retries: Maximum number of retries to attempt
    :param backoff_factor: Backoff factor used to calculate time between retries. e.g. For 10 - 5, 10, 20, 40,...
    :param status_forcelist: A tuple containing the response status codes that should trigger a retry.

    :return: Session Object
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def performance_endpt_checkpoint(helper, sourcetype, endpoint, metrics_ids, config_details, opt="GET", value=None):
    """
    Function to initialize checkpoint for performance/space endpoints sourcetype of particular input.

    :param helper: object of BaseModInput class
    :param sourcetype: Splunk Sourcetype to get checkpoint
    :param endpoint: REST endpoint to get data
    :param metrics_ids: IDs of endpoints for which we want performance/space data
    :param config_details: Basic configuration details
    :param opt: Get or update checkpoint
    :param value: Value to be given for checkpoint key
    """
    sourcetype = sourcetype.split(":")[-1]
    endpoint = endpoint.split("/")[-1]
    stanza_name = config_details.get('stanza')

    checkpoint_name = stanza_name + "_" + sourcetype + "_" + endpoint + "_" + metrics_ids

    if opt == "GET":
        checkpoint_time = helper.get_check_point(checkpoint_name)
        date_7d_ago = config_details.get('end_date') - (7 * 86400 * 1000)
        start_date = helper.get_arg('start_date')

        if checkpoint_time:
            start_date = checkpoint_time
        elif start_date:
            time_pattern = "%Y-%m-%dT%H:%M:%SZ"
            start_date = calendar.timegm(
                time.strptime(start_date, time_pattern))
            start_date = int(start_date * 1000)
        else:
            helper.log_warning(
                "type={type} name={sname} msg=Collecting {edpt} of"
                " last 7 days".format(type=config_details["input_type"], sname=config_details["stanza"], edpt=endpoint))
            return date_7d_ago

        if start_date > date_7d_ago:
            return start_date
        else:
            helper.log_warning(
                "type={type} name={sname} msg=Start date is older than 7 days. "
                "Collecting {edpt} for ID: {metrics_ids} of last 7 days".
                format(type=config_details["input_type"],
                       sname=config_details["stanza"], edpt=endpoint, metrics_ids=metrics_ids))
            return date_7d_ago
    else:
        helper.log_debug("type={type} name={sname} msg=PureStorage Debug: "
                         "Checkpoint updated for {name}: {value}".format(
                             type=config_details["input_type"],
                             sname=config_details["stanza"], name=checkpoint_name, value=value))
        helper.save_check_point(checkpoint_name, value)


def reset_time_to_7d(helper, config_details, new_start_date, endpoint):
    """
    Function to initialize checkpoint for particular sourcetype of particular input.

    :param helper: object of BaseModInput class
    :param config_details: Basic configuration details
    :param new_start_date: If its less than 7 days then return epoch time of last 7days
    :param endpoint: REST endpoint to get data
    """
    date_7d_ago = config_details.get('end_date') - (7 * 86400 * 1000)
    if new_start_date < date_7d_ago and not config_details['collect_historical_data']:
        new_start_date = date_7d_ago
        helper.log_warning(
            "type={} name={} msg=Collecting data of last 7 days"
            " for endpoint {} from {}.".format(config_details["input_type"],
                                               config_details["stanza"], endpoint, new_start_date))
    else:
        helper.log_warning(
            "type={} name={} msg=Collecting data"
            " of endpoint {} from {}.".format(config_details["input_type"],
                                              config_details["stanza"], endpoint, new_start_date))

    return new_start_date


def get_checkpoint(helper, config_details, sourcetype, endpoint, space_perf=None):
    """
    Function to initialize checkpoint for particular sourcetype of particular input.

    :param helper: object of BaseModInput class
    :param config_details: Basic configuration details
    :param sourcetype: Splunk Sourcetype to get checkpoint
    :param endpoint: REST endpoint to get data
    """
    endpoint_list = ["purestorage:flasharray:volumes", "purestorage:flasharray:snapshots",
                     "purestorage:flashblade:inventory", "purestorage:pure1:buckets", "purestorage:pure1:policies",
                     "purestorage:pure1:objectstore_inventory", "purestorage:pure1:snapshots",
                     "purestorage:pure1:filesystem_inventory", "purestorage:pure1:health"]
    logs_endpoint_list = ["purestorage:flasharray:alerts", "purestorage:flasharray:audits",
                          "purestorage:flasharray:login"]

    stanza_name = config_details.get('stanza')
    sourcetype_original = sourcetype
    sourcetype = sourcetype.split(":")[-1]
    endpoint = endpoint.split("/")[-1]
    checkpoint_name = stanza_name + "_" + sourcetype + "_" + endpoint

    # Store diff checkpoints for FA API v2
    if space_perf:
        checkpoint_name = checkpoint_name + "_" + space_perf

    start_date = helper.get_arg('start_date')
    if start_date:
        time_pattern = "%Y-%m-%dT%H:%M:%SZ"
        start_date = calendar.timegm(
            time.strptime(start_date, time_pattern))
        start_date = int(start_date * 1000)
    else:
        start_date = config_details.get('end_date') - (
            7 * 86400 * 1000)  # 7 Days in Milliseconds
    checkpoint_time = helper.get_check_point(checkpoint_name)

    try:
        config_details['offset'] = checkpoint_time.get('offset', 0)
        checkpoint_time = checkpoint_time.get('end_date')
        config_details['offset_in_checkpoint'] = True
    except Exception:
        config_details['offset'] = 0

    new_start_date = checkpoint_time if checkpoint_time else start_date
    if sourcetype_original in endpoint_list:
        new_start_date = checkpoint_time if checkpoint_time else None

    if config_details.get('major_api_version') == 2:
        if sourcetype_original == "purestorage:flasharray:volumes":
            new_start_date = checkpoint_time if checkpoint_time else start_date
        if checkpoint_time and sourcetype_original in logs_endpoint_list:
            # Set to True only when checkpoint is available
            config_details[sourcetype_original] = True
            new_start_date = checkpoint_time if checkpoint_time else start_date

    # For Alert/Audit/Session logs API v2.x checkpoint is either in File or Kvstore
    # So, keep same conditions in get_alert_audit_session_logs function

    final_start_date = new_start_date

    if new_start_date and config_details["input_type"] != "pure1" and sourcetype_original not in logs_endpoint_list:
        final_start_date = reset_time_to_7d(helper, config_details, new_start_date, endpoint)

    config_details['start_date'] = final_start_date
    config_details['checkpoint_name'] = checkpoint_name


def update_checkpoint(helper, config_details, store_offset=True):
    """
    Function to update checkpoint for particular sourcetype of particular input.

    :param helper: object of BaseModInput class
    :param config_details: Basic configuration details
    """
    end_date = config_details.get('end_date') if config_details.get(
        'chkpt_date', None) is None else config_details.get('chkpt_date')
    checkpoint_name = config_details.get('checkpoint_name')
    offset = config_details.get('offset', None)
    if offset is None or not store_offset:
        checkpoint_key = end_date
    else:
        checkpoint_key = {"end_date": end_date, "offset": offset}
    helper.save_check_point(checkpoint_name, checkpoint_key)
    helper.log_debug("type={type} name={sname} msg=PureStorage Debug: Checkpoint updated for {name}: {value}".format(
        name=checkpoint_name, value=checkpoint_key, type=config_details["input_type"], sname=config_details["stanza"]))


def ingest_in_splunk(helper, ew, records, sourcetype,
                     additional_fields, source=None, config_details=None):
    """
    Ingests Records to Splunk.

    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param records: Records to be ingested in Splunk
    :param sourcetype: Sourcetype for Splunk Ingestion
    :param additional_fields: Dictionary of required fields to be added in record.
    """
    updated_additional_list = update_additional_fields(
        additional_fields)
    as_of_field_endpoints = ["purestorage:pure1:filesystems", "purestorage:pure1:flasharray:array",
                             "purestorage:pure1:flasharray:pods", "purestorage:pure1:flasharray:snapshots",
                             "purestorage:pure1:flasharray:volumes", "purestorage:pure1:flashblade:array",
                             "purestorage:pure1:flashblade:health", "purestorage:pure1:flashblade:inventory"]

    is_pure1_sourcetype = False if sourcetype.split(":")[1] != "pure1" else True
    for record in records:
        record.update(updated_additional_list)
        if sourcetype == "purestorage:flashblade:alerts":
            record['alert_index'] = record.pop('index', None)
        if 'source' in record:
            if is_pure1_sourcetype:
                record['pure1_source'] = record.pop('source')
            else:
                record['file_system_source'] = record.pop('source')
        index_time = record.get(additional_fields.get('time_field'))
        if 'host' in additional_fields:
            host = additional_fields['host']
        else:
            host = None
        if index_time:
            if not is_time_format(index_time):
                index_time = int(
                    index_time) / 1000.0
            else:
                index_time = convert_to_epoch(index_time)
        else:
            index_time = time.time()
        if is_pure1_sourcetype and 'arrays' in record and isinstance(record['arrays'], list):
            print_record = record.copy()
            print_record.pop('arrays')
            for record_arrays in record['arrays']:
                for key, value in record_arrays.items():
                    print_record["array_{}".format(key)] = value
                event = helper.new_event(time=index_time,
                                         index=helper.get_output_index(),
                                         sourcetype=sourcetype,
                                         source=source,
                                         data=json.dumps(print_record), host=host)
                ew.write_event(event)
        else:
            event = helper.new_event(time=index_time,
                                     index=helper.get_output_index(),
                                     sourcetype=sourcetype,
                                     source=source,
                                     data=json.dumps(record), host=host)
            ew.write_event(event)
        if config_details:
            if sourcetype == "purestorage:pure1:alerts":
                config_details["chkpt_date"] = record["updated"]
            elif sourcetype == "purestorage:pure1:audits":
                config_details["chkpt_date"] = record["time"]
            elif sourcetype == "purestorage:flasharray:alerts":
                config_details["chkpt_date"] = record["updated"]
            elif sourcetype == "purestorage:flasharray:audits":
                config_details["chkpt_date"] = record["time"]
            elif sourcetype == "purestorage:flasharray:login":
                config_details["chkpt_date"] = record["start_time"]
            elif sourcetype in as_of_field_endpoints:
                config_details["chkpt_date"] = record["_as_of"]


def update_additional_fields(additional_fields):
    """
    Function returns list of fields to be added to records ingested in splunk.

    :params additional_fields: Dictionary of additional fields that can be ingested to splunk with records
    :return dictionary of relevant fields to be ingested in splunk with records
    """
    updated_additional_list = {}
    if 'array_name' in additional_fields:
        updated_additional_list['array_name'] = additional_fields.get(
            'array_name')
    if 'array_id' in additional_fields:
        updated_additional_list['array_id'] = additional_fields.get(
            'array_id')
    if 'storage_protocol' in additional_fields:
        updated_additional_list[
            'storage_protocol'] = additional_fields.get('storage_protocol')
    if 'storage_type' in additional_fields:
        updated_additional_list['storage_type'] = additional_fields.get(
            'storage_type')
    if 'file_system_snapshots' in additional_fields:
        updated_additional_list[
            'file_system_snapshots'] = additional_fields.get(
                'file_system_snapshots')
    return updated_additional_list


def is_time_format(input):
    """Check if string is in time format."""
    try:
        time.strptime(str(input), '%Y-%m-%dT%H:%M:%SZ')
        return True
    except ValueError:
        return False


def convert_to_epoch(input):
    """Convert datetime to epoch."""
    if is_time_format(input):
        date_time_obj = time.strptime(str(input), '%Y-%m-%dT%H:%M:%SZ')
        epoch = calendar.timegm(date_time_obj)
        return epoch
    else:
        return input


def format_proxy_uri(proxy_dict):
    """
    Function to get proxy uri in format of.

    <protocol>://<user_name>:<password>@<proxy_server_ip>:<proxy_port>

    :param proxy_dict: dict, Dictionary containing proxy information

    :return: proxy_uri: str, proxy uri in standard format
    """
    uname = requests.compat.quote_plus(proxy_dict.get('proxy_username', ''))
    passwd = requests.compat.quote_plus(proxy_dict.get('proxy_password', ''))
    protocol = proxy_dict.get('proxy_type')
    proxy_url = proxy_dict.get('proxy_url')
    proxy_port = proxy_dict.get('proxy_port')
    proxy_uri = "%s://%s:%s@%s:%s" % (protocol,
                                      uname, passwd, proxy_url, proxy_port)

    return proxy_uri


def get_conf_file(conf_file, app_name=ta_name, folder="local"):
    """Get the configured inputs details."""
    conf_parser = six.moves.configparser.ConfigParser()
    conf = os.path.join(make_splunkhome_path(
        ["etc", "apps", app_name, folder, conf_file]))
    stanzas = []
    if os.path.isfile(conf):
        with io.open(conf, 'r', encoding='utf_8_sig') as conffp:
            conf_parser.readfp(conffp)
        stanzas = conf_parser.sections()
    return conf_parser, stanzas


def input_with_account_exists(input_stanzas, input_parser_obj, account, input_type,
                              input_stanza_name, check_disabled=False, stanza_prefix="purestorage_unified_input://"):
    """Identify input configured with same system credentials."""
    input_name = None
    if check_disabled:
        for stanza in input_stanzas:
            if(
                stanza.startswith(stanza_prefix) and input_parser_obj.get(stanza, "input_type") == input_type
                and input_stanza_name != stanza.split('://')[1]
                and (not is_true(input_parser_obj.get(stanza, "disabled", fallback="0")))
                and input_parser_obj.get(stanza, "global_account") == account
            ):
                input_name = stanza.split('://')[1]
                break
    else:
        for stanza in input_stanzas:
            if(
                stanza.startswith(stanza_prefix) and input_parser_obj.get(stanza, "input_type") == input_type
                and input_stanza_name != stanza.split('://')[1]
                and input_parser_obj.get(stanza, "global_account") == account
            ):
                input_name = stanza.split('://')[1]
                break
    return input_name


def read_conf_file(session_key, param_name, stanza=PURESTORAGE_ADDITIONAL_PARAMETERS):
    """
    Get conf file content with conf_manager.

    :param session_key: Splunk session key
    :param param_name: Parameter to be read
    :param stanza: Stanza from which parameter is to be taken
    """
    conf_manager_results = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm='__REST_CREDENTIAL__#{}#configs/conf-{}'.format(
            APP_NAME, SETTING_CONF_FILE
        )).get_conf(SETTING_CONF_FILE).get(stanza)
    if param_name == "verify_ssl":
        try:
            return is_true(conf_manager_results.get("verify_ssl"))
        except Exception:
            return True

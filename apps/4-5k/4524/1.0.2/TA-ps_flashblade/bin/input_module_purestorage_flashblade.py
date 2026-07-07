import time
import re
import calendar
import json
import datetime
import requests
import splunk.version as ver


def validate_input(helper, definition):
    """
    This function validates interval and start date entered by user.
    :param helper: object of BaseModInput class
    :param definition: object containing input parameters
    """
    start_date = definition.parameters.get('start_date')
    interval = definition.parameters.get('interval')

    helper.log_debug("PureStorage Debug: interval is "+str(interval))
    current_utc = calendar.timegm(datetime.datetime.utcnow().timetuple())

    if not (int(interval) >= 60):
        msg = 'interval should be greater than or equal to 60 seconds.'
        helper.log_error("PureStorage Error: " + msg)
        raise Exception(msg)

    if start_date:
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", start_date):
            msg = 'start date should be in "YYYY-MM-DDThh:mm:ssZ" format.'
            helper.log_error("PureStorage Error: " + msg)
            raise Exception(msg)

        time_pattern = "%Y-%m-%dT%H:%M:%SZ"
        start_date = calendar.timegm(time.strptime(start_date, time_pattern))

        if start_date < 0:
            msg = 'start date can not be lesser than "1970-01-01T00:00:00Z".'
            helper.log_error("PureStorage Error: " + msg)
            raise Exception(msg)

        if start_date > current_utc:
            helper.log_error(
                msg='start date can not be greater than current UTC.'
                "PureStorage Error: " + msg)
            raise Exception(msg)


def request_get(endpoint, config_details, params=None):
    """
    Makes request to PureStorage FlashBlade
    :param endpoint: endpoint to fetch data
    :param config_details: Basic configuration details
    :param params: request parameters
    :return records received in response, continuation_token
    """
    header_data = {
        "x-auth-token": config_details.get('x_auth_token'),
        "User-Agent": config_details.get('user_agent')
    }
    server_address = config_details.get('server_address')
    proxy_settings = config_details.get('proxy_settings')
    verify_ssl = config_details.get('verify_ssl')

    try:
        response = requests.get(server_address + endpoint, params=params,
                                headers=header_data, verify=verify_ssl, proxies=proxy_settings)
        response.raise_for_status()
        data = json.loads(response.text)
        records = data.get('items')
        continuation_token = data.get(
            'pagination_info').get('continuation_token')
        return continuation_token, records
    except Exception as e:
        raise e


def update_additional_fields(additional_fields):
    '''
    function returns list of fields to be added to records ingested in splunk
    :params additional_fields: Dictionary of additional fields that can be ingested to splunk with records
    :return dictionary of relevant fields to be ingested in splunk with records
    '''
    updated_additional_list = {}
    if additional_fields.has_key('array_name'):
        updated_additional_list['array_name'] = additional_fields.get(
            'array_name')
    if additional_fields.has_key('array_id'):
        updated_additional_list['array_id'] = additional_fields.get('array_id')
    if additional_fields.has_key('storage_protocol'):
        updated_additional_list['storage_protocol'] = additional_fields.get(
            'storage_protocol')
    if additional_fields.has_key('storage_type'):
        updated_additional_list['storage_type'] = additional_fields.get(
            'storage_type')
    if additional_fields.has_key('file_system_snapshots'):
        updated_additional_list['file_system_snapshots'] = additional_fields.get(
            'file_system_snapshots')
    return updated_additional_list


def ingest_in_splunk(helper, ew, records, sourcetype, additional_fields):
    """
    Ingests Records to Splunk
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param records: Records to be ingested in Splunk
    :param sourcetype: Sourcetype for Splunk Ingestion
    :param additional_fields: Dictionary of required fields to be added in record.
    """
    updated_additional_list = update_additional_fields(additional_fields)
    for record in records:
        record.update(updated_additional_list)
        if record.has_key('source'):
            record['file_system_source'] = record.pop('source')
        index_time = record.get(additional_fields.get('time_field'))
        index_time = long(index_time)/1000.0 if index_time else time.time()
        event = helper.new_event(time=index_time,
                                 index=helper.get_output_index(),
                                 sourcetype=sourcetype, data=json.dumps(record))
        ew.write_event(event)


def get_checkpoint(helper, config_details, sourcetype, endpoint):
    """
    Function to initialize checkpoint for particular sourcetype of particular input.
    :param helper: object of BaseModInput class
    :param config_details: Basic configuration details
    :param sourcetype: Splunk Sourcetype to get checkpoint
    :param endpoint: REST endpoint to get data
    """
    stanza_name = config_details.get('stanza')
    sourcetype = sourcetype.split(":")[-1]
    endpoint = endpoint.split("/")[-1]
    checkpoint_name = stanza_name + "_" + sourcetype + "_" + endpoint

    start_date = helper.get_arg('start_date')
    if start_date:
        time_pattern = "%Y-%m-%dT%H:%M:%SZ"
        start_date = calendar.timegm(time.strptime(start_date, time_pattern))
        start_date = int(start_date*1000)
    else:
        start_date = config_details.get(
            'end_date') - (7*86400*1000)  # 7 Days in Milliseconds
    checkpoint_time = helper.get_check_point(checkpoint_name)
    start_date = checkpoint_time if checkpoint_time else start_date

    config_details['start_date'] = start_date
    config_details['checkpoint_name'] = checkpoint_name


def update_checkpoint(helper, config_details):
    """
    Function to update checkpoint for particular sourcetype of particular input.
    :param helper: object of BaseModInput class
    :param config_details: Basic configuration details
    """
    end_date = config_details.get('end_date')
    checkpoint_name = config_details.get('checkpoint_name')
    helper.save_check_point(checkpoint_name, end_date)
    helper.log_debug(
        "PureStorage Debug: checkpoint updated for "+checkpoint_name+".")


def get_array_data(helper, ew, config_details):
    """
    Ingests Details of array of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    """
    endpoint = config_details['endpoint_prefix'] + "/arrays"
    sourcetype = "purestorage:flashblade:array"
    get_checkpoint(helper, config_details, sourcetype, endpoint)
    additional_fields = {}
    try:
        _, records = request_get(endpoint, config_details)
        if records:
            config_details['array_name'] = records[0].get('name')
            config_details['array_id'] = records[0].get('id')
        else:
            helper.log_error(
                "PureStorage Error: Terminating the data collection unsuccessfully. Reason: array name and array id not found while fetching array data.")
            exit(1)
        additional_fields['time_field'] = "_as_of"
        additional_fields['array_name'] = config_details.get('array_name')
        additional_fields['array_id'] = config_details.get('array_id')
        ingest_in_splunk(helper, ew, records, sourcetype, additional_fields)
        helper.log_debug(
            "PureStorage Debug: data collection completed for array data.")
        update_checkpoint(helper, config_details)
    except Exception as e:
        helper.log_error(
            "PureStorage Error: while collecting array data: {}".format(e))
        helper.log_error(
            "PureStorage Error: Terminating the data collection unsuccessfully. Reason: array name and array id not found while fetching array data.")
        exit(1)


def get_inventory_data_util(helper, ew, config_details, endpoint, sourcetype):
    """
    Ingest Inventory data of different endpoints provided at function call
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    :param endpoint: Endpoint to fetch data from
    :param sourcetype: Splunk Sourcetype for inventory data
    """
    get_checkpoint(helper, config_details, sourcetype, endpoint)
    additional_fields = {}
    params = {}
    if not endpoint.endswith("policies"):
        # for filesystem, snapshot, objectstore and buckets
        start_date = config_details.get('start_date')
        if start_date:
            params['filter'] = "created>={}".format(start_date)
        additional_fields['time_field'] = "created"
        if 'file-system' in endpoint:
            # for filesystem and snapshot
            additional_fields['storage_type'] = "File Systems"
            additional_fields['file_system_snapshots'] = False
            if 'snapshots' in endpoint:
                additional_fields['file_system_snapshots'] = True
        elif endpoint.endswith("buckets"):
            # for buckets
            additional_fields['storage_type'] = "Buckets"
        else:
            # for objectstore
            additional_fields['storage_type'] = "Object Store"

    else:
        # for policies
        additional_fields['storage_type'] = "Policies"

    try:
        _, records = request_get(endpoint, config_details, params)
        additional_fields['array_name'] = config_details.get('array_name')
        additional_fields['array_id'] = config_details.get('array_id')
        ingest_in_splunk(helper, ew, records, sourcetype, additional_fields)
        helper.log_debug("PureStorage Debug: data collection completed for {} inventory data.".format(
            additional_fields['storage_type']))
        update_checkpoint(helper, config_details)
    except Exception as e:
        helper.log_error(
            "PureStorage Error: while collecting {} inventory data: {}".format(additional_fields['storage_type'], e))


def get_filesystems_inventory_data(helper, ew, config_details, sourcetype):
    """
    Ingests Inventory Details of File-systems of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    :param sourcetype: Splunk Sourcetype for inventory data
    """
    endpoint = config_details['endpoint_prefix'] + "/file-systems"
    get_inventory_data_util(helper, ew, config_details, endpoint, sourcetype)


def get_snapshots_inventory_data(helper, ew, config_details, sourcetype):
    """
    Ingests Snapshots Details of File-systems of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    :param sourcetype: Splunk Sourcetype for inventory data
    """
    endpoint = config_details['endpoint_prefix'] + "/file-system-snapshots"
    get_inventory_data_util(helper, ew, config_details, endpoint, sourcetype)


def get_objectstore_inventory_data(helper, ew, config_details, sourcetype):
    """
    Ingests Account Details of Object Store of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    :param sourcetype: Splunk Sourcetype for inventory data
    """
    endpoint = config_details['endpoint_prefix'] + "/object-store-accounts"
    get_inventory_data_util(helper, ew, config_details, endpoint, sourcetype)


def get_policies_inventory_data(helper, ew, config_details, sourcetype):
    """
    Ingests Policies Inventory Details of File-systems of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    :param sourcetype: Splunk Sourcetype for inventory data
    """
    endpoint = config_details['endpoint_prefix'] + "/policies"
    get_inventory_data_util(helper, ew, config_details, endpoint, sourcetype)


def get_bucket_inventory_data(helper, ew, config_details, sourcetype):
    """
    Ingests Buckets Inventory Details of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    :param sourcetype: Splunk Sourcetype for inventory data
    """
    endpoint = config_details['endpoint_prefix'] + "/buckets"
    get_inventory_data_util(helper, ew, config_details, endpoint, sourcetype)


def get_inventory_data(helper, ew, config_details):
    """
    Ingests Inventory Details of File-systems, Snapshots, Object store & Policies
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    """
    sourcetype = "purestorage:flashblade:inventory"

    get_filesystems_inventory_data(helper, ew, config_details, sourcetype)
    get_snapshots_inventory_data(helper, ew, config_details, sourcetype)
    get_objectstore_inventory_data(helper, ew, config_details, sourcetype)
    get_policies_inventory_data(helper, ew, config_details, sourcetype)
    get_bucket_inventory_data(helper, ew, config_details, sourcetype)


def set_date_and_resolution(params, helper):
    """
    Returns a list of dictionary which specifies start_time, end_time and resolution as follows:
        for first 3 hours -> 30s resolution
        for next 24 hours -> 5m resolution
        for next 7 days -> 30m resolution
        for next 30 days -> 2h resolution
        for next 366 days -> 1d resolution
    :param params: list of parameter required for making rest call for fetching data
    :param helper: object of BaseModInput class
    :return list of dictionary having start_time, end_time and resolution as specified above
    """

    date_resolution_list = []
    time_resolution_list = [{'time': 2592000000, 'resolution': 86400000}, {'time': 604800000, 'resolution': 7200000}, {
        'time': 86400000, 'resolution': 1800000}, {'time': 10800000, 'resolution': 300000}, {'time': 0, 'resolution': 30000}]

    end_time = params.get('end_time')
    start_time = params.get('start_time')

    diff = end_time-start_time
    for value in time_resolution_list:
        if diff > value.get('time'):
            date_resolution_list.append({'end_time': end_time - value.get('time'), 'start_time': start_time,
                                         'resolution': value.get('resolution')})
            start_time = end_time - value.get('time')
            diff = end_time - start_time

    helper.log_debug(" PureStorage Debug: time and resolution distribution")
    helper.log_debug('\n'.join('for start_time -> {} to end_time -> {} with resolution -> {}'.format(time.ctime(
        x['start_time']/1000), time.ctime(x['end_time']/1000), x['resolution']) for x in date_resolution_list))
    return date_resolution_list


def get_array_performance_data(helper, ew, config_details, sourcetype):
    """
    Ingests Details of 'Performance of Array' of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    :param sourcetype: Splunk sourcetype for performance data
    """
    get_checkpoint(helper, config_details, sourcetype, "arrays_performance")
    endpoint = config_details['endpoint_prefix'] + "/arrays/performance"
    start_date = config_details.get('start_date')
    end_date = config_details.get('end_date')
    params = {
        'end_time': end_date
    }
    additional_fields = {}

    if start_date:
        params['start_time'] = start_date

    try:
        # for Array Performance over Different Protocol
        storage_protocols = ['array', 'http', 'smb', 's3', 'nfs']
        storage_type = "Array"
        date_resolution_list = set_date_and_resolution(params, helper)
        for storage_protocol in storage_protocols:
            if storage_protocol != "array":
                params['protocol'] = storage_protocol
            for value in date_resolution_list:
                params['start_time'], params['end_time'], params['resolution'] = value.get(
                    'start_time'), value.get('end_time'), value.get('resolution')
                _, records = request_get(endpoint, config_details, params)
                additional_fields['time_field'] = "time"
                additional_fields['storage_type'] = storage_type
                additional_fields['storage_protocol'] = storage_protocol.upper()
                additional_fields['array_name'] = config_details.get(
                    'array_name')
                additional_fields['array_id'] = config_details.get('array_id')
                ingest_in_splunk(helper, ew, records,
                                 sourcetype, additional_fields)
                helper.log_debug("PureStorage Debug: ingested {} records in array performance for {} between start_time -> {} and end_time -> {} with resolution -> {}".format(
                    len(records), storage_protocol, time.ctime(value.get('start_time')/1000), time.ctime(value.get('end_time')/1000), value.get('resolution')))

        helper.log_debug(
            "PureStorage Debug: data collection completed for array performance data.")
        update_checkpoint(helper, config_details)
    except Exception as e:
        helper.log_error(
            "PureStorage Error: while collecting array performance data: {}".format(e))


def get_filesystem_performance_data(helper, ew, config_details, sourcetype):
    """
    Ingests Details of 'Performance of File-systems' of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    :param sourcetype: Splunk sourcetype for performance data
    """
    get_checkpoint(helper, config_details, sourcetype,
                   "filesystems_performance")
    endpoint = config_details['endpoint_prefix'] + "/file-systems/performance"
    start_date = config_details.get('start_date')
    end_date = config_details.get('end_date')
    params = {
        'end_time': end_date,
        'limit': 5
    }
    additional_fields = {}

    if start_date:
        params['start_time'] = start_date

    try:
        # for File-Systems Performance over Different Protocol
        storage_protocols = ['nfs']
        storage_type = "File Systems"
        date_resolution_list = set_date_and_resolution(params, helper)
        for storage_protocol in storage_protocols:
            params['protocol'] = storage_protocol
            for value in date_resolution_list:
                params['start_time'], params['end_time'], params['resolution'] = value.get(
                    'start_time'), value.get('end_time'), value.get('resolution')
                while True:
                    continuation_token, records = request_get(
                        endpoint, config_details, params)
                    additional_fields['time_field'] = "time"
                    additional_fields['storage_type'] = storage_type
                    additional_fields['storage_protocol'] = storage_protocol.upper(
                    )
                    additional_fields['array_name'] = config_details.get(
                        'array_name')
                    additional_fields['array_id'] = config_details.get(
                        'array_id')
                    ingest_in_splunk(helper, ew, records,
                                     sourcetype, additional_fields)
                    helper.log_debug("PureStorage Debug: ingested {} records in file systems performance for {} between start_time -> {} and end_time -> {} with resolution -> {}".format(
                        len(records), storage_protocol, time.ctime(value.get('start_time')/1000), time.ctime(value.get('end_time')/1000), value.get('resolution')))
                    if not continuation_token:
                        break
                    params['token'] = continuation_token

        helper.log_debug(
            "PureStorage Debug: data collection completed for file-systems performance data.")
        update_checkpoint(helper, config_details)
    except Exception as e:
        helper.log_error(
            "PureStorage Error: while collecting file-systems performance data: {}".format(e))


def get_performance_data(helper, ew, config_details):
    """
    Ingests Details of Performance of 'File-systems' & 'Object Store' of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    """
    sourcetype = "purestorage:flashblade:performance"

    get_array_performance_data(helper, ew, config_details, sourcetype)
    get_filesystem_performance_data(helper, ew, config_details, sourcetype)


def get_space_data(helper, ew, config_details):
    """
    Ingests Details of used and free space of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    """
    endpoint = config_details['endpoint_prefix'] + "/arrays/space"
    sourcetype = "purestorage:flashblade:space"
    get_checkpoint(helper, config_details, sourcetype, endpoint)

    start_date = config_details.get('start_date')
    end_date = config_details.get('end_date')
    params = {
        'end_time': end_date,
    }
    additional_fields = {}

    if start_date:
        params['start_time'] = start_date

    try:
        # for Space Data over Different Storage Type
        storage_types = [{'array': 'Array'}, {
            'file-system': 'File Systems'}, {'object-store': 'Object Store'}]
        date_resolution_list = set_date_and_resolution(params, helper)
        for storage_type in storage_types:
            for storage_type_key, storage_type_value in storage_type.iteritems():
                if storage_type_key != "array":
                    params['type'] = storage_type_key
                for value in date_resolution_list:
                    params['start_time'], params['end_time'], params['resolution'] = value.get(
                        'start_time'), value.get('end_time'), value.get('resolution')
                    _, records = request_get(endpoint, config_details, params)
                    additional_fields['time_field'] = "time"
                    additional_fields['storage_type'] = storage_type_value
                    additional_fields['array_name'] = config_details.get(
                        'array_name')
                    additional_fields['array_id'] = config_details.get(
                        'array_id')
                    ingest_in_splunk(helper, ew, records,
                                     sourcetype, additional_fields)
                    helper.log_debug("PureStorage Debug: ingested {} records in space for {} between start_time -> {} and end_time -> {} with resolution -> {}".format(
                        len(records), storage_type_value, time.ctime(value.get('start_time')/1000), time.ctime(value.get('end_time')/1000), value.get('resolution')))

            helper.log_debug(
                "PureStorage Debug: data collection completed for space data.")
            update_checkpoint(helper, config_details)
    except Exception as e:
        helper.log_error(
            "PureStorage Error: while collecting Space Data: {}".format(e))


def get_alerts_data(helper, ew, config_details):
    """
    Ingests Details of alerts generated in Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    """
    endpoint = config_details['endpoint_prefix'] + "/alerts"
    sourcetype = "purestorage:flashblade:alerts"
    get_checkpoint(helper, config_details, sourcetype, endpoint)
    start_date = config_details.get('start_date')
    params = {}
    additional_fields = {}

    if start_date:
        params['filter'] = "updated>={}".format(start_date)

    try:
        _, records = request_get(endpoint, config_details, params)
        additional_fields['time_field'] = "updated"
        additional_fields['array_name'] = config_details.get('array_name')
        additional_fields['array_id'] = config_details.get('array_id')
        ingest_in_splunk(helper, ew, records, sourcetype, additional_fields)
        helper.log_debug(
            "PureStorage Debug: data collection completed for alerts data.")
        update_checkpoint(helper, config_details)
    except Exception as e:
        helper.log_error(
            "PureStorage Error: while collecting alerts data: {}".format(e))


def get_health_data(helper, ew, config_details):
    """
    Ingests Details of health of Flashblade
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param config_details: Basic configuration details
    """
    endpoint = config_details['endpoint_prefix'] + "/blades"
    sourcetype = "purestorage:flashblade:health"
    get_checkpoint(helper, config_details, sourcetype, endpoint)
    additional_fields = {}
    try:
        _, records = request_get(endpoint, config_details)
        additional_fields['array_name'] = config_details.get('array_name')
        additional_fields['array_id'] = config_details.get('array_id')
        ingest_in_splunk(helper, ew, records, sourcetype, additional_fields)
        helper.log_debug(
            "PureStorage Debug: data collection completed for health data.")
        update_checkpoint(helper, config_details)
    except Exception as e:
        helper.log_error(
            "PureStorage Error: while collecting health data: {}".format(e))


def collect_events(helper, ew):
    """
    Fetches data from FlashBlade and ingests it to Splunk
    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    """
    # Getting Input Data
    global_account = helper.get_arg('global_account')
    api_token = global_account.get('api_token')
    server_address = global_account.get('server_address')
    verify_ssl = bool(int(global_account.get('verify_ssl')))
    stanza_name = str(helper.get_input_stanza_names())
    current_time = int(time.time()*1000)

    # Getting Splunk Version
    splunk_version = ver.__version__
    if not splunk_version:
        helper.log_error(
            "PureStorage Error: unable to fetch splunk version.")
        return

    # Fetching proxy data
    uri = helper._get_proxy_uri()
    proxy_settings = {
        "http": uri,
        "https": uri
    }

    # Storing necessary data into dictionary
    config_details = {}
    config_details['server_address'] = server_address
    config_details['user_agent'] = "Splunk/{}".format(splunk_version)
    config_details['stanza'] = stanza_name
    config_details['end_date'] = current_time
    config_details['proxy_settings'] = proxy_settings
    config_details['verify_ssl'] = verify_ssl
    config_details['api_version'] = "1.5"
    config_details['endpoint_prefix'] = "/api/" + config_details['api_version']

    # Login on PureStorage Server and create session
    headers = {
        "api-token": api_token,
        "User-Agent": config_details.get('user_agent')
    }
    try:
        response = requests.post("{}/api/login".format(server_address), headers=headers,
                                 verify=verify_ssl, proxies=proxy_settings)
        response.raise_for_status()
        config_details['x_auth_token'] = response.headers.get('x-auth-token')
        helper.log_debug("PureStorage Debug: connection established.")
    except Exception as e:
        helper.log_error(
            "PureStorage Error: unable to establish connection: {}".format(e))
        return

    # Function calls for collect data from different REST Endpoints.
    get_array_data(helper, ew, config_details)
    get_inventory_data(helper, ew, config_details)
    get_alerts_data(helper, ew, config_details)
    get_health_data(helper, ew, config_details)
    get_space_data(helper, ew, config_details)
    get_performance_data(helper, ew, config_details)

    # Logout from PureStorage Server and delete session
    del headers["api-token"]
    headers['x-auth-token'] = config_details['x_auth_token']
    try:
        response = requests.post(server_address + "/api/logout", headers=headers,
                                 verify=False, proxies=proxy_settings)
        response.raise_for_status()
        helper.log_debug(
            "PureStorage Debug: data collection completed, terminating session.")
    except Exception as e:
        helper.log_error(
            "PureStorage Error: unable to terminate session: {}".format(e))

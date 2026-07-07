import time
import json
import requests
import splunk.version as ver
import purestorage_unified_utils as utils
from distutils.version import StrictVersion
import traceback
from solnlib.utils import is_true


class PureStroageFlashblade():
    """Description: Flashblade data collection object."""

    supported_rest_versions = ["1.0", "1.1", "1.2", "1.3", "1.4",
                               "1.5", "1.6", "1.7", "1.8", "1.9", "1.11", "2.2", "2.8"]

    def request_get(self, endpoint, helper, config_details, params=None):
        """
        Makes request to PureStorage FlashBlade.

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

        response = requests.get(server_address + endpoint,
                                params=params,
                                headers=header_data,
                                verify=verify_ssl,
                                proxies=proxy_settings)
        if response.status_code != 200:
            helper.log_error("type={} name={} msg=Response status code: {}\n Response: {}\n URL: {} "
                             "Params: {}".format(config_details["input_type"], config_details["stanza"],
                                                 response.status_code, response.text,
                                                 server_address + endpoint, params))
        response.raise_for_status()
        data = json.loads(response.text)
        records = data.get('items')
        try:
            continuation_token = data.get('pagination_info').get(
                'continuation_token')
        except AttributeError:  # APIv2 support
            continuation_token = data.get('continuation_token')
        return continuation_token, records

    def get_array_data(self, helper, ew, config_details):
        """
        Ingests Details of array of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        """
        helper.log_info(
            'type={} name={} msg=Getting array details from FlashBlade REST service for {}'.format(
                config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
        )
        endpoint = config_details['endpoint_prefix'] + "/arrays"
        sourcetype = "purestorage:flashblade:array"
        additional_fields = {}
        event_count = 0
        try:
            _, records = self.request_get(endpoint, helper, config_details)
            if records:
                config_details['array_name'] = records[0].get('name')
                config_details['array_id'] = records[0].get('id')
            else:
                helper.log_error(
                    "type={} name={} msg=PureStorage Error: Terminating the data collection unsuccessfully."
                    " Reason: array name and array id not found while fetching array data.".format(
                        config_details["input_type"], config_details["stanza"])
                )
                exit(1)
            additional_fields['time_field'] = "_as_of"
            additional_fields['array_name'] = config_details.get('array_name')
            additional_fields['array_id'] = config_details.get('array_id')
            utils.ingest_in_splunk(helper, ew, records, sourcetype,
                                   additional_fields)
            event_count = len(records)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed for array"
                " data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for array data.".format(config_details["input_type"], config_details["stanza"], event_count))

        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting array data: {}".
                format(config_details["input_type"], config_details["stanza"], e))
            helper.log_error(
                "type={} name={} msg=PureStorage Error: Terminating the data collection unsuccessfully."
                " Reason: array name and array id not found while fetching array data.".format(
                    config_details["input_type"], config_details["stanza"])
            )
            helper.log_debug(traceback.format_exc())
            exit(1)

    def get_inventory_data_util(self, helper, ew, config_details, endpoint,
                                sourcetype):
        """
        Ingest Inventory data of different endpoints provided at function call.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        :param endpoint: Endpoint to fetch data from
        :param sourcetype: Splunk Sourcetype for inventory data
        """
        additional_fields = {}
        params = {}
        event_count = 0
        if not endpoint.endswith("policies"):
            # for filesystem, snapshot, objectstore and buckets
            if not (endpoint.endswith("file-systems") or endpoint.endswith("object-store-accounts")
                    or endpoint.endswith("buckets")):
                utils.get_checkpoint(helper, config_details, sourcetype, endpoint)
                start_date = config_details.get('start_date')
                if start_date:
                    params['filter'] = "created>={}".format(start_date)
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
            _, records = self.request_get(endpoint, helper, config_details, params)
            additional_fields['array_name'] = config_details.get('array_name')
            additional_fields['array_id'] = config_details.get('array_id')
            utils.ingest_in_splunk(helper, ew, records, sourcetype,
                                   additional_fields)
            event_count = len(records)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed for {} inventory data.".
                format(config_details["input_type"], config_details["stanza"], additional_fields['storage_type']))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for {} inventory data.".format(config_details["input_type"],
                                                 config_details["stanza"], event_count,
                                                 endpoint))
            # Update checkpoint only for endpoints we perform get_checkpoint
            if not (endpoint.endswith("policies") or endpoint.endswith("file-systems")
                    or endpoint.endswith("object-store-accounts") or endpoint.endswith("buckets")):
                utils.update_checkpoint(helper, config_details)
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting {} inventory data: {}".
                format(config_details["input_type"], config_details["stanza"], additional_fields['storage_type'], e))
            helper.log_debug(traceback.format_exc())

    def get_filesystems_inventory_data(self, helper, ew, config_details,
                                       sourcetype):
        """
        Ingests Inventory Details of File-systems of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        :param sourcetype: Splunk Sourcetype for inventory data
        """
        helper.log_info('type={} name={} msg=Getting filesystems details from FlashBlade REST service'
                        ' for {}'.format(config_details["input_type"],
                                         config_details["stanza"], config_details['flahblade_name']))
        endpoint = config_details['endpoint_prefix'] + "/file-systems"
        self.get_inventory_data_util(helper, ew, config_details, endpoint,
                                     sourcetype)

    def get_snapshots_inventory_data(self, helper, ew, config_details,
                                     sourcetype):
        """
        Ingests Snapshots Details of File-systems of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        :param sourcetype: Splunk Sourcetype for inventory data
        """
        helper.log_info('type={} name={} msg=Getting snapshots details'
                        ' from FlashBlade REST service for {}'.format(
                            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
                        )
        endpoint = config_details['endpoint_prefix'] + "/file-system-snapshots"
        self.get_inventory_data_util(helper, ew, config_details, endpoint,
                                     sourcetype)

    def get_objectstore_inventory_data(self, helper, ew, config_details,
                                       sourcetype):
        """
        Ingests Account Details of Object Store of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        :param sourcetype: Splunk Sourcetype for inventory data
        """
        helper.log_info('type={} name={} msg=Getting objectstore details'
                        ' from FlashBlade REST service for {}'.format(
                            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
                        )
        endpoint = config_details['endpoint_prefix'] + "/object-store-accounts"
        self.get_inventory_data_util(helper, ew, config_details, endpoint,
                                     sourcetype)

    def get_policies_inventory_data(self, helper, ew, config_details,
                                    sourcetype):
        """
        Ingests Policies Inventory Details of File-systems of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        :param sourcetype: Splunk Sourcetype for inventory data
        """
        helper.log_info('type={} name={} msg=Getting policies details '
                        'from FlashBlade REST service for {}'.format(
                            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
                        )
        endpoint = config_details['endpoint_prefix'] + "/policies"
        self.get_inventory_data_util(helper, ew, config_details, endpoint,
                                     sourcetype)

    def get_bucket_inventory_data(self, helper, ew, config_details,
                                  sourcetype):
        """
        Ingests Buckets Inventory Details of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        :param sourcetype: Splunk Sourcetype for inventory data
        """
        helper.log_info('type={} name={} msg=Getting bucket details from FlashBlade REST service for {}'.format(
            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
        )
        endpoint = config_details['endpoint_prefix'] + "/buckets"
        self.get_inventory_data_util(helper, ew, config_details, endpoint,
                                     sourcetype)

    def get_inventory_data(self, helper, ew, config_details):
        """
        Ingests Inventory Details of File-systems, Snapshots, Object store & Policies.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        """
        sourcetype = "purestorage:flashblade:inventory"

        self.get_filesystems_inventory_data(helper, ew, config_details,
                                            sourcetype)
        self.get_snapshots_inventory_data(helper, ew, config_details,
                                          sourcetype)
        self.get_objectstore_inventory_data(helper, ew, config_details,
                                            sourcetype)
        self.get_policies_inventory_data(helper, ew, config_details,
                                         sourcetype)
        self.get_bucket_inventory_data(helper, ew, config_details, sourcetype)

    def set_date_and_resolution(self, params, helper, config_details):
        """
        Returns a list of dictionary which specifies start_time, end_time and resolution as follows.

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
        time_resolution_list = [{
            'time': 2592000000,
            'resolution': 86400000
        }, {
            'time': 604800000,
            'resolution': 7200000
        }, {
            'time': 86400000,
            'resolution': 1800000
        }, {
            'time': 10800000,
            'resolution': 300000
        }, {
            'time': 0,
            'resolution': 30000
        }]

        end_time = params.get('end_time')
        start_time = params.get('start_time')

        diff = end_time - start_time
        for value in time_resolution_list:
            if diff > value.get('time'):
                date_resolution_list.append({
                    'end_time':
                    end_time - value.get('time'),
                    'start_time':
                    start_time,
                    'resolution':
                    value.get('resolution')
                })
                start_time = end_time - value.get('time')
                diff = end_time - start_time

        helper.log_debug(
            " type={} name={} msg=PureStorage Debug: time and resolution"
            " distribution".format(config_details["input_type"], config_details["stanza"]))
        helper.log_debug('\n'.join(  # pending
            'for start_time -> {} to end_time -> {} with resolution -> {}'.
            format(time.ctime(x['start_time'] / 1000), time.ctime(x['end_time'] / 1000), x['resolution'])
            for x in date_resolution_list))
        return date_resolution_list

    def get_array_performance_data(self, helper, ew, config_details,
                                   sourcetype):
        """
        Ingests Details of 'Performance of Array' of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        :param sourcetype: Splunk sourcetype for performance data
        """
        helper.log_info('type={} name={} msg=Getting array performance'
                        ' details from FlashBlade REST service for {}'.format(
                            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
                        )
        utils.get_checkpoint(helper, config_details, sourcetype,
                             "arrays_performance")
        endpoint = config_details['endpoint_prefix'] + "/arrays/performance"
        start_date = config_details.get('start_date')
        end_date = config_details.get('end_date')
        params = {'end_time': end_date}
        additional_fields = {}

        if start_date:
            params['start_time'] = start_date

        try:
            # for Array Performance over Different Protocol
            storage_protocols = ['array', 'http', 'smb', 's3', 'nfs']
            storage_type = "Array"
            date_resolution_list = self.set_date_and_resolution(params, helper, config_details)
            for storage_protocol in storage_protocols:
                if storage_protocol != "array":
                    params['protocol'] = storage_protocol
                for value in date_resolution_list:
                    params['start_time'], params['end_time'], params[
                        'resolution'] = value.get('start_time'), value.get(
                            'end_time'), value.get('resolution')
                    _, records = self.request_get(endpoint, helper, config_details,
                                                  params)
                    additional_fields['time_field'] = "time"
                    additional_fields['storage_type'] = storage_type
                    additional_fields[
                        'storage_protocol'] = storage_protocol.upper()
                    additional_fields['array_name'] = config_details.get(
                        'array_name')
                    additional_fields['array_id'] = config_details.get(
                        'array_id')
                    utils.ingest_in_splunk(helper, ew, records, sourcetype,
                                           additional_fields)
                    helper.log_debug(
                        "type={} name={} msg=PureStorage Debug: ingested {} records in array performance for {}"
                        " between start_time -> {} and end_time -> {} with resolution -> {}"
                        .format(config_details["input_type"], config_details["stanza"], len(records), storage_protocol,
                                time.ctime(value.get('start_time') / 1000),
                                time.ctime(value.get('end_time') / 1000),
                                value.get('resolution')))

            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed for"
                " array performance data.".format(
                    config_details["input_type"], config_details["stanza"])
            )
            utils.update_checkpoint(helper, config_details)
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting array performance data: {}"
                .format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_filesystem_performance_data(self, helper, ew, config_details,
                                        sourcetype):
        """
        Ingests Details of 'Performance of File-systems' of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        :param sourcetype: Splunk sourcetype for performance data
        """
        helper.log_info('type={} name={} msg=Getting filesystem '
                        'performance details from FlashBlade REST service for {}'.format(
                            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
                        )
        utils.get_checkpoint(helper, config_details, sourcetype,
                             "filesystems_performance")
        start_date = config_details.get('start_date')
        end_date = config_details.get('end_date')
        params = {'end_time': end_date, 'limit': 5}
        additional_fields = {}

        if start_date:
            params['start_time'] = start_date

        try:
            # for File-Systems Performance over Different Protocol
            # for getting the list of all the file systems
            endpoint = config_details['endpoint_prefix'] + "/file-systems"
            _, records = self.request_get(endpoint, helper, config_details)
            file_systems_list = set()
            if records:
                for record in records:
                    file_systems_list.add(record["name"])
            file_systems_list = list(file_systems_list)
            endpoint = config_details['endpoint_prefix'] + "/file-systems/performance"
            # getting creating param to pass in the request
            date_resolution_list = self.set_date_and_resolution(params, helper, config_details)
            while file_systems_list:
                filesystem_param = ",".join(file_systems_list[:5])
                file_systems_list = file_systems_list[5:]
                params["names"] = filesystem_param
                storage_protocols = ['nfs']
                storage_type = "File Systems"
                for storage_protocol in storage_protocols:
                    params['protocol'] = storage_protocol
                    for value in date_resolution_list:
                        params['start_time'], params['end_time'], params[
                            'resolution'] = value.get('start_time'), value.get(
                                'end_time'), value.get('resolution')
                        while True:
                            continuation_token, records = self.request_get(
                                endpoint, helper, config_details, params)
                            additional_fields['time_field'] = "time"
                            additional_fields['storage_type'] = storage_type
                            additional_fields[
                                'storage_protocol'] = storage_protocol.upper()
                            additional_fields['array_name'] = config_details.get(
                                'array_name')
                            additional_fields['array_id'] = config_details.get(
                                'array_id')
                            utils.ingest_in_splunk(helper, ew, records, sourcetype,
                                                   additional_fields)
                            helper.log_debug(
                                "type={} name={} msg=PureStorage Debug: ingested {} records"
                                " in file systems performance for {}"
                                " between start_time -> {} and end_time -> {} with resolution -> {}"
                                .format(config_details["input_type"], config_details["stanza"],
                                        len(records), storage_protocol, time.ctime(value.get('start_time') / 1000),
                                        time.ctime(value.get('end_time') / 1000),
                                        value.get('resolution')))
                            if not continuation_token:
                                break
                            params['token'] = continuation_token

            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed for file-systems"
                " performance data.".format(config_details["input_type"], config_details["stanza"])
            )
            utils.update_checkpoint(helper, config_details)
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting file-systems performance data: {}"
                .format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_buckets_performance_data(self, helper, ew, config_details,
                                     sourcetype):
        """
        Ingests Details of 'Performance of Buckets' of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        :param sourcetype: Splunk sourcetype for performance data
        """
        helper.log_info('type={} name={} msg=Getting Object Store performance details'
                        ' from FlashBlade REST service for {}'.format(
                            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
                        )
        utils.get_checkpoint(helper, config_details, sourcetype,
                             "buckets_performance")
        start_date = config_details.get('start_date')
        end_date = config_details.get('end_date')
        params = {'end_time': end_date}
        additional_fields = {}

        if start_date:
            params['start_time'] = start_date

        try:
            # for getting the list of all the buckets
            endpoint = config_details['endpoint_prefix'] + "/buckets"
            _, records = self.request_get(endpoint, helper, config_details)
            buckets_list = set()
            if records:
                for record in records:
                    if record.get("destroyed"):
                        continue
                    buckets_list.add(record["name"])
            buckets_list = list(buckets_list)
            buckets_list.sort()
            endpoint = config_details['endpoint_prefix'] + "/buckets/performance"
            # creating param to pass in the request
            date_resolution_list = self.set_date_and_resolution(params, helper, config_details)
            while buckets_list:
                bucket_param = ",".join(buckets_list[:5])
                buckets_list = buckets_list[5:]
                params["names"] = bucket_param
                storage_type = "Object Store"
                for value in date_resolution_list:
                    params['start_time'], params['end_time'], params[
                        'resolution'] = value.get('start_time'), value.get(
                            'end_time'), value.get('resolution')
                    while True:
                        continuation_token, records = self.request_get(
                            endpoint, helper, config_details, params)
                        additional_fields['time_field'] = "time"
                        additional_fields['storage_type'] = storage_type
                        additional_fields['array_name'] = config_details.get(
                            'array_name')
                        additional_fields['array_id'] = config_details.get('array_id')
                        utils.ingest_in_splunk(helper, ew, records, sourcetype,
                                               additional_fields)
                        helper.log_debug(
                            "type={} name={} msg=PureStorage Debug: ingested {} records in buckets performance"
                            " for {} between start_time -> {} and end_time -> {} with resolution -> {}"
                            .format(config_details["input_type"], config_details["stanza"], len(records), bucket_param,
                                    time.ctime(value.get('start_time') / 1000),
                                    time.ctime(value.get('end_time') / 1000),
                                    value.get('resolution')))
                        if not continuation_token:
                            break
                        params['token'] = continuation_token

            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed for"
                " buckets performance data.".format(config_details["input_type"], config_details["stanza"]))
            utils.update_checkpoint(helper, config_details)
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting buckets performance data: {}"
                .format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_performance_data(self, helper, ew, config_details):
        """
        Ingests Details of Performance of 'File-systems' & 'Object Store' of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        """
        sourcetype = "purestorage:flashblade:performance"

        self.get_array_performance_data(helper, ew, config_details, sourcetype)
        self.get_filesystem_performance_data(helper, ew, config_details,
                                             sourcetype)
        self.get_buckets_performance_data(helper, ew, config_details, sourcetype)

    def get_space_data(self, helper, ew, config_details):
        """
        Ingests Details of used and free space of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        """
        helper.log_info('type={} name={} msg=Getting space details from FlashBlade REST service for {}'.format(
            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
        )
        endpoint = config_details['endpoint_prefix'] + "/arrays/space"
        sourcetype = "purestorage:flashblade:space"
        utils.get_checkpoint(helper, config_details, sourcetype, endpoint)

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
            storage_types = [{
                'array': 'Array'
            }, {
                'file-system': 'File Systems'
            }, {
                'object-store': 'Object Store'
            }]
            date_resolution_list = self.set_date_and_resolution(params, helper, config_details)
            for storage_type in storage_types:
                for storage_type_key, storage_type_value in storage_type.items(
                ):
                    if storage_type_key != "array":
                        params['type'] = storage_type_key
                    for value in date_resolution_list:
                        params['start_time'], params['end_time'], params[
                            'resolution'] = value.get('start_time'), value.get(
                                'end_time'), value.get('resolution')
                        _, records = self.request_get(endpoint, helper, config_details,
                                                      params)
                        additional_fields['time_field'] = "time"
                        additional_fields['storage_type'] = storage_type_value
                        additional_fields['array_name'] = config_details.get(
                            'array_name')
                        additional_fields['array_id'] = config_details.get(
                            'array_id')
                        utils.ingest_in_splunk(helper, ew, records, sourcetype, additional_fields)
                        helper.log_debug(
                            "type={} name={} msg=PureStorage Debug: ingested {} records in space for {}"
                            " between start_time -> {} and end_time -> {} "
                            "with resolution -> {}".format(config_details["input_type"], config_details["stanza"],
                                                           len(records), storage_type_value,
                                                           time.ctime(value.get('start_time') / 1000),
                                                           time.ctime(value.get('end_time') / 1000),
                                                           value.get('resolution')))

                helper.log_debug(
                    "type={} name={} msg=PureStorage Debug: data collection completed for space data.".format(
                        config_details["input_type"], config_details["stanza"])
                )
                utils.update_checkpoint(helper, config_details)
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: "
                "while collecting Space Data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_alerts_data(self, helper, ew, config_details):
        """
        Ingests Details of alerts generated in Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        """
        helper.log_info('type={} name={} msg=Getting alert details from FlashBlade REST service for {}'.format(
            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
        )
        endpoint = config_details['endpoint_prefix'] + "/alerts"
        sourcetype = "purestorage:flashblade:alerts"
        utils.get_checkpoint(helper, config_details, sourcetype, endpoint)
        start_date = config_details.get('start_date')
        params = {}
        additional_fields = {}

        if start_date:
            params['filter'] = "updated>={}".format(start_date)

        try:
            _, records = self.request_get(endpoint, helper, config_details, params)
            additional_fields['time_field'] = "updated"
            additional_fields['array_name'] = config_details.get('array_name')
            additional_fields['array_id'] = config_details.get('array_id')
            utils.ingest_in_splunk(helper, ew, records, sourcetype,
                                   additional_fields)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed for alerts data.".format(
                    config_details["input_type"], config_details["stanza"])
            )
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for alerts data.".format(config_details["input_type"], config_details["stanza"], len(records)))
            utils.update_checkpoint(helper, config_details)
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting alerts data: {}".format(
                    config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_health_data(self, helper, ew, config_details):
        """
        Ingests Details of health of Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        """
        helper.log_info('type={} name={} msg=Getting health details from FlashBlade REST service for {}'.format(
            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
        )
        endpoint = config_details['endpoint_prefix'] + "/blades"
        sourcetype = "purestorage:flashblade:health"
        additional_fields = {}
        try:
            _, records = self.request_get(endpoint, helper, config_details)
            additional_fields['array_name'] = config_details.get('array_name')
            additional_fields['array_id'] = config_details.get('array_id')
            utils.ingest_in_splunk(helper, ew, records, sourcetype,
                                   additional_fields)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed for health data.".format(
                    config_details["input_type"], config_details["stanza"],)
            )
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for health data.".format(config_details["input_type"], config_details["stanza"], len(records)))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting health data: {}".format(
                    config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_audits_data(self, helper, ew, config_details):
        """
        Ingests Details of audits generated in Flashblade.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        """
        helper.log_info('type={} name={} msg=Getting audit details from FlashBlade REST service for {}'.format(
            config_details["input_type"], config_details["stanza"], config_details['flahblade_name'])
        )
        endpoint = config_details['endpoint_prefix'] + "/audits"
        sourcetype = "purestorage:flashblade:audits"
        utils.get_checkpoint(helper, config_details, sourcetype, endpoint)
        start_date = config_details.get('start_date')
        params = {}
        additional_fields = {}

        if start_date:
            start_date = int(start_date) + 1
            params['filter'] = "time>={}".format(start_date)

        try:
            _, records = self.request_get(endpoint, helper, config_details, params)
            additional_fields['time_field'] = "time"
            additional_fields['array_name'] = config_details.get('array_name')
            additional_fields['array_id'] = config_details.get('array_id')
            utils.ingest_in_splunk(helper, ew, records, sourcetype,
                                   additional_fields)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed for audits data.".format(
                    config_details["input_type"], config_details["stanza"])
            )
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for audits data.".format(config_details["input_type"], config_details["stanza"], len(records)))
            utils.update_checkpoint(helper, config_details)
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: "
                "while collecting audits data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def _choose_rest_version(self, helper, config_details):
        """Return the newest REST API version supported by target array."""
        versions = self._list_available_rest_versions(helper, config_details)
        versions = [x for x in versions if x in self.supported_rest_versions]
        if versions:
            return max(versions, key=StrictVersion)
        else:
            return "1.11"

    def _list_available_rest_versions(self, helper, config_details):
        """Return a list of the REST API versions supported by the array."""
        server_address = config_details['server_address']
        headers = {"Content-Type": "application/json"}
        headers['User-Agent'] = config_details.get('user_agent')
        verify_ssl = config_details['verify_ssl']
        proxy_settings = config_details['proxy_settings']
        url = "{0}/api/api_version".format(server_address)
        try:
            response = requests.request("GET", url, headers=headers, verify=verify_ssl, proxies=proxy_settings)
        except Exception:
            helper.log_error("type={} name={} msg=Could not get versions from flashblade. Setting"
                             " default version as latest version1".format(config_details["input_type"],
                                                                          config_details["stanza"]))
            helper.log_debug(traceback.format_exc())
            return []
        if response.status_code == 200 or response.status_code == 201:
            data = json.loads(response.text)
            versions = data.get("versions")
            if versions:
                return versions
            else:
                helper.log_error("type={} name={} msg=Could not get versions from flashblade"
                                 ". Setting default version as latest version2".format(
                                     config_details["input_type"], config_details["stanza"]))
                return []
        else:
            helper.log_error("type={} name={} msg=Response status code: {}\n Response: {}\n URL: {}".format(
                config_details["input_type"], config_details["stanza"], response.status_code, response.text, url))
            helper.log_error("type={} name={} msg=Could not get versions from flashblade. Setting default"
                             " version as latest version3".format(config_details["input_type"],
                                                                  config_details["stanza"]))
            return []

    def collect_events(self, helper, ew):
        """
        Fetches data from FlashBlade and ingests it to Splunk.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        """
        # Getting Input Data
        global_account = helper.get_arg('global_account')
        api_token = global_account.get('api_token')
        server_address = global_account.get('server_address')
        verify_ssl = utils.read_conf_file(helper.context_meta["session_key"], "verify_ssl")
        stanza_name = str(helper.get_input_stanza_names())
        current_time = int(time.time() * 1000)

        config_details = {}
        config_details['stanza'] = stanza_name
        config_details["input_type"] = helper.get_arg('input_type')

        # Getting Splunk Version
        splunk_version = ver.__version__
        if not splunk_version:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: unable to "
                " fetch splunk version.".format(config_details["input_type"], config_details["stanza"]))
            return

        # Fetching proxy data
        proxy_dict = helper.get_proxy()
        proxy_uri = None
        if proxy_dict:
            proxy_uri = utils.format_proxy_uri(proxy_dict)
        proxy_settings = {"http": proxy_uri, "https": proxy_uri}

        # Storing necessary data into dictionary
        server_address = "https://{}".format(server_address)
        config_details['server_address'] = server_address
        config_details['flahblade_name'] = server_address.replace("https://", "")  # noqa: E231
        config_details['user_agent'] = "Splunk/{}".format(splunk_version)
        config_details['end_date'] = current_time
        config_details['proxy_settings'] = proxy_settings
        config_details['verify_ssl'] = verify_ssl
        rest_version = self._choose_rest_version(helper, config_details)
        if rest_version:
            config_details['api_version'] = rest_version
        else:
            config_details['api_version'] = "1.11"

        config_details[
            'endpoint_prefix'] = "/api/" + config_details['api_version']

        # Handle Upgrade Scenario
        config_details['collect_historical_data'] = True
        if helper.get_arg('historical_data'):
            config_details['collect_historical_data'] = is_true(helper.get_arg('historical_data'))

        enable_disable = "enabled" if config_details['collect_historical_data'] else "disabled"

        helper.log_warning("type={} name={} msg=PureStorage Warning: Historical data collection is {}.".format(
            config_details["input_type"], config_details["stanza"], enable_disable))

        start_time = time.time()

        # Login on PureStorage Server and create session
        headers = {
            "api-token": api_token,
            "User-Agent": config_details.get('user_agent')
        }
        try:
            response = requests.post("{}/api/login".format(server_address),
                                     headers=headers,
                                     verify=verify_ssl,
                                     proxies=proxy_settings)
            response.raise_for_status()
            config_details['x_auth_token'] = response.headers.get(
                'x-auth-token')
            helper.log_debug("type={} name={} msg=PureStorage Debug: connection established.".format(
                config_details["input_type"], config_details["stanza"]))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: unable to establish connection: {}".format(
                    config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())
            return

        # Function calls for collect data from different REST Endpoints.
        self.get_array_data(helper, ew, config_details)
        self.get_inventory_data(helper, ew, config_details)
        self.get_alerts_data(helper, ew, config_details)
        self.get_health_data(helper, ew, config_details)
        self.get_space_data(helper, ew, config_details)
        self.get_performance_data(helper, ew, config_details)
        self.get_audits_data(helper, ew, config_details)

        # Logout from PureStorage Server and delete session
        del headers["api-token"]
        headers['x-auth-token'] = config_details['x_auth_token']
        try:
            response = requests.post(server_address + "/api/logout",
                                     headers=headers,
                                     verify=verify_ssl,
                                     proxies=proxy_settings)
            response.raise_for_status()
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed, terminating session.".format(
                    config_details["input_type"], config_details["stanza"])
            )
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: unable to terminate "
                "session: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

        helper.log_info("type={} name={} msg=PureStorage Info: Done with data collection. "
                        "Time taken: {} minutes for: {}.".format(config_details["input_type"],
                                                                 stanza_name, ((time.time() - start_time) / 60),
                                                                 stanza_name))

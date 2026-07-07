
# encoding = utf-8

import os
import time
import json
import datetime
import requests
import splunk.version as ver
import purestorage_unified_utils as utils
from distutils.version import StrictVersion
import traceback
from solnlib.utils import is_true

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def update_log_state(details, input_name, name, date_7d_ago, time_format):
    """
    Description: Filter out recent log data state and update log state.

    Parameters: details: input data
                name: name of source
    Return: filter input data
    """
    file_name = "input.json"
    log_state_dir = os.path.join(APP_DIR, 'logstate')
    if not os.path.exists(log_state_dir):
        os.mkdir(log_state_dir)
    if os.path.exists(os.path.join(log_state_dir, file_name)):
        with open(os.path.join(log_state_dir, file_name), 'r+') as f:
            f.seek(0)
            data = json.loads(f.read())
            if input_name in data:
                date_var = ""
                if data.get(input_name).get(name):
                    date_var = data.get(input_name).get(name)
                # Collect only 7 days data if checkbox is unticked
                if date_7d_ago:
                    date_var = datetime.datetime.utcfromtimestamp(
                        int(date_7d_ago) / 1000).strftime(time_format)
                details = [x for x in details if x['opened']
                           is not None and x['opened'] > date_var]
                if details:
                    data[input_name][name] = details[-1].get("opened")
            else:
                temp = {input_name: {"log_alert": None,
                                     "log_login": None, "log_audit": None}}
                temp[input_name][name] = details[-1].get("opened")
                data.update(temp)
            f.seek(0)
            json.dump(data, f, sort_keys=True, indent=4)
            f.truncate()
        return details
    else:
        with open(os.path.join(log_state_dir, file_name), "w") as f:
            temp = {input_name: {"log_alert": None,
                                 "log_login": None, "log_audit": None}}
            temp[input_name][name] = details[-1].get("opened")
            f.write(json.dumps(temp))
            return details


def merge_lists(list1, list2, key):
    """
    Description: Merge two lists base on key.

    Parameters: list1: first list
                list2: second list
    Return: List
    """
    merged = {}
    if list1 or list2:
        for item in list1 + list2:
            if item[key] in merged:
                merged[item[key]].update(item)
            else:
                merged[item[key]] = item
        return list(merged.values())


def remove_duplicates(alerts, type):
    """
    Description: Method remove duplicates event from data.

    Parameter: data: event data
    Return: list of dict
    """
    temp = []
    if type == "log_login":
        for alert in alerts:
            flag = 0
            for row in temp:
                if row.get('component_type') == alert.get('component_type') and row.get('event') == alert.get('event'):
                    flag = 1
            if flag == 0:
                temp.append(alert)
    else:
        for alert in alerts:
            flag = 0
            for row in temp:
                if (
                    row.get("component_name") == alert.get("component_name")
                    and row.get("component_type") == alert.get("component_type")
                    and row.get("event") == alert.get("event")
                ):
                    if "closed" in alert:
                        break
                    else:
                        flag = 1
            if flag == 0:
                temp.append(alert)
    return temp


def get_checkpoint_from_file(helper, sourcetype):
    """
    Description: Fetch flash array alert/audit/session details.

    Parameters: helper: helper object
                input_name: Name of Input Configured
                sourcetype: Data would be ingested in given sourcetype

    Return: String
    """
    endpoint_old_checkpoint_dict = {}
    endpoint_old_checkpoint_dict[SourceType.sourcetype_alert_logs] = "log_alert"
    endpoint_old_checkpoint_dict[SourceType.sourcetype_alert_audit] = "log_audit"
    endpoint_old_checkpoint_dict[SourceType.sourcetype_alert_login] = "log_login"
    file_name = "input.json"
    log_state_dir = os.path.join(APP_DIR, 'logstate')
    date_var = None
    name = endpoint_old_checkpoint_dict[sourcetype]

    input_name = helper.get_arg("input_name")

    if not os.path.exists(log_state_dir):
        return date_var
    if os.path.exists(os.path.join(log_state_dir, file_name)):
        with open(os.path.join(log_state_dir, file_name), 'r') as f:
            f.seek(0)
            data = json.loads(f.read())
            helper.log_debug("type={} name={} msg=Json file contents {}".format(
                helper.get_arg("input_type"), input_name, data))
            if input_name in data and data.get(input_name).get(name):
                date_var = data.get(input_name).get(name)
    return date_var


class PureStroageFlasharray():
    """Flasharray support object."""

    supported_rest_versions = [
        "1.13", "1.14", "1.15", "1.16", "1.17", "1.18", "2.2"
    ]
    time_format = '%Y-%m-%dT%H:%M:%SZ'
    cookies = {}

    def _request(self, method, path, helper, config_details, data=None, reestablish_session=True, params=None, headers={}, set_headers=True):  # noqa E501
        """Perform HTTP request for REST API."""
        if path.startswith("https"):
            url = path  # For cases where URL of different form is needed.
        else:
            helper.log_error("type={} name={} msg=Url does not start with https.".format(
                config_details["input_type"], config_details["stanza"]))
            return
        content_type = "application/json"
        headers["Content-Type"] = content_type
        headers['User-Agent'] = config_details.get('user_agent')
        proxy_settings = config_details.get('proxy_settings')
        verify_ssl = config_details.get('verify_ssl')

        if set_headers and config_details.get('major_api_version') == 2 and method == "GET":
            headers['x-auth-token'] = config_details['x-auth-token']

        try:
            response = requests.request(method, url, data=data, headers=headers,
                                        cookies=self.cookies, verify=verify_ssl, proxies=proxy_settings, params=params)
        except requests.exceptions.RequestException as err:
            # error outside scope of HTTP status codes
            # e.g. unable to resolve domain name

            raise PureError(err)

        if response.status_code == 200:
            if content_type in response.headers.get("Content-Type", ""):
                if response.cookies:
                    self.cookies.update(response.cookies)
                else:
                    self.cookies.clear()
                content = response.json()
                if isinstance(content, list):
                    content = ResponseList(content)
                elif isinstance(content, dict):
                    content = ResponseDict(content)
                content.headers = response.headers
                if set_headers and config_details.get('major_api_version') == 2 and method == "POST":
                    config_details['x-auth-token'] = response.headers.get('x-auth-token')
                return content
            raise PureError("Response not in JSON: " + response.text)
        elif response.status_code == 401 and reestablish_session:
            self._start_session(helper, config_details)
            return self._request(method, url, helper, config_details, data, False)
        else:
            helper.log_error("type={} name={} msg=Response status code: {}\n Response: {}\n  URL: {} Params: "
                             "{}".format(config_details["input_type"],
                                         config_details["stanza"], response.status_code, response.text, url, params))
            raise PureError("Response status code: {}\n Response: {}\n URL: {} Params: {}".format(
                response.status_code, response.text, url, params))

    def get_array_details(self, helper, ew, array, config_details):
        """
        Description: Fetch flash array details.

        Parameters: helper: helper object
                    ew: log object
                    array: array name
                    config_details: Config details of array
        """
        final_array_details = []
        event_count = 0
        helper.log_info('type={} name={} msg=Getting array details from array REST service for {}'.format(
            config_details["input_type"], config_details["stanza"], config_details['host']))
        path = self.create_path(config_details, "array")
        try:
            array_details = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            if array_details:
                config_details['array_name'] = array_details.get('array_name')
                config_details['array_id'] = array_details.get('id')
            else:
                helper.log_error(
                    "type={} name={} msg=PureStorage Error: Terminating the data collection unsuccessfully."
                    "Reason: array name and array id not found while fetching array data.".format(
                        config_details["input_type"], config_details["stanza"])
                )
                exit(1)
            path = self.create_path(config_details, "array?space=true")
            if array_details:
                array_details_with_space = self._request("GET", path, helper,
                                                         config_details, reestablish_session=True)
                if array_details_with_space:
                    array_details.update(array_details_with_space[0])

                path = self.create_path(config_details, "array?action=monitor&mirrored=true")
                array_details_with_monitor = self._request("GET", path, helper,
                                                           config_details, reestablish_session=True)
                if array_details_with_monitor:
                    array_details.update(array_details_with_monitor[0])

            # array_details.update(connection.get(action='monitor')[0])
            # time field is obtained from the monitor call
            additional_fields = {}
            additional_fields['time_field'] = 'time'
            additional_fields['array_name'] = config_details['array_name']
            additional_fields['host'] = config_details['host']
            final_array_details.append(array_details)
            if array_details:
                utils.ingest_in_splunk(helper, ew, final_array_details, SourceType.sourcetype_array,
                                       additional_fields, source=Source.source_array)
                event_count = len(final_array_details)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed"
                " for array data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for array data.".format(config_details["input_type"], config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting array data: {}".format(
                    config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_arrays_details(self, helper, ew, config_details):
        """
        Description: Fetch flash array details only for API v2.x.

        It will give detail of one array so pagination is not required. Also, pagination is not done for arrays API v1.x

        Parameters: helper: helper object
                    ew: log object
                    config_details: Config details of array
        """
        helper.log_info('type={} name={} msg=Getting arrays details from array REST service for {}'.format(
            config_details["input_type"], config_details["stanza"], config_details['host']))
        additional_fields = {}
        additional_fields['host'] = config_details['host']
        event_count = 0

        try:
            path = self.create_path(config_details, "arrays")
            array_details = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            if array_details:
                array_details_items = array_details.get("items", [])
                if len(array_details_items) > 0:
                    config_details['array_name'] = array_details_items[0].get('name')
                    config_details['array_id'] = array_details_items[0].get('id')
                    additional_fields['array_name'] = config_details['array_name']
                    utils.ingest_in_splunk(helper, ew, array_details_items, SourceType.sourcetype_array,
                                           additional_fields, source=Source.source_array)
                    event_count = len(array_details_items)
                else:
                    helper.log_error(
                        "type={} name={} msg=PureStorage Error: Terminating the data collection unsuccessfully."
                        "Reason: array name and array id not found while fetching arrays data.".format(
                            config_details["input_type"], config_details["stanza"])
                    )
                    exit(1)

            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed"
                " for arrays data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for arrays data.".format(config_details["input_type"], config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting arrays data: {}".format(
                    e, config_details["input_type"], config_details["stanza"]))
            helper.log_debug(traceback.format_exc())

    def get_volume_details(self, helper, ew, array, config_details):
        """
        Description: Fetch flash array volume details.

        Parameters: helper: helper object
                    ew: log object
                    array: array name
                    config_details: Config details of array
        """
        try:
            event_count = 0
            start_date = config_details.get('start_date')
            params = None
            if start_date:
                start_date_formated = datetime.datetime.utcfromtimestamp(
                    int(start_date) / 1000).strftime(self.time_format)
                params = {"filter": "created>='{}'".format(start_date_formated)}
            helper.log_info('type={} name={} msg=Getting volume details from array REST service for {}'.format(
                config_details['host'], config_details["input_type"], config_details["stanza"]))
            path = self.create_path(
                config_details, "volume")
            volumes_details = self._request(
                "GET", path, helper, config_details, reestablish_session=True, params=params)
            path = self.create_path(config_details, "volume?space=true")
            array_details_with_space_true = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            updated_volume_details = merge_lists(
                volumes_details, array_details_with_space_true, 'name')
            if params:
                params = {"filter": "time>='{}'".format(start_date_formated)}
            path = self.create_path(
                config_details, "volume?action=monitor&mirrored=true")
            array_details_with_action_monitor = self._request(
                "GET", path, helper, config_details, reestablish_session=True, params=params)
            updated_volume_details_with_monitor_true = None
            if array_details_with_action_monitor or updated_volume_details:
                updated_volume_details_with_monitor_true = merge_lists(
                    updated_volume_details, array_details_with_action_monitor, 'name')

            # time field is obtained from the monitor call
            if updated_volume_details_with_monitor_true:
                # Don't add below loop for API v2.x since Source field is not coming for volume space and performance
                for index, row in enumerate(updated_volume_details_with_monitor_true):
                    source = row.get('source', 'NO_SOURCE_KEY')
                    if source != 'NO_SOURCE_KEY':
                        del row['source']
                    else:
                        source = None
                    row['source_volume'] = source
                additional_fields = {}
                additional_fields['time_field'] = 'time'
                additional_fields['host'] = config_details['host']
                utils.ingest_in_splunk(
                    helper,
                    ew,
                    updated_volume_details_with_monitor_true,
                    SourceType.sourcetype_volume,
                    additional_fields,
                    source=Source.source_volume,
                )
                event_count = len(updated_volume_details_with_monitor_true)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed"
                " for volume data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for volume data.".format(config_details["input_type"], config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting volume data: {}".format(
                    config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_volume_snap_details(self, helper, ew, array, config_details):
        """
        Description: Fetch flash array volume snapshots details.

        Parameters: helper: helper object
                    ew: log object
                    array: array name
                    config_details: Config details of array
        """
        # We expect the 'created' field to be extracted as the event time for Snapshots
        # and no time field for pgroups (will get the current time)
        try:
            event_count = 0
            helper.log_info(
                'type={} name={} msg=Getting pgroup details'
                ' from array REST service for {}'.format(config_details["input_type"],
                                                         config_details["stanza"], config_details['host']))
            path = self.create_path(config_details, "pgroup")
            # Getting protection group information
            snapshot_details = []
            try:
                pgroup_list = self._request("GET", path, helper,
                                            config_details, reestablish_session=True)
                path = self.create_path(config_details, "pgroup?space=true")
                space_details = self._request(
                    "GET", path, helper, config_details, reestablish_session=True)
                pgroup_list = merge_lists(pgroup_list, space_details, "name")
                if pgroup_list:
                    for row in pgroup_list:
                        del row['source']
                additional_fields = {}
            except Exception as e:
                helper.log_error(
                    "type={} name={} msg=PureStorage Error: "
                    " while collecting pgroup data: {}".format(config_details["input_type"],
                                                               config_details["stanza"], e))
                helper.log_debug(traceback.format_exc())
            if pgroup_list:
                additional_fields['host'] = config_details['host']
                utils.ingest_in_splunk(helper, ew, pgroup_list, SourceType.sourcetype_pgroup,
                                       additional_fields, source=Source.source_pgroup)
                event_count = len(pgroup_list)
                helper.log_debug(
                    "type={} name={} msg=PureStorage Debug: data collection completed "
                    "for pgroup data.".format(config_details["input_type"], config_details["stanza"]))
                pgroup_list = [x['name'] for x in pgroup_list]
            else:
                helper.log_debug("type={} name={} msg=PureStorage"
                                 "Debug: No data found for {}"
                                 .format(config_details["input_type"],
                                         config_details["stanza"], SourceType.sourcetype_pgroup))
                pgroup_list = []
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for pgroup data.".format(config_details["input_type"], config_details["stanza"], event_count))
            event_count = 0
            helper.log_info(
                'type={} name={} msg=Getting volume snap details from array REST service for {}'.format(
                    config_details["input_type"], config_details["stanza"], config_details['host'])
            )
            config_details['start_date'] = helper.get_arg('start_date')
            utils.get_checkpoint(
                helper, config_details, SourceType.sourcetype_snapshots, "/Snapshots"
            )

            start_date = config_details.get('start_date')
            params = {"snap": "true"}
            if start_date:
                start_date_formated = datetime.datetime.utcfromtimestamp(
                    int(start_date) / 1000
                ).strftime(self.time_format)
                params["filter"] = "created>='{}'".format(start_date_formated)
            path = self.create_path(
                config_details, "volume")
            all_snap = self._request("GET", path, helper,
                                     config_details, reestablish_session=True, params=params)
            if params.get("filter"):
                del params["filter"]
            params["space"] = "true"
            path = self.create_path(
                config_details, "volume")
            all_space = self._request("GET", path, helper,
                                      config_details, reestablish_session=True, params=params)
            temp = merge_lists(all_snap, all_space, 'name')
            if temp:
                for snap in temp:
                    if str(snap['name']).startswith(tuple(pgroup_list)):
                        group = snap['name'].split('.')[0]
                        snap.update({"pgroup": group})
                    if snap.get("source"):
                        snap['volume'] = snap['source']
                        del snap['source']
                    snapshot_details.append(snap)
            if snapshot_details:
                additional_fields = {}
                additional_fields['host'] = config_details['host']
                utils.ingest_in_splunk(helper, ew, snapshot_details, SourceType.sourcetype_snapshots,
                                       additional_fields, source=Source.source_snapshots)
                event_count = len(snapshot_details)
                utils.update_checkpoint(helper, config_details)
                helper.log_debug(
                    "type={} name={} msg=PureStorage Debug: "
                    " data collection completed for "
                    "snapshots data.".format(config_details["input_type"], config_details["stanza"]))
            else:
                helper.log_debug("type={} name={} msg=PureStorage Debug: No data "
                                 "collected for {}".format(config_details["input_type"],
                                                           config_details["stanza"], SourceType.sourcetype_snapshots))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: "
                "data collection completed for "
                "volume snap data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for volume snap data.".format(config_details["input_type"], config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error:"
                " while collecting snapshots data: {}".format(config_details["input_type"],
                                                              config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_protection_group_volumes(self, helper, config_details):
        """
        Description: Fetch flash array volume snapshots details.

        Parameters: helper: helper object
                    config_details: Config details of array
        """
        try:
            helper.log_info(
                'type={} name={} msg=Getting protection-groups/volumes details from array '
                'REST service for {}'.format(config_details["input_type"],
                                             config_details["stanza"], config_details['host']))
            path = self.create_path(config_details, "protection-groups/volumes")

            # Getting protection group information
            pgroup_items = []
            pgroup_dict = {}

            params = {"offset": 0}
            while True:
                pgroup_api_response = self._request("GET", path, helper,
                                                    config_details, params=params)
                if pgroup_api_response:
                    pgroup_items = pgroup_api_response.get("items", [])
                    if len(pgroup_items) > 0:
                        for resp in pgroup_items:
                            # The group_names parameter represents the name of the protection group881919
                            # The member_names parameter represents the name of the volume.
                            pgroup_name = str(resp.get("group").get("name"))
                            if pgroup_name in pgroup_dict.keys():
                                pgroup_dict[pgroup_name].append(str(resp.get("member").get("name")))
                            else:
                                pgroup_dict[pgroup_name] = [str(resp.get("member").get("name"))]

                    if not pgroup_api_response.get("more_items_remaining"):
                        break
                    else:
                        params["offset"] += len(pgroup_items)
                else:
                    break
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: "
                "while collecting protection-groups/volumes "
                "data: {}".format(config_details["input_type"], config_details["stanza"], e))
        return pgroup_dict

    def get_host_details(self, helper, ew, array, config_details):
        """
        Description: Fetch flash array host details.

        Parameters: helper: helper object
                    ew: log object
                    array: array name
                    config_details: Config details of array
        """
        # There is no datetime field extracted from the host level calls
        # We are manually ingesting the current time as a 'time' field
        try:
            event_count = 0
            helper.log_info('type={} name={} msg=Getting host details from array REST service for {}'.format(
                config_details["input_type"], config_details["stanza"], config_details['host']))
            path = self.create_path(config_details, "host")
            hosts_details = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            path = self.create_path(config_details, "host?all=true")
            hosts_details_with_all_true = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            if hosts_details and hosts_details_with_all_true:
                for host in hosts_details:
                    volumes = set()
                    host_name = host.get('name')
                    for item in hosts_details_with_all_true:
                        if item.get('name') == host_name:
                            volumes.add(item.get('vol'))
                    host.update({"vols": list(volumes)})
            additional_fields = {}
            additional_fields['host'] = config_details['host']
            if hosts_details:
                utils.ingest_in_splunk(helper, ew, hosts_details, SourceType.sourcetype_host,
                                       additional_fields, source=Source.source_host)
                event_count += len(hosts_details)
            path = self.create_path(config_details, "host?space=true")
            hosts_details = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            if hosts_details:
                additional_fields['host'] = config_details['host']
                utils.ingest_in_splunk(helper, ew, hosts_details, SourceType.sourcetype_host,
                                       additional_fields, source=Source.source_host)
                event_count += len(hosts_details)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed for "
                "hosts data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for hosts data.".format(config_details["input_type"], config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting hosts data: {}".format(
                    config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_alert_audit_session_logs(self, helper, ew, config_details, endpoint_details_dict):
        """
        Description: Fetch flash array alert/audit/session details.

        Parameters: helper: helper object
                    ew: log object
                    config_details: Config details of array
                    endpoint_details_dict: Dict holding below details:
                    * endpoint: Hit this FA endpoint
                    * sort_field: Sorting parameter for API call
                    * filter_parameter: Filter parameter for API call
                    * time_field: Value to be given in _time field in Splunk
                    * source: Ingest data in given source in Splunk
                    * sourcetype: Ingest data in given sourcetype in Splunk
        """
        helper.log_info(
            'type={} name={} msg=Getting {} details from array REST service'
            ' for {}'.format(config_details["input_type"], config_details["stanza"],
                             endpoint_details_dict["endpoint"], config_details['host']))
        try:
            params = {}
            params["sort"] = endpoint_details_dict["sort_field"]
            utils.get_checkpoint(helper, config_details,
                                 endpoint_details_dict["sourcetype"], endpoint_details_dict["endpoint"])

            start_date = config_details.get("start_date")
            if start_date:
                # If Kvstore is empty and json file is not empty refer to JSON File
                # If Kvstore is empty and json file is empty refer to user configured start date
                # If Kvstore is not empty and json file is not empty refer to KVStore
                # If Kvstore is not empty and json file is empty refer to KVStore

                if not config_details.get(endpoint_details_dict["sourcetype"]):
                    file_start_date = get_checkpoint_from_file(
                        helper, endpoint_details_dict["sourcetype"])
                    if file_start_date:
                        start_date = file_start_date
                start_date = utils.reset_time_to_7d(helper, config_details, start_date,
                                                    endpoint_details_dict["endpoint"])

                params["filter"] = "{}>'{}'".format(
                    endpoint_details_dict["filter_parameter"], utils.convert_to_epoch(start_date))

            while True:
                path = self.create_path(config_details, endpoint_details_dict["endpoint"])
                alert_details = self._request(
                    "GET", path, helper, config_details, params=params, reestablish_session=True)
                if alert_details:
                    alert_details_items = alert_details.get("items", [])
                    if len(alert_details_items) > 0:
                        additional_fields = {}
                        additional_fields['time_field'] = endpoint_details_dict["time_field"]
                        additional_fields['host'] = config_details['host']
                        utils.ingest_in_splunk(helper, ew, alert_details_items, endpoint_details_dict["sourcetype"],
                                               additional_fields, source=endpoint_details_dict["source"],
                                               config_details=config_details)
                        # Instead of storing offset: Store latest value of
                        # additional_fields['time_field'] coming in API in checkpoint
                        # For sessions data checkpoint, either store value of start_time if it's not null in the API
                        # response or store the current time in the checkpoint.

                        utils.update_checkpoint(helper, config_details, store_offset=False)
                        helper.log_debug(
                            'type={} name={} msg=PureStorage Debug: Ingested {} {} records with params: {} for '
                            ' {}'.format(config_details["input_type"], config_details["stanza"],
                                         len(alert_details_items), endpoint_details_dict["endpoint"],
                                         params, config_details['host']))
                    if not alert_details.get("more_items_remaining"):
                        break
                    else:
                        config_details['offset'] += len(alert_details_items)
                        params["offset"] = config_details['offset']
                else:
                    break
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: "
                "while collecting {} data: {}".format(config_details["input_type"],
                                                      config_details["stanza"], endpoint_details_dict["endpoint"], e))
            helper.log_debug(traceback.format_exc())

        helper.log_debug(
            "type={} name={} msg=PureStorage Debug: Data collection"
            " completed for {} data.".format(config_details["input_type"],
                                             config_details["stanza"], endpoint_details_dict["endpoint"]))

    def get_message_details(self, helper, ew, array, config_details):
        """
        Description: Fetch flash array alert details.

        Parameters: helper: helper object
                    ew: log object
                    array: array name
                    config_details: Config details of array
        """
        time_format = self.time_format
        date_7d_ago = None
        if not config_details['collect_historical_data']:
            helper.log_warning(
                "type={} name={} msg=Collecting data of last 7 days"
                " for message endpoint.".format(config_details["input_type"],
                                                config_details["stanza"]))
            date_7d_ago = config_details.get('end_date') - (7 * 86400 * 1000)

        try:
            event_count = 0
            # The time field is extracted from 'opened' column
            stanza_name = str(helper.get_input_stanza_names())
            # Alert logs
            helper.log_info(
                'type={} name={} msg=Getting alert and messages details'
                ' from array REST service for {}'.format(config_details["input_type"],
                                                         config_details["stanza"], config_details['host']))
            path = self.create_path(config_details, "message")
            alert_details = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            if alert_details:
                alert_details = update_log_state(
                    alert_details, stanza_name, "log_alert", date_7d_ago, time_format)
                # removing this line to match the count with UI of product
                # alert_details = remove_duplicates(alert_details, "log_alert")
                additional_fields = {}
                additional_fields['time_field'] = 'opened'
                additional_fields['host'] = config_details['host']
                event_count = len(alert_details)
                utils.ingest_in_splunk(helper, ew, alert_details, SourceType.sourcetype_alert_logs,
                                       additional_fields, source=Source.source_alert_logs)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug:"
                " data collection completed for"
                " alert_log data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for alert_log data.".format(config_details["input_type"], config_details["stanza"], event_count))

        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: "
                "while collecting log_alert data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

        try:
            event_count = 0
            # Audit logs
            helper.log_info(
                'type={} name={} msg=Getting audit alert and messages '
                'details from array REST service for {}'.format(
                    config_details["input_type"], config_details["stanza"], config_details['host'])
            )
            path = self.create_path(config_details, "message?audit=true")
            alert_details = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            if alert_details:
                alert_details = update_log_state(
                    alert_details, stanza_name, "log_audit", date_7d_ago, time_format)
                additional_fields['host'] = config_details['host']
                event_count = len(alert_details)
                utils.ingest_in_splunk(helper, ew, alert_details, SourceType.sourcetype_alert_audit,
                                       additional_fields, source=Source.source_alert_audit)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed "
                "for alert_audit data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for alert_audit data.".format(config_details["input_type"], config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error("type={} name={} msg=PureStorage Error: "
                             " while collecting "
                             "log_audit data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())
        try:
            event_count = 0
            # Login logs
            helper.log_info(
                'type={} name={} msg=Getting login alert and messages details '
                'from array REST service for {}'.format(
                    config_details["input_type"], config_details["stanza"], config_details['host'])
            )
            path = self.create_path(config_details, "message?login=true")
            alert_details = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            if alert_details:
                alert_details = update_log_state(
                    alert_details, stanza_name, "log_login", date_7d_ago, time_format)
                additional_fields['host'] = config_details['host']
                event_count = len(alert_details)
                utils.ingest_in_splunk(helper, ew, alert_details, SourceType.sourcetype_alert_login,
                                       additional_fields, source=Source.source_alert_login)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection"
                " completed for alert_login data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for alert_login data.".format(config_details["input_type"], config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: "
                "while collecting log_login data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def set_date_and_resolution(self, params, helper, config_details, endpoint, get_perf_data):
        """
        Returns a list of dictionary which specifies start_time, end_time and resolution for Performance Data.

            for first 3 hours -> 30s resolution
            for next 24 hours -> 5m resolution
            for next 7 days -> 30m resolution
            for next 30 days -> 2h resolution
            for next 366 days -> 1d resolution

        Returns a list of dictionary which specifies start_time, end_time and resolution for Space Data.

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
            'time': 0,
            'resolution': 300000
        }]

        if get_perf_data == "performance":
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
            "type={} name={} msg=PureStorage Debug: time and resolution"
            " distribution for {} {}".format(config_details["input_type"],
                                             config_details["stanza"], endpoint, get_perf_data))
        helper.log_debug('\n'.join(
            'type={} name={} msg=PureStorage Debug: for start_time -> {} to end_time -> '
            '{} with resolution -> {}'.format(config_details["input_type"],
                                              config_details["stanza"], time.ctime(x['start_time'] / 1000),
                                              time.ctime(x['end_time'] / 1000), x['resolution'])
            for x in date_resolution_list))
        return date_resolution_list

    def get_space_performance_details(self, helper, ew, config_details, endpoint_details_dict):
        """
        Description: Fetch flash array alert details.

        Parameters: helper: helper object
                    ew: log object
                    array: array name
                    config_details: Config details of array
                    endpoint_details_dict: Dict holding below details:
                    * endpoint: Hit this FA endpoint
                    * time_field: Value to be given in _time field in Splunk
                    * source: Ingest data in given source in Splunk
                    * sourcetype: Ingest data in given sourcetype in Splunk
        """
        helper.log_info(
            'type={} name={} msg=Getting {} details from array REST '
            'service for {}'.format(config_details["input_type"], config_details["stanza"],
                                    endpoint_details_dict["endpoint"], config_details['host']))
        params = {}
        params["sort"] = endpoint_details_dict["time_field"]
        params["end_time"] = config_details['end_date']

        for space_perf in endpoint_details_dict["space_perf_list"]:
            utils.get_checkpoint(helper, config_details,
                                 endpoint_details_dict["sourcetype"],
                                 endpoint_details_dict["endpoint"], space_perf=space_perf)

            start_date = config_details.get("start_date")

            params["start_time"] = start_date
            flag = True
            try:
                date_resolution_list = self.set_date_and_resolution(
                    params, helper, config_details, endpoint_details_dict["endpoint"], space_perf)
                path = self.create_path(config_details, "{}/{}".format(endpoint_details_dict["endpoint"], space_perf))
                for parameters in date_resolution_list:
                    while True:
                        params["start_time"] = parameters["start_time"]
                        params["end_time"] = parameters["end_time"]
                        params["resolution"] = parameters["resolution"]

                        api_details = self._request("GET", path, helper, config_details, params=params)
                        if api_details:
                            api_details_items = api_details.get("items", [])
                            if len(api_details_items) > 0:
                                additional_fields = {}
                                additional_fields['time_field'] = endpoint_details_dict["time_field"]
                                additional_fields['host'] = config_details['host']

                                # Ingest fields in v2.x just like v1.x
                                if endpoint_details_dict['endpoint'] == "arrays":
                                    additional_fields['array_name'] = config_details.get('array_name')
                                if space_perf == "space" and endpoint_details_dict["endpoint"] == "protection-groups":
                                    # Get volume name from /protection-groups/volumes endpoint
                                    # and ingest it as a part of /protection-groups/space response.
                                    orig_api_details_items = api_details_items
                                    api_details_items = []
                                    for snap in orig_api_details_items:
                                        if str(snap['name']) in endpoint_details_dict["protection_group_volumes"]:
                                            snap.update(
                                                {"volumes": endpoint_details_dict["protection_group_volumes"][snap['name']]})  # noqa E501
                                        api_details_items.append(snap)
                                utils.ingest_in_splunk(helper, ew, api_details_items,
                                                       endpoint_details_dict["sourcetype"], additional_fields,
                                                       source="{}:{}".format(endpoint_details_dict["source"],
                                                                             space_perf))
                                config_details["chkpt_date"] = params["end_time"]
                                utils.update_checkpoint(helper, config_details)
                                helper.log_debug(
                                    'type={} name={} msg=PureStorage Debug: Ingested {} records in {} {} '
                                    'with params: {} for {}'.format(config_details["input_type"],
                                                                    config_details["stanza"],
                                                                    len(api_details_items),
                                                                    endpoint_details_dict["endpoint"],
                                                                    space_perf, params, config_details['host']))
                            if not api_details.get("more_items_remaining"):
                                break
                            else:
                                config_details['offset'] += len(api_details_items)
                                params["offset"] = config_details['offset']
                        else:
                            break

            except Exception as e:
                flag = False
                helper.log_error(
                    "type={} name={} msg=PureStorage Error: while collecting {}"
                    " {} data: {}".format(config_details["input_type"],
                                          config_details["stanza"],
                                          endpoint_details_dict["endpoint"], space_perf, e))
                helper.log_debug(traceback.format_exc())

            # The common code ingests offset as checkpoint key. Offset is not needed for this call.
            # Set offset to None, to avoid storing in checkpoint.
            if flag:
                config_details["offset"] = None
                config_details["chkpt_date"] = config_details.get('end_date')
                utils.update_checkpoint(helper, config_details)

            helper.log_debug(
                "type={} name={} msg=Data collection completed"
                " for {} {} data.".format(config_details["input_type"], config_details["stanza"],
                                          endpoint_details_dict["endpoint"], space_perf))

    def get_volume_snapshots(self, helper, ew, config_details):
        """
        Description: Fetch flash array volume snapshots details.

        Parameters: helper: helper object
                    ew: log object
                    config_details: Config details of array
        """
        try:
            helper.log_info(
                'type={} name={} msg=Getting protection-groups details '
                'from array REST service for {}'.format(config_details["input_type"],
                                                        config_details["stanza"], config_details['host']))
            path = self.create_path(config_details, "protection-groups")

            # Getting protection group information
            pgroup_name_list = []
            params = {"offset": 0}
            while True:
                pgroup_api_response = self._request("GET", path, helper,
                                                    config_details, params=params)
                if pgroup_api_response:
                    pgroup_items = pgroup_api_response.get("items", [])
                    if len(pgroup_items) > 0:
                        for resp in pgroup_items:
                            pgroup_name_list.append(str(resp["name"]))
                    if not pgroup_api_response.get("more_items_remaining"):
                        break
                    else:
                        params["offset"] += len(pgroup_items)
                else:
                    break
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting"
                " protection-groups data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

        try:
            event_count = 0
            helper.log_info(
                'type={} name={} msg=Getting volume-snapshots details from array REST'
                ' service for {}'.format(config_details["input_type"],
                                         config_details["stanza"],
                                         config_details['host']))
            path = self.create_path(config_details, "volume-snapshots")

            # Getting protection group information
            volume_snapshots_items = []
            params = {"offset": 0}
            additional_fields = {}
            additional_fields['host'] = config_details['host']
            while True:
                volume_snapshots_response = self._request("GET", path, helper,
                                                          config_details, params=params)
                if volume_snapshots_response:
                    volume_snapshots_items = volume_snapshots_response.get("items", [])
                    if len(volume_snapshots_items) > 0:
                        orig_api_details_items = volume_snapshots_items
                        api_details_items = []
                        for snap in orig_api_details_items:
                            if str(snap['name']).startswith(tuple(pgroup_name_list)):
                                group = snap['name'].split('.')[0]
                                snap.update({"pgroup": group})
                            if snap.get("source"):
                                snap['volume_source'] = snap['source']
                                del snap['source']
                            api_details_items.append(snap)
                        event_count += len(api_details_items)
                        utils.ingest_in_splunk(helper, ew, api_details_items, SourceType.sourcetype_snapshots,
                                               additional_fields, source=Source.source_snapshots)
                    if not volume_snapshots_response.get("more_items_remaining"):
                        break
                    else:
                        params["offset"] += len(volume_snapshots_items)
                else:
                    break

            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection"
                " completed for volume-snapshots data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for volume-snapshots data.".format(config_details["input_type"],
                                                     config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting"
                " volume-snapshots data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_host_connections(self, helper, ew, config_details):
        """
        Description: Fetch flash array hosts and connections details for API v2.x.

        Parameters: helper: helper object
                    ew: log object
                    config_details: Config details of array
        """
        # Getting connections endpoint information
        host_volume_dict = {}

        try:
            helper.log_info(
                'type={} name={} msg=Getting connection details '
                'from array REST service for {}'.format(config_details["input_type"],
                                                        config_details["stanza"], config_details['host']))
            path = self.create_path(config_details, "connections")

            params = {"offset": 0}
            while True:
                connection_api_response = self._request("GET", path, helper,
                                                        config_details, params=params)
                if connection_api_response:
                    connection_items = connection_api_response.get("items", [])
                    if len(connection_items) > 0:
                        for resp in connection_items:
                            key = str(resp["host"]["name"])
                            if key in host_volume_dict:
                                host_volume_dict[key].append(str(resp["volume"]["name"]))
                            else:
                                host_volume_dict[key] = [str(resp["volume"]["name"])]
                    if not connection_api_response.get("more_items_remaining"):
                        break
                    else:
                        params["offset"] += len(connection_items)
                else:
                    break
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting"
                " connections data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

        event_count = 0
        try:
            helper.log_info(
                'type={} name={} msg=Getting hosts details '
                'from array REST service for {}'.format(config_details["input_type"],
                                                        config_details["stanza"], config_details['host']))
            path = self.create_path(config_details, "hosts")

            params = {"offset": 0}

            additional_fields = {}
            additional_fields['host'] = config_details['host']

            while True:
                host_api_response = self._request("GET", path, helper,
                                                  config_details, params=params)
                if host_api_response:
                    host_items = host_api_response.get("items", [])
                    if len(host_items) > 0:
                        if len(host_volume_dict) > 0:
                            for resp in host_items:
                                host_name = str(resp["name"])
                                if host_name in host_volume_dict:
                                    resp["vols"] = host_volume_dict[host_name]
                        utils.ingest_in_splunk(helper, ew, host_items, SourceType.sourcetype_host,
                                               additional_fields, source=Source.source_host)
                        event_count += len(host_items)
                    if not host_api_response.get("more_items_remaining"):
                        break
                    else:
                        params["offset"] += len(connection_items)
                else:
                    break
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed for "
                "hosts data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for hosts data.".format(config_details["input_type"], config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while collecting"
                " hosts data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_pod_details(self, helper, ew, array, config_details):
        """
        Description: Fetch flash array pod details.

        Parameters: helper: helper object
                    ew: log object
                    array: array name
                    config_details: Config details of array
        """
        try:
            event_count = 0
            helper.log_info('type={} name={} msg=Getting pod details from array REST service for {}'.format(
                config_details["input_type"], config_details["stanza"], config_details['host']))
            path = self.create_path(
                config_details, "pod")
            pods_details = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            path = self.create_path(config_details, "pod?space=true")
            pod_details_with_space_true = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            updated_pod_details = merge_lists(
                pods_details, pod_details_with_space_true, 'name')
            path = self.create_path(config_details, "pod?footprint=true")
            pod_details_with_footprint_true = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            updated_pod_details_with_footprint_true = merge_lists(
                updated_pod_details, pod_details_with_footprint_true, 'name')
            path = self.create_path(
                config_details, "pod?action=monitor&mirrored=true")
            pod_details_with_action_monitor = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            updated_pod_details_with_monitor_true = None
            if pod_details_with_action_monitor or updated_pod_details_with_footprint_true:
                updated_pod_details_with_monitor_true = merge_lists(
                    updated_pod_details_with_footprint_true, pod_details_with_action_monitor, 'name')

            # time field is obtained from the monitor call
            if updated_pod_details_with_monitor_true:
                additional_fields = {}
                additional_fields['time_field'] = 'time'
                additional_fields['host'] = config_details['host']
                utils.ingest_in_splunk(helper, ew, updated_pod_details_with_monitor_true, SourceType.sourcetype_pod,
                                       additional_fields, source=Source.source_pod)
                event_count = len(updated_pod_details_with_monitor_true)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection completed "
                "for pod data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for pod data.".format(config_details["input_type"], config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error:"
                " while collecting pod data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def get_vgroup_details(self, helper, ew, array, config_details):
        """
        Description: Fetch flash array vgroup details.

        Parameters: helper: helper object
                    ew: log object
                    array: array name
                    config_details: Config details of array
        """
        try:
            event_count = 0
            utils.get_checkpoint(helper, config_details,
                                 "purestorage:flasharray:vgroups", "/vgroups")
            start_date = config_details.get('start_date')
            start_date_formated = datetime.datetime.utcfromtimestamp(
                int(start_date) / 1000).strftime(self.time_format)
            helper.log_info('type={} name={} msg=Getting vgroup details from array REST service for {}'.format(
                config_details["input_type"], config_details["stanza"], config_details['host']))
            path = self.create_path(
                config_details, "vgroup")
            vgroups_details = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            for item in vgroups_details:
                item["volume_names"] = item["volumes"]
            path = self.create_path(config_details, "vgroup?space=true")
            vgroup_details_with_space_true = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            updated_vgroup_details = merge_lists(
                vgroups_details, vgroup_details_with_space_true, 'name')
            path = self.create_path(
                config_details, "vgroup?action=monitor&filter=time>='{}'".format(start_date_formated))
            vgroup_details_with_action_monitor = self._request(
                "GET", path, helper, config_details, reestablish_session=True)
            updated_vgroup_details_with_monitor_true = None
            if vgroup_details_with_action_monitor or updated_vgroup_details:
                updated_vgroup_details_with_monitor_true = merge_lists(
                    updated_vgroup_details, vgroup_details_with_action_monitor, 'name')

            # time field is obtained from the monitor call
            if updated_vgroup_details_with_monitor_true:
                additional_fields = {}
                additional_fields['time_field'] = 'time'
                additional_fields['host'] = config_details['host']
                utils.ingest_in_splunk(helper, ew, updated_vgroup_details_with_monitor_true,
                                       SourceType.sourcetype_vgroup, additional_fields, source=Source.source_vgroup)
                event_count = len(updated_vgroup_details_with_monitor_true)
            utils.update_checkpoint(helper, config_details)
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: data collection"
                " completed for vgroup data.".format(config_details["input_type"], config_details["stanza"]))
            helper.log_debug(
                "type={} name={} msg=PureStorage Debug: Ingested {} events"
                " for vgroup data.".format(config_details["input_type"], config_details["stanza"], event_count))
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: while "
                "collecting vgroup data: {}".format(config_details["input_type"], config_details["stanza"], e))
            helper.log_debug(traceback.format_exc())

    def _choose_rest_version(self, helper, config_details):
        """Return the newest REST API version supported by target array."""
        versions = self._list_available_rest_versions(helper, config_details)
        versions = [x for x in versions if x in self.supported_rest_versions]
        if versions:
            return max(versions, key=StrictVersion)
        else:
            return "1.8"

    def _list_available_rest_versions(self, helper, config_details):
        """Return a list of the REST API versions supported by the array."""
        server_address = config_details['server_address']
        url = "{0}/api/api_version".format(server_address)
        data = self._request("GET", url, helper,
                             config_details, reestablish_session=False, set_headers=False)
        if data:
            return data["version"]
        else:
            return []

    def create_path(self, config_details, endpoint):
        """Create URI."""
        path = "{}/api/{}/{}".format(
            config_details['server_address'], config_details['api_version'], endpoint)
        return path

    def _start_session(self, helper, config_details):
        """Start a REST API session."""
        api_token = config_details['api_token']
        data = None
        headers = {}

        # API token is passed in data for API v1.x
        # API token is passed in header for API v2.x

        if int(config_details['api_version'].split(".")[0]) == 2:
            path = self.create_path(config_details, "login")
            headers = {'api-token': api_token}
        else:
            path = self.create_path(config_details, "auth/session")
            data = {'api_token': api_token}
            data = json.dumps(data).encode("utf-8")
        self._request("POST", path, helper, config_details, data,
                      reestablish_session=False, headers=headers)

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
        config_details["input_type"] = helper.get_arg('input_type')
        config_details["stanza"] = stanza_name

        # Getting Splunk Version
        splunk_version = ver.__version__
        if not splunk_version:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: unable to "
                "fetch splunk version.".format(config_details["input_type"], config_details["stanza"]))
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
        array = server_address.split("https://")[1]
        config_details['host'] = array
        config_details['user_agent'] = "Splunk/{}".format(splunk_version)
        config_details['end_date'] = current_time
        config_details['proxy_settings'] = proxy_settings
        config_details['verify_ssl'] = verify_ssl
        config_details['api_token'] = api_token
        config_details['x-auth-token'] = None

        # Handle Upgrade Scenario
        config_details['collect_historical_data'] = True
        if helper.get_arg('historical_data'):
            config_details['collect_historical_data'] = is_true(helper.get_arg('historical_data'))
        enable_disable = "enabled" if config_details['collect_historical_data'] else "disabled"

        helper.log_warning("type={} name={} msg=PureStorage Warning: Historical data collection is {}.".format(
            config_details["input_type"], config_details["stanza"], enable_disable))

        rest_version = self._choose_rest_version(helper, config_details)
        if rest_version:
            config_details['api_version'] = rest_version
        else:
            config_details['api_version'] = "1.18"
        self.rest_version = config_details['api_version']
        config_details['major_api_version'] = int(config_details['api_version'].split(".")[0])

        start_time = time.time()

        # Login on PureStorage Server and create session
        self._start_session(helper, config_details)

        helper.log_debug("type={} name={} msg=PureStorage Debug: connection established.".format(
            config_details["input_type"], config_details["stanza"]))
        # Function calls for collect data from different REST Endpoints.

        # Alert, Audit and Login/Session Details
        if config_details['major_api_version'] == 2:
            dict_of_params = {}
            dict_of_params["alert_endpoint"] = {"endpoint": "alerts", "sort_field": "updated",
                                                "filter_parameter": "updated", "time_field": "updated",
                                                "sourcetype": SourceType.sourcetype_alert_logs,
                                                "source": Source.source_alert_logs}
            dict_of_params["audit_endpoint"] = {"endpoint": "audits", "sort_field": "time",
                                                "filter_parameter": "time", "time_field": "time",
                                                "sourcetype": SourceType.sourcetype_alert_audit,
                                                "source": Source.source_alert_audit}
            dict_of_params["session_endpoint"] = {"endpoint": "sessions", "sort_field": "start_time",
                                                  "filter_parameter": "start_time", "time_field": "start_time",
                                                  "sourcetype": SourceType.sourcetype_alert_login,
                                                  "source": Source.source_alert_login,
                                                  "min_api_version": "2.4"}

            for endpoint_details_dict in dict_of_params.values():
                # Min API version for sessions endpoint is 2.4
                if endpoint_details_dict.get("min_api_version"):
                    config_details['api_version'] = endpoint_details_dict.get("min_api_version")
                else:
                    config_details['api_version'] = self.rest_version
                config_details['major_api_version'] = int(config_details['api_version'].split(".")[0])
                self.get_alert_audit_session_logs(helper, ew, config_details, endpoint_details_dict)

            # Set back orig version
            config_details['api_version'] = self.rest_version
            config_details['major_api_version'] = int(config_details['api_version'].split(".")[0])

            historical_endpoint_dict = {}
            # Array details

            self.get_arrays_details(helper, ew, config_details)

            # Fetch Historical data
            # Array details
            historical_endpoint_dict["arrays"] = {"endpoint": "arrays", "time_field": "time",
                                                  "source": Source.source_array,
                                                  "sourcetype": SourceType.sourcetype_array,
                                                  "space_perf_list": ["space", "performance"]}

            # Volume details
            historical_endpoint_dict["volumes"] = {"endpoint": "volumes", "time_field": "time",
                                                   "source": Source.source_volume,
                                                   "sourcetype": SourceType.sourcetype_volume,
                                                   "space_perf_list": ["space", "performance"]}

            # Hosts details
            historical_endpoint_dict["hosts"] = {"endpoint": "hosts", "time_field": "time",
                                                 "source": Source.source_host,
                                                 "sourcetype": SourceType.sourcetype_host,
                                                 "space_perf_list": ["space"]}
            # Get volumes for protection groups
            pgroup_dict = self.get_protection_group_volumes(helper, config_details)

            # Protection Group details
            historical_endpoint_dict["pgroups"] = {"endpoint": "protection-groups", "time_field": "time",
                                                   "source": Source.source_pgroup,
                                                   "sourcetype": SourceType.sourcetype_pgroup,
                                                   "space_perf_list": ["space"],
                                                   "protection_group_volumes": pgroup_dict}

            # Pod details
            historical_endpoint_dict["pods"] = {"endpoint": "pods", "time_field": "time",
                                                "source": Source.source_pod,
                                                "sourcetype": SourceType.sourcetype_pod,
                                                "space_perf_list": ["space", "performance"]}

            # Volume Groups details
            historical_endpoint_dict["volume-groups"] = {"endpoint": "volume-groups", "time_field": "time",
                                                         "source": Source.source_vgroup,
                                                         "sourcetype": SourceType.sourcetype_vgroup,
                                                         "space_perf_list": ["space", "performance"]}

            for space_perf_endpoint_dict in historical_endpoint_dict.values():
                self.get_space_performance_details(helper, ew, config_details, space_perf_endpoint_dict)

            # Get Host details
            self.get_host_connections(helper, ew, config_details)

            # Get volume-snapshots details
            pgroup_dict = self.get_volume_snapshots(helper, ew, config_details)

        else:
            self.get_message_details(helper, ew, server_address, config_details)

            # Array details
            self.get_array_details(helper, ew, server_address, config_details)

            # Volume details
            self.get_volume_details(helper, ew, server_address, config_details)

            # Volume snapshot and protection group details
            self.get_volume_snap_details(
                helper, ew, server_address, config_details)

            # Host details
            self.get_host_details(helper, ew, server_address, config_details)

            # Pod details
            self.get_pod_details(helper, ew, server_address, config_details)

            # Vgroup details
            self.get_vgroup_details(helper, ew, server_address, config_details)

        headers = {"Content-Type": "application/json"}
        headers['User-Agent'] = config_details.get('user_agent')
        data = None
        if int(config_details['api_version'].split(".")[0]) == 2:
            path = self.create_path(config_details, "login")
            headers = {'api-token': api_token}
        else:
            path = self.create_path(config_details, "auth/session")
            data = {'api_token': api_token}
            data = json.dumps(data).encode("utf-8")
        try:
            requests.request(
                "DELETE", path, data=data, headers=headers, verify=verify_ssl)
        except Exception as e:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: unable to terminate"
                " session: {}".format(config_details["input_type"], stanza_name, e))
            helper.log_debug(traceback.format_exc())

        helper.log_info("type={} name={} msg=PureStorage Info: Done with FlashArray data collection. "
                        "Time taken: {} minutes for: {}.".format(config_details["input_type"],
                                                                 stanza_name, ((time.time() - start_time) / 60),
                                                                 stanza_name))


class Source:
    """Description: Class maintain flash array source details."""

    source_array = "Array"
    source_volume = "Volumes"
    source_host = "Hosts"
    source_alert_logs = "Logs_Alerts"
    source_alert_login = "Logs_Login"
    source_alert_audit = "Logs_Audit"
    source_pgroup = "Pgroups"
    source_snapshots = "Snapshots"
    sourcetype = "PureStorage_REST"
    source_vgroup = "vgroup"
    source_pod = "pod"


class SourceType:
    """Description: Class maintain flash array sourcetype details."""

    sourcetype_array = "purestorage:flasharray:array"
    sourcetype_volume = "purestorage:flasharray:volumes"
    sourcetype_host = "purestorage:flasharray:hosts"
    sourcetype_alert_logs = "purestorage:flasharray:alerts"
    sourcetype_alert_login = "purestorage:flasharray:login"
    sourcetype_alert_audit = "purestorage:flasharray:audit"
    sourcetype_pgroup = "purestorage:flasharray:pgroups"
    sourcetype_snapshots = "purestorage:flasharray:snapshots"
    sourcetype_vgroup = "purestorage:flasharray:vgroup"
    sourcetype_pod = "purestorage:flasharray:pod"


class PureError(Exception):
    """Exception type raised by FlashArray object.

    :param reason: A message describing why the error occurred.
    :type reason: str

    :ivar str reason: A message describing why the error occurred.

    """

    def __init__(self, reason):
        """Init."""
        self.reason = reason
        super(PureError, self).__init__()

    def __str__(self):
        """Custom error message format."""
        return "PureError: {0}".format(self.reason)


class ResponseList(list):
    """
    List type returned by FlashArray object.

    :ivar dict headers: The headers returned in the request.
    """

    def __init__(self, lst=()):
        """Init."""
        super(ResponseList, self).__init__(lst)
        self.headers = {}


class ResponseDict(dict):
    """
    Dict type returned by FlashArray object.

    :ivar dict headers: The headers returned in the request.
    """

    def __init__(self, d=()):
        """Init."""
        super(ResponseDict, self).__init__(d)
        self.headers = {}

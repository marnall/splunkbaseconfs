import time
import json
import requests
import splunk.version as ver
import threading
import purestorage_unified_utils as utils
from threadpool import ThreadPool


class PureStroagePure1():
    """Description: Pure1 data collection object."""

    all_fa_arrays_dict_form = {}
    all_fb_arrays_dict_form = {}
    all_file_system_dict_form = {}
    all_volumes_dict_form = {}
    all_pods_dict_form = {}
    LIMIT = utils.LIMIT
    REQUEST_TIMEOUT = utils.REQUEST_TIMEOUT
    SESSION = utils.requests_retry_session()
    LOCK = threading.Lock()
    EFFECTIVE_API_CALLS_PER_MIN = 0
    EFFECIVE_START_TIME = -1
    BUFFER_PENALTY = 5

    def prevent_api_limits(self, helper, config_details):
        """Locking mechanism to avoid API limitations."""
        self.LOCK.acquire()
        if self.EFFECIVE_START_TIME < 0:
            helper.log_info("type={} name={} msg=PureStorage Pure1: "
                            "Initializing trackers to prevent "
                            "reaching to API limit.".format(config_details["input_type"], config_details['stanza']))
            self.EFFECIVE_START_TIME = time.time()
        self.EFFECTIVE_API_CALLS_PER_MIN += 1
        effective_diff = time.time() - self.EFFECIVE_START_TIME
        if effective_diff >= 60:
            helper.log_info("type={} name={} msg=PureStorage Pure1: "
                            "Resetting API limit trackers as"
                            " a minute is passed.".format(config_details["input_type"], config_details['stanza']))
            self.EFFECIVE_START_TIME = time.time()
            self.EFFECTIVE_API_CALLS_PER_MIN = 0
        elif effective_diff < 60 and self.EFFECTIVE_API_CALLS_PER_MIN > 100:
            helper.log_info("type={} name={} msg= Thread will go to sleep as "
                            "it is about to breach"
                            " API limit.".format(config_details["input_type"], config_details['stanza']))
            time.sleep(60 - effective_diff + self.BUFFER_PENALTY)
            helper.log_info("type={} name={} msg=PureStorage Pure1: Thread will now continue execution.".format(
                config_details["input_type"], config_details['stanza']))

            helper.log_info("type={} name={} msg=PureStorage Pure1: Resetting API limit trackers"
                            " as the API limit preventing measures "
                            "are already taken.".format(config_details["input_type"], config_details['stanza']))
            self.EFFECTIVE_API_CALLS_PER_MIN = 0
            self.EFFECIVE_START_TIME = time.time()
        self.LOCK.release()

    def _request(self, path, helper, config_details, data=None, params=None):
        """Perform HTTP request for REST API."""
        if path.startswith("https"):
            url = path  # For cases where URL of different form is needed.
        else:
            helper.log_error("type={} name={} msg=Url does not start with https.".format(
                config_details["input_type"], config_details['stanza']))
            return
        headers = {"Content-Type": "application/json"}
        headers['User-Agent'] = config_details.get('user_agent')
        headers['Authorization'] = "Bearer {}".format(
            config_details["api_token"])
        proxy_settings = config_details.get('proxy_settings')
        verify_ssl = config_details.get('verify_ssl')

        body = json.dumps(data).encode("utf-8")
        try:
            self.prevent_api_limits(helper, config_details)
            response = self.SESSION.get(
                url, data=body, headers=headers, verify=verify_ssl,
                proxies=proxy_settings, params=params, timeout=self.REQUEST_TIMEOUT)
        except requests.exceptions.SSLError:
            raise PureError(
                "SSL certificate verification failed. Please add a valid SSL"
                " Certificate or Change verify_ssl flag to False.")

        except requests.exceptions.ProxyError:
            raise PureError("Please verify provided proxy settings.")

        except requests.exceptions.RequestException as err:
            # error outside scope of HTTP status codes
            # e.g. unable to resolve domain name

            raise PureError(err)

        if response.status_code == 200:
            if "application/json" in response.headers.get("Content-Type", ""):
                content = response.json()
                if isinstance(content, list):
                    content = ResponseList(content)
                elif isinstance(content, dict):
                    content = ResponseDict(content)
                content.headers = response.headers
                return content
            raise PureError("Response not in JSON: " + response.text)
        elif response.status_code == 401:
            self._start_session(helper, config_details)
            return self._request(url, helper, config_details, data, False)
        else:
            helper.log_error("type={} name={} msg=Response status code: {}\n Response: {}".format(
                config_details["input_type"], config_details['stanza'], response.status_code, response.text))
            response.raise_for_status()

    def get_array_details(self, helper, ew, config_details):
        """
        Ingests Pure1 array details in Splunk.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        """
        helper.log_info('type={} name={} msg=Getting array details from array REST service'.format(
            config_details["input_type"], config_details['stanza']))
        config_details['offset_in_checkpoint'] = False

        utils.get_checkpoint(helper, config_details,
                             "purestorage:pure1:array", "pure1_array")

        start_date = config_details.get('start_date')

        fa_arrays = []
        fb_arrays = []

        offset = config_details.get('offset', 0)
        flag = False
        time_field = "_as_of"
        params = {"sort": time_field, "limit": self.LIMIT, "offset": offset}

        path = self.create_path(config_details, "arrays")

        if start_date:
            if config_details['offset_in_checkpoint']:
                params["filter"] = "{field}>='{date}'".format(field=time_field, date=start_date)
            else:
                params["filter"] = "{field}>'{date}'".format(field=time_field, date=start_date)

        while True:
            array_details = None
            try:
                array_details = self._request(
                    path, helper, config_details, params=params)
            except Exception as e:
                flag = False
                helper.log_error(
                    "type={} name={} msg=PureStorage Error: while collecting pure1 array data: {}".format(
                        config_details["input_type"], config_details['stanza'], e))
                break

            try:
                if array_details and len(array_details['items']) > 0:
                    event_count = len(array_details['items'])
                    flag = True
                    config_details["offset"] = params["offset"]

                    for item in array_details["items"]:
                        if item["os"] == "Purity//FA":
                            fa_arrays.append(item)
                            self.all_fa_arrays_dict_form[item.get("id")] = item.get("name")
                        elif item["os"] == "Purity//FB":
                            fb_arrays.append(item)
                            self.all_fb_arrays_dict_form[item.get("id")] = item.get("name")
                        else:
                            helper.log_error(
                                "type={} name={} msg=PureStorage Error: While collecting pure1 array data,"
                                " OS other than FA and FB found.".format(config_details["input_type"],
                                                                         config_details['stanza']))
                    additional_fields = {}
                    additional_fields['time_field'] = time_field
                    additional_fields['host'] = config_details['host']
                    if 'flasharray' in config_details['collect_data_of']:
                        utils.ingest_in_splunk(
                            helper, ew, fa_arrays, "purestorage:pure1:flasharray:array", additional_fields,
                            source="pure1:arrays", config_details=config_details
                        )
                    if 'flashblade' in config_details['collect_data_of']:
                        utils.ingest_in_splunk(
                            helper, ew, fb_arrays, "purestorage:pure1:flashblade:array", additional_fields,
                            source="pure1:arrays", config_details=config_details
                        )
                    params["offset"] += params["limit"]
                    utils.update_checkpoint(helper, config_details)
                    helper.log_debug(
                        "type={type} name={name} msg=PureStorage Debug: Data collection completed "
                        "for pure1 array endpoint with params: {params} Event"
                        " Count: {count}.".format(name=config_details["input_type"],
                                                  type=config_details['stanza'], params=params, count=event_count))
                else:
                    if not flag:
                        helper.log_info("type={} name={} msg=No events reterived from arrays endpoint".format(
                            config_details["input_type"], config_details['stanza']))
                    break

            except Exception as e:
                flag = False
                helper.log_error(
                    "type={type} name={name} msg=PureStorage Error: "
                    "while processing pure1 array data: {err}".format(name=config_details["input_type"],
                                                                      type=config_details['stanza'], err=str(e)))
                break
        if flag:
            config_details["offset"] = None
            utils.update_checkpoint(helper, config_details)

        helper.log_info("type={} name={} msg=PureStorage Info:"
                        " Data collection completed for pure1 array data.".format(
                            config_details["input_type"], config_details['stanza']))

    def get_inventory_data(self, helper, ew, config_details):
        """
        Ingests Pure1's Flashblade inventory details in Splunk.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        """
        sourcetype = "purestorage:pure1:flashblade:inventory"

        # Get Snapshot Details:
        self.get_inventory_details(helper, ew, config_details,
                                   sourcetype, chkpt_sourcetype="purestorage:pure1:snapshots_inventory",
                                   endpoint="file-system-snapshots", time_field="_as_of")

        # Get Object Store Details:
        self.get_inventory_details(helper, ew, config_details,
                                   sourcetype, chkpt_sourcetype="purestorage:pure1:objectstore_inventory",
                                   endpoint="object-store-accounts", time_field="_as_of")

        # Get Bucket Details:
        self.get_inventory_details(helper, ew, config_details,
                                   sourcetype, chkpt_sourcetype="purestorage:pure1:buckets",
                                   endpoint="buckets", time_field="_as_of")

        # Get Policies Details
        self.get_inventory_details(helper, ew, config_details,
                                   sourcetype, chkpt_sourcetype="purestorage:pure1:policies",
                                   endpoint="policies", time_field="_as_of")

    def get_inventory_details(self, helper, ew, config_details,
                              sourcetype, chkpt_sourcetype, endpoint, time_field, get_id_names=False):
        """
        Ingests Pure1 inventory details for Flashblade in Pure1.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param config_details: Basic configuration details
        :param sourcetype: Sourcetype in which data is to be ingested
        :param chkpt_sourcetype: Sourcetype used to form checkpoint key
        :param endpoint: Endpoint to which API call is to be done
        :param time_field: API response field from which we will get _time value and which will be used in filter param
        """
        config_details['offset_in_checkpoint'] = False

        utils.get_checkpoint(helper, config_details,
                             chkpt_sourcetype, "/pure1_{edpt}".format(edpt=endpoint))

        start_date = config_details.get('start_date')

        offset = config_details.get('offset', 0)
        flag = False

        params = {"sort": time_field, "limit": self.LIMIT, "offset": offset}

        if start_date:
            date_30d_ago = config_details.get('end_date') - (29 * 86400 * 1000)
            if endpoint == "audits" and start_date < date_30d_ago:
                start_date = date_30d_ago
                helper.log_warning(
                    "type={} name={} msg=Start date is older than 30 days. "
                    "Collecting audits performance of 30 days".format(config_details["input_type"],
                                                                      config_details['stanza']))

            if config_details['offset_in_checkpoint']:
                params["filter"] = "{field}>='{date}'".format(field=time_field, date=start_date)
            else:
                params["filter"] = "{field}>'{date}'".format(field=time_field, date=start_date)

        path = self.create_path(
            config_details, endpoint)

        while True:
            helper.log_debug(
                "type={type} name={name} msg=PureStorage Debug: "
                "Fetching data for pure1 {edpt} endpoint with params: {params}.".format(
                    name=config_details["input_type"],
                    type=config_details['stanza'], edpt=endpoint, params=params))
            inv_details = None
            try:
                inv_details = self._request(
                    path, helper, config_details, params=params)
            except Exception as e:
                flag = False
                helper.log_error(
                    "type={type} name={name} msg=PureStorage Error: while collecting"
                    " pure1 {edpt} data: {err}".format(name=config_details["input_type"],
                                                       type=config_details['stanza'], err=str(e), edpt=endpoint))
                break

            try:
                additional_fields = {}
                additional_fields['time_field'] = time_field
                additional_fields['host'] = config_details['host']
                if inv_details and len(inv_details['items']) > 0:
                    event_count = len(inv_details['items'])
                    inv_details = inv_details['items']
                    flag = True
                    config_details["offset"] = params["offset"]
                    utils.ingest_in_splunk(helper, ew, inv_details,
                                           sourcetype, additional_fields, source="pure1:{edpt}".format(edpt=endpoint),
                                           config_details=config_details)
                    if get_id_names:
                        for item in inv_details:
                            if endpoint == "pods":
                                self.all_pods_dict_form[item.get("id")] = item.get("name")
                            elif endpoint == "volumes":
                                # The volumes endpoint may have null value for id field.
                                # Passing null value in metrics/history API params is throwing 404 error.
                                # Omit storing None value in final Dict
                                if item.get("id"):
                                    self.all_volumes_dict_form[item.get("id")] = item.get("name")
                            elif endpoint == "file-systems":
                                self.all_file_system_dict_form[item.get("id")] = item.get("name")

                    utils.update_checkpoint(helper, config_details)
                    helper.log_debug(
                        "type={type} name={name} msg=PureStorage Debug: Data collection completed for pure1 {edpt}"
                        " endpoint with params: {params} Event Count: {count}."
                        .format(name=config_details["input_type"],
                                type=config_details['stanza'], edpt=endpoint, params=params, count=event_count))
                    params["offset"] += params["limit"]
                else:
                    if not flag:
                        helper.log_info(
                            "type={type} name={name} msg=No data retrived from pure1 "
                            "{edpt} endpoint".format(name=config_details["input_type"],
                                                     type=config_details['stanza'], edpt=endpoint))
                    break

            except Exception as e:
                flag = False
                helper.log_error(
                    "type={type} name={name} msg=PureStorage Error: while processing "
                    "{edpt} pure1 data: {err}".format(name=config_details["input_type"],
                                                      type=config_details['stanza'], err=str(e), edpt=endpoint))
                break

        if flag:
            config_details["offset"] = None
            utils.update_checkpoint(helper, config_details)

        helper.log_info(
            "type={type} name={name} msg=PureStorage Info: Data collection completed"
            " for pure1 {edpt} data.".format(name=config_details["input_type"],
                                             type=config_details['stanza'], edpt=endpoint))

    def get_system_performance_data(self, helper, ew, config_details, endpoint,
                                    sourcetype, device_id, device_names, metric_fields, mirrored_metric_fields=None):
        """
        Ingests Pure1's performance details in Splunk.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        :param endpoint: array/volumes/pods/file-systems
        :param config_details: Basic configuration details
        :param sourcetype: Sourcetype in which data is to be ingested in Splunk
        :param device_id: Specific endpoint's ID for which we want performance data
        :param device_names: Specific endpoint's name for which we want performance data
        :param metric_fields: List of metrics for which we want performance data
        """
        path = self.create_path(config_details, "metrics/history")

        device_id_list = []
        devide_name_list = []
        if len(device_id) == 2:
            device_id_list.append(device_id[0])
            device_id_list.append(device_id[1])

            devide_name_list.append(device_names[0])
            devide_name_list.append(device_names[1])
            new_params = "'{}','{}'".format(
                device_id[0], device_id[1])
        else:
            device_id_list.append(device_id[0])
            devide_name_list.append(device_names[0])
            new_params = "'{}'".format(
                device_id[0])

        space_perf = "space" if sourcetype == "purestorage:pure1:space" else "performance"

        start_date = utils.performance_endpt_checkpoint(helper,
                                                        "purestorage:pure1:{edpt}:{space_perf}".format(
                                                            space_perf=space_perf, edpt=endpoint),
                                                        "/pure1_{edpt}-{space_perf}".format(
                                                            space_perf=space_perf, edpt=endpoint),
                                                        new_params, config_details, opt="GET")

        # End Time is current_time - 1hr, because the data is updated with delay in Pure1 API
        end_time = config_details.get('current_date_-1h')
        if end_time < start_date:
            helper.log_warning(
                "type={type} name={name} msg=Start date is older than End Date."
                " Skipping {edpt} {space_perf} data collection for: {device}".format(
                    name=config_details["input_type"],
                    type=config_details['stanza'], edpt=endpoint, space_perf=space_perf, device=device_id_list))
            return

        params = {'end_time': end_time, 'start_time': start_date, 'resolution': 86400000}

        if sourcetype == "purestorage:pure1:space":
            date_resolution_list = [params]
        else:
            date_resolution_list = self.set_date_and_resolution(config_details, params, helper)

        additional_fields = {}
        additional_fields['time_field'] = 'time'
        additional_fields['host'] = config_details['host']

        try:
            for value in date_resolution_list:
                params['start_time'], params['end_time'], params[
                    'resolution'] = value.get('start_time'), value.get(
                        'end_time'), value.get('resolution')
                if endpoint != "filesystems":
                    params['names'] = metric_fields
                params['aggregation'] = "'avg'"
                params['resource_ids'] = new_params

                # If more than call is required for same parameter
                # i.e. due to more number of metrics execute below psuedo code
                # all_metrics = None
                # all_metrics = metrics_data (init after 1st call)
                # Add below line to combine values
                # for item in metrics_data["items"]:
                #     all_metrics["items"].append(item)
                # After doing this call sort_data and following functions

                helper.log_debug("type={type} name={name} msg=PureStorage Debug: Fetching {space_perf} "
                                 "data for {edpt}: {names} between start_time {start} "
                                 "and end_time {end} and resolution: {rs}.".format(name=config_details["input_type"],
                                                                                   type=config_details['stanza'],
                                                                                   space_perf=space_perf, edpt=endpoint,
                                                                                   names=params['resource_ids'],
                                                                                   start=params['start_time'],
                                                                                   end=params['end_time'],
                                                                                   rs=params['resolution']))
                metrics_data = None
                if endpoint == "filesystems":
                    params['names'] = metric_fields[0]
                    metrics_data = self._request(
                        path, helper, config_details, params=params)
                    params['names'] = metric_fields[-1]
                    metrics_data_file_system_read_bandwidth = self._request(
                        path, helper, config_details, params=params)
                    metrics_data["items"].extend(metrics_data_file_system_read_bandwidth.get("items"))
                else:
                    metrics_data = self._request(
                        path, helper, config_details, params=params)
                    if mirrored_metric_fields:
                        params['names'] = mirrored_metric_fields
                        metrics_data_mirrored_write = self._request(
                            path, helper, config_details, params=params)
                        metrics_data["items"].extend(metrics_data_mirrored_write.get("items"))
                if metrics_data:
                    end_date, performance_details = self.sort_data(config_details, metrics_data,
                                                                   device_id_list, devide_name_list, helper)

                    utils.ingest_in_splunk(helper, ew, performance_details, sourcetype,
                                           additional_fields, source="pure1:{edpt}-{space_perf}".format(
                                               space_perf=space_perf, edpt=endpoint))

                    utils.performance_endpt_checkpoint(helper, "purestorage:pure1:{edpt}:{space_perf}".format(
                        space_perf=space_perf, edpt=endpoint),
                        "/pure1_{edpt}-{space_perf}".format(space_perf=space_perf, edpt=endpoint),
                        new_params, config_details, opt="POST", value=end_date)

                else:
                    helper.log_debug(
                        "type={type} name={name} msg=No data retrived from pure1 {edpt} {space_perf} endpoint".format(
                            name=config_details["input_type"],
                            type=config_details['stanza'],
                            space_perf=space_perf, edpt=endpoint))

        except Exception as e:
            helper.log_error(
                "type={type} name={name} msg=PureStorage Error: Error occured for {space_perf} "
                "endpoint: {edpt}: {err}".format(
                    name=config_details["input_type"],
                    type=config_details['stanza'],
                    err=str(e), space_perf=space_perf, edpt=endpoint))

    def sort_data(self, config_details, metrics_data, device_ids, device_names, helper):
        """
        Process performance data to be ingested in Splunk.

        :param metrics_data: Response returned as an output of metrics/history endpoint
        :param device_ids: Specific endpoint's ID for which we want performance data
        :param device_names: Specific endpoint's name for which we want performance data
        :param helper: object of BaseModInput class
        :return list: The members of list will have details of all performance metrics with same device ID
        and same timestamp
        :return string: The value of _as_of field for the last stanza which will be serve as checkpoint time
        """
        final_events = {}
        end_date = None
        for item in metrics_data['items']:
            end_date = item["_as_of"] if end_date is None or end_date < item["_as_of"] else end_date
            for resource in item['resources']:
                helper.log_debug("type={type} name={inp_name} msg=PureStorage Pure1 Debug: ID: {id}, {len} entries"
                                 " for metric: {name}, resolution: {res}".format(inp_name=config_details["input_type"],
                                                                                 type=config_details['stanza'],
                                                                                 id=resource['id'], name=item['name'],
                                                                                 len=len(item['data']),
                                                                                 res=item['resolution']))
                for dvc_id in range(len(device_ids)):
                    if device_ids[dvc_id] == resource['id']:  # match ids in device_ids and API response
                        op_name = item['name']  # metrics_name
                        if item['data']:
                            for data in item['data']:
                                dict_key = '{}_{}'.format(data[0], device_ids[dvc_id])
                                if dict_key not in final_events.keys():
                                    final_events[dict_key] = {}
                                    final_events[dict_key]["name"] = device_names[dvc_id]
                                    final_events[dict_key]["id"] = device_ids[dvc_id]
                                    final_events[dict_key]["time"] = data[0]
                                    final_events[dict_key]["resolution"] = item['resolution']
                                final_events[dict_key]["{}_as_of".format(op_name)] = item['_as_of']
                                final_events[dict_key][op_name] = '{}'.format(data[1])
        return end_date, final_events.values()

    def set_date_and_resolution(self, config_details, params, helper):
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

        helper.log_debug("type={} name={} msg=PureStorage Debug: "
                         "time and resolution distribution".format(config_details["input_type"],
                                                                   config_details['stanza']))

        helper.log_debug('\n'.join('type={} name={}'
                                   'for start_time -> {} to end_time -> {} '
                                   'with resolution -> {}'.
                                   format(config_details["input_type"], config_details['stanza'],
                                          time.ctime(x['start_time'] / 1000),
                                          time.ctime(x['end_time'] / 1000), x['resolution'])
                                   for x in date_resolution_list))
        return date_resolution_list

    def create_path(self, config_details, endpoint):
        """
        Form the entire URL for Pure1 endpoint.

        :param config_details: Basic configuration details
        :param endpoint: Pure1 Endpoint
        : return FQDN for Pure1
        """
        path = "{}/api/{}/{}".format(
            config_details['server_address'], config_details['api_version'], endpoint)
        return path

    def _start_session(self, helper, config_details):
        """
        Generate access token to perform API calls.

        :param helper: object of BaseModInput class
        :param config_details: Basic configuration details
        """
        jwt_token = config_details['jwt_token']
        post_data = {'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
                     'subject_token_type': 'urn:ietf:params:oauth:token-type:jwt',
                     'subject_token': jwt_token}
        path = config_details["server_address"] + "/oauth2/1.0/token"

        try:
            response = self.SESSION.post(
                path, data=post_data, verify=config_details['verify_ssl'], timeout=self.REQUEST_TIMEOUT,
                proxies=config_details['proxy_settings'])
            if response:
                if response.status_code == 200 or response.status_code == 201:
                    try:
                        config_details["api_token"] = str(
                            response.json()['access_token'])
                        return str(response.json()['access_token'])
                    except Exception:
                        return str(response.json()['items'][0]['access_token'])
                else:
                    raise PureError('Could not retrieve a access token')
            else:
                raise PureError('Could not retrieve a access token')
        except requests.exceptions.ProxyError:
            helper.log_error("type={} name={} msg=PureError: Could not retrieve a access token. Error:"
                             " Account authentication failed due to proxy error. "
                             "Please verify provided proxy settings.".format(config_details["input_type"],
                                                                             config_details['stanza']))
            return False
        except Exception as err:
            helper.log_error("type={} name={} msg=PureError: Could not retrieve a access token. Error: {}".format(
                config_details["input_type"], config_details['stanza'], err))
            return False

    def collect_events(self, helper, ew):
        """
        This function is autogenerated by AoB.

        :param helper: object of BaseModInput class
        :param ew: object of EventWriter class
        """
        global_account = helper.get_arg('global_account')
        api_token = global_account.get('api_token')
        server_address = global_account.get('server_address')
        verify_ssl = utils.read_conf_file(helper.context_meta["session_key"], "verify_ssl")
        stanza_name = str(helper.get_input_stanza_names())
        current_time = int(time.time() * 1000)
        config_details = {}
        config_details["input_type"] = helper.get_arg('input_type')
        config_details['stanza'] = stanza_name

        # Getting Splunk Version
        splunk_version = ver.__version__
        if not splunk_version:
            helper.log_error(
                "type={} name={} msg=PureStorage Error: "
                "unable to fetch splunk version.".format(config_details["input_type"], config_details['stanza']))
            return

        # Fetching proxy data
        proxy_dict = helper.get_proxy()
        proxy_uri = None
        if proxy_dict:
            proxy_uri = utils.format_proxy_uri(proxy_dict)
        proxy_settings = {"http": proxy_uri, "https": proxy_uri}
        server_address = "https://{}".format(server_address)
        array = server_address.split("https://")[1]
        # Storing necessary data into dictionary

        config_details['host'] = array
        config_details['server_address'] = server_address
        config_details['user_agent'] = "Splunk/{}".format(splunk_version)
        config_details['end_date'] = current_time
        config_details['current_date_-1h'] = current_time - 3600000
        config_details['proxy_settings'] = proxy_settings
        config_details['verify_ssl'] = verify_ssl
        config_details['jwt_token'] = api_token
        config_details['api_version'] = "1.latest"
        config_details['collect_data_of'] = utils.PURE1_COLLECT_DATA_OF

        metric_fields = {}

        metric_fields["pods"] = "'pod_read_latency_us', 'pod_write_latency_us', 'pod_read_iops',"\
            "  'pod_write_iops', 'pod_read_bandwidth', 'pod_write_bandwidth'"

        metric_fields["volumes"] = "'volume_read_bandwidth', 'volume_write_bandwidth', 'volume_read_iops',"\
            " 'volume_read_latency_us', 'volume_write_latency_us', 'volume_write_iops'"

        # Using a list of metric names as a workaround to make two requests
        # because using all the metrics in same request doesn't return file_system_read_bandwidth metric data.
        # This can be made into a single string of metric names thus reducing
        # the two seperate requests to one once the api issue is resolved.
        metric_fields["filesystems"] = ["'file_system_other_iops','file_system_read_iops',"
                                        "'file_system_other_latency_us','file_system_read_latency_us',"
                                        "'file_system_write_latency_us','file_system_write_bandwidth',"
                                        "'file_system_write_iops'", "'file_system_read_bandwidth'"]

        metric_fields["array"] = "'array_read_bandwidth', 'array_write_bandwidth', 'array_read_iops',"\
            "'array_write_iops', 'array_read_latency_us', 'array_write_latency_us', 'array_total_load'"

        metric_fields["mirrored_metrics"] = "'array_mirrored_write_iops','array_mirrored_write_bandwidth',"\
            "'array_mirrored_write_latency_us'"

        metric_fields["array_space"] = "'array_total_capacity', 'array_data_reduction', 'array_volume_space',"\
            " 'array_shared_space', 'array_snapshot_space', 'array_file_system_space',"\
            "'array_object_store_space'"

        # Login on PureStorage Server and create session
        if self._start_session(helper, config_details):
            try:
                no_of_threads = utils.MAX_WORKER_THREADS
                if no_of_threads not in range(1, 5):
                    helper.log_error(
                        "type={} name={} msg=PureStorage Error: Number of threads should be greater than zero"
                        " and less than or equal to 4. "
                        "Please change the value first and then enable the script ".format(
                            config_details["input_type"], config_details['stanza'])
                    )
                    return
            except Exception as e:
                helper.log_error(
                    "type={} name={} msg=PureStorage Error: Error occured while fetching number of threads from "
                    "purestorage_unified_utils.py.py Exception: {}. Defaulting to 4".format(
                        str(e), config_details["input_type"], config_details['stanza'])
                )
                no_of_threads = 4

            try:
                if not isinstance(self.LIMIT, int) or self.LIMIT <= 0:
                    helper.log_error(
                        "type={} name={} msg=PureStorage Error: self.LIMIT should be greater than zero"
                        " and less than or equal to 1000. "
                        "Please change the value first and then"
                        " enable the script ".format(config_details["input_type"], stanza_name)
                    )
                    return
                if self.LIMIT > 1000:
                    helper.log_error(
                        "type={} name={} msg=PureStorage Error: LIMIT should be greater than zero"
                        " and less than or equal to 1000.  Defaulting to 1000.".format(
                            config_details["input_type"], stanza_name)
                    )
                    self.LIMIT = 1000
            except Exception as e:
                helper.log_error(
                    "type={} name={} msg=PureStorage Error: Error occured while fetching value of LIMIT from "
                    "purestorage_unified_utils.py. Exception: {}. "
                    "Defaulting to 1000".format(config_details["input_type"], stanza_name, str(e))
                )
                self.LIMIT = 1000

            try:
                if not isinstance(self.REQUEST_TIMEOUT, int) or self.REQUEST_TIMEOUT <= 0:
                    helper.log_error(
                        "type={} name={} msg=PureStorage Error: self.REQUEST_TIMEOUT should be greater than zero."
                        "Please change the value first and then enable the script ".format(
                            config_details["input_type"], stanza_name)
                    )
                    return
            except Exception as e:
                helper.log_error(
                    "type={} name={} msg=PureStorage Error: Error occured while fetching value of "
                    "REQUEST_TIMEOUT from purestorage_unified_utils.py."
                    " Exception: {}. Defaulting to 180".format(config_details["input_type"], stanza_name, str(e))
                )
                self.REQUEST_TIMEOUT = 180

            pool = ThreadPool(no_of_threads, helper)
            start_time = time.time()

            helper.log_info(
                "type={} name={} msg=PureStorage Info: Starting with data"
                " collection for Pure1.".format(config_details["input_type"], stanza_name))

            helper.log_debug("type={} name={} msg=PureStorage Debug: connection established.".format(
                config_details["input_type"], stanza_name))

            # Function calls for collect data from different REST Endpoints.

            # Audits details
            endpoint = "audits"
            sourcetype = "purestorage:pure1:audits"
            self.get_inventory_details(helper, ew, config_details, sourcetype=sourcetype,
                                       chkpt_sourcetype=sourcetype, endpoint=endpoint, time_field="time")

            # Alerts details

            endpoint = "alerts"
            sourcetype = "purestorage:pure1:alerts"

            self.get_inventory_details(helper, ew, config_details, sourcetype=sourcetype,
                                       chkpt_sourcetype=sourcetype, endpoint=endpoint, time_field="updated")

            # Array details
            self.get_array_details(helper, ew, config_details)

            endpoint = "array"

            # FlashArray Performance details
            if len(self.all_fa_arrays_dict_form) > 0:
                # Make py2 and py3 compatible
                fa_array_keys = list(self.all_fa_arrays_dict_form.keys())
                fa_array_values = list(self.all_fa_arrays_dict_form.values())

                for array in range(0, len(fa_array_keys), 2):
                    pool.add_task(self.get_system_performance_data, helper, ew, config_details,
                                  endpoint, "purestorage:pure1:flasharray:performance",
                                  fa_array_keys[array:array + 2],
                                  fa_array_values[array:array + 2], metric_fields[endpoint],
                                  metric_fields["mirrored_metrics"])

                    pool.add_task(self.get_system_performance_data, helper, ew, config_details,
                                  "flasharray", "purestorage:pure1:space",
                                  fa_array_keys[array:array + 2],
                                  fa_array_values[array:array + 2], metric_fields["array_space"])

            # FlashBlade > Array Performance details
            if len(self.all_fb_arrays_dict_form) > 0:
                # Make py2 and py3 compatible
                fb_array_keys = list(self.all_fb_arrays_dict_form.keys())
                fb_array_values = list(self.all_fb_arrays_dict_form.values())

                for array in range(0, len(fb_array_keys), 2):
                    pool.add_task(self.get_system_performance_data, helper, ew, config_details,
                                  endpoint, "purestorage:pure1:flashblade:performance",
                                  fb_array_keys[array:array + 2],
                                  fb_array_values[array:array + 2], metric_fields[endpoint])

                    pool.add_task(self.get_system_performance_data, helper, ew, config_details,
                                  "flashblade", "purestorage:pure1:space",
                                  fb_array_keys[array:array + 2],
                                  fb_array_values[array:array + 2], metric_fields["array_space"])

            # Get File System Details
            self.get_inventory_details(helper, ew, config_details,
                                       "purestorage:pure1:filesystems",
                                       chkpt_sourcetype="purestorage:pure1:filesystems_inventory",
                                       endpoint="file-systems", time_field="_as_of", get_id_names=True)

            # File System Performance details
            endpoint = "filesystems"

            if len(self.all_file_system_dict_form) > 0:
                # Make py2 and py3 compatible
                file_system_keys = list(self.all_file_system_dict_form.keys())
                file_system_values = list(self.all_file_system_dict_form.values())

                for array in range(0, len(file_system_keys), 2):
                    pool.add_task(self.get_system_performance_data, helper, ew, config_details,
                                  endpoint, "purestorage:pure1:filesystems:performance",
                                  file_system_keys[array:array + 2],
                                  file_system_values[array:array + 2], metric_fields[endpoint])

            if "flasharray" in utils.PURE1_COLLECT_DATA_OF:
                endpoint = "volumes"

                # Volume details
                self.get_inventory_details(helper, ew, config_details,
                                           sourcetype="purestorage:pure1:flasharray:volumes",
                                           chkpt_sourcetype="purestorage:pure1:volumes",
                                           endpoint=endpoint, time_field="_as_of", get_id_names=True)

                # Volume Performance details
                if len(self.all_volumes_dict_form) > 0:
                    # Make py2 and py3 compatible
                    volumes_keys = list(self.all_volumes_dict_form.keys())
                    volumes_values = list(self.all_volumes_dict_form.values())

                    for array in range(0, len(volumes_keys), 2):
                        pool.add_task(self.get_system_performance_data, helper, ew, config_details,
                                      endpoint, "purestorage:pure1:flasharray:performance",
                                      volumes_keys[array:array + 2],
                                      volumes_values[array:array + 2], metric_fields[endpoint])

                # Volume snapshot and protection group details
                endpoint = "volume-snapshots"
                self.get_inventory_details(helper, ew, config_details,
                                           sourcetype="purestorage:pure1:flasharray:snapshots",
                                           chkpt_sourcetype="purestorage:pure1:snapshots",
                                           endpoint=endpoint, time_field="_as_of")

                endpoint = "pods"
                # Pod details
                self.get_inventory_details(helper, ew, config_details, sourcetype="purestorage:pure1:flasharray:pods",
                                           chkpt_sourcetype="purestorage:pure1:pods",
                                           endpoint=endpoint, time_field="_as_of", get_id_names=True)

                # Pods Performance details
                if len(self.all_pods_dict_form) > 0:
                    # Make py2 and py3 compatible
                    pod_keys = list(self.all_pods_dict_form.keys())
                    pod_values = list(self.all_pods_dict_form.values())

                    for array in range(0, len(pod_keys), 2):
                        pool.add_task(self.get_system_performance_data, helper, ew, config_details,
                                      endpoint, "purestorage:pure1:flasharray:performance",
                                      pod_keys[array:array + 2],
                                      pod_values[array:array + 2], metric_fields[endpoint])

            if "flashblade" in utils.PURE1_COLLECT_DATA_OF:
                # Inventory details
                self.get_inventory_data(helper, ew, config_details)

                # Health details
                self.get_inventory_details(helper, ew, config_details, sourcetype="purestorage:pure1:flashblade:health",
                                           chkpt_sourcetype="purestorage:pure1:health",
                                           endpoint="blades", time_field="_as_of")
            # Wait for all threads to complete
            pool.wait_completion()
            helper.log_info("type={} name={} msg=PureStorage Info: Done with data collection. "
                            "Time taken: {} minutes.".format(config_details["input_type"],
                                                             stanza_name, ((time.time() - start_time) / 60)))


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
    """List type returned by FlashArray object.

    :ivar dict headers: The headers returned in the request.

    """

    def __init__(self, lst=()):
        """Init."""
        super(ResponseList, self).__init__(lst)
        self.headers = {}


class ResponseDict(dict):
    """Dict type returned by FlashArray object.

    :ivar dict headers: The headers returned in the request.

    """

    def __init__(self, d=()):
        """Init."""
        super(ResponseDict, self).__init__(d)
        self.headers = {}

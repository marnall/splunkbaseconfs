# encoding = utf-8
import re
from datetime import datetime, time
from daily_connections_manager import DailyConnectionsManager
from constants import AGENTS, PREV_TIMESTAMP_C, PREV_TIMESTAMP_R, CONNECTIONS, REPUTATION_LOG
from logger import Logger, LogLevel
from utils import GuardicoreHelper


class GuardicoreClient:
    """Splunk Addon class. Contains the logic for collecting data from the Guardicore management server and writing it to the Splunk index."""

    def __init__(self, helper, ew, guardicore_utils):
        self.helper = helper
        self.ew = ew
        self.limit = int(self.helper.get_arg("event_limit"))
        self.use_daily_connections = self.helper.get_arg("use_daily_connections")
        self.mgmt_server = helper.get_arg("guardicore_management_server")
        self.global_port = helper.get_arg("port")
        self.log = Logger(self.helper).log
        self.utils = guardicore_utils
        self.connection_type = helper.get_arg("connection_type")
        self.policy_verdict = helper.get_arg("policy_verdict")
        self.filter_by_labels = self.helper.get_arg("filter_by_labels")

    ###########################################
    ### AGENT, COMPONENT AND DASHBOARD HEALTH STATUS FUNCTIONS
    ###########################################

    def collect_agent_flags_status(self):
        """Collect the status flags of the Guardicore agents."""
        self.log(LogLevel.INFO, "Starting to collect agent status flags")

        parameters = dict(status_flags="undefined", limit=min(self.limit, 1000))
        total_count = self.get_total_count(AGENTS, parameters)

        if not total_count:
            self.log(LogLevel.INFO, "No new events for {}", AGENTS)
            return

        from_event = 0
        to_event = min(self.limit, total_count)

        flags = {}
        while (total_count + self.limit - 1) >= to_event:
            parameters.update({"offset": from_event, "limit": min(self.limit, 1000)})
            agents = self.utils.request(AGENTS, parameters=parameters)["objects"]

            from_event = to_event
            to_event += self.limit

            for agent in agents:
                display_name = agent["display_name"]
                for flag in agent["status_flags"]:
                    flag_type = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', flag["flag_type"])

                    if flag_type not in flags:
                        flags[flag_type] = {"count": 0, "agent_names": []}
                    elif display_name in flags[flag_type]["agent_names"]:
                        continue

                    flags[flag_type]["count"] += 1
                    flags[flag_type]["agent_names"].append(display_name)

        for flag, values in flags.items():
            self.utils.write_event(data={"data_type": "agent_flags", "flag": flag, "count": values["count"],
                                         "agents": values["agent_names"]})

        self.log(LogLevel.INFO, "Finished collecting data from {}", AGENTS)

    def collect_component_status(self):
        """Collect the status of the Guardicore components, such as agent aggregators, honeypots, and collectors."""
        self.log(LogLevel.INFO, "Starting to collect component status")

        parameters = dict(filter_name="display_status", limit=min(self.limit, 1000))
        for component in ["agent_aggregators", "honeypots", "collectors"]:
            endpoint = "{}/filter-options".format(component)
            status_count = self.utils.request(endpoint, parameters=parameters)

            if not "available_options" in status_count or len(status_count["available_options"]) < 1:
                self.log(LogLevel.INFO, "No {} status available", component)
                continue

            options = status_count.get("available_options", [])
            for status in options:
                self.log(LogLevel.DEBUG, "Status: {}", status)
                data = {"data_type": "component_status", "status": status["text"], "count": status["count"],
                        "component_type": component}
                self.utils.write_event(data)

        self.log(LogLevel.INFO, "Finished collecting component status")

    def collect_dashboard_health_status(self):
        """Collect the health status of the Guardicore management server."""
        self.log(LogLevel.INFO, "Starting to retrieve dashboard health status")

        dashboard_data = self.utils.request("dashboards/dashboard/security-dashboard/data?time_frame=HOUR")
        health_data = {}

        for widget in dashboard_data.values():
            if widget.get("key", "") == "health":
                health_data = widget.get("data", {})
                break
        mgmt_ip = self.mgmt_server
        mgmt_port = self.global_port

        # check mgmt resources
        self.log(LogLevel.INFO, "Checking management resources")
        resources = health_data.get("resources", {})

        storage_data = {"data_type": "hosts_storage", "mgmt_ip": mgmt_ip, "mgmt_port": mgmt_port}
        memory_data = {"data_type": "mgmt_memory", "mgmt_ip": mgmt_ip, "mgmt_port": mgmt_port}

        if not resources:
            self.log(LogLevel.WARNING, "No resources data available, environment might be SaaS")
            storage_data.update({"is_ok": True, "count": 0})
            memory_data.update({"is_ok": True, "count": 0})
        else:
            host_storage = resources.get("hosts_storage", {})
            memory_date = resources.get("management_memory", {})
            memory_data.update({"is_ok": memory_date.get("is_ok", False), "count": memory_date.get("count", 0)})
            storage_data.update({"is_ok": host_storage.get("is_ok", False), "count": host_storage.get("count", 0)})

        self.utils.write_event(storage_data)
        self.utils.write_event(memory_data)

        # check components
        self.log(LogLevel.INFO, "collecting system components stats")
        system_components = health_data.get("components", {})

        for component in system_components.keys():
            self.log(LogLevel.DEBUG, "Checking {} components", component)
            component_data = {"data_type": "component_overview", "component_type": component}

            status = system_components[component]
            if status:
                component_data.update(system_components[component])
                self.utils.write_event(component_data)

        agents = health_data.get("agents", {}).get("agents", {})
        self.utils.write_event({"data_type": "component_overview", "component_type": "agents", "is_ok": agents["is_ok"],
                                "count": agents["count"]})

        self.log(LogLevel.INFO, "Finished collecting component status")

    ###########################################
    ### CONNECTION AND REPUTATION ALERTS FUNCTIONS
    ###########################################

    def collect_data(self, endpoint, parameters, process_func):
        """Collect data from an endpoint and process it using the provided function."""
        self.log(LogLevel.INFO, "Collecting data from endpoint {}", endpoint)

        total_count = self.get_total_count(endpoint, parameters)

        if not total_count:
            self.log(LogLevel.INFO, "No new events for {}", endpoint)
            return

        from_event = 0
        to_event = min(self.limit, total_count)

        while from_event < total_count:
            parameters.update({"offset": from_event, "limit": self.limit})
            response = self.utils.request(endpoint, parameters=parameters)

            data = response.get("objects", [])
            if not data:
                self.log(LogLevel.WARNING, f"No data returned from endpoint {endpoint} for offset {from_event}")
                break

            last_event = data[-1]
            for item in data:
                process_func(item, item == last_event)

            self.log(LogLevel.INFO, "Collected {} out of {} events in {}", to_event, total_count, endpoint)

            from_event = to_event
            to_event = min(from_event + self.limit, total_count)

        self.log(LogLevel.INFO, "Finished collecting {} logs from {}", total_count, endpoint)

    def get_total_count(self, endpoint, parameters):
        """Get the total count of items from an endpoint."""
        total_count = self.utils.request(endpoint, parameters=parameters).get("total_count")
        self.log(LogLevel.INFO, "Found {} new items from endpoint {}", total_count, endpoint)

        return total_count

    def create_parameters(self, from_time, to_time, sort):
        """Create the parameters for the API call. Inserts the time range and sort order."""
        parameters = dict(from_time=from_time, to_time=to_time, sort=sort)
        return parameters

    def get_verdict(self, conn):
        """Get the policy verdict of a connection."""
        if conn["policy_verdict"] in ["blocked_by_source", "blocked_by_destination"]:
            return "blocked"
        elif conn["policy_verdict"].startswith("alerted"):
            return "alerted"
        else:
            return "allowed"

    def detect_date_format(self, date_string):
        date_formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S"
        ]

        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(date_string, date_format)
                return date_format
            except ValueError:
                continue
        return None

    def process_connection(self, conn, last_event=False):
        """Process a connection and write it to the Splunk index."""
        conn["data_type"] = "connection"
        conn["rule_display_name"] = "RUL-{}".format(conn["policy_rule"][:8])
        conn["verdict"] = self.get_verdict(conn)
        conn["exported_timestamp"] = self.utils.set_log_exported_timestamp(conn["slot_start_time"])
        self.utils.write_event(conn)

        if last_event and not self.use_daily_connections:
            # Add 1 second to the timestamp to avoid duplicates
            timestamp = int(conn["exported_timestamp"]) + 1000
            self.utils.save_env_checkpoint(PREV_TIMESTAMP_C, timestamp)

    def process_reputation_alert(self, alert, last_event=False):
        """Process a reputation alert and write it to the Splunk index."""
        alert["data_type"] = "reputation_alert"
        alert["exported_timestamp"] = self.utils.set_log_exported_timestamp(alert["request_time"])
        self.utils.write_event(alert)
        if last_event:
            # Add 1 second to the timestamp to avoid duplicates
            timestamp = int(alert["exported_timestamp"]) + 1000
            self.utils.save_env_checkpoint(PREV_TIMESTAMP_R, timestamp)

    def collect_connections(self):
        """Collect connections from the Guardicore management server."""
        from_time, to_time = self.utils.get_timestamps(CONNECTIONS, PREV_TIMESTAMP_C)
        parameters = self.create_parameters(from_time, to_time, "slot_start_time")

        if self.filter_by_labels:
            label_ids_str = self.resolve_labels(self.filter_by_labels)
            self.log(LogLevel.DEBUG, "Resolved label IDs: {} ", label_ids_str)
            formated_labels = f"labels:{label_ids_str}"
            parameters.update({"any_side": formated_labels})

        mapped_types = self.map_connection_types()
        if mapped_types != ['any']:
            # we need to filter by connection_type only if the user has selected specific types
            connection_types = ",".join(mapped_types)
            self.log(LogLevel.DEBUG, "Connection types: {} ", connection_types)
            parameters.update({"connection_type": connection_types})

        mapped_verdicts = self.map_policy_verdicts()
        if mapped_verdicts != ['any']:
            # we need to filter by policy_verdict only if the user has selected specific verdicts
            verdicts = ",".join(mapped_verdicts)
            self.log(LogLevel.DEBUG, "Policy verdicts: {} ", verdicts)
            parameters.update({"policy_verdict": verdicts})

        self.collect_data(CONNECTIONS, parameters, self.process_connection)

    def map_policy_verdicts(self):
        verdict_mapping = {
            'Blocked': 'blocked',
            'Will be blocked': 'will_be_blocked',
            'Alerted': 'alerted_by_management',
            'Could not block': 'blocked_by_management',
            'Allowed': 'allowed',
            'Allowed and Encrypted': 'allowed_and_encrypted',
            'Any': 'any'
        }
        mapped_verdicts = [verdict_mapping.get(val, val) for val in self.policy_verdict]
        return mapped_verdicts

    def map_connection_types(self):
        connection_type_mapping = {
            'Established': 'successful',
            'Failed': 'failed',
            'Redirected': 'redirected_to_hpvm',
            'Any': 'any'
        }
        mapped_types = [connection_type_mapping.get(val, val) for val in self.connection_type]
        return mapped_types

    def resolve_labels(self, labels_by_key_value):
        """Extract label IDs from list of key-value pairs.
        Send a request: /labels?fields=id,key,value&key=<key>&value=<value>
        Returns a pipe-separated string of label IDs."""
        ids = []
        pairs = [pair.strip() for pair in labels_by_key_value.split(",") if pair.strip()]
        self.log(LogLevel.DEBUG, "Extracted label pairs: {} ", pairs)
        for pair in pairs:
            if ":" not in pair:
                continue
            key, value = [x.strip() for x in pair.split(":", 1)]
            params = {
                "fields": "id,key,value",
                "key": key,
                "value": value
            }
            response = self.utils.request("labels", parameters=params, api_v4=True)
            self.log(LogLevel.DEBUG, "Received response: {} ", response)
            for obj in response.get("objects", []):
                if "id" in obj:
                    ids.append(obj["id"])
        return "|".join(ids)

    def collect_reputation_alerts(self):
        """Collect reputation alerts from the Guardicore management server."""
        from_time, to_time = self.utils.get_timestamps(REPUTATION_LOG, PREV_TIMESTAMP_R)
        parameters = self.create_parameters(from_time, to_time, "request_time")
        parameters.update({"response": "malicious"})
        self.collect_data(REPUTATION_LOG, parameters, self.process_reputation_alert)


def validate_param(helper, param, param_name, error_message, validation_func):
    try:
        if param and not validation_func(param):
            raise ValueError(error_message)
    except Exception as e:
        helper.log_error(f"An error occurred while validating {param_name}: {e}")
        raise ValueError(error_message)


def validate_input(helper, definition):
    """Validate the user input. Check if the guardicore_management_server parameter is a valid IP or FQDN and if the port"""
    helper.log_info("Validating user input for {}".format(definition.parameters.get("guardicore_management_server")))

    # Validate the guardicore_management_server parameter
    validate_param(helper, definition.parameters.get('guardicore_management_server', None),
                   'guardicore_management_server',
                   "Field Guardicore Management Server must be a valid IP or FQDN",
                   lambda x: isinstance(x, str) and x.strip() and (
                           re.match(r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$', x) or re.match(
                       r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
                       x)))

    # Validate the port parameter
    validate_param(helper, definition.parameters.get('port', None),
                   'port',
                   "Field Port must be a valid integer in the range 1-65535",
                   lambda x: re.match(r'^[1-9][0-9]{0,4}$', x) and 1 <= int(x) <= 65535)

    # Validate the start_date parameter
    validate_param(helper, definition.parameters.get("start_date"),
                   'start_date',
                   "Field `Start date` must be a valid date in the format YYYY/MM/DD",
                   lambda x: bool(datetime.strptime(x, '%Y/%m/%d')))

    # Validate the end_date parameter
    validate_param(
        helper,
        definition.parameters.get("end_date"),
        'end_date',
        "Field `End date` must be a valid date, larger than `Start date` in the format YYYY/MM/DD. "
        "Daily connections must be enabled.",
        lambda x: (
                bool(x) and
                bool(datetime.strptime(x, '%Y/%m/%d')) and
                bool(definition.parameters.get("start_date")) and
                bool(int(definition.parameters.get('use_daily_connections')))
        )
    )

    start_date_str = definition.parameters.get("start_date")
    end_date_str = definition.parameters.get("end_date")
    if start_date_str and end_date_str:
        start_date, end_date = map(lambda x: datetime.strptime(x, '%Y/%m/%d'), (start_date_str, end_date_str))

        if end_date < start_date:
            helper.log_error(f"An error occurred while validating {end_date=} {start_date=}")
            raise ValueError("Field `End date` must be greater than or equal to `Start date`")

    # Validate the request_timeout parameter
    validate_param(helper, definition.parameters.get('request_timeout', None),
                   'request_timeout',
                   "Field `Request timeout` must be a valid integer less than 100",
                   lambda x: re.match(r'^[1-9][0-9]{0,3}$', x) and 1 <= int(x) <= 100)

    # Validate the event_limit parameter
    validate_param(helper, definition.parameters.get('event_limit', None),
                   'event_limit',
                   "Field `Event limit` must be a valid integer less than 5000",
                   lambda x: re.match(r'^[1-9][0-9]{0,3}$', x) and 1 <= int(x) <= 5000)

    # Validate the log_export_delay parameter
    validate_param(helper, definition.parameters.get('log_export_delay', None),
                   'log_export_delay',
                   "Field `Log export delay` must be a valid integer less than 180",
                   lambda x: re.match(r'^[1-9][0-9]{0,2}$', x) and 0 <= int(x) <= 180)

    # Validate the maximum_task_retries_per_date parameter
    validate_param(helper, definition.parameters.get('maximum_task_retries_per_date', None),
                   'maximum_task_retries_per_date',
                   "Field `Maximum task retries per date` must be a valid positive integer less or equal to 10",
                   lambda x: re.match(r'^[1-9][0-9]?$', x) and 0 <= int(x) <= 10)

    # Validate the connection_type parameter
    selected_connections = definition.parameters.get('connection_type', None)
    # Split the '~' separated values into a list
    selections = selected_connections.split('~')
    validate_param(helper, selections,
                   'connection_type',
                   "Field `Connection type` can't contain the `Any` option together with other options",
                   lambda x: not ("Any" in (x if isinstance(x, list) else [opt.strip() for opt in x.split(",")]) and
                                  len(x if isinstance(x, list) else [opt.strip() for opt in x.split(",")]) > 1))

    # Validate the policy_verdict parameter
    selected_verdicts = definition.parameters.get('policy_verdict', None)
    # Split the '~' separated values into a list
    selections = selected_verdicts.split('~')
    validate_param(helper, selections,
                   'policy_verdict',
                   "Field `Policy verdict` can't contain the `Any` option together with other options",
                   lambda x: not ("Any" in (x if isinstance(x, list) else [opt.strip() for opt in x.split(",")]) and
                                  len(x if isinstance(x, list) else [opt.strip() for opt in x.split(",")]) > 1))

    # Validate the filter_by_labels parameter
    validate_param(helper, definition.parameters.get('filter_by_labels', None),
                   'filter_by_labels',
                   "Field `Filter by Labels` must be a comma-separated list of key:value pairs (e.g. key1:val1,key2:val2)",
                   lambda x: all(
                       pair.count(":") == 1 and all(s.strip() for s in pair.split(":", 1))
                       for pair in x.split(",") if pair.strip()
                    ) if x else True
    )

    helper.log_info("Inputs validated!")
    pass


def collect_events(helper, ew):
    """Collect events from Guardicore management server. Creates a SplunkAddon object and collects data from the API.

    :param helper: Splunk helper object
    :param ew: Splunk Event Writer object"""
    utils = GuardicoreHelper(helper, ew)
    client = GuardicoreClient(helper, ew, utils)
    daily_connections_manager = DailyConnectionsManager(helper, ew, utils)
    token = utils.get_token()

    if token:
        mgmt_server = helper.get_arg("guardicore_management_server")
        mgmt_port = helper.get_arg("port")
        use_daily_connections = helper.get_arg("use_daily_connections")
        filter_by_labels = helper.get_arg("filter_by_labels")
        connection_type = helper.get_arg("connection_type")
        policy_verdict = helper.get_arg("policy_verdict")
        helper.log_info(
            "Connected to Guardicore management server {}:{} successfully. Config:\n "
            " Using daily connections: {}, \n "
            " Filter by Labels: {}, \n "
            " Connection type: {}, \n "
            " Policy verdict: {}, \n ".format(
                mgmt_server,mgmt_port,
                use_daily_connections,
                filter_by_labels,
                connection_type,
                policy_verdict))

        utils.headers = {"Authorization": "bearer {}".format(token)}

        use_daily_connections = helper.get_arg("use_daily_connections")
        collect_connections = daily_connections_manager.collect_daily_connections \
            if use_daily_connections else client.collect_connections

        # collect data from REST API
        for func in [client.collect_agent_flags_status, client.collect_component_status,
                     client.collect_dashboard_health_status, collect_connections,
                     client.collect_reputation_alerts]:

            func()
        utils.logout()
    else:
        helper.log_error("Error connecting to mgmt server {}".format(helper.get_arg("guardicore_management_server")))

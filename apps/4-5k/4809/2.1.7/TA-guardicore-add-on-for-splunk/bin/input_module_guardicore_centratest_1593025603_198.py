
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import calendar
import traceback


LIMIT = 1000
VERIFY=True

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    pass

def datetime_to_timestamp(dt):
    """
    Convert a datetime object to timestamp in ms since epoch (which is the format
     used to query management).
    :param dt: datetime timestamp
    :return: dt as milliseconds since epoch
    """
    return int(calendar.timegm(dt.timetuple()) * 1000 + dt.microsecond / 1000)

def _get_data(helper, endpoint, method="GET", parameters=None, headers={}, payload=None, use_proxy=True):
    global_centra_management_server = helper.get_arg("centra_management_server")
    global_port = helper.get_arg("port")
    timeout = int(helper.get_arg("request_timeout"))
    mgmt_api_uri = "https://{}:{}/api/v3.0".format(global_centra_management_server, global_port)
    
    url = "/".join([mgmt_api_uri, endpoint])
    if method == "POST":
        headers.update({"Content-Type": "application/json"})
    
    try:
        response = helper.send_http_request(url=url, method=method, headers=headers, parameters=parameters, payload=payload, use_proxy=use_proxy, verify=VERIFY, timeout=timeout)
        try:
            return response.json()
        except ValueError:
            return response.text
    except Exception as e:
        helper.log_critical("Failed getting data from REST API") 
        helper.log_error(traceback.format_exc())
        
def _get_token(helper):
    username = helper.get_arg("api_username")
    password= helper.get_arg("api_password")
    
    payload = {"username": username, "password": password}
    return _get_data(helper, "authenticate", method="POST", payload=payload).get("access_token")
    
def _logout(helper, headers):
    return _get_data(helper, "logout", method="POST", headers=headers)

def _write_event(helper, ew, data):
    event_data = json.dumps(data)
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=event_data)
    ew.write_event(event)

def collect_agent_flags_status(helper, ew, headers):
    helper.log_debug("starting to collect agent status flags")
    parameters = dict(filter_name="status_flags", limit=1000)
    flags_count = _get_data(helper, "agents/filter-options", headers=headers, parameters=parameters)
    
    if "available_options" in flags_count: # changed in v32
        flags_count = flags_count.get("available_options", [])
    
    for flag in flags_count:
        helper.log_debug(flag)
        if flag["value"] != "undefined":
            data = {"data_type": "agent_flags", "flag": flag["text"], "count": flag["count"]}
            _write_event(helper, ew, data)
    helper.log_debug("done collecting agent status flags")

    
def collect_componenet_status(helper, ew, headers):
    helper.log_debug("starting to collect component status")
    parameters = dict(filter_name="display_status", limit=1000)
    
    for component in ["agent_aggregators", "honeypots", "collectors"]:
        endpoint = "{}/filter-options".format(component)
        status_count = _get_data(helper, endpoint, headers=headers, parameters=parameters)
        
        if "available_options" in status_count: # changed in v32
            status_count = status_count.get("available_options", [])
        
        for status in status_count:
            helper.log_debug(status)
            data = {"data_type": "component_status", "status": status["text"], "count": status["count"], "component_type": component}
            _write_event(helper, ew, data)
    helper.log_debug("finished collecting component status")

            
def collect_mgmt_status(helper, ew, headers):
    stats = _get_data(helper, "system-status/stats", headers=headers)["stats"]
    mgmt_ip = helper.get_arg("centra_management_server")
    mgmt_port = helper.get_arg("port")

    # check mgmt services
    helper.log_debug("checking mgmt services")
    services = stats["services"]
    service_errors = 0
    total_services = 0
    for service in services["data"]:
        total_services += 1
        if not service["is_running"]:
            service_errors += 1
    
    data = {"data_type": "mgmt_services", "errors": service_errors,"total_services": total_services, "mgmt_ip": mgmt_ip, "mgmt_port": mgmt_port} 
    _write_event(helper, ew, data)
    
    # check resources
    helper.log_debug("checking mgmt resources")
    resources = stats["resources"]
    resources_errors = 0
    for resource in resources["data"].values():
        if resource["is_problem"]:
            resources_errors += 1
    
    data = {"data_type": "mgmt_resources", "errors": resources_errors, "mgmt_ip": mgmt_ip, "mgmt_port": mgmt_port} 
    _write_event(helper, ew, data)
    
    # check components
    helper.log_debug("collecting system components stats")
    system_components = stats["system_components"]
    for component in system_components["data"]:
        component["data_type"] = "component_overview"
        component["component_type"] = component.pop("key")        
        _write_event(helper, ew, component)

def _get_timestamps(key, helper):
    conn_aggr_time = int(helper.get_arg("connection_aggregation_time"))
    from_time = helper.get_check_point(key)
    if from_time is None:
        from_time = str(datetime_to_timestamp(datetime.datetime.utcnow() - 3*datetime.timedelta(minutes=conn_aggr_time)))
    to_time = str(datetime_to_timestamp(datetime.datetime.utcnow() - 2*datetime.timedelta(minutes=conn_aggr_time)))
    return from_time, to_time

def collect_connections(helper, ew, headers):
    helper.log_debug("starting to collect connections")

    from_time, to_time = _get_timestamps("prev_timestamp_c", helper)
    helper.save_check_point("prev_timestamp_c", to_time)

    parameters = dict(policy_verdict="blocked,alerted_by_management", from_time=from_time, to_time=to_time, sort="-slot_start_time")
    if helper.get_arg("collect_allowed_connections"):
        parameters.pop("policy_verdict")
    
    total_count = _get_data(helper, "connections", headers=headers, parameters=parameters)["total_count"]
    helper.log_debug("found {} new connections".format(total_count))

    from_event = 0
    to_event = min(LIMIT, total_count)
    while (total_count + LIMIT - 1) >= to_event:
        parameters.update({"from": from_event, "limit": LIMIT})
        connections = _get_data(helper, "connections", headers=headers, parameters=parameters)["objects"]
        for conn in connections:
            conn["data_type"] = "connection"
            conn["rule_display_name"] = "RUL-{}".format(conn["policy_rule"][:8])
            if conn["policy_verdict"] in ["blocked_by_source", "blocked_by_destination"] :
                conn["verdict"] = "blocked"
            elif conn["policy_verdict"].startswith("alerted"):
                conn["verdict"] = "alerted"
            else:
                conn["verdict"] = "allowed"
            _write_event(helper, ew, conn)
        from_event = to_event
        to_event += LIMIT

    helper.log_debug("finished collecting connections")


def collect_reputation_alerts(helper, ew, headers):
    helper.log_debug("starting to collect reputation alerts")
    from_time, to_time = _get_timestamps("prev_timestamp_r", helper)
    helper.save_check_point("prev_timestamp_r", to_time)

    parameters = dict(response="malicious", from_time=from_time, to_time=to_time, sort="-request_time")

    total_count = _get_data(helper, "reputation-log", headers=headers, parameters=parameters)["total_count"]
    helper.log_debug("found {} new reputation alerts".format(total_count))

    from_event = 0
    to_event = min(LIMIT, total_count)
    while (total_count + LIMIT - 1) >= to_event:
        parameters.update({"from": from_event, "limit": LIMIT})
        alerts = _get_data(helper, "reputation-log", headers=headers, parameters=parameters)["objects"]
        for alert in alerts:
            alert["data_type"] = "reputation_alert"
            _write_event(helper, ew, alert)
        from_event = to_event
        to_event += LIMIT

    helper.log_debug("finished collecting reputation alerts")
    

def collect_events(helper, ew):
    if not helper.get_arg("collect_data"):
        helper.log_info("skipping data collection")
        return
    
    # authentication
    token = _get_token(helper)
    if token:
        helper.log_info("connected to mgmt server successfully")
        headers = {"Authorization": "bearer {}".format(token)}
        
        # collect data from REST API
        for func in [collect_agent_flags_status, collect_componenet_status, collect_mgmt_status,collect_connections, collect_reputation_alerts]:
            try:
                func(helper, ew, headers)
            except:
                helper.log_error("Error running {}".format(func))
                helper.log_error(traceback.format_exc())
        _logout(helper, headers)
        
    else:
        helper.log_error("Error connecting to mgmt server")


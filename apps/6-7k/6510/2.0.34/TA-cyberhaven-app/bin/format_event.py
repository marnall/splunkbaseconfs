# format_event
from jsonpath_ng.ext import parse

parse_results_cache = {}
def parse_with_cache(expression):
    if not expression in parse_results_cache:
        try:
            parse_results_cache[expression] = parse(expression)
        except Exception as err:
          parse_results_cache[expression] = None  
    return parse_results_cache[expression]


LIST_DELIMITER = ", "

user_reaction_messages = {
    'acknowledged': "Acknowledged",
    'none': "None",
    'not_applicable': "N/A",
    'provided_explanation': "Provided an explanation",
    'requested_review': "Requested review",
    'requested_unblock': "Self-unblocked",
    'warned': "Viewed the warning",
}

sensor_name_to_sensor_type = {
	"EndpointSensorApplication":         "endpoint",
	"EndpointSensorFinder":              "endpoint",
	"EndpointSensorExplorer":            "endpoint",
	"EndpointSensorOneDrive":            "endpoint",
	"EndpointSensorOutlook":             "endpoint",
	"EndpointSensorBrowser":             "endpoint",
	"EndpointSensorOfficeDocTracker":    "endpoint",
	"EndpointSensorClipboard":           "endpoint",
	"EndpointSensorMicrosoftWord":       "endpoint",
	"EndpointSensorMicrosoftExcel":      "endpoint",
	"EndpointSensorMicrosoftPowerPoint": "endpoint",
	"EndpointSensorSlack":               "endpoint",

	"CloudSensorOneDrive":       "cloud",
	"CloudSensorEmailOffice365": "cloud",
	"CloudSensorEmailGoogle":    "cloud",
	"CloudSensorSalesforce":     "cloud",

	"BrowserExtensionSensor": "browser extension",
}

incident_response_to_message = {
    'access_restricted': "Blocked",
    'access_restricted_expired': "Blocking expired",
    'access_restricted_removed': "Blocking removed",
    'access_restricted_rate_limited': "Blocked, Response skipped: throttled",
    'not_applicable': "N/A",
    'skipped_rate_limited': "Response skipped: throttled",
    'skipped_timeout': "Response skipped: timeout",
    'pending': "Response pending",
    'warning_received': "Warning received by endpoint",
    'warned': "Warning shown",
}

severity_messages = {
    '0': "Informational",
    '1': "Low",
    '2': "Medium",
    '3': "High",
    '4': "Critical",
}

sensitivity_messages = {
    '0': "Unrestricted",
    '1': "Low",
    '2': "Moderate",
    '3': "High",
    '4': "Critical",
}

ai_assessment_level = {
    '0': "Informational",
    '1': "Low",
    '2': "Medium",
    '3': "High",
    '4': "Critical",
}

created_by_map = {
    'policy_engine': 'policy',
    'linea': 'linea-ai',
}

DEFAULT_FIELDS_CONFIG = {
    "id": {"template": "id"},
    "search_name": {"template": "Dataset: {dataset[name]}, Category: {category[name]}"},
    "file_name": {"template": "file", "default": "none"},
    "source_location": {"template": "edge.source.location_outline"},
    "source_type": {"template": "edge.source.location"},
    "destination_location": {"template": "edge.destination.location_outline"},
    "destination_type": {"template": "edge.destination.location"},
    
    "alert_id": {"template": "alert_id"},
    "event_type": {"template": "edge.destination.event_type"},
    "created_by": {"template": "incident_type", "mappers": created_by_map},
    "ai_assessed_risk": {"template": "ai_severity", "mappers": ai_assessment_level},

    "assignee": {"template": "assignee"},
    "resolution_status": {"template": "resolution_status"},
    "severity": {"template": ["category.severity", "severity"], "mappers": severity_messages},
    "sensitivity": {"template": ["dataset.sensitivity"], "mappers": sensitivity_messages},
    "dataset_name": {"template": "dataset.name"},
    "policy_name": {"template": "category.name"},
    "user": {"template": "user"},
    "file": {"template": "file"},
    "document_tags": {"template": "document_tags"},
    "response": {"template": "incident_response", "mappers": incident_response_to_message, "default": 'N/A'},
    "user_reaction": {"template": "incident_reactions", "mappers": user_reaction_messages},
    "resolved_by": {"template": "admin_history[?(@.new_status==\"resolved\")].user"},

    "date": {"template": "edge.destination.local_time"},
    "event_time": {"template": "event_time"},
    "trigger_time": {"template": "trigger_time"},
    "local_time UTC": {"template": "edge.destination.local_time"},
    "resolution_time UTC": {"template": "resolution_time"},

    "app_name": {"template": "edge.destination.app_name"},
    "app_main_window_title": {"template": "data.app_main_window_title"},
    "app_package_name": {"template": "data.app_package_name"},
    "app_description": {"template": "data.app_description"},
    "app_command_line": {"template": "data.app_command_line", "default": False},
    "blocked": {"template": "edge.destination.blocked", "default": False},
    "explanation": {"template": "explanation"},
    "browser_page_url": {"template": "edge.destination.browser_page_url"},
    "browser_page_domain": {"template": "edge.destination.browser_page_domain"},
    "browser_page_title": {"template": "edge.destination.browser_page_title"},
    "content_uri": {"template": "edge.destination.content_uri"},
    "cloud_provider": {"template": "edge.destination.cloud_provider"},
    "cloud_app": {"template": "edge.destination.cloud_app"},
    "cloud_app_account": {"template": "edge.destination.cloud_app_account"},
    "data_size": {"template": ["data.data_size", "source_data.data_size"]},
    "domain": {"template": "edge.destination.domain"},
    "domain_category": {"template": "data.destination[0]"},
    "endpoint_id": {"template": "edge.destination.endpoint_id"},
    "email_account": {"template": "edge.destination.email_account"},
    "file_path": {"template": "data.path"},
    "file_extension": {"template": "data.extension"},
    "file_size": {"template": ["data.file_size", "source_data.file_size"]},
    "group_name": {"template": "edge.destination.group_name"},
    "hostname": {"template": "edge.destination.hostname"},
    "location": {"template": "edge.destination.location"},
    "local_user_name": {"template": "edge.destination.local_user_name"},
    "local_user_sid": {"template": "edge.destination.local_user_sid"},
    "local_groups": {"template": "edge.destination.local_groups", "map_fun": "{sid}: {name}"},

    "local_machine_name": {"template": "edge.destination.local_machine_name"},
    "media_category": {"template": "data.media_category"},
    "md5_hash": {"template": "edge.destination.md5_hash"},
    "salesforce_account_name": {"template": "data.salesforce_account_name"},
    "salesforce_account_domains": {"template": "data.salesforce_account_domains"},
    "printer_name": {"template": "data.printer_name"},
    "removable_device_name": {"template": "data.removable_device_name"},
    "removable_device_vendor_id": {"template": "data.removable_device_vendor_id"},
    "removable_device_product_id": {"template": "data.removable_device_product_id"},
    "url": {"template": "data.url"},
    "content_identification_policies": {"template": ["content_identification_policies", "data.content_identification_policies"]},
    "exact_data_match": {"template": ["edm_attributes", "data.edm_attributes"]},
    "sensor_type": {"template": "data.sensor_name", "mappers": sensor_name_to_sensor_type},

    #  CIM fields https://docs.splunk.com/Documentation/CIM/4.2.0/User/Alerts
    "app": {"template": "edge.destination.app_name"},
    "body": {"template": ["personal_info", "data.personal_info"]},
    "dest": {"template": ["edge.destination.location_outline", "data.location_outline"]},
    "dest_category": {"template": "category.id"},
    "src": {"template": "edge.source.hostname"},
    "src_bunit": {"template": "edge.source.location"},
    "src_category": {"template": "edge.source.event_type"},
    "src_priority": {"template": "edge.source.event_type"},
    "subject": {"template": "category.name"},
    "tag": {"template": "document_tags"},
    "type": {"template": "edge.destination.event_type"},
}


def format_event(event, config = DEFAULT_FIELDS_CONFIG):
    if not config:
        config = DEFAULT_FIELDS_CONFIG
    result_formatted = {}
    for key, conf in config.items():
        template_list = conf.get('template')
        map_fun = conf.get('map_fun')
        mappers = conf.get('mappers')
        default_value = conf.get('default')

        if isinstance(template_list, str):
            template_list = [template_list]

        for template in template_list:
            value = parse_temp(template, event, map_fun)
            mapped_value = value
            if mappers:
                if isinstance(value, list):
                    mapped_value = LIST_DELIMITER.join([mappers.get(key) or key
                                                        for key in value or []])
                if isinstance(value, str) or isinstance(value, int):
                    mapped_value = mappers.get(str(value)) or value

            result_formatted[key] = format_value(mapped_value)
            if mapped_value:
                break

    if not result_formatted[key] and default_value != None:
        result_formatted[key] = default_value

    return result_formatted


def is_temp_expression(input_string):
    return "{" in input_string


def parse_template_str(input_string):
    result = []
    start_index = 0

    # Iterate over each character in the input string
    for i in range(len(input_string)):
        char = input_string[i]
        if char == "{":
            text = input_string[start_index:i]
            result.append({"text": text})
            start_index = i + 1  # Add 1 to exclude the "{" character
        elif char == "}":
            # If we encounter a "}" character and we're currently in an expression,
            # add the expression segment to the result and reset the start index
            end_index = i
            expression = input_string[start_index:end_index]
            result.append({"expression": expression})
            start_index = i + 1

    # Add the final text segment to the result
    if start_index is not None:
        expression = input_string[start_index:]
        result.append({"text": expression})
    return result


def parse_exp_result(result):
    if len(result) > 0:
        value = result[0].value
        if isinstance(value, list):
            return LIST_DELIMITER.join(value)
        else:
            return value
    else:
        return "None"


def parse_temp_expression(value, event):
    parsed_list = parse_template_str(value)
    str_result_list = []
    for item in parsed_list:
        if 'text' in item:
            str_result_list.append(item.get('text'))
        else:
            jsonpath_expr = parse_with_cache(item.get('expression'))
            if not jsonpath_expr:
                break
            result = jsonpath_expr.find(event)
            str_result_list.append(parse_exp_result(result))

    return ''.join(str_result_list)


def parse_temp(template, object_val, map_fun):
    if isinstance(object_val, list):
        result = []
        for val in object_val:
            temp_result = parse_temp(template, val, map_fun)
            if temp_result:
                result.append(temp_result)

        return result

    if is_temp_expression(template):
        return parse_temp_expression(template, object_val)
    else:
        jsonpath_expr = parse_with_cache(template)
        if not jsonpath_expr:
            return None
        result = jsonpath_expr.find(object_val)
        if not len(result):
            return None
        if map_fun:
            return parse_temp(map_fun, result[0].value, None)
        return result[0].value


def format_value(value):
    if not value:
        return value
    if isinstance(value, list):
        value = LIST_DELIMITER.join(value)

    if isinstance(value, str):
        return value.replace('\r', '').replace('\n', '')
    return value

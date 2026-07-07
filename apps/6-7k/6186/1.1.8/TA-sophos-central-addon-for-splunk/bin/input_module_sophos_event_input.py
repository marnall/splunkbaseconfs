# encoding = utf-8
import json
from log_manager import setup_logging
from sophos_consts import EVENT_ENDPOINT
from sophos_collect import SophosCollect
from sophos_common_utils import read_tenants
import sophos_common_utils as utils

_LOGGER = setup_logging("sophos_event_input")


def validate_input(helper, definition):
    """Validate the input stanza configurations."""
    pass


def get_exculde_paramerters(helper):
    """To form the parameters list which needs to be excluded.

        Args:
            helper (obj): Splunk helper object

        Returns:
            str: excluded events string
    """
    endpoint_application_allowed = helper.get_arg("endpoint_application_allowed")
    endpoint_compliant = helper.get_arg("endpoint_compliant")
    endpoint_device_alerted_only = helper.get_arg("endpoint_device_alerted_only")
    endpoint_non_compliant = helper.get_arg("endpoint_non_compliant")
    endpoint_save_scan_complete = helper.get_arg("endpoint_save_scan_complete")
    endpoint_update_failure = helper.get_arg("endpoint_update_failure")
    endpoint_update_success = helper.get_arg("endpoint_update_success")
    endpoint_web_control_violation = helper.get_arg("endpoint_web_control_violation")
    endpoint_web_filtering_blocked = helper.get_arg("endpoint_web_filtering_blocked")

    exclusions = {
        "endpoint_application_allowed": endpoint_application_allowed,
        "endpoint_compliant": endpoint_compliant,
        "endpoint_device_alerted_only": endpoint_device_alerted_only,
        "endpoint_non_compliant": endpoint_non_compliant,
        "endpoint_save_scan_complete": endpoint_save_scan_complete,
        "endpoint_update_failure": endpoint_update_failure,
        "endpoint_update_success": endpoint_update_success,
        "endpoint_web_control_violation": endpoint_web_control_violation,
        "endpoint_web_filtering_blocked": endpoint_web_filtering_blocked,
    }
    params = {
        "endpoint_non_compliant": "Event::Endpoint::NonCompliant",
        "endpoint_compliant": "Event::Endpoint::Compliant",
        "endpoint_device_alerted_only": "Event::Endpoint::Device::AlertedOnly",
        "endpoint_update_failure": "Event::Endpoint::UpdateFailure",
        "endpoint_save_scan_complete": "Event::Endpoint::SavScanComplete",
        "endpoint_application_allowed": "Event::Endpoint::Application::Allowed",
        "endpoint_update_success": "Event::Endpoint::UpdateSuccess",
        "endpoint_web_control_violation": "Event::Endpoint::WebControlViolation",
        "endpoint_web_filtering_blocked": "Event::Endpoint::WebFilteringBlocked"
    }
    param_values = []
    for event, value in exclusions.items():
        if value:
            param_values.append(params[event])
    params = ",".join(param_values)
    if params:
        _LOGGER.info("Excluded event parameters %s" % params)
    return params


def get_events(sophos_collect, tenant_id, api_host, cursor, exclude_params, page_limit):
    """Get events for a given tenant."""
    events = []
    headers = {"X-Tenant-Id": tenant_id}
    parameters = {"limit": page_limit}
    if cursor:
        parameters["cursor"] = cursor

    if exclude_params:
        parameters["exclude_types"] = exclude_params

    response = sophos_collect._call_endpoint(
        api_host,
        EVENT_ENDPOINT,
        headers=headers,
        method="GET",
        scheme_flag=True,
        parameters=parameters,
    )
    if not response:
        return events, None
    response = response.json()
    events = response.get("items")
    next_cursor = response.get("next_cursor")
    while response.get("has_more") is True:
        parameters["cursor"] = next_cursor
        response = sophos_collect._call_endpoint(
            api_host,
            EVENT_ENDPOINT,
            headers=headers,
            method="GET",
            parameters=parameters,
            scheme_flag=True,
        )
        if response:
            response = response.json()
            for event in response.get("items"):
                events.append(event)
            next_cursor = response.get("next_cursor")
        else:
            break

    return events, str(next_cursor)


def collect_events(helper, ew):
    """To collect sophos events."""
    try:
        # Get Splunk session key
        session_key = helper.context_meta["session_key"]
        # Get API page limit
        page_limit = helper.get_arg("page_limit")
        # Get input name
        input_name = helper.get_input_stanza_names()
        # Fetch last stored cursor
        cursors = helper.get_check_point(input_name) or {}
        # Initialize SophosCollect Object
        sophos_collect = SophosCollect(session_key)
        # Verify Sophos Configurations exist
        try:
            sophos_collect.check_credentials()
        except Exception as e:
            _LOGGER.error(str(e))
            exit()

        who_am_i = utils.get_sophos_config_params(session_key)
        account_id_type = who_am_i.get("account_id_type")
        tenants_data = []
        if account_id_type == "tenant":
            tenants_data.append(
                (
                    who_am_i.get("apihost_dataregion"),
                    who_am_i.get("account_id"),
                )
            )
        elif account_id_type in ["partner", "organization"]:
            bulk_tenants = read_tenants(_LOGGER, "Events")
            tenants_data = [
                (tenant.get("apiHost"), tenant.get("id"))
                for tenant in bulk_tenants["items"]
            ]
        else:
            _LOGGER.info(
                "Saved credentails are not for either tenant, partner or organization hence exiting.")
            exit()
        tenant_cursor = cursors if cursors else {}
        exclude_params = get_exculde_paramerters(helper)
        _LOGGER.info("Starting data collection process for {} input with {} page_limit.".format(
            input_name, str(page_limit)))
        for api_host, tenant_id in tenants_data:
            try:
                # Collect Sophos Events data
                response, cursor = get_events(
                    sophos_collect,
                    tenant_id,
                    api_host,
                    tenant_cursor.get(tenant_id),
                    exclude_params,
                    page_limit
                )
                if not (response or cursor):
                    _LOGGER.error(
                        "Failed to fetched events for tenant ID {} from Sophos.".format(
                            tenant_id
                        )
                    )
                    continue
                _LOGGER.debug(
                    "Successfully fetched events for tenant ID {} from Sophos.".format(
                        tenant_id
                    )
                )

                # Iterate over the response and index it in Splunk
                for data in response:
                    event = helper.new_event(
                        source=helper.get_input_type(),
                        index=helper.get_output_index(),
                        sourcetype=helper.get_sourcetype(),
                        data=json.dumps(data),
                    )
                    ew.write_event(event)
                _LOGGER.info(
                    "Successfully ingested events for tenant ID: {} and input: {}.".format(
                        tenant_id, input_name
                    )
                )
                if cursor:
                    tenant_cursor[tenant_id] = cursor
            except Exception as exception:
                _LOGGER.error(
                    "Exception occurred while ingesting events for tenant ID {} and input {}. Exception: {}".format(
                        tenant_id, input_name, str(exception)), stack_info=True
                )
                continue

        # Store checkpoint time
        helper.save_check_point(input_name, tenant_cursor)
        _LOGGER.info("Checkpoint is updated for {} input.".format(input_name))
        _LOGGER.info("Data collection process is completed for {} input.".format(input_name))
    except Exception as exception:
        _LOGGER.error(
            "Exception occurred for {} input. Exception: {}".format(str(input_name), str(exception)),
            stack_info=True
        )

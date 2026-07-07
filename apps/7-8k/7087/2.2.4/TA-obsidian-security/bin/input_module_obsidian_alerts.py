# encoding = utf-8

import json

import jwt
import obsidian_queries
import obsidian_utils
import requests

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""

ALERTS_FETCH_TYPE = "obsidian:alerts"


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    try:
        interval = int(definition.parameters.get("interval") or "60")
    except (ValueError, TypeError) as e:
        raise Exception(
            f"Invalid interval value: {definition.parameters.get('interval')} - {str(e)}"
        )
    if interval != -1 and interval < 60:
        raise Exception(
            "Interval must be greater or equal to 60, or -1 for one-time execution"
        )

    # obtain the api_token
    input_name = definition.metadata.get("name")
    session_key = definition.metadata.get("session_key")
    opt_obsidian_api_token = obsidian_utils.lookup_api_token(
        "obsidian_alerts", input_name, session_key
    )

    # Validate the other fields
    opt_subdomain = definition.parameters.get("subdomain")
    if (
        opt_subdomain.find(":") > -1
        or opt_subdomain.find("/") > -1
        or obsidian_utils.is_full_domain(opt_subdomain)
    ):
        raise Exception(
            "Subdomain: unexpected input. Please input only subdomain, not the full url."
        )

    token_payload = jwt.decode(
        opt_obsidian_api_token, options={"verify_signature": False}
    )
    token_subdomain_name = token_payload.get("aud")
    if token_subdomain_name:
        if token_subdomain_name.lower() != opt_subdomain.lower():
            raise Exception(
                f"The token is not valid for the given subdomain. The subdomain name is {token_subdomain_name}, but your input subdomain name is {opt_subdomain}, please check!"
            )
    else:
        helper.log_info(
            f'msg=The subdomain name in the token is not able to be validated. The subdomain name in token is:{token_subdomain_name}"'
        )

    is_fetch_related_events = definition.parameters.get("fetch_related_events")
    if is_fetch_related_events:
        try:
            max_retries = int(definition.parameters.get("max_retries") or "5")
        except (ValueError, TypeError) as e:
            raise Exception(
                f"Invalid max_retries value: {definition.parameters.get('max_retries')} - {str(e)}"
            )
        if max_retries < 5:
            raise Exception(
                "Max Retries for fetching alert related events must be greater or equal to 5"
            )
    try:
        initial_alert_id = int(definition.parameters.get("initial_alert_id") or "0")
    except (ValueError, TypeError) as e:
        raise Exception(
            f"Invalid initial_alert_id value: {definition.parameters.get('initial_alert_id')} - {str(e)}"
        )
    if initial_alert_id < 0:
        raise Exception("Initial Alert ID should be greater or equal 0.")
    if initial_alert_id >= 2147483647:
        raise Exception("Initial Alert ID should be less than 2147483647.")

    opt_proxy_setting = definition.parameters.get("proxy_setting") or None

    obsidian_api_url = (
        definition.parameters.get("obsidian_api_url") or "https://api.obsec.io/v1/gql"
    )

    try:
        # Set Obsidian API URL
        headers = obsidian_utils.build_headers(opt_obsidian_api_token, opt_subdomain)

        gql_query = obsidian_queries.api_version_query()
        gql_payload = {"query": gql_query, "variables": {}}

        helper.log_debug(
            f'msg="Validate alert input through Obsidian API", org={opt_subdomain}, api_url={obsidian_api_url}, proxy={opt_proxy_setting}'
        )
        response = obsidian_utils.make_request(
            helper, gql_payload, headers, opt_proxy_setting, obsidian_api_url
        )

        response.raise_for_status()
        helper.log_debug(
            f'msg="Successfully connected to Obsidian API", org={opt_subdomain}, api_url={obsidian_api_url}, proxy={opt_proxy_setting}'
        )
    except requests.HTTPError as e:
        helper.log_error(
            f'msg="HTTP Error: {e}", org={opt_subdomain}, api_url={obsidian_api_url}, proxy={opt_proxy_setting}'
        )
        raise Exception(f"HTTP Error: {e}")


def alerts_result_to_json(
    helper,
    result,
    subdomain,
    api_url="https://api.obsec.io/v1/gql",
):
    # returns alert, events list
    d = {"actors": [], "targets": []}

    for entity in result.get("actors", []) or []:
        d["actors"].append(obsidian_utils.entity_to_json(entity))

    for entity in result.get("targets", []) or []:
        d["targets"].append(obsidian_utils.entity_to_json(entity))

    # service is a nested object, change to a string
    service = (result.get("service", {}).get("name", "") or "").lower()
    result["service"] = service

    # datetime fields
    result["event_datetime"] = result["eventDatetime"]
    del result["eventDatetime"]

    # datetime fields
    result["generated_datetime"] = result["generatedDatetime"]
    del result["generatedDatetime"]

    # flatten the catalog stuff
    catalog = result.get("intelligenceCatalogReference") or {}
    result["severity"] = catalog.get("severity", "")
    result["origin"] = catalog.get("origin", "").lower()
    result["intel_type"] = catalog.get("identifier", "")
    del result["intelligenceCatalogReference"]

    # setup title
    result["title"] = (result.get("humanReadableDescription", {}) or {}).get(
        "plain", ""
    )
    del result["humanReadableDescription"]

    # Handle activity filter the same way as JavaScript frontend
    activity_filter = result.get("relatedQueryParameters", {}).get("activityFilter", {})

    # Set events_filter to either the filter property or activityFilter itself
    events_filter = (
        activity_filter.get("filter", activity_filter) if activity_filter else {}
    )

    # If activityFilter has a query property, add it to events_filter
    if activity_filter.get("query"):
        if isinstance(events_filter, dict):
            events_filter = dict(events_filter)  # Create a copy
            events_filter["query"] = activity_filter["query"]
        else:
            events_filter = {"query": activity_filter["query"]}

    result["activity_filter"] = events_filter
    result["query"] = activity_filter.get("query", "")
    del result["relatedQueryParameters"]

    # taxonomy
    result["taxonomy"] = result.get("taxonomy", {})

    # alertExtraData
    result["alert_extra_data"] = result.get("alertExtraData", {})
    del result["alertExtraData"]

    result["actors"] = d["actors"]
    result["targets"] = d["targets"]
    result["obsidian_tenant"] = subdomain

    ticket_id_raw = result.get("ticketId")
    try:
        ticket_id = int(ticket_id_raw)
    except (ValueError, TypeError) as e:
        helper.log_error(
            f"Invalid ticketId in alert result: {ticket_id_raw}, error: {e}"
        )
        ticket_id = 0
    domain_name = obsidian_utils.get_domain_from_api_url(api_url)
    result["obsidian_url"] = f"https://{subdomain}.{domain_name}/alerts/{ticket_id}"

    # Filter raw_event_parsed to keep only specific fields and prevent indexing issues
    # raw_event_parsed is a JSON field, so we get it as a Python dict
    context = result.get("context")
    if context is not None and isinstance(context, dict):
        raw_event_parsed = context.get("raw_event_parsed")
        filtered_raw_event_parsed = obsidian_utils.get_filtered_raw_event_parsed(
            helper, raw_event_parsed
        )
        context["raw_event_parsed"] = filtered_raw_event_parsed

    return result


def get_alert_minmax_id_value(
    helper,
    headers,
    proxy_setting,
    subdomain,
    query_filter,
    obsidian_api_url,
    is_min=True,
):
    if is_min:
        alerts_id_query = obsidian_queries.get_min_alert_id(query_filter=query_filter)
    else:
        alerts_id_query = obsidian_queries.get_max_alert_id(query_filter=query_filter)

    gql_payload = {"query": alerts_id_query, "variables": {}}
    response = obsidian_utils.make_request(
        helper, gql_payload, headers, proxy_setting, obsidian_api_url
    )
    if response.status_code != 200:
        helper.log_error(
            f"msg=\"Received {response.status_code} code and response '{response.content}' for alert count\", org={subdomain}, fetch_type={ALERTS_FETCH_TYPE}"
        )
        return

    try:
        response_data = response.json()
    except ValueError as e:
        helper.log_error(
            f"Invalid JSON response for alert ID: {response.text[:200]}... - {str(e)}"
        )
        return 0

    # Check for GraphQL errors
    if "errors" in response_data:
        helper.log_error(f"GraphQL errors in alert ID query: {response_data['errors']}")
        return 0

    # Safely extract results
    data = response_data.get("data", {})
    if not data:
        helper.log_error("No data field in GraphQL response for alert ID")
        return 0

    intelligence = data.get("getIntelligence", {})
    if not intelligence:
        helper.log_error("No getIntelligence field in GraphQL response for alert ID")
        return 0

    results = intelligence.get("results", [])
    if not results or len(results) == 0:
        helper.log_warning("No alerts found in query results")
        return 0

    result = results[0]
    helper.log_debug(f"Get alert result: {result}")

    ticket_id = result.get("ticketId")
    if ticket_id is None:
        helper.log_warning("ticketId is null in alert result")
        return 0

    try:
        return int(ticket_id)
    except (ValueError, TypeError) as e:
        helper.log_error(f"Invalid ticketId value: {ticket_id}, error: {e}")
        return 0


def fetch_alerts(
    helper,
    ew,
    headers,
    query_filter,
    subdomain,
    proxy_setting,
    fetch_related_events,
    obsidian_api_url,
    max_retries=5,
    initial_alert_id=0,
):
    current_input_name = helper.get_input_stanza_names()
    fetched_related_events_alerts = []
    # Get Checkpoint
    alert_checkpoint_name = f"{subdomain}_alerts"
    existing_alert_id = helper.get_check_point(alert_checkpoint_name)
    if not existing_alert_id:
        helper.log_info(
            f'msg="No existing checkpoint.", org={subdomain}, fetch_type={ALERTS_FETCH_TYPE}'
        )
        if int(initial_alert_id) > 0:
            start_id = int(initial_alert_id)
        else:
            # if we don't have a start id, set one here based on the minimum id (in case it is > 1)
            start_id = get_alert_minmax_id_value(
                helper,
                headers,
                proxy_setting,
                subdomain,
                query_filter,
                obsidian_api_url,
                is_min=True,
            )
        helper.log_info(
            f'msg="Setting start id to {start_id} (based on alert minimum id)", org={subdomain}, fetch_type={ALERTS_FETCH_TYPE}'
        )
    else:
        helper.log_info(
            f'msg="last fetched alert from checkpoint is {existing_alert_id}", org={subdomain}, fetch_type={ALERTS_FETCH_TYPE}'
        )
        # we want to be 1 more than the alert id we fetched last time
        start_id = int(existing_alert_id) + 1

    max_saved_id = start_id
    total_saved_alerts = 0

    # get the max alert id
    alerts_max_id = get_alert_minmax_id_value(
        helper,
        headers,
        proxy_setting,
        subdomain,
        query_filter,
        obsidian_api_url,
        is_min=False,
    )
    if alerts_max_id == 0 or alerts_max_id < start_id:
        helper.log_info(
            f'msg="No new alerts, max:{alerts_max_id}", org={subdomain}, fetch_type={ALERTS_FETCH_TYPE}'
        )
        return total_saved_alerts

    # log that we are starting now
    helper.log_info(
        f'msg="Start fetching alerts, start_id:{start_id}, max_id:{alerts_max_id}", org={subdomain}, fetch_type={ALERTS_FETCH_TYPE}'
    )
    if not fetch_related_events:
        helper.log_info(
            f'msg="Fetching alerts without related events", org={subdomain}, fetch_type={ALERTS_FETCH_TYPE}'
        )

    # set a limit
    limit = 1000

    # Get alerts and related events
    gql_queries = obsidian_queries.get_alert_queries(
        helper,
        start_id,
        alerts_max_id,
        limit,
        query_filter,
    )
    for gql_query in gql_queries:
        gql_payload = {"query": gql_query, "variables": {}}

        response = obsidian_utils.make_request(
            helper, gql_payload, headers, proxy_setting, obsidian_api_url
        )
        if response.status_code != 200:
            helper.log_error(
                f"msg=\"Received {response.status_code} code and response '{response.content}'\", org={subdomain}, fetch_type={ALERTS_FETCH_TYPE}"
            )

            return total_saved_alerts

        raw_results = (
            response.json().get("data", {}).get("getIntelligence", {}).get("results")
            or []
        )
        if not raw_results:
            helper.log_info(
                f'msg="No alerts for this range", org={subdomain}, fetch_type={ALERTS_FETCH_TYPE}'
            )
            continue

        alert_count = 0

        for raw_result in raw_results:
            alert_count = alert_count + 1
            alert = alerts_result_to_json(
                helper, raw_result, subdomain, obsidian_api_url
            )
            try:
                existing_alert_id = int(alert.get("ticketId", 0))
            except (ValueError, TypeError) as e:
                helper.log_error(
                    f"Invalid ticketId in alert: {alert.get('ticketId')}, error: {e}"
                )
                continue
            alert_timestamp_str = alert.get("event_datetime") or "1970-01-01T00:00:00Z"
            alert_output = helper.new_event(
                time=alert_timestamp_str,
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype(),
                data=json.dumps(alert),
            )
            total_saved_alerts += 1
            ew.write_event(alert_output)

            if fetch_related_events:
                helper.log_info(
                    f'msg="Fetching related events for alert_id: {existing_alert_id}"'
                )
                alert_activity_filter = alert.get("activity_filter")
                alert_activity_query = alert.get("query")

                related_alert_activity_checkpoint_name = (
                    f"{subdomain}_{current_input_name}_related_alert_activity"
                )
                alert_activity_query_queue = helper.get_check_point(
                    related_alert_activity_checkpoint_name
                )
                if not alert_activity_query_queue:
                    helper.log_debug(
                        'msg="No existing checkpoint for related alert activity. Fetching all related events"'
                    )
                    alert_activity_query_queue = []

                if existing_alert_id in fetched_related_events_alerts:
                    helper.log_debug(
                        f"Skipping alert_id: {existing_alert_id} as it was already processed in this run."
                    )
                else:

                    helper.log_debug("Adding alert to related activity queue")
                    # If current alert has activity filter, add it to the queue
                    # else, skip it and move on to fetch related events for the alert in the queue
                    if alert_activity_filter:
                        alert_activity_query_queue.append(
                            {
                                "alert_id": existing_alert_id,
                                "activity_filter": alert_activity_filter,
                                "query": alert_activity_query,
                                "count": 0,
                            }
                        )

                    fetched_related_events_alerts.append(existing_alert_id)
                    alert_activity_query_queue = process_fetch_related_events(
                        helper,
                        ew,
                        alert_activity_query_queue,
                        headers,
                        subdomain,
                        proxy_setting,
                        obsidian_api_url,
                        max_retries,
                    )

                    helper.save_check_point(
                        related_alert_activity_checkpoint_name,
                        alert_activity_query_queue,
                    )

            if existing_alert_id >= max_saved_id:
                max_saved_id = existing_alert_id
                # Save checkpoint, should save last fetched alert if we had no hits
                helper.save_check_point(alert_checkpoint_name, str(max_saved_id))

        helper.log_info(
            f'msg="received {alert_count} alerts, new max: {max_saved_id}", org={subdomain}, fetch_type={ALERTS_FETCH_TYPE}'
        )
    return total_saved_alerts


def write_related_events(helper, ew, events, alert_id):
    """
    Write related events to Splunk
    """
    count = 0
    for event in events:
        event["alert_id"] = alert_id
        splunk_event = helper.new_event(
            time=obsidian_utils.get_event_time(event["datetime"]),
            source="obsidian_events",
            index=helper.get_output_index(),
            sourcetype="obsidian:events",
            data=json.dumps(event),
        )
        ew.write_event(splunk_event)
        count += 1
    return count


def collect_events(helper, ew):
    """
    Event collection logic
    """
    # Set log level
    helper.set_log_level(helper.get_log_level())

    # Set variables from input args
    opt_subdomain = obsidian_utils.sanitize_subdomain(helper.get_arg("subdomain"))
    opt_obsidian_api_token = helper.get_arg("api_token")
    opt_alert_query = obsidian_utils.escape_quotes(helper.get_arg("alert_query") or "")
    proxy_setting = helper.get_arg("proxy_setting") or None
    fetch_related_events = helper.get_arg("fetch_related_events") or False
    try:
        max_retries = int(helper.get_arg("max_retries") or "5")
    except (ValueError, TypeError) as e:
        helper.log_error(
            f"Invalid max_retries value: {helper.get_arg('max_retries')}, using default 5 - {str(e)}"
        )
        max_retries = 5
    try:
        initial_alert_id = int(helper.get_arg("initial_alert_id") or "0")
    except (ValueError, TypeError) as e:
        helper.log_error(
            f"Invalid initial_alert_id value: {helper.get_arg('initial_alert_id')}, using default 0 - {str(e)}"
        )
        initial_alert_id = 0
    obsidian_api_url = (
        helper.get_arg("obsidian_api_url") or "https://api.obsec.io/v1/gql"
    )

    headers = obsidian_utils.build_headers(opt_obsidian_api_token, opt_subdomain)

    proxy_log_message = ""
    if proxy_setting:
        proxy_log_message = f" (proxy: {proxy_setting})"

    helper.log_info(
        f'msg="starting collection{proxy_log_message}", org={opt_subdomain}, fetch_type={ALERTS_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
    )
    try:
        count = fetch_alerts(
            helper,
            ew,
            headers,
            opt_alert_query,
            opt_subdomain,
            proxy_setting,
            fetch_related_events,
            obsidian_api_url,
            max_retries,
            initial_alert_id,
        )
        helper.log_info(
            f'msg="fetch complete, saved {count} alerts", org={opt_subdomain}, fetch_type={ALERTS_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
        )
    except requests.exceptions.HTTPError as e:
        helper.log_error(
            f'msg="caught HTTP exception in fetch_alerts: {e}", org={opt_subdomain}, fetch_type={ALERTS_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
        )
    except Exception as e:
        helper.log_error(
            f'msg="caught exception in fetch_alerts: {e}", org={opt_subdomain}, fetch_type={ALERTS_FETCH_TYPE}, obsidian_api_url={obsidian_api_url}'
        )


def process_fetch_related_events(
    helper,
    ew,
    related_activity_queue,
    headers,
    subdomain,
    proxy_setting,
    obsidian_api_url,
    max_retries,
):
    """
    If have activity checkpoint, pop the first one and try to get
    related events
    Count the number of events, over 300, we will stop fetching events,
    wait for next run
    If any failures happened, this will append to the end of the queue for try
    again, count + 1, if count > 5, drop it.
    The data structure of checkpoint will be a list with members like:
    {"alert_id": 123, "activity_filter": {"filter": "activity_filter", "query": "query"}, “query": "query",  "count": 0}
    """
    MAX_EVENTS = 300
    MAX_RETRIES = max_retries if max_retries else 5
    current_total_events = 0
    helper.log_debug(f"Fetch alert related event max retries: {MAX_RETRIES}")

    while related_activity_queue:
        # Pop the first checkpoint
        checkpoint = related_activity_queue.pop(0)
        alert_id = checkpoint["alert_id"]
        activity_filter = checkpoint["activity_filter"]
        query = checkpoint["query"]
        retry_count = checkpoint["count"]

        helper.log_debug(
            f"Processing alert_id: {alert_id} with retry count: {retry_count}"
        )

        try:
            # Fetch related events using the activity filter
            events = fetch_related_events_for_alert(
                helper,
                activity_filter,
                query,
                alert_id,
                headers,
                subdomain,
                proxy_setting,
                obsidian_api_url,
            )
            event_count = len(events)
            current_total_events += event_count

            if event_count == 0:
                helper.log_debug(f"No events found for alert_id: {alert_id}")
                continue

            helper.log_debug(f"Fetched {event_count} events for alert_id: {alert_id}")

            # Process the events (for demonstration, just printing them)
            write_event_count = write_related_events(helper, ew, events, alert_id)
            helper.log_debug(
                f"Saved {write_event_count} events for alert_id: {alert_id}"
            )

            # If the number of events exceeds the limit, stop fetching and wait for next run
            if current_total_events > MAX_EVENTS:
                helper.log_debug(
                    f"Exceeded max events for alert_id: {alert_id}, stopping fetch for now."
                )
                break

        except Exception as e:
            helper.log_debug(
                f"Error occurred while processing alert_id: {alert_id}: {e}"
            )

            # Increment retry count and add back to the queue if under retry limit
            retry_count += 1
            if retry_count <= MAX_RETRIES:
                checkpoint["count"] = retry_count
                related_activity_queue.append(checkpoint)
                helper.log_debug(
                    f"Re-added alert_id: {alert_id} to the queue with retry count: {retry_count}"
                )
            else:
                helper.log_debug(
                    f"Dropping alert_id: {alert_id} after {MAX_RETRIES} retries"
                )

    return related_activity_queue


def fetch_related_events_for_alert(
    helper,
    activity_filter,
    query,
    alert_id,
    headers,
    subdomain,
    proxy_setting,
    obsidian_api_url,
):
    """
    Fetch related events for an alert using the activity filter
    """
    total_events = 0
    events = []

    # fetch in a loop in case we have a cursor here, all for the same range from above just iterating with cursor
    graphql_query = obsidian_queries.get_alert_related_events()
    gql_payload = {
        "query": graphql_query,
        "variables": {
            "eventFilter": activity_filter,
            "orderBy": "DATETIME_DESCENDING",
            "query": query,
        },
    }
    helper.log_debug(f"Fetching alert related events with query: {query}")
    response = obsidian_utils.make_request(
        helper, gql_payload, headers, proxy_setting, obsidian_api_url
    )
    if response.status_code != 200:
        helper.log_error(
            f"msg=\"Fetching alert related events received {response.status_code} code and response '{response.content}'\""
        )
        return

    try:
        response_data = response.json()
    except ValueError as e:
        helper.log_error(
            f"Invalid JSON response for related events: {response.text[:200]}... - {str(e)}"
        )
        return []

    helper.log_debug(f"Response data keys: {list(response_data.keys())}")

    # Check for GraphQL errors
    if "errors" in response_data:
        helper.log_error(
            f"GraphQL errors in related events query: {response_data['errors']}"
        )
        return []

    data = response_data.get("data", {}).get("getEvents", {})

    results = data.get("results", []) or []
    count = len(results)
    total_events = total_events + count

    if results:
        for result in results:
            # convert to the format we want to store it in
            d = obsidian_utils.process_event_result(helper, result, subdomain)
            events.append(d)

        helper.log_info(
            f'msg="Fetched {total_events} related events for alert_id: {alert_id}"'
        )
    return events

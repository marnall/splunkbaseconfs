# encoding = utf-8

import json
import time
from datetime import datetime, timedelta, timezone

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


EVENTS_FETCH_TYPE = "obsidian:events"


def validate_input(helper, definition):
    """Validate the arguments provided during adding of an input"""

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
        "obsidian_events", input_name, session_key
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
                "The token is not valid for the given subdomain. "
                f"The subdomain name is {token_subdomain_name}, "
                f"but your input subdomain name is {opt_subdomain}, please check!"
            )
    else:
        helper.log_info(
            "msg=The subdomain name in the token is not able to be validated. "
            f'The subdomain name in token is:{token_subdomain_name}"'
        )

    opt_proxy_setting = definition.parameters.get("proxy_setting") or None
    obsidian_api_url = (
        definition.parameters.get("obsidian_api_url") or "https://api.obsec.io/v1/gql"
    )

    try:
        min_time_window_seconds = int(
            definition.parameters.get("min_time_window_seconds") or "30"
        )
        if min_time_window_seconds < 2:
            raise Exception("Min Time Window Seconds must be greater or equal than 2")
    except (ValueError, TypeError) as e:
        raise Exception(
            "Invalid Min Time Window Seconds value: "
            f"{definition.parameters.get('min_time_window_seconds')} - {str(e)}"
        )

    try:
        time_window_seconds = int(
            definition.parameters.get("time_window_seconds") or "7200"
        )
        if time_window_seconds < 1800:
            raise Exception(
                "Max Time Window Seconds must be greater or equal than 1800"
            )
    except (ValueError, TypeError) as e:
        raise Exception(
            "Invalid Time Window Seconds value: "
            f"{definition.parameters.get('time_window_seconds')} - {str(e)}"
        )

    try:
        batch_size = int(definition.parameters.get("batch_size") or "1000")
        if batch_size < 100 or batch_size > 5000:
            raise Exception("Batch Size must be between 100 and 5000")
    except (ValueError, TypeError) as e:
        raise Exception(
            f"Invalid Batch Size value: {definition.parameters.get('batch_size')} - {str(e)}"
        )

    try:
        eps_threshold = int(definition.parameters.get("eps_threshold") or "500")
        if eps_threshold < 50:
            raise Exception("EPS Threshold High must be greater or equal than 50")
    except (ValueError, TypeError) as e:
        raise Exception(
            f"Invalid EPS Threshold value: {definition.parameters.get('eps_threshold')} - {str(e)}"
        )

    try:
        # Set Obsidian API URL
        headers = obsidian_utils.build_headers(opt_obsidian_api_token, opt_subdomain)

        gql_query = obsidian_queries.api_version_query()
        gql_payload = {"query": gql_query, "variables": {}}

        response = obsidian_utils.make_request(
            helper, gql_payload, headers, opt_proxy_setting, obsidian_api_url
        )
        response.raise_for_status()
        helper.log_info(
            f'msg="successfully connected to Obsidian API", opt_subdomain={opt_subdomain}, obsidian_api_url={obsidian_api_url}'
        )
    except requests.exceptions.HTTPError as e:
        helper.log_error(
            f'msg="HTTP Error: {e}", opt_subdomain={opt_subdomain}, obsidian_api_url={obsidian_api_url}'
        )
        raise Exception(f"HTTP Error: {e}")


def fetch_events(
    helper,
    ew,
    event_query,
    headers,
    proxy_setting,
    subdomain,
    obsidian_api_url,
):
    """
    Do the work of fetching the events from the Obsidian API.
    """

    # Get Checkpoint
    existing_state = helper.get_check_point(f"{subdomain}_activity")
    incremental_delta_secs = int(helper.get_arg("time_window_seconds") or 7200)
    if not existing_state:
        helper.log_debug(
            f'msg="no existing checkpoint. Fetching events from the past 24 hours", events_fetch_type={EVENTS_FETCH_TYPE}, subdomain={subdomain}'
        )
        # Default to 24hrs on first run
        existing_state = (
            datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=24)
        ).isoformat()

    # Set the start and end times
    start_date = datetime.fromisoformat(existing_state)
    now = datetime.now(timezone.utc) - timedelta(minutes=1)
    incremental_delta = timedelta(seconds=incremental_delta_secs)

    while start_date < now:
        # Increment the end date by incremental_delta_secs past the start date

        end_date = start_date + incremental_delta
        end_date = end_date if end_date < now else now
        start_date_str = start_date.isoformat().split("+")[0] + "Z"
        end_date_str = end_date.isoformat().split("+")[0] + "Z"

        gql_query = obsidian_queries.get_events_count(
            event_query, start_date_str, end_date_str
        )
        gql_payload = {"query": gql_query, "variables": {}}

        # get the total number of events to help us throttle if necessary
        response = obsidian_utils.make_request(
            helper, gql_payload, headers, proxy_setting, obsidian_api_url
        )

        if response.status_code != 200:
            helper.log_error(
                f'msg="received {response.status_code} code and response {response.content} for activity count", events_fetch_type={EVENTS_FETCH_TYPE}, subdomain={subdomain}'
            )
            return

        # get the resulting value
        try:
            response_data = response.json()
        except ValueError as e:
            helper.log_error(
                f"Invalid JSON response for event count: {response.text[:200]}... - {str(e)}"
            )
            return

        # Check for GraphQL errors
        if "errors" in response_data:
            helper.log_error(
                f"GraphQL errors in event count query: {response_data['errors']}"
            )
            return

        data = response_data.get("data", {}).get("getEventAggregates", {})
        counts = data.get("counts", [])

        # Handle empty counts array
        if not counts or len(counts) == 0:
            helper.log_warning("No counts found in event aggregates response")
            # Update checkpoint and wait for the next run
            helper.save_check_point(f"{subdomain}_activity", end_date.isoformat())
            time.sleep(0.1)
            # Use the original incremental_delta_secs for the next iteration
            incremental_delta = timedelta(seconds=incremental_delta_secs)
            if end_date == now:
                return
            else:
                start_date = end_date
                continue

        # Use the first count (total events) and log if there are multiple counts
        event_count = counts[0]
        if len(counts) > 1:
            helper.log_debug(
                f"Multiple counts found: {counts}, using first count: {event_count}"
            )

        # Handle zero events case - skip processing this time window
        if event_count <= 0:
            helper.log_debug(
                f'msg="No events found for time range {start_date_str} to {end_date_str}, skipping", events_fetch_type={EVENTS_FETCH_TYPE}, subdomain={subdomain}'
            )
            # Update checkpoint and wait for the next run
            helper.save_check_point(f"{subdomain}_activity", end_date.isoformat())
            time.sleep(0.1)
            # Use the original incremental_delta_secs for the next iteration
            incremental_delta = timedelta(seconds=incremental_delta_secs)
            if end_date == now:
                return
            else:
                start_date = end_date
                continue

        # Get customer-specific throttling configuration
        throttling_config = obsidian_utils.get_customer_throttling_config(helper)

        # Use EPS-based throttling instead of count-based throttling
        (
            new_time_window,
            batch_size,
            start_fetching_from_now,
        ) = obsidian_utils.calculate_adaptive_throttling(
            helper, event_count, int(incremental_delta.total_seconds()), throttling_config
        )
        helper.log_debug(
            f'msg="Calculate the throttling returned", new_time_window={new_time_window}, batch_size={batch_size}, start_fetching_from_now={start_fetching_from_now}',
        )
        if not start_fetching_from_now:
            incremental_delta = timedelta(seconds=int(new_time_window))
            helper.log_debug(
                f'msg="high volume events detected: reducing the time window", incremental_delta={incremental_delta}',
            )
            continue

        helper.log_debug(
            f'msg="fetch range: {start_date_str} to {end_date_str}, expected count {event_count}", events_fetch_type={EVENTS_FETCH_TYPE}, subdomain={subdomain}'
        )

        cursor = None
        total_events = 0

        # fetch in a loop in case we have a cursor here, all for the same range from above just iterating with cursor
        while True:
            if cursor:
                helper.log_debug(
                    f'msg="making pagination request for time range {start_date_str} to {end_date_str} with {cursor}", events_fetch_type={EVENTS_FETCH_TYPE}, subdomain={subdomain}'
                )
                token = f'token: "{cursor}"'
            else:
                token = ""

            graphql_query = obsidian_queries.get_events(
                token,
                event_query,
                start_date_str,
                end_date_str,
                batch_size,
            )

            gql_payload = {"query": graphql_query, "variables": {}}

            response = obsidian_utils.make_request(
                helper, gql_payload, headers, proxy_setting, obsidian_api_url
            )
            if response.status_code != 200:
                helper.log_error(
                    f'msg="Received {response.status_code} code and response {response.content}", events_fetch_type={EVENTS_FETCH_TYPE}, subdomain={subdomain}'
                )
                return

            try:
                response_data = response.json()
            except ValueError as e:
                helper.log_error(
                    f"Invalid JSON response for events: {response.text[:200]}... - {str(e)}"
                )
                continue

            # Check for GraphQL errors
            if "errors" in response_data:
                helper.log_error(
                    f"GraphQL errors in events query: {response_data['errors']}"
                )
                continue

            data = response_data.get("data", {}).get("getEvents", {})
            cursor = data.get("cursor")
            has_more_results = data.get("hasMoreResults")
            results = data.get("results", []) or []

            count = len(results)
            total_events = total_events + count

            for result in results:

                # convert to the format we want to store it in
                d = obsidian_utils.process_event_result(helper, result, subdomain)

                # Create an event and save it
                event = helper.new_event(
                    time=obsidian_utils.get_event_time(d["datetime"]),
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype(),
                    data=json.dumps(d),
                )
                event_checkpoint = datetime.fromisoformat(
                    d["datetime"].replace("Z", "+00:00")
                )
                try:
                    ew.write_event(event)
                except Exception as e:
                    # Log the error but continue processing other events
                    helper.log_warning(
                        f'msg="Failed to process event: {str(e)}", events_fetch_type={EVENTS_FETCH_TYPE}, subdomain={subdomain}, event_data={result.get("id", "unknown")}'
                    )
                    helper.save_check_point(
                        f"{subdomain}_activity", event_checkpoint.isoformat()
                    )
                    helper.log_debug(
                        f"msg=Saved checkpoint for event: {event_checkpoint.isoformat()}, events_fetch_type={EVENTS_FETCH_TYPE}, subdomain={subdomain}",
                    )

            if not has_more_results:
                helper.log_info(
                    f'msg="total events for time range {start_date_str} to {end_date_str}: {total_events}", events_fetch_type={EVENTS_FETCH_TYPE}, subdomain={subdomain}'
                )
                break

            time.sleep(0.1)

        helper.save_check_point(f"{subdomain}_activity", end_date.isoformat())
        time.sleep(0.1)
        incremental_delta = timedelta(seconds=new_time_window)
        start_date = end_date

    helper.log_debug(
        f'msg="fetch_events completed.", start_date={start_date}, incremental_delta={incremental_delta}',
    )
    return


def collect_events(helper, ew):
    """
    Event collection logic
    """
    # Set log level
    helper.set_log_level(helper.get_log_level())

    # Set variables from input args
    opt_subdomain = obsidian_utils.sanitize_subdomain(helper.get_arg("subdomain"))
    opt_obsidian_api_token = helper.get_arg("api_token")
    opt_event_query = obsidian_utils.escape_quotes(helper.get_arg("event_query") or "")
    proxy_setting = helper.get_arg("proxy_setting") or None
    obsidian_api_url = (
        helper.get_arg("obsidian_api_url") or "https://api.obsec.io/v1/gql"
    )

    # Set Obsidian API URL
    headers = obsidian_utils.build_headers(opt_obsidian_api_token, opt_subdomain)

    proxy_log_message = ""
    if proxy_setting:
        proxy_log_message = f" (proxy: {proxy_setting})"

    helper.log_info(
        f'msg="starting collection.", events_fetch_type={EVENTS_FETCH_TYPE}, proxy_log_message={proxy_log_message}, opt_subdomain={opt_subdomain}, obsidian_api_url={obsidian_api_url}'
    )
    try:
        fetch_events(
            helper,
            ew,
            opt_event_query,
            headers,
            proxy_setting,
            opt_subdomain,
            obsidian_api_url,
        )

        helper.log_info(
            f'msg="fetch complete.", events_fetch_type={EVENTS_FETCH_TYPE}, opt_subdomain={opt_subdomain}, obsidian_api_url={obsidian_api_url}'
        )
    except requests.exceptions.HTTPError as e:
        helper.log_error(
            f'msg="caught HTTP exception in fetch_events: {e}", events_fetch_type={EVENTS_FETCH_TYPE}, opt_subdomain={opt_subdomain}, obsidian_api_url={obsidian_api_url}'
        )
    except Exception as e:
        helper.log_error(
            f'msg="caught exception in fetch_events: {e}", events_fetch_type={EVENTS_FETCH_TYPE}, opt_subdomain={opt_subdomain}, obsidian_api_url={obsidian_api_url}'
        )

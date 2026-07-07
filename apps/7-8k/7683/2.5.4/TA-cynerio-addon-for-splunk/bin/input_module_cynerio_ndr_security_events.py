# encoding = utf-8



import json

from datetime import datetime, timedelta



def validate_input(helper, definition):

    """Implement your own validation logic to validate the input stanza configurations."""

    pass



def fetch_events(helper, zone, token, date_from, date_to, page, per_page, ew):

    """

    Fetch events from the outbound integrations API (v3).

    """

    url = f"https://{zone}.app.cynerio.com/outbound-integrations/integration/v3/events"

    payload = {

        "filters": {

            "date_from": date_from

        },

        "page": page,

        "per_page": per_page,

    }

    headers = {

        "Authorization": f"Bearer {token}",

        "Content-Type": "application/json",

    }



    try:

        helper.log_debug(f"Fetching events from URL: {url}")

        helper.log_debug(f"Request Payload: {json.dumps(payload)}")

        response = helper.send_http_request(

            url,

            "POST",

            payload=json.dumps(payload),

            headers=headers,

            timeout=30

        )

        helper.log_debug(f"Events response status code: {response.status_code}")

        response.raise_for_status()

        return response.json()

    except Exception as e:

        helper.log_error(f"Error during API call: {e}")

        raise



def get_bearer_token(helper, zone, client_id, secret):

    """

    Fetch the bearer token from the auth API.

    """

    url = f"https://{zone}-portal-login.cynerio.com/identity/resources/auth/v1/api-token"

    payload = {"clientId": client_id, "secret": secret}

    headers = {"Content-Type": "application/json"}



    helper.log_debug(f"Requesting token from URL: {url}")

    response = helper.send_http_request(

        url,

        "POST",

        payload=json.dumps(payload),

        headers=headers,

        timeout=30

    )

    helper.log_debug(f"Token response status code: {response.status_code}")

    helper.log_debug(f"Token response content: {response.text}")

    response.raise_for_status()

    token_data = response.json()

    return token_data.get("accessToken")



def get_last_date_to(helper, checkpoint_key, ew):

    """

    Retrieve the last processed timestamp using Splunk's checkpoint system.

    """

    last_date_to = helper.get_check_point(checkpoint_key)

    if last_date_to:

        helper.log_debug(f"Retrieved last_date_to from checkpoint: {last_date_to}")



        return last_date_to

    else:

        helper.log_debug("Checkpoint not found. Starting from default date range.")

        return None



def save_last_date_to(helper, checkpoint_key, date_to, ew):

    """

    Save the last processed timestamp using Splunk's checkpoint system.

    Increment the timestamp by 1 second to avoid duplication on the next run.

    """

    try:

        # Parse the date_to string and increment by 1 second

        # Attempt parsing with microseconds if '.' found, else without

        if '.' in date_to:

            date_format = "%Y-%m-%dT%H:%M:%S.%f"

        else:

            date_format = "%Y-%m-%dT%H:%M:%S"



        date_to_dt = datetime.strptime(date_to, date_format)

        incremented_dt = date_to_dt + timedelta(seconds=1)

        incremented_date_to = incremented_dt.strftime(date_format)



        helper.save_check_point(checkpoint_key, incremented_date_to)

        helper.log_debug(f"Checkpoint updated to: {incremented_date_to}")

    except Exception as e:

        helper.log_error(f"Failed to save checkpoint: {e}")

        raise



def collect_events(helper, ew):
    """
    Main function to collect and write events to Splunk.
    Writes all fetched events as a single aggregated Splunk event.
    """
    client_id = helper.get_arg("client_id")
    secret = helper.get_arg("secret")
    zone = helper.get_arg("zone")
    checkpoint_key = "CYNERIO_NDR"

    helper.log_debug(f"Collecting events for zone: {zone}")

    try:
        # Fetch the bearer token
        token = get_bearer_token(helper, zone, client_id, secret)
        helper.log_debug("Retrieved bearer token")

        # Retrieve the last processed timestamp
        last_date_to = get_last_date_to(helper, checkpoint_key, ew)
        current_time = datetime.utcnow()
        date_to = current_time.strftime("%Y-%m-%dT%H:%M:%S")
        date_from = last_date_to or (current_time - timedelta(minutes=60)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

        helper.log_debug(f"Fetching events from {date_from} to {date_to}")

        page = 1
        per_page = 100
        latest_timestamp = None
        aggregated_events = []

        while True:
            # Fetch events from the API
            events_data = fetch_events(helper, zone, token, date_from, date_to, page, per_page, ew)
            events = events_data.get("items", [])
            helper.log_debug(f"Fetched {len(events)} events on page {page}")

            if not events:
                helper.log_info("No more events to process.")
                break

            for event in events:
                timestamp = event.get("timestamp")
                if not timestamp:
                    helper.log_warning(f"Event missing timestamp: {json.dumps(event)}")
                    continue

                # Update latest_timestamp if this event is newer
                if latest_timestamp is None or timestamp > latest_timestamp:
                    latest_timestamp = timestamp

                aggregated_events.append(event)

            page += 1

        if aggregated_events:
            # Create a single Splunk event with all aggregated events
            splunk_event = helper.new_event(json.dumps(aggregated_events), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
            # Write the single aggregated event to Splunk
            ew.write_event(splunk_event)
            helper.log_info(f"Written {len(aggregated_events)} events as a single batch event.")

            save_last_date_to(helper, checkpoint_key, latest_timestamp, ew)
        else:
            helper.log_info("No valid events to write.")

    except Exception as e:
        helper.log_error(f"Error collecting events: {e}")
        raise
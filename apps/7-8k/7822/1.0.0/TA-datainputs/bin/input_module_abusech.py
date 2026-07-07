import json

import requests

import urllib.parse



# API URL is now hardcoded (no need for user input)

API_URL = "https://urlhaus-api.abuse.ch/v1/urls/recent/"



# Function to fetch data from Abuse.ch URLHaus

def fetch_abusech_data():

    try:

        # Making a GET request to the Abuse.ch URLHaus API

        response = requests.get(API_URL)

        response.raise_for_status()  # Raises an error for bad status codes

        return response.json()

    except requests.exceptions.HTTPError as http_err:

        helper.log_error(f"HTTP error occurred: {http_err}")

    except requests.exceptions.ConnectionError as conn_err:

        helper.log_error(f"Connection error occurred: {conn_err}")

    except requests.exceptions.RequestException as e:

        helper.log_error(f"Failed to fetch Abuse.ch data: {str(e)}")

    return None



# Recursive function to flatten JSON

def flatten_json(json_obj, parent_key='', separator='_'):

    items = []

    for key, value in json_obj.items():

        new_key = f"{parent_key}{separator}{key}" if parent_key else key

        if isinstance(value, dict):

            items.extend(flatten_json(value, new_key, separator=separator).items())

        elif isinstance(value, list):

            for i, item in enumerate(value):

                items.extend(flatten_json({f"{new_key}_{i}": item}, separator=separator).items())

        else:

            items.append((new_key, value))

    return dict(items)



# Function to validate input parameters

def validate_input(helper, definition):

    """Validate the input configuration."""

    dummy_var = helper.get_arg("dummy_var")  # Splunk requires at least one input variable

    return True



# Main function to collect events

# Main function to collect events

def collect_events(helper, ew):

    """Data collection logic for Splunk modular input"""

    dummy_var = helper.get_arg('dummy_var')  # Required but not used

    abusech_data = fetch_abusech_data()

    if abusech_data and 'urls' in abusech_data:

        # Limit to the first 5 URLs
        limited_urls = abusech_data['urls'][:5]

        for url_info in limited_urls:

            flattened_url_info = flatten_json(url_info)

            event_data = json.dumps(flattened_url_info)

            event = helper.new_event(
                data=event_data,
                sourcetype="threat_intel1",
                source="abuse_ch_urlhaus",
                index="add_on_builder_index",
                done=True,
                unbroken=True
            )

            ew.write_event(event)

        helper.log_info(f"Successfully processed {len(limited_urls)} URLs from Abuse.ch (limited to 100).")

    else:

        helper.log_error("Failed to fetch Abuse.ch URLHaus data or no data available.")


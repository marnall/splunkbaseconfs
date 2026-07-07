import json
import requests
import urllib.parse

# API URL is now hardcoded (no need for user input)
API_URL = "https://otx.alienvault.com/api/v1/pulses/subscribed"
API_KEY = "f260e31bdbf69dbcd8038b1860c4825564d61a3f7ae7f7fef3010894af3d5647"

# Function to fetch data from AlienVault OTX
def fetch_otx_data():
    headers = {'X-OTX-API-KEY': API_KEY}
    try:
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch OTX data: {str(e)}")
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
def collect_events(helper, ew):
    """Data collection logic for Splunk modular input"""
    dummy_var = helper.get_arg('dummy_var')  # Required but not used
    otx_data = fetch_otx_data()
    if otx_data and 'results' in otx_data:
        for pulse in otx_data['results']:
            flattened_pulse = flatten_json(pulse)
            event_data = json.dumps(flattened_pulse)
            event = helper.new_event(
                data=event_data,
                sourcetype="threat_intel2",
                source="alienvault_otx",
                index="add_on_builder_index",
                done=True,
                unbroken=True
            )
            ew.write_event(event)
        helper.log_info(f"Successfully processed {len(otx_data['results'])} pulses from AlienVault OTX.")
    else:
        helper.log_error("Failed to fetch AlienVault OTX data or no data available.")

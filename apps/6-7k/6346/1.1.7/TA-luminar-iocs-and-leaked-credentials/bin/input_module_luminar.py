# encoding = utf-8
"""
This module provides functionalities for handling threat intelligence ingestion.

It includes functions for parsing, enriching, and processing various indicators of
compromise (IoCs) from Luminar source.
"""
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict
from urllib import parse

LUMINAR_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
STIX_REGEX_PARSER = re.compile(
    r"([\w-]+?):(\w.+?) (?:[!><]?=|IN|MATCHES|LIKE) '(.*?)' *[" + r"OR|AND|FOLLOWEDBY]?"
)


def sha1_field_mapping(_ind: Any, value: str) -> Dict[str, str]:
    """
    Maps a SHA-1 hash value.

    Parameters:
    ind (Any): Indicator type (not used in this function).
    value (str): The SHA-1 hash value.

    Returns:
    Dict[str, str]: A dictionary containing the SHA-1 hash mapping.
    """
    return {"SHA1": value}


def md5_field_mapping(_ind: Any, value: str) -> Dict[str, str]:
    """
    Maps an MD5 hash value.

    Parameters:
    ind (Any): Indicator type (not used in this function).
    value (str): The MD5 hash value.

    Returns:
    Dict[str, str]: A dictionary containing the MD5 hash mapping.
    """
    return {"MD5": value}


def sha256_field_mapping(_ind: Any, value: str) -> Dict[str, str]:
    """
    Maps a SHA-256 hash value.

    Parameters:
    ind (Any): Indicator type (not used in this function).
    value (str): The SHA-256 hash value.

    Returns:
    Dict[str, str]: A dictionary containing the SHA-256 hash mapping.
    """
    return {"SHA256": value}


def sha512_field_mapping(_ind: Any, value: str) -> Dict[str, str]:
    """
    Maps a SHA-512 hash value.

    Parameters:
    ind (Any): Indicator type (not used in this function).
    value (str): The SHA-512 hash value.

    Returns:
    Dict[str, str]: A dictionary containing the SHA-512 hash mapping.
    """
    return {"SHA512": value}


def ip_field_mapping(_ind: Any, _value: str) -> Dict[str, str]:
    """
    Maps an IP address.

    Parameters:
    ind (Any): Indicator type (not used in this function).
    value (str): The IP address.

    Returns:
    Dict[str, str]: An empty dictionary (no mapping logic implemented).
    """
    return {}


def file_name_mapping(_ind: Any, value: str) -> Dict[str, str]:
    """
    Maps a file name and extracts the extension.

    Parameters:
    ind (Any): Indicator type (not used in this function).
    value (str): The file name including the extension.

    Returns:
    Dict[str, str]: A dictionary containing file extension and associated file names.
    """
    file_name, extension = value.split(".")[0], value.split(".")[1]
    return {
        "File Extension": extension,
        "Associated File Names": file_name,
        "File Type": file_name,
    }


def file_size_mapping(ind: Dict[str, Any], value: str) -> Dict[str, str]:
    """
    Maps file size information.

    Parameters:
    ind (Dict[str, Any]): A dictionary containing file metadata.
    value (str): The file size.

    Returns:
    Dict[str, str]: A dictionary containing file size and file type.
    """
    return {"Size": value, "File Type": ind.get("name", "")}


def url_mapping(_ind: Any, _value: str) -> Dict[str, str]:
    """
    Maps a URL.

    Parameters:
    ind (Any): Indicator type (not used in this function).
    value (str): The URL.

    Returns:
    Dict[str, str]: An empty dictionary (no mapping logic implemented).
    """
    return {}


splunkIndicatorTypes = {
    "file:hashes.'SHA-1'": {
        "indicatorType": "file_intel",
        "fieldMappingMethod": sha1_field_mapping,
    },
    "file:hashes.MD5": {
        "indicatorType": "file_intel",
        "fieldMappingMethod": md5_field_mapping,
    },
    "file:hashes.'SHA-256'": {
        "indicatorType": "file_intel",
        "fieldMappingMethod": sha256_field_mapping,
    },
    "file:hashes.'SHA-512'": {
        "indicatorType": "file_intel",
        "fieldMappingMethod": sha512_field_mapping,
    },
    "ipv4-addr": {"indicatorType": "ip_intel", "fieldMappingMethod": ip_field_mapping},
    "file:name": {
        "indicatorType": "file_intel",
        "fieldMappingMethod": file_name_mapping,
    },
    "file:size": {
        "indicatorType": "file_intel",
        "fieldMappingMethod": file_size_mapping,
    },
    "url": {"indicatorType": "URL", "fieldMappingMethod": url_mapping},
    "email-addr": {"indicatorType": "email_intel"},
    "domain-name": {"indicatorType": "ip_intel"},
    "ipv6-addr": {"indicatorType": "ip_intel"},
    "mac-addr": {"indicatorType": "ip_intel"},
    "directory": {"indicatorType": "registry_intel"},
}


def validate_input(helper, definition):
    """
    Implement your own validation logic to validate the input stanza
    configurations.
    """
    # This example accesses the modular input variable
    demo = definition.parameters.get("demo", None)
    if all([demo is not None, not demo, str(demo).isdigit()]):
        pass
    else:
        # TODO better handle this situation
        helper.log_warning("Invalid value for demo/limit")


def is_valid_date(date_str: str) -> bool:
    """
    Check if the given string is a valid date in the format YYYY-MM-DD.

    Parameters:
    date_str (str): The date string to validate.

    Returns:
    bool: True if the date is valid, False otherwise.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def get_timestamp():
    """
    Retrieves the current timestamp in UTC format with microsecond precision.

    This function fetches the current time in UTC, formats it into an ISO 8601 string
    with microsecond precision, and appends a 'Z' to indicate that the time is in UTC.

    Returns:
        str: The current timestamp in UTC with microsecond precision, formatted as
             'YYYY-MM-DDTHH:MM:SS.mmmmmmZ'.
    """
    current_time = datetime.now(timezone.utc)
    return (
        current_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{current_time.microsecond:06d}Z"
    )


def check_created_date(helper, obj_date: str, from_date: datetime) -> bool:
    """
    Validates whether the given object creation date is greater than or equal
    to the specified 'from_date'.

    :param obj_date: A string representing the creation date of the object in
                     ISO 8601 format ("%Y-%m-%dT%H:%M:%S.%fZ").
    :param from_date: A datetime object representing the threshold date.
    :return: True if obj_date is valid and greater than or equal to from_date,
             otherwise False.
    """
    try:
        return datetime.strptime(obj_date, LUMINAR_DATE_FORMAT) >= from_date
    except Exception as ex:
        helper.log_error(f"Invalid date format: {obj_date}; {ex}")
        return False


def create_lookup_dict(list_of_dicts):
    """
    Converts a list of dictionaries into a lookup dictionary indexed by 'id'.

    :param list_of_dicts: List of dictionaries to process.
    :return: A dictionary where keys are 'id' values (str) and values are the corresponding dictionaries.
    """
    return {dict_item["id"]: dict_item for dict_item in list_of_dicts}


def enrich_incident_items(parent, childrens):
    """
    Enriches incident items by updating child items with information from the parent incident.

    This function processes each child item in the provided list of `childrens` and enriches it with relevant
    information from the parent incident, including fields like "created", "modified", "incident_id", "description",
    and "incident_name". These fields are added to each child in the `childrens` list.

    Parameters:
        parent (dict): A dictionary representing the parent incident, containing fields like "created", "modified",
                       "id", "description", and "name".
        childrens (list): A list of child dictionaries representing individual incident-related items to be enriched.

    Returns:
        tuple: A tuple containing the updated `parent` and `childrens` lists with enriched data.
    """
    # Extract relevant information from the parent incident
    enrich_info = {
        "created": parent.get("created"),
        "modified": parent.get("modified"),
        "incident_id": parent.get("id"),
        "description": parent.get("description"),
        "incident_name": parent.get("name"),
    }

    # Update each child with the enriched information from the parent
    for children in childrens:
        children.update(enrich_info)

    return parent, childrens


def enrich_malware_items(parent, childrens):
    """
    Enriches malware items by updating child items with relevant indicator types and mapping methods.

    This function processes each child item in the provided list of `childrens`. For each child, it looks for
    matches in the `pattern` attribute using a regular expression parser, identifies the type and properties of the
    indicators, and enriches the child item with additional fields based on these indicators. If a valid indicator
    type is found, the child item is updated with the corresponding `fieldMappingMethod` and `malware_types` from
    the parent. Additionally, the parent item's `name` field is updated with the child's `name`.

    Parameters:
        parent (dict): A dictionary representing the parent malware item, which contains fields like "malware_types".
        childrens (list): A list of child dictionaries representing individual malware items, each containing a "pattern".

    Returns:
        tuple: A tuple containing the updated `parent` and `childrens` lists with enriched data.
    """
    for children in childrens:
        pattern = children.get("pattern")
        if pattern:

            # Find matches in the pattern using the STIX_REGEX_PARSER
            for match in STIX_REGEX_PARSER.findall(pattern):
                stix_type, stix_property, value = match

                # Get the corresponding indicator type from the splunkIndicatorTypes dictionary
                if stix_type == "file":
                    indicator_type = splunkIndicatorTypes.get(
                        f"{stix_type}:{stix_property}"
                    )
                else:
                    indicator_type = splunkIndicatorTypes.get(stix_type)

                # Skip if no valid indicator type is found
                if indicator_type is None:
                    continue

                # If a field mapping method is present, apply it
                if "fieldMappingMethod" in indicator_type:
                    mapping_method = indicator_type["fieldMappingMethod"]

                    # Apply the mapping method if it is not a dictionary
                    extra_info = (
                        mapping_method(children, value)
                        if not isinstance(mapping_method, dict)
                        else mapping_method
                    )
                    indicator_type["fieldMappingMethod"] = extra_info

                # Update the child with malware types from the parent and set the indicator type
                children["malware_types"] = parent.get("malware_types", [])
                children.update(indicator_type=indicator_type)

                # Update the parent's name with the child's name
                # parent["name"] = children["name"]
                if children.get("name"):
                    parent["name"] = children["name"]


    return parent, childrens


def get_access_token(
    helper,
    luminar_endpoint,
    luminar_account_id,
    luminar_client_id,
    luminar_client_secret,
):
    """
    Fetches an access token from the Luminar API using client credentials.

    This function sends a POST request to the Luminar API's token endpoint,
    providing the necessary client credentials and scope to obtain an access token.
    If the request is successful, the function returns the access token and cookies.
    In case of failure, it logs the error details.

    Parameters:
        helper (object): An object responsible for sending HTTP requests and logging information.
        luminar_endpoint (str): The base URL of the Luminar API endpoint.
        luminar_account_id (str): The Luminar account ID for the API request.
        luminar_client_id (str): The Luminar client ID for the API request.
        luminar_client_secret (str): The Luminar client secret for the API request.

    Returns:
        tuple: A tuple containing the access token (str) and cookies (dict) if successful,
               or (None, None) if an error occurs.
    """
    try:
        # Construct the URL for the token request
        req_url = f"{luminar_endpoint}/externalApi/v2/realm/{luminar_account_id}/token"

        # Set headers for the request
        req_headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
        }

        # Prepare the payload with the required fields
        payload = parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": luminar_client_id,
                "client_secret": luminar_client_secret,
                "scope": "externalAPI/stix.readonly",
            }
        )

        # Send the HTTP POST request to fetch the access token
        response = helper.send_http_request(
            req_url,
            "POST",
            headers=req_headers,
            payload=payload,
        )

        # Raise an exception if the response status is not 2xx
        response.raise_for_status()

        # Return the access token and cookies if successful
        return response.json()["access_token"], response.cookies

    except Exception as e:
        # Log error details if the request fails
        helper.log_error(f"Exception getting access token: {str(e)}")

        # Return None if an error occurred
        return None, None


def collect_events(helper, ew):
    """
    Collects events from a Luminar endpoint, processes them, and writes them to the event writer.

    This function retrieves records from the Luminar collections (such as 'iocs' and 'leakedrecords')
    after a certain timestamp, processes the records (enriching them if necessary), and writes events
    to Splunk using the event writer (ew). It handles pagination and token expiration, and maintains a checkpoint
    for the next run.

    Parameters:
        helper (object): An object responsible for managing configurations, sending HTTP requests, and logging information.
        ew (object): The event writer used to write events to Splunk.

    Returns:
        None
    """
    try:
        # Fetch configuration parameters from the helper
        luminar_endpoint = helper.get_arg("luminar_base_url")
        luminar_account_id = helper.get_arg("luminar_api_account_id")
        luminar_client_id = helper.get_arg("luminar_api_client_id")
        luminar_client_secret = helper.get_arg("luminar_api_client_secret")
        luminar_initial_fetch_date = helper.get_arg("luminar_initial_fetch_date")

        input_name = helper.get_input_stanza_names()
        helper.log_info(f"Input stanza name: {input_name}")

        if not is_valid_date(luminar_initial_fetch_date):
            helper.log_error(
                f"Invalid initial fetch date: {luminar_initial_fetch_date}; Please provide a valid date in the format 'YYYY-MM-DD'."
            )
            return
        luminar_initial_fetch_date = luminar_initial_fetch_date + "T00:00:00.000000Z"
        # Ensure the Luminar endpoint is properly formatted
        luminar_endpoint = f"https://{luminar_endpoint}"

        # Obtain access token and cookies using the provided credentials
        access_token, cookies = get_access_token(
            helper,
            luminar_endpoint,
            luminar_account_id,
            luminar_client_id,
            luminar_client_secret,
        )

        if not access_token:
            return
        
        checkpoint = luminar_initial_fetch_date
        
        get_checkpoint = helper.get_check_point(input_name)
        if get_checkpoint:
            checkpoint = get_checkpoint.get("next_run_timestamp", luminar_initial_fetch_date)

        helper.log_info(f"Getting records added after timestamp: {checkpoint}")
        # Set parameters for the API request
        params = {"limit": 9999, "added_after": checkpoint}

        taxii_collection_ids = {}

        # Fetch collection IDs from Luminar
        resp_for_ids = helper.send_http_request(
            f"{luminar_endpoint}/externalApi/taxii/collections/",
            "GET",
            headers={"Authorization": f"Bearer {access_token}"},
            cookies=cookies,
        )

        if resp_for_ids.status_code == 200:
            collections_data = resp_for_ids.json()["collections"]
            helper.log_info(f"Cognyte Luminar collections: {collections_data}")

            # Store collection alias and id mapping
            for collection in collections_data:
                taxii_collection_ids[collection.get("alias")] = collection.get("id")

        # If no collections are found, exit the function
        if not taxii_collection_ids:
            return

        # Get the current timestamp for the checkpoint
        next_checkpoint = get_timestamp()

        # Fetch IOC and leaked records from the respective collections
        ioc_records = get_collection_objects(
            helper,
            taxii_collection_ids["iocs"],
            access_token,
            cookies,
            luminar_endpoint,
            luminar_account_id,
            luminar_client_id,
            luminar_client_secret,
            params,
        )
        leaked_records = get_collection_objects(
            helper,
            taxii_collection_ids["leakedrecords"],
            access_token,
            cookies,
            luminar_endpoint,
            luminar_account_id,
            luminar_client_id,
            luminar_client_secret,
            params,
        )

        helper.log_info(f"Total number of IOC objects fetched: {len(ioc_records)}")
        helper.log_info(
            f"Total number of leaked records objects fetched: {len(leaked_records)}"
        )


        from_date = datetime.strptime(checkpoint, LUMINAR_DATE_FORMAT)


        ioc_records = [x for x in ioc_records if x.get("type") in ["relationship", "indicator", "malware"]]
        leaked_records = [x for x in leaked_records if x.get("type") in ["relationship", "incident", "user-account", "malware"]]

        iocs_filtered = [ x
            for x in ioc_records
            if not x.get("created")
            or check_created_date(helper, x["created"], from_date)]
        
        leaked_records_filtered = [ x
            for x in leaked_records
            if not x.get("created")
            or check_created_date(helper, x["created"], from_date)]
        
        if iocs_filtered:
            create_events_from_records(helper, ew, iocs_filtered, "iocs")
        if leaked_records_filtered:
            create_events_from_records(helper, ew, leaked_records_filtered, "leakedrecords")

        helper.save_check_point(input_name, {"next_run_timestamp": next_checkpoint})
        helper.log_info(f"Checkpoint created for next run: {next_checkpoint}")

    except Exception as ex:
        # Log any errors encountered during the execution
        helper.log_error(ex)


def create_events_from_records(helper, ew, records, feed_name):
    """
    Creates and writes events to the event writer from the provided records.

    This function iterates over a list of records, converts each record to a JSON string,
    creates an event using the helper's new_event method, and writes the event to the event writer (ew).
    It also keeps track of the number of events created and logs this information.

    Parameters:
        helper (object): An object responsible for managing configurations, sending HTTP requests, and logging information.
        ew (object): The event writer used to write events to Splunk.
        records (list): A list of records (dictionaries) to be converted into events.
    """
    number_of_events_created = 0
    ioc_and_leaked_dict = create_lookup_dict(records)
    get_item_by_id = lambda id: ioc_and_leaked_dict.get(id, {})

    relationships = {}
    # Process relationships between items
    for relationship in filter(
        lambda x: x.get("type") == "relationship", records
    ):
        relationship_items = relationships.get(
            relationship.get("target_ref"), []
        )
        relationship_items.append(relationship.get("source_ref"))
        relationships[relationship["target_ref"]] = relationship_items

    # Iterate over the relationships and enrich items
    for key, group in relationships.items():
        parent = get_item_by_id(key)
        children = list(
            filter(None, [get_item_by_id(item_id) for item_id in group])
        )
        if parent and children:

            if feed_name == "iocs":
                if parent.get("type") == "malware":
                    parent, modified_childrens = enrich_malware_items(
                        parent, children
                    )
            elif feed_name == "leakedrecords":
                if parent.get("type") == "incident":
                    parent, modified_childrens = enrich_incident_items(
                        parent, children
                    )
                

            # Write the parent event
            event = helper.new_event(
                json.dumps(parent),
                index=helper.get_output_index(),
                source=helper.get_input_type(),
                sourcetype=helper.get_sourcetype(),
            )
            ew.write_event(event)
            number_of_events_created += 1

            # Write the modified children events
            for item in modified_childrens:

                event = helper.new_event(
                    json.dumps(item),
                    index=helper.get_output_index(),
                    source=helper.get_input_type(),
                    sourcetype=helper.get_sourcetype(),
                )
                ew.write_event(event)
                number_of_events_created += 1
    helper.log_info(
            f"Number of events created for {feed_name}: {number_of_events_created}"
        )



def get_collection_objects(
    helper,
    collection,
    access_token,
    cookies,
    luminar_endpoint,
    luminar_account_id,
    luminar_client_id,
    luminar_client_secret,
    params,
):
    """
    Fetches all objects from a specified collection using pagination.

    This function sends requests to the Luminar API to retrieve objects from a given collection.
    If the access token expires, it attempts to refresh the token and retries the request.
    The function handles pagination by checking for a "next" link in the response and continues to fetch additional objects
    until all objects from the collection are retrieved.

    Parameters:
        helper (object): An object responsible for sending HTTP requests and logging information.
        collection (str): The collection identifier to fetch objects from.
        access_token (str): The authorization token to access the API.
        cookies (dict): The cookies required for the request.
        luminar_endpoint (str): The endpoint URL of the Luminar service.
        luminar_account_id (str): The Luminar account ID for token generation.
        luminar_client_id (str): The Luminar client ID for token generation.
        luminar_client_secret (str): The Luminar client secret for token generation.
        params (dict): The query parameters for the API request, including pagination data.

    Returns:
        list: A list containing all objects from the collection.
    """

    helper.log_info(
        f"Fetching objects from collection: {collection} and params: {params}"
    )
    parameters = params.copy()

    collection_objects = []
    retries = 0
    max_retries = 3

    while retries <= max_retries:
        # Send a request to fetch objects from the collection
        resp = helper.send_http_request(
            f"{luminar_endpoint}/externalApi/taxii/collections/{collection}/objects/",
            "GET",
            parameters=parameters,
            headers={"Authorization": f"Bearer {access_token}"},
            cookies=cookies,
        )

        # Handle the case where the access token has expired
        if resp.status_code == 401:
            helper.log_info(
                f"Access token has expired, status_code={resp.status_code} and response={resp.text}"
            )
            access_token, cookies = get_access_token(
                helper,
                luminar_endpoint,
                luminar_account_id,
                luminar_client_id,
                luminar_client_secret,
            )
            continue

        # Process the response when it is successful (status code 200)
        if resp.status_code == 200:
            response_json = resp.json()
            all_objects = response_json.get("objects", [])
            collection_objects += all_objects
            helper.log_info(f"number of collection objects {len(collection_objects)}")

            # Check if there is a "next" page of objects and update the params
            if "next" in response_json:
                parameters["next"] = response_json["next"]
            else:
                break
        else:
            # Log an error for any unexpected status code
            retries += 1
            helper.log_error(
                f"Error occurred while fetching objects from collection: {collection}"
                f"status_code={resp.status_code} and response={resp.text}"
                f"Retrying {retries}/{max_retries}..."
            )
            # break

    # Log the completion of object fetching
    helper.log_info(f"Fetched all objects from collection: {collection}")

    return collection_objects

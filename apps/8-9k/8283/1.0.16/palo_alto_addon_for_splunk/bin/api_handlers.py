"""
API Handler Functions for Palo Alto Add-on

This module contains the script type handler functions that process
API responses from Palo Alto devices. Each function corresponds to a
script_type defined in the API endpoints configuration.
"""

import logging
import requests
import urllib3
import xml.etree.ElementTree as ET
import urllib.parse
import time
from datetime import datetime, timedelta, timezone

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def GET_api_generic(logger: logging.Logger, api_url: str, endpoint_name: str):
    """
    Generic HTTPS GET request for API endpoints.
    Returns raw XML response for Splunk to parse using KV_MODE=xml.

    Args:
        logger: Logger instance
        api_url: Fully constructed API URL with substituted variables
        endpoint_name: Name of the endpoint for logging

    Returns:
        List of data records to be ingested (raw XML text)
    """
    logger.info(f"Making generic HTTPS GET request to endpoint: {endpoint_name}")

    try:
        # Disable SSL verification to allow self-signed certificates
        response = requests.get(api_url, verify=False, timeout=30)
        response.raise_for_status()

        logger.info(f"Successfully retrieved data from {api_url}")

        # Return raw XML response - Splunk will parse it using KV_MODE=xml
        return [{"_raw": response.text}]

    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request to {endpoint_name}: {str(e)}")
        raise


def custom_GET_api_threat_traffic(logger: logging.Logger, api_url: str, endpoint_name: str):
    """
    Custom function for threat/traffic log API endpoints.
    Queries Palo Alto threat/traffic logs with time-based filtering,
    polls for job completion, and filters for high/critical severity events.

    Args:
        logger: Logger instance
        api_url: Fully constructed API URL with substituted variables (contains base URL with key)
        endpoint_name: Name of the endpoint for logging

    Returns:
        List of data records to be ingested (filtered events)
    """
    logger.info(f"Making threat/traffic logs request to endpoint: {endpoint_name}")

    # Parse the api_url to extract base URL and API key
    # Expected format: https://host:port/api/?...&key=APIKEY...
    parsed_url = urllib.parse.urlparse(api_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

    # Extract API key from query parameters
    query_params = urllib.parse.parse_qs(parsed_url.query)
    apikey = query_params.get('key', [''])[0]

    # Extract host (IP address) for event source field
    host = parsed_url.hostname

    # Configuration parameters
    timezone_offset = 0  # hours
    duration = 1800      # seconds (30 minutes)

    logger.info(f"Querying threat/traffic logs from host: {host}")

    try:
        # --- Time calculation ---
        last_collection = datetime.now(timezone.utc) + timedelta(hours=timezone_offset) - timedelta(seconds=duration)
        query_time_str = last_collection.strftime("%Y/%m/%d %H:%M:%S")

        # --- Build threat query ---
        threat_query = f"receive_time geq '{query_time_str}'"
        encoded_query = urllib.parse.quote(threat_query)

        # Construct the query URL
        threat_query_url = f"{base_url}?type=log&log-type=threat&nlogs=5000&query=({encoded_query})&key={apikey}"

        logger.info(f"Querying threats with time filter: {query_time_str}")

        # --- Perform initial query to get job IDs ---
        resp = requests.get(threat_query_url, verify=False, timeout=30)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        job_ids = [elem.text for elem in root.iter("job")]

        logger.info(f"Retrieved {len(job_ids)} job(s) to process")

        event_list = []

        # --- Process each job ---
        for job_id in job_ids:
            report_url = f"{base_url}?type=log&action=get&job-id={job_id}&key={apikey}"

            logger.debug(f"Polling job {job_id}")

            # Poll for job completion (max 11 attempts)
            for i in range(11):
                r = requests.get(report_url, verify=False, timeout=30)
                r.raise_for_status()

                xml_root = ET.fromstring(r.text)
                status = xml_root.findtext(".//job/status")

                if status == "FIN":
                    logger.info(f"Job {job_id} completed, processing entries")

                    # Process entries from completed job
                    for entry in xml_root.iter("entry"):
                        logid = entry.attrib.get("logid")
                        if not logid:
                            continue

                        severity = entry.findtext("severity", "")
                 
                        # Filter for high/critical severity only
                        if severity.lower() in ("high", "critical"):
                            event = {
                                "happenedOn": entry.findtext("time_generated", ""),
                                "severity": "warn",
                                "source": host,
                                "message": f"{severity} :: [{logid}] {entry.findtext('type', '')} - "
                                           f"{entry.findtext('subtype', '').capitalize()} : {entry.findtext('threatid', '')} "
                                           f"({entry.findtext('direction', '')} {entry.findtext('src', '')} -> {entry.findtext('dst', '')})"
                            }
                            event_list.append(event)

                    logger.info(f"Job {job_id}: Found {len([e for e in event_list if e.get('source') == host])} high/critical events")
                    break
                else:
                    logger.debug(f"Job {job_id} status: {status}, waiting...")
                    time.sleep(0.05)  # 50 ms delay
            else:
                logger.warning(f"Job {job_id} did not complete within timeout")

        logger.info(f"Total events collected: {len(event_list)}")

        # Return events in format expected by Splunk
        # Each event is a dictionary that will be JSON-serialized
        return event_list if event_list else []

    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request to {endpoint_name}: {str(e)}")
        raise
    except ET.ParseError as e:
        logger.error(f"Error parsing XML response from {endpoint_name}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in {endpoint_name}: {str(e)}")
        raise

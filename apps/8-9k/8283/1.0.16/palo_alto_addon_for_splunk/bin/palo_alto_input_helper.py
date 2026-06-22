import json
import logging
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from string import Template

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi

# Import API handler functions
from api_handlers import GET_api_generic, custom_GET_api_threat_traffic


ADDON_NAME = "palo_alto_addon_for_splunk"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account_api_key(session_key: str, account_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-palo_alto_addon_for_splunk_account",
    )
    account_conf_file = cfm.get_conf("palo_alto_addon_for_splunk_account")
    return account_conf_file.get(account_name).get("api_key")


def get_api_endpoint_config(session_key: str, endpoint_name: str):
    """Retrieve API endpoint configuration from Splunk."""
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
    )
    api_endpoints_conf = cfm.get_conf("palo_alto_addon_for_splunk_api_endpoints")
    return api_endpoints_conf.get(endpoint_name)


def substitute_variables(url_template: str, variables: dict) -> str:
    """Substitute variables in URL template using ${variable} format."""
    template = Template(url_template)
    return template.safe_substitute(variables)


def xml_to_json(xml_text: str, endpoint_name: str, host: str) -> dict:
    """
    Convert XML response to JSON format for events.

    Recursively converts XML elements to nested dictionaries/lists,
    preserving all data in JSON structure.

    Args:
        xml_text: Raw XML response text
        endpoint_name: Name of the endpoint (used as metadata)
        host: IP address of the device (used as metadata)

    Returns:
        Dictionary with JSON representation of XML:
        {
            "endpoint": "endpoint_name",
            "host": "192.168.1.1",
            "data": {nested XML structure}
        }
    """
    result = {
        "endpoint": endpoint_name,
        "host": host
    }

    try:
        root = ET.fromstring(xml_text)

        def element_to_dict(element):
            """Recursively convert XML element to dictionary"""
            # Get element attributes
            node = {}
            if element.attrib:
                node.update({"@" + k: v for k, v in element.attrib.items()})

            # Get child elements
            children = list(element)
            if children:
                child_dict = {}
                for child in children:
                    child_data = element_to_dict(child)
                    # Handle multiple children with same tag
                    if child.tag in child_dict:
                        # Convert to list if not already
                        if not isinstance(child_dict[child.tag], list):
                            child_dict[child.tag] = [child_dict[child.tag]]
                        child_dict[child.tag].append(child_data)
                    else:
                        child_dict[child.tag] = child_data
                node.update(child_dict)

            # Get text content
            if element.text and element.text.strip():
                text = element.text.strip()
                # If no children and no attributes, just return the text value
                if not node:
                    # Try to convert to appropriate type
                    try:
                        return int(text)
                    except ValueError:
                        try:
                            return float(text)
                        except ValueError:
                            return text
                else:
                    node["#text"] = text

            return node if node else None

        # Convert root element
        result["data"] = {root.tag: element_to_dict(root)}

    except ET.ParseError as e:
        result["error"] = f"XML parsing failed: {str(e)}"

    return result


def xml_to_metrics(xml_text: str, endpoint_name: str, host: str) -> dict:
    """
    Convert XML response to Splunk metrics JSON format.

    Extracts numeric values from XML and formats them as a JSON object
    where metric field names are prefixed with "metric_name:".

    Args:
        xml_text: Raw XML response text
        endpoint_name: Name of the endpoint (used as dimension)
        host: IP address of the device (used as dimension)

    Returns:
        Dictionary with metrics in format:
        {
            "endpoint": "endpoint_name",
            "host": "192.168.1.1",
            "metric_name:result.system.cpu": 15.2,
            "metric_name:result.system.memory": 62.8,
            ...
        }
    """
    metrics_data = {
        "endpoint": endpoint_name,
        "host": host
    }

    try:
        root = ET.fromstring(xml_text)

        # Recursively extract all numeric elements
        def extract_metrics(element, parent_path=""):
            for child in element:
                # Build metric name from XML path
                metric_path = f"{parent_path}.{child.tag}" if parent_path else child.tag

                # If element has text and it's numeric, add to metrics
                if child.text and child.text.strip():
                    text_value = child.text.strip()
                    try:
                        # Try to convert to float (metrics must be numeric)
                        numeric_value = float(text_value)
                        # Add with metric_name: prefix in the key
                        metrics_data[f"metric_name:{metric_path}"] = numeric_value
                    except ValueError:
                        # Not a numeric value, skip
                        pass

                # Recursively process children
                if len(child) > 0:
                    extract_metrics(child, metric_path)

        extract_metrics(root)

    except ET.ParseError:
        # If XML parsing fails, return empty dict
        pass

    return metrics_data


def process_host_endpoints(host, api_key, api_endpoints, session_key, input_item, event_writer, logger, sourcetype, index_type):
    """
    Process all API endpoints for a single host.

    Args:
        host: IP address of the device
        api_key: API key for authentication
        api_endpoints: List of endpoint names to query
        session_key: Splunk session key
        input_item: Input configuration dictionary
        event_writer: Splunk event writer
        logger: Logger instance
        sourcetype: Sourcetype for events
        index_type: Type of index (events or metrics)

    Returns:
        Tuple of (host, total_events_count, success_bool)
    """
    total_events = 0

    try:
        logger.info(f"Processing host: {host}")

        # Process each API endpoint for this host
        for endpoint_name in api_endpoints:
            endpoint_name = endpoint_name.strip()
            if not endpoint_name:
                continue

            logger.info(f"Processing API endpoint '{endpoint_name}' for host: {host}")

            try:
                # Get endpoint configuration
                endpoint_config = get_api_endpoint_config(session_key, endpoint_name)
                api_url_template = endpoint_config.get("api_url")
                script_type = endpoint_config.get("script_type")

                # Build variable substitution dictionary
                variables = {
                    "host": host,
                    "apikey": api_key,
                    "api_key": api_key,  # Support both formats
                }

                # Substitute variables in URL
                api_url = substitute_variables(api_url_template, variables)

                logger.info(f"Calling endpoint '{endpoint_name}' on host {host} with script type: {script_type} on API URL: {api_url}")

                # Call appropriate function based on script type
                if script_type == "GET_api_generic_xml_output":
                    data = GET_api_generic(logger, api_url, endpoint_name)
                elif script_type == "custom_GET_api_threat_traffic":
                    data = custom_GET_api_threat_traffic(logger, api_url, endpoint_name)
                else:
                    logger.error(f"Unknown script type: {script_type}")
                    continue
                
                # Ingest data
                if index_type == "metrics":
                    # Convert XML to metrics JSON format
                    for record in data:
                        # Extract raw XML from record
                        if isinstance(record, dict) and "_raw" in record:
                            xml_text = record["_raw"]
                        else:
                            xml_text = json.dumps(record, ensure_ascii=False, default=str)

                        # Convert XML to metrics JSON format (dict with metric_name: prefixed keys)
                        metrics_dict = xml_to_metrics(xml_text, endpoint_name, host)

                        # Write the metrics event if we got metrics (more than just endpoint and host fields)
                        if len(metrics_dict) > 2:  # More than just endpoint and host
                            # Serialize to JSON
                            metrics_json = json.dumps(metrics_dict, ensure_ascii=False)
                            event_writer.write_event(
                                smi.Event(
                                    data=metrics_json,
                                    index=input_item.get("index"),
                                    sourcetype=sourcetype,
                                    source=f"palo_alto:{endpoint_name}",
                                    host=host
                                )
                            )
                            total_events += 1
                            logger.info(f"Written metrics event for endpoint '{endpoint_name}' on host {host}: {len(metrics_dict)-2} metrics")
                else:
                    # Format data as events (default) - convert XML to JSON
                    for record in data:
                        # Extract raw XML from record
                        if isinstance(record, dict) and "_raw" in record:
                            xml_text = record["_raw"]
                        else:
                            xml_text = json.dumps(record, ensure_ascii=False, default=str)

                        # Convert XML to JSON format
                        event_dict = xml_to_json(xml_text, endpoint_name, host)

                        # Serialize to JSON
                        event_json = json.dumps(event_dict, ensure_ascii=False)

                        event_writer.write_event(
                            smi.Event(
                                data=event_json,
                                index=input_item.get("index"),
                                sourcetype=sourcetype,
                                source=f"palo_alto:{endpoint_name}",
                                host=host
                            )
                        )

                    total_events += len(data)
                    logger.info(f"Written {len(data)} event(s) for endpoint '{endpoint_name}' on host {host}")

            except Exception as endpoint_error:
                logger.error(f"Error processing endpoint '{endpoint_name}' for host {host}: {str(endpoint_error)}")
                # Continue processing other endpoints even if one fails
                continue

        logger.info(f"Completed processing host {host}: {total_events} events ingested")
        return (host, total_events, True)

    except Exception as host_error:
        logger.error(f"Error processing host {host}: {str(host_error)}")
        return (host, 0, False)


def validate_input(definition: smi.ValidationDefinition):
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    # inputs.inputs is a Python dictionary object like:
    # {
    #   "palo_alto_input://<input_name>": {
    #     "account": "<account_name>",
    #     "ip_address": "<device_ip1>, <device_ip2>, ...",
    #     "api_endpoints": "<endpoint1>,<endpoint2>,...",
    #     "sourcetype": "<sourcetype>",
    #     "index_type": "<events|metrics>",
    #     "disabled": "0",
    #     "host": "$decideOnStartup",
    #     "index": "<index_name>",
    #     "interval": "<interval_value>",
    #     "python.version": "python3",
    #   },
    # }
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="palo_alto_addon_for_splunk_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            # Get configuration
            api_key = get_account_api_key(session_key, input_item.get("account"))
            ip_addresses_raw = input_item.get("ip_address", "")
            api_endpoints = input_item.get("api_endpoints", "").split(",")
            sourcetype = input_item.get("sourcetype", "pan:log")
            index_type = input_item.get("index_type", "events")

            # Parse comma-separated IP addresses
            hosts = [ip.strip() for ip in ip_addresses_raw.split(",") if ip.strip()]

            if not hosts:
                logger.error("No valid IP addresses configured")
                continue

            logger.info(f"Processing {len(hosts)} host(s): {', '.join(hosts)}")

            # Use ThreadPoolExecutor to process multiple hosts in parallel
            # Up to 20 hosts can be configured (validated in globalConfig.json)
            # Set max_workers to actual number of hosts for full parallelism
            max_workers = len(hosts)

            total_events_all_hosts = 0
            successful_hosts = 0
            failed_hosts = 0

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all host processing tasks
                future_to_host = {
                    executor.submit(
                        process_host_endpoints,
                        host,
                        api_key,
                        api_endpoints,
                        session_key,
                        input_item,
                        event_writer,
                        logger,
                        sourcetype,
                        index_type
                    ): host for host in hosts
                }

                # Collect results as they complete
                for future in as_completed(future_to_host):
                    host = future_to_host[future]
                    try:
                        host_ip, events_count, success = future.result()
                        if success:
                            successful_hosts += 1
                            total_events_all_hosts += events_count
                            logger.info(f"Host {host_ip} completed successfully: {events_count} events")
                        else:
                            failed_hosts += 1
                            logger.warning(f"Host {host_ip} completed with errors")
                    except Exception as exc:
                        failed_hosts += 1
                        logger.error(f"Host {host} generated an exception: {str(exc)}")

            # Log summary
            logger.info(f"Processing complete: {successful_hosts} hosts successful, {failed_hosts} hosts failed, {total_events_all_hosts} total events ingested")

            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:
            log.log_exception(logger, e, "modular_input_error", msg_before=f"Exception raised while ingesting data for {normalized_input_name}: ")

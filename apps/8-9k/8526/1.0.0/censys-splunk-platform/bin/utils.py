"""
utility.py .

Helper file containing useful methods
"""

import import_declare_test
import logging
import traceback
import re
from datetime import datetime
import uuid
import sys
import time
import random

import splunk
import splunklib.client as client
import splunk.rest
import splunk.clilib.cli_common
from solnlib import conf_manager
from splunk.clilib.bundle_paths import make_splunkhome_path

from censys_exceptions import APIKeyNotFoundError
from common.consts import (
    IPV4_REGEX,
    SHA256_REGEX,
    DOMAIN_REGEX,
    HOST_REGEX,
    CENSYS_SPLUNK_PLATFORM_VERSION,
    DEFAULT_VALUE_NA,
    IndicatorTypes,
)

APP_NAME = import_declare_test.ta_name


def get_conf_file(
    session_key,
    file,
    app=APP_NAME,
    realm="__REST_CREDENTIAL__#{app_name}#configs/conf-censys-splunk-platform_settings".format(
        app_name=APP_NAME
    ),
):
    """
    Returns the conf object of the file.

    :param session_key:
    :param file:
    :param app:
    :param realm:
    :return: Conf File Object
    """
    cfm = conf_manager.ConfManager(session_key, app, realm=realm)
    return cfm.get_conf(file)


def get_log_level(session_key):
    """
    Returns the log level from the Censys config.

    :param session_key:
    :return: level
    """
    # Get configuration file from the helper method defined in utility
    conf = get_conf_file(session_key, "censys-splunk-platform_settings")

    # Get logging stanza from the settings
    logging_config = conf.get("logging", {})
    logging_level = logging_config.get("loglevel", "INFO")
    level = logging.INFO
    if logging_level == "INFO":
        level = logging.INFO
    elif logging_level == "DEBUG":
        level = logging.DEBUG
    elif logging_level == "WARNING":
        level = logging.WARNING
    elif logging_level == "ERROR":
        level = logging.ERROR
    elif logging_level == "CRITICAL":
        level = logging.CRITICAL

    return level


def setup_logger(
    logger=None,
    log_format=(
        "%(asctime)s log_level=%(levelname)s, pid=%(process)d, "
        "tid=%(threadName)s, func_name=%(funcName)s, code_line_no=%(lineno)d | "
    ),
    logger_name="censys_main",
    session_key=None,
    log_context="Censys App",
):
    """Get a logger object with specified log level."""
    if logger is None:
        logger = logging.getLogger(logger_name)

    # Get the logging level
    level = get_log_level(session_key)

    # Prevent the log messages from being duplicated in the python.log file
    logger.propagate = False
    logger.setLevel(level)

    log_name = logger_name + ".log"
    file_handler = logging.handlers.RotatingFileHandler(
        make_splunkhome_path(["var", "log", "splunk", log_name]),
        maxBytes=2500000,
        backupCount=5,
    )

    # Adding the source of the logs to the log format
    log_format = log_format + "[{log_context}] %(message)s".format(
        log_context=log_context
    )
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)

    logger.handlers = []
    logger.addHandler(file_handler)

    return logger


def get_api_key(session_key, logger):
    """
    Returns the API key configured by the user from the Splunk endpoint, returns blank when no API key is found.

    :param session_key:
    :param logger: logger information
    :return: API Key
    """
    # Get configuration file from the helper method defined in utility
    conf = get_conf_file(session_key, "censys-splunk-platform_settings")

    api_key_stanza = conf.get("parameters", {})
    api_key = api_key_stanza.get("api_key", "")

    if not api_key:
        message = "API key not found. Please configure the Censys for Splunk Platform."
        make_error_message(message, session_key, logger)
        raise APIKeyNotFoundError(message)

    return api_key


def get_proxy(session_key, logger):
    """
    Returns the proxy configured by the user from the Splunk endpoint, returns blank when no proxy is found.

    :param session_key:
    :param logger: logger information
    :return: proxy url
    """
    # Get configuration file from the helper method defined in utility
    conf = get_conf_file(session_key, "censys-splunk-platform_settings")

    param_stanza = conf.get("parameters", {})
    proxy = param_stanza.get("proxy", "")

    logger.debug("Proxy server found in config: {}".format(proxy))

    return proxy


def make_error_message(message, session_key, logger):
    """
    Generates Splunk Error Message.

    :param message:
    :param session_key:
    :param logger: logger information
    :return: error message
    """
    try:
        splunk.rest.simpleRequest(
            "/services/messages/new",
            postargs={"name": APP_NAME, "value": "%s" % message, "severity": "error"},
            method="POST",
            sessionKey=session_key,
        )
    except Exception:
        logger.error(
            "Error occurred while generating error message for Splunk, Error: {}".format(
                str(traceback.format_exc())
            )
        )


def check_indicator_type(value):
    """Check indicator type."""
    if re.search(IPV4_REGEX, value):
        return IndicatorTypes.HOST.value
    elif re.search(HOST_REGEX, value):
        return IndicatorTypes.HOST.value
    elif re.search(SHA256_REGEX, value):
        return IndicatorTypes.CERTIFICATE.value
    elif re.search(DOMAIN_REGEX, value):
        return IndicatorTypes.WEB_PROPERTY.value
    else:
        return None


def get_enriched_host_fields(response_data, scan_type, event=None):
    """Filter out the enriched fields for host."""
    data = response_data.get("result", {}).get("resource", {})
    services = data.get("services", [])
    ports = []
    protocols = []
    transport_protocols = []
    services_labels = []
    services_vulns = []
    services_threats = []
    service_scan_times = []
    for service in services:
        ports.append(service.get("port", ""))
        protocols.append(service.get("protocol", ""))
        transport_protocols.append(service.get("transport_protocol", ""))
        src_labels = service.get("labels", [])
        src_vulns = service.get("vulns", [])
        src_threats = service.get("threats", [])
        service_scan_times.append(service.get("scan_time", ""))
        for label in src_labels:
            services_labels.append(label.get("value", ""))
        for vul in src_vulns:
            services_vulns.append(vul.get("name", ""))
        for threat in src_threats:
            services_threats.append(threat.get("name", ""))
    all_labels = data.get("labels", [])
    label_values = []
    for label in all_labels:
        label_values.append(label.get("value", ""))
    enriched_event = {
        "_key": str(uuid.uuid4()),
        "ip": data.get("ip", ""),
        "labels": label_values,
        "service_count": data.get("service_count", 0),
        "services_ports": ports,
        "services_protocols": protocols,
        "services_transport_protocols": transport_protocols,
        "services_labels": services_labels,
        "services_vulns": services_vulns,
        "services_threats": services_threats,
        "services_scan_times": service_scan_times,
        "dns_names": data.get("dns", {}).get("names", []),
        "forward_dns_names": data.get("dns", {})
        .get("forward_dns", {})
        .get("names", []),
        "reverse_dns_names": data.get("dns", {})
        .get("reverse_dns", {})
        .get("names", []),
        "network_name": data.get("whois", {}).get("network", {}).get("name", ""),
        "cidrs": data.get("whois", {}).get("network", {}).get("cidrs", []),
        "autonomous_system_name": data.get("autonomous_system", {}).get("name", ""),
        "autonomous_system_asn": data.get("autonomous_system", {}).get("asn", ""),
        "city": data.get("location", {}).get("city", ""),
        "province": data.get("location", {}).get("province", ""),
        "postal_code": data.get("location", {}).get("postal_code", ""),
        "country": data.get("location", {}).get("country", ""),
        "country_code": data.get("location", {}).get("country_code", ""),
        "continent": data.get("location", {}).get("continent", ""),
        "latitude": data.get("location", {}).get("coordinates", {}).get("latitude", ""),
        "longitude": data.get("location", {})
        .get("coordinates", {})
        .get("longitude", ""),
        "last_enriched": datetime.now().isoformat(),
        "scan_type": scan_type,
    }
    if event:
        raw_event = event.get("_raw")
        additional_fields = {
            "raw_event": str(raw_event),
            "index": event.get("index", ""),
            "sourcetype": event.get("sourcetype", ""),
            "timestamp": event.get("timestamp", ""),
        }
        enriched_event.update(additional_fields)
    return enriched_event


def get_enriched_web_property_fields(response_data, scan_type, event=None):
    """Filter out the enriched fields for web property."""
    data = response_data.get("result", {}).get("resource", {})
    labels = data.get("labels", [])
    label_values = []
    for label in labels:
        label_values.append(label.get("value", ""))

    softwares = data.get("software", [])
    products = []
    vendors = []
    versions = []
    for software in softwares:
        products.append(software.get("product", ""))
        vendors.append(software.get("vendor", ""))
        versions.append(software.get("version", ""))

    endpoints = data.get("endpoints", [])
    endpoint_types = []
    endpoint_paths = []
    for endpoint in endpoints:
        endpoint_types.append(endpoint.get("endpoint_type", ""))
        endpoint_paths.append(endpoint.get("path", ""))

    threats = data.get("threats", [])
    threats_names = []
    for threat in threats:
        threats_names.append(threat.get("name", ""))

    vulns = data.get("vulns", [])
    vulns_names = []
    for vuln in vulns:
        vulns_names.append(vuln.get("name", ""))

    enriched_event = {
        "_key": str(uuid.uuid4()),
        "hostname": data.get("hostname", ""),
        "port": data.get("port", ""),
        "scan_time": data.get("scan_time", ""),
        "endpoint_types": endpoint_types,
        "endpoint_paths": endpoint_paths,
        "labels": label_values,
        "threats_names": threats_names,
        "vulns_names": vulns_names,
        "vendors": vendors,
        "products": products,
        "versions": versions,
        "fingerprint_sha256": data.get("cert", {}).get("fingerprint_sha256", ""),
        "self_signed": data.get("cert", {})
        .get("parsed", {})
        .get("signature", {})
        .get("self_signed", ""),
        "subject_dn": data.get("cert", {}).get("parsed", {}).get("subject_dn", ""),
        "issuer_dn": data.get("cert", {}).get("parsed", {}).get("issuer_dn", ""),
        "common_names": data.get("cert", {})
        .get("parsed", {})
        .get("subject", {})
        .get("common_name", []),
        "not_before": data.get("cert", {})
        .get("parsed", {})
        .get("validity_period", {})
        .get("not_before", ""),
        "not_after": data.get("cert", {})
        .get("parsed", {})
        .get("validity_period", {})
        .get("not_after", ""),
        "last_enriched": datetime.now().isoformat(),
        "scan_type": scan_type,
    }
    if event:
        raw_event = event.get("_raw")
        additional_fields = {
            "raw_event": str(raw_event),
            "index": event.get("index", ""),
            "sourcetype": event.get("sourcetype", ""),
            "timestamp": event.get("timestamp", ""),
        }
        enriched_event.update(additional_fields)
    return enriched_event


def get_enriched_certificate_fields(response_data, scan_type, event=None):
    """Filter out the enriched fields for certificate."""
    data = response_data.get("result", {}).get("resource", {})
    enriched_event = {
        "_key": str(uuid.uuid4()),
        "fingerprint_sha256": data.get("fingerprint_sha256", ""),
        "self_signed_signature": data.get("parsed", {})
        .get("signature", {})
        .get("self_signed", ""),
        "valid_to": data.get("valid_to", ""),
        "self_signed": data.get("self_signed", ""),
        "subject_dn": data.get("parsed", {}).get("subject_dn", ""),
        "issuer_dn": data.get("parsed", {}).get("issuer_dn", ""),
        "common_names": data.get("parsed", {})
        .get("subject", {})
        .get("common_name", []),
        "valid_not_before": data.get("parsed", {})
        .get("validity_period", {})
        .get("not_before", ""),
        "valid_not_after": data.get("parsed", {})
        .get("validity_period", {})
        .get("not_after", ""),
        "last_enriched": datetime.now().isoformat(),
        "scan_type": scan_type,
    }
    if event:
        raw_event = event.get("_raw")
        additional_fields = {
            "raw_event": str(raw_event),
            "index": event.get("index", ""),
            "sourcetype": event.get("sourcetype", ""),
            "timestamp": event.get("timestamp", ""),
        }
        enriched_event.update(additional_fields)
    return enriched_event


def get_enriched_host_event_history_fields(
    host_id, event_time, historical_host_link, resource_type, resource_key_values
):
    """Filter out the enriched fields for host event history."""
    enriched_event = {
        "_key": str(uuid.uuid4()),
        "host_ip": host_id,
        "event_time": event_time,
        "historical_host_link": historical_host_link,
        "resource_type": resource_type,
        "resource_key_values": resource_key_values,
        "last_enriched": datetime.now().isoformat(),
    }

    return enriched_event


def get_mgmt_hostname_and_port():
    """
    Get the management hostname and port from Splunk.

    Returns:
        tuple: (hostname, port)
    """
    mgmt_uri = splunk.clilib.cli_common.getMgmtUri()
    hostname = mgmt_uri.split("//")[-1].split(":")[0]  # Extract hostname from URI
    port = mgmt_uri.split("//")[-1].split(":")[-1]  # Extract port from URI
    return hostname, port


def construct_censys_host_event_history_link(host_id, encoded_time, organization_id):
    """Construct the Censys host event history link."""
    return f"hosts/{host_id}?at_time={encoded_time}&org={organization_id}"


def get_splunk_version(session_key):
    """Get the Splunk version."""
    # Creating client for connecting server
    _, port = get_mgmt_hostname_and_port()
    service = client.connect(port=port, token=session_key, app=APP_NAME)
    info = service.info
    return info["version"]


def get_python_version():
    """Get the Python version."""
    python_version = sys.version
    python_version = python_version.split(" ")[0]
    return python_version


def get_censys_version():
    """Get the Censys version."""
    return CENSYS_SPLUNK_PLATFORM_VERSION


def extract_resource_type_and_values(resource):
    """
    Extract resource_type and resource_key_values from a resource object.

    This function handles the common logic for extracting resource type and key values
    from different types of resources in the Censys event history data.

    Args:
        resource (dict): The resource object from Censys event history

    Returns:
        tuple: (resource_type, resource_key_values) or (None, None) if resource type not recognized
    """
    resource_type = ""
    resource_key_values = ""

    if "service_scanned" in resource:
        resource_type = "service_scanned"
        scan_data = resource.get("service_scanned", {}).get("scan", {})
        port = scan_data.get("port", DEFAULT_VALUE_NA)
        protocol = scan_data.get("protocol", DEFAULT_VALUE_NA)
        transport_protocol = scan_data.get("transport_protocol", DEFAULT_VALUE_NA)
        resource_key_values = f"{port}/{protocol}/{transport_protocol}"

    elif "reverse_dns_resolved" in resource:
        resource_type = "reverse_dns_resolved"
        dns_data = resource.get("reverse_dns_resolved", {})
        names = dns_data.get("names", [])
        resource_key_values = names[0] if names else DEFAULT_VALUE_NA

    elif "endpoint_scanned" in resource:
        resource_type = "endpoint_scanned"
        scan_data = resource.get("endpoint_scanned", {}).get("scan", {})
        port = scan_data.get("port", DEFAULT_VALUE_NA)
        endpoint_type = scan_data.get("endpoint_type", DEFAULT_VALUE_NA)
        endpoint_path = scan_data.get("path", DEFAULT_VALUE_NA)
        if endpoint_path and endpoint_path != "/":
            resource_key_values = f"{port}/{endpoint_type}/{endpoint_path}"
        else:
            resource_key_values = f"{port}/{endpoint_type}"

    elif "forward_dns_resolved" in resource:
        resource_type = "forward_dns_resolved"
        dns_data = resource.get("forward_dns_resolved", {})
        name = dns_data.get("name", DEFAULT_VALUE_NA)
        resource_key_values = name

    elif "jarm_scanned" in resource:
        resource_type = "jarm_scanned"
        scan_data = resource.get("jarm_scanned", {}).get("scan", {})
        fingerprint = scan_data.get("fingerprint", DEFAULT_VALUE_NA)
        resource_key_values = fingerprint

    elif "location_updated" in resource:
        resource_type = "location_updated"
        location = resource.get("location_updated", {}).get("location", {})
        city = location.get("city", DEFAULT_VALUE_NA)
        country = location.get("country", DEFAULT_VALUE_NA)
        resource_key_values = f"{city}/{country}"

    elif "route_updated" in resource:
        resource_type = "route_updated"
        route = resource.get("route_updated", {}).get("route", {})
        asn = route.get("asn", DEFAULT_VALUE_NA)
        organization = route.get("organization", DEFAULT_VALUE_NA)
        resource_key_values = f"{asn}/{organization}"

    elif "whois_updated" in resource:
        resource_type = "whois_updated"
        whois = resource.get("whois_updated", {}).get("whois", {})
        org = whois.get("organization", {})
        org_name = org.get("name", DEFAULT_VALUE_NA)
        resource_key_values = org_name
    else:
        return None, None
    return resource_type, resource_key_values


def wait_for_scan_completion(
    rest_helper_obj, tracked_scan_id, acc_org_id, resource_identifier, logger
):
    """
    Wait for a Censys scan to complete with exponential backoff and jitter.

    Args:
        rest_helper_obj: RestHelper object to make API calls
        tracked_scan_id: ID of the scan to track
        acc_org_id: Organization ID
        resource_identifier: String identifier for the resource being scanned (e.g. "host 1.2.3.4:80")
        logger: Logger object for logging messages

    Returns:
        tuple: (success, message) where success is a boolean indicating if scan completed successfully
              and message contains details about the scan result or error
    """
    retry_count = 0
    max_retries = 20  # Approximately 10 minutes with exponential backoff
    base_sleep_time = 10  # Start with 10 seconds
    max_sleep_time = 50  # Cap at 50 seconds

    while retry_count < max_retries:
        scan_status = rest_helper_obj.get_current_scan_status(
            tracked_scan_id, acc_org_id
        )

        if not scan_status:
            error_msg = f"Error while getting scan status for {resource_identifier}."
            logger.error(error_msg)
            return False, error_msg

        # Check if scan is completed
        is_completed = False
        if isinstance(scan_status.get("result", {}), dict) and scan_status.get(
            "result", {}
        ).get("completed", False) in (True, "true", 1):
            is_completed = True

        if is_completed:
            success_msg = f"Scan completed successfully for {resource_identifier}."
            logger.info(success_msg)
            return True, success_msg
        else:
            retry_count += 1
            # Calculate sleep time with exponential backoff and jitter
            # Formula: min(max_sleep_time, base_sleep_time * (1.5 ^ retry_count) + random jitter)
            exponent = min(retry_count, 8)  # Prevent potential overflow
            sleep_time = min(max_sleep_time, base_sleep_time * (1.5**exponent))
            # Add jitter (±20%)
            jitter = sleep_time * 0.2 * (random.random() * 2 - 1)
            sleep_time = max(base_sleep_time, sleep_time + jitter)

            msg = (
                f"Scan is not completed for {resource_identifier} after {retry_count} retries. "
                f"Waiting for {sleep_time:.1f} seconds before next check."
            )
            logger.debug(msg)

            time.sleep(sleep_time)

    timeout_msg = (
        f"Scan is not completed for {resource_identifier} after maximum retries."
    )
    logger.error(timeout_msg)
    return False, timeout_msg

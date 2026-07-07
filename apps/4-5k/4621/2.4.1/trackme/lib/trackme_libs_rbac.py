#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import logging

# Networking and URL handling imports
import requests
from requests.structures import CaseInsensitiveDict
from urllib.parse import urlencode
import urllib.parse
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


def trackme_kvcollection_get_acl(session_key, splunkd_uri, tenant_id, collection_name):

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    record_url = f"{splunkd_uri}/servicesNS/nobody/trackme/storage/collections/config/{collection_name}/acl"

    get_effective_logger().info(
        f'function trackme_kvcollection_get_acl, tenant_id="{tenant_id}", attempting to retrieve ACL for collection collection_name="{collection_name}"'
    )
    try:
        response = requests.get(
            record_url,
            headers=header,
            verify=False,
            timeout=600,
            params={"output_mode": "json"},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        get_effective_logger().error(
            f'function trackme_kvcollection_get_acl, tenant_id="{tenant_id}", failure to retrieve ACL for collection collection_name="{collection_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_macro_get_acl(session_key, splunkd_uri, tenant_id, macro_name):

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    record_url = f"{splunkd_uri}/servicesNS/admin/trackme/data/macros/{macro_name}/acl"

    get_effective_logger().info(
        f'function trackme_macro_get_acl, tenant_id="{tenant_id}", attempting to retrieve ACL for macro macro_name="{macro_name}"'
    )
    try:
        response = requests.get(
            record_url,
            headers=header,
            verify=False,
            timeout=600,
            params={"output_mode": "json"},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        get_effective_logger().error(
            f'function trackme_macro_get_acl, tenant_id="{tenant_id}", failure to retrieve ACL for macro macro_name="{macro_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_transform_get_acl(session_key, splunkd_uri, tenant_id, transform_name):

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    record_url = f"{splunkd_uri}/servicesNS/admin/trackme/data/transforms/lookups/{transform_name}/acl"

    get_effective_logger().info(
        f'function trackme_transform_get_acl, tenant_id="{tenant_id}", attempting to retrieve ACL for transforms transform_name="{transform_name}"'
    )
    try:
        response = requests.get(
            record_url,
            headers=header,
            verify=False,
            timeout=600,
            params={"output_mode": "json"},
        )
        response.raise_for_status()
        get_effective_logger().info(
            f'function trackme_transform_get_acl, tenant_id="{tenant_id}", action="success", transform_name="{transform_name}"'
        )
        return response.json()
    except Exception as e:
        get_effective_logger().error(
            f'function trackme_transform_get_acl, tenant_id="{tenant_id}", failure to retrieve ACL for transforms transform_name="{transform_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_report_get_acl(session_key, splunkd_uri, tenant_id, report_name):

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    record_url = f"{splunkd_uri}/servicesNS/nobody/trackme/saved/searches/{urllib.parse.quote(str(report_name))}/acl"

    get_effective_logger().info(
        f'function trackme_report_get_acl, tenant_id="{tenant_id}", attempting to retrieve ACL for report report_name="{report_name}"'
    )
    try:
        response = requests.get(
            record_url,
            headers=header,
            verify=False,
            timeout=600,
            params={"output_mode": "json"},
        )
        response.raise_for_status()
        get_effective_logger().info(
            f'function trackme_report_get_acl, tenant_id="{tenant_id}", action="success", report_name="{report_name}"'
        )
        return response.json()
    except Exception as e:
        get_effective_logger().error(
            f'function trackme_report_get_acl, tenant_id="{tenant_id}", failure to retrieve ACL for report report_name="{report_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_kvcollection_update_acl(
    session_key, splunkd_uri, tenant_id, collection_name, collection_acl_properties
):

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    record_url = f"{splunkd_uri}/servicesNS/nobody/trackme/storage/collections/config/{collection_name}/acl"

    get_effective_logger().info(
        f'function trackme_kvcollection_update_acl, tenant_id="{tenant_id}", attempting to update collection collection_name="{collection_name}"'
    )
    try:
        response = requests.post(
            record_url,
            headers=header,
            data=collection_acl_properties,
            verify=False,
            timeout=600,
        )
        get_effective_logger().info(
            f'function trackme_kvcollection_update_acl, tenant_id="{tenant_id}", action="success", collection_name="{collection_name}"'
        )
        return "success"
    except Exception as e:
        get_effective_logger().error(
            f'function trackme_kvcollection_update_acl, tenant_id="{tenant_id}", failure to update collection collection_name="{collection_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_macro_update_acl(
    session_key, splunkd_uri, tenant_id, macro_name, macro_acl_properties
):

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    record_url = f"{splunkd_uri}/servicesNS/admin/trackme/data/macros/{macro_name}/acl"

    get_effective_logger().info(
        f'function trackme_macro_update_acl, tenant_id="{tenant_id}", attempting to update macro macro_name="{macro_name}"'
    )
    try:
        response = requests.post(
            record_url,
            headers=header,
            data=macro_acl_properties,
            verify=False,
            timeout=600,
        )
        get_effective_logger().info(
            f'function trackme_macro_update_acl, tenant_id="{tenant_id}", action="success", macro_name="{macro_name}"'
        )
        return "success"
    except Exception as e:
        get_effective_logger().error(
            f'function trackme_macro_update_acl, tenant_id="{tenant_id}", failure to update macro macro_name="{macro_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_transform_update_acl(
    session_key, splunkd_uri, tenant_id, transform_name, transform_acl_properties
):

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    record_url = f"{splunkd_uri}/servicesNS/admin/trackme/data/transforms/lookups/{transform_name}/acl"

    get_effective_logger().info(
        f'function trackme_transform_update_acl, tenant_id="{tenant_id}", attempting to update transforms transform_name="{transform_name}"'
    )
    try:
        response = requests.post(
            record_url,
            headers=header,
            data=transform_acl_properties,
            verify=False,
            timeout=600,
        )
        get_effective_logger().info(
            f'function trackme_transform_update_acl, tenant_id="{tenant_id}", action="success", transform_name="{transform_name}"'
        )
        return "success"
    except Exception as e:
        get_effective_logger().error(
            f'function trackme_transform_update_acl, tenant_id="{tenant_id}", failure to update transforms transform_name="{transform_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))


def trackme_report_update_acl(
    session_key, splunkd_uri, tenant_id, report_name, report_acl_properties
):

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    record_url = f"{splunkd_uri}/servicesNS/nobody/trackme/saved/searches/{urllib.parse.quote(str(report_name))}/acl"

    get_effective_logger().info(
        f'function trackme_report_update_acl, tenant_id="{tenant_id}", attempting to update report report_name="{report_name}"'
    )
    try:
        response = requests.post(
            record_url,
            headers=header,
            data=report_acl_properties,
            verify=False,
            timeout=600,
        )
        get_effective_logger().info(
            f'function trackme_report_update_acl, tenant_id="{tenant_id}", action="success", report_name="{report_name}"'
        )
        return "success"
    except Exception as e:
        get_effective_logger().error(
            f'function trackme_report_update_acl, tenant_id="{tenant_id}", failure to update report report_name="{report_name}" with exception:"{str(e)}"'
        )
        raise Exception(str(e))

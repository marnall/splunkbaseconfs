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
import time
import datetime
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler

# Networking and URL handling imports
import urllib3
import requests

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# import TrackMe libs
from trackme_libs import JSONFormatter

"""
Simple functions handle old and new value types
"""


def verify_type_values(old_value, new_value):

    # if any of the two is a float, convert the other to a float
    if isinstance(old_value, float) or isinstance(new_value, float):
        try:
            old_value = float(old_value)
            new_value = float(new_value)
        except Exception as e:
            pass

    # if any of the two is an integer, convert the other to an integer
    elif isinstance(old_value, int) or isinstance(new_value, int):
        try:
            old_value = int(old_value)
            new_value = int(new_value)
        except Exception as e:
            pass

    return old_value, new_value


"""
TrackMe Audit call function
"""


def trackme_audits_callback(
    session_key,
    splunkd_uri,
    tenant_id=None,
    audit_events=None,
):
    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": f"Splunk {session_key}",
        "Content-Type": "application/json",
    }

    # Audit

    # set
    url = f"{splunkd_uri}/services/trackme/v2/audit/audit_events_v2"
    data = {
        "tenant_id": f"{tenant_id}",
        "audit_events": audit_events,
    }

    # Proceed
    get_effective_logger().info(f'calling endpoint with data="{json.dumps(data)}"')
    try:
        response = requests.post(
            url, headers=header, data=json.dumps(data), verify=False, timeout=600
        )
        if response.ok:
            get_effective_logger().debug(f'Success audit event, data="{response}"')
            response_json = response.json()
            return response_json
        else:
            error_message = f'Function trackme_audits_call has failed, status_code={response.status_code}, response_text="{response.text}"'
            get_effective_logger().error(error_message)
            raise Exception(error_message)

    except Exception as e:
        error_msg = f'Function trackme_audits_call has failed, exception="{str(e)}"'
        raise Exception(error_msg)


"""
TrackMe Audit gen Library
"""


def trackme_audit_gen(audit_index, audit_event_list):

    try:
        if not isinstance(audit_event_list, list):
            raise Exception(
                f"Invalid audit event list, a list should be providen, received: {type(audit_event_list)}, content={audit_event_list}"
            )

        # Create a dedicated logger for audit events
        audit_logger = logging.getLogger("trackme.audit.events")
        audit_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not audit_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_audit_events.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter(timestamp=time.time())
            logging.Formatter.converter = time.gmtime
            filehandler.setFormatter(formatter)
            audit_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            audit_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in audit_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_audit_events.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter(timestamp=time.time())
                logging.Formatter.converter = time.gmtime
                filehandler.setFormatter(formatter)
                audit_logger.addHandler(filehandler)

        for audit_event in audit_event_list:
            # calculate the event_id as the sha-256 sum of the audit_event
            event_id = hashlib.sha256(json.dumps(audit_event).encode()).hexdigest()
            audit_event["event_id"] = event_id

            # add human readable time
            audit_event["timeStr"] = str(datetime.datetime.now())

            # if no comment is provided, set it to "No comment for update."
            if "comment" not in audit_event:
                audit_event["comment"] = "No comment for update."

            audit_logger.info(
                "Audit - group=audit_events",
                extra={
                    "target_index": audit_index,
                    "event": json.dumps(audit_event),
                },
            )

    except Exception as e:
        raise Exception(str(e))


"""
TrackMe handler events gen Library
"""


def trackme_handler_events_gen(
    target_index, handler_event_list, target_source, target_sourcetype
):

    try:
        if not isinstance(handler_event_list, list):
            raise Exception(
                f"Invalid handler event list, a list should be providen, received: {type(handler_event_list)}, content={handler_event_list}"
            )

        # Create a dedicated logger for handler events
        handler_logger = logging.getLogger("trackme.handler.events")
        handler_logger.setLevel(logging.INFO)

        # Only add the handler if it doesn't exist yet
        if not handler_logger.handlers:
            # Set up the file handler
            filehandler = RotatingFileHandler(
                f"{splunkhome}/var/log/splunk/trackme_handler_events.log",
                mode="a",
                maxBytes=100000000,
                backupCount=1,
            )
            formatter = JSONFormatter(timestamp=time.time())
            logging.Formatter.converter = time.gmtime
            filehandler.setFormatter(formatter)
            handler_logger.addHandler(filehandler)
            # Prevent propagation to root logger
            handler_logger.propagate = False
        else:
            # Find the RotatingFileHandler among existing handlers
            filehandler = None
            for handler in handler_logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    filehandler = handler
                    break
            
            # If no RotatingFileHandler found, create one
            if filehandler is None:
                filehandler = RotatingFileHandler(
                    f"{splunkhome}/var/log/splunk/trackme_handler_events.log",
                    mode="a",
                    maxBytes=100000000,
                    backupCount=1,
                )
                formatter = JSONFormatter(timestamp=time.time())
                logging.Formatter.converter = time.gmtime
                filehandler.setFormatter(formatter)
                handler_logger.addHandler(filehandler)

        for handler_event in handler_event_list:
            # calculate the event_id as the sha-256 sum of the audit_event
            event_id = hashlib.sha256(json.dumps(handler_event).encode()).hexdigest()
            handler_event["event_id"] = event_id

            # add human readable time
            handler_event["timeStr"] = str(datetime.datetime.now())

            handler_logger.info(
                "Audit - group=handler_events",
                extra={
                    "target_index": target_index,
                    "target_source": target_source,
                    "target_sourcetype": target_sourcetype,
                    "event": json.dumps(handler_event),
                },
            )

    except Exception as e:
        raise Exception(str(e))

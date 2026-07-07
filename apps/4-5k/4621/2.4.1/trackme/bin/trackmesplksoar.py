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

# Built-in libraries
import json
import logging
import os
import sys
import time
from ast import literal_eval

# Third-party libraries
import requests
import urllib3

# Logging handlers
from logging.handlers import RotatingFileHandler

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_soar.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)  # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
log.setLevel(logging.INFO)

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# Import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackMeRestHandler(GeneratingCommand):
    soar_server = Option(
        doc="""
        **Syntax:** **The soar_server=****
        **Description:** Mandatory, SOAR server account as configured in the Splunk App for SOAR""",
        require=False,
        default="*",
        validate=validators.Match("url", r"^.*"),
    )

    action = Option(
        doc="""
        **Syntax:** **The action to be requested=****
        **Description:** A pre-built set of actions or a single action, valid options: soar_get, soar_post, soar_test_apps, soar_automation_broker_manage""",
        require=False,
        default="soar_get",
        validate=validators.Match(
            "action",
            r"^(?:soar_get|soar_post|soar_test_apps|soar_health_status|soar_health_memory|soar_health_load|soar_automation_broker_manage|soar_playbook_status)$",
        ),
    )

    action_data = Option(
        doc="""
        **Syntax:** **The data body for the actions to be requested=****
        **Description:** Some actions may accept options, this should be a JSON formatted object""",
        require=False,
        default=None,
        validate=validators.Match("action_data", r"^\{.*\}$"),
    )

    action_params = Option(
        doc="""
        **Syntax:** **Optional extra params for the actions to be requested=****
        **Description:** In some cases, you may want to add extra params to the query, this should be a JSON formatted object""",
        require=False,
        default=None,
        validate=validators.Match("action_params", r"^\{.*\}$"),
    )

    def _fetch_and_validate_health_response(self, session, headers, root_url):
        """
        Helper method to fetch and validate SOAR health endpoint response.
        
        Args:
            session: requests.Session object
            headers: HTTP headers dict
            root_url: Base URL for the REST endpoint
        
        Returns:
            dict: Validated response_soar dict
        
        Raises:
            Exception: If API call fails or response is invalid
        """
        target_url = f"{root_url}/soar_get_endpoint"
        data = {"soar_server": self.soar_server, "endpoint": "health"}
        
        response = session.post(
            target_url, headers=headers, verify=False, data=json.dumps(data)
        )
        
        if response.status_code != 200:
            error_msg = (
                f'request has failed, response.status_code="{response.status_code}", '
                f'response.text="{response.text}"'
            )
            logging.error(error_msg)
            raise Exception(error_msg)
        
        try:
            response_json = response.json()
            response_soar = response_json.get("response")
            logging.debug(f'response_soar="{json.dumps(response_soar)}"')
            
            # Validate response_soar is a dict, not a string
            if not isinstance(response_soar, dict):
                error_msg = (
                    f'Unexpected health response type, expected dict but got {type(response_soar).__name__}, '
                    f'response_soar="{str(response_soar)[:200]}"'
                )
                logging.error(error_msg)
                raise ValueError(error_msg)
            
            return response_soar
            
        except (json.JSONDecodeError, ValueError, TypeError, AttributeError) as e:
            error_msg = (
                f'Error parsing SOAR health response, exception="{str(e)}", '
                f'response_text="{response.text[:200]}"'
            )
            logging.error(error_msg)
            raise Exception(error_msg)

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get the session key
        session_key = self._metadata.searchinfo.session_key

        # Build header and target
        header = f"Splunk {session_key}"
        root_url = f"{reqinfo['server_rest_uri']}/services/trackme/v2/splk_soar"

        # Set HTTP headers
        headers = {"Authorization": header}
        headers["Content-Type"] = "application/json"

        # load action_data, if any
        if self.action_data:
            if not isinstance(self.action_data, dict):
                try:
                    # Try parsing as standard JSON (with double quotes)
                    action_data = json.loads(self.action_data)
                except ValueError:
                    # If it fails, try parsing with ast.literal_eval (supports single quotes)
                    action_data = literal_eval(self.action_data)
        else:
            action_data = None

        # load action_params, if any
        if self.action_params:
            if not isinstance(self.action_params, dict):
                try:
                    # Try parsing as standard JSON (with double quotes)
                    action_params = json.loads(self.action_params)
                except ValueError:
                    # If it fails, try parsing with ast.literal_eval (supports single quotes)
                    action_params = literal_eval(self.action_params)
        else:
            action_params = None

        # Set session and proceed
        with requests.Session() as session:
            #
            # Active SOAR test apps connectivity
            #

            if self.action == "soar_test_apps":
                target_url = f"{root_url}/admin/soar_test_assets"

                if not action_data:
                    active_check = "True"
                    assets_allow_list = "None"
                    assets_block_list = "None"
                else:
                    # active check, if defined, otherwise defaults to True
                    active_check = action_data.get("active_check", "True")

                    # get assets_allow_list, if any
                    assets_allow_list = action_data.get("assets_allow_list", "None")

                    # get assets_block_list, if any
                    assets_block_list = action_data.get("assets_block_list", "None")

                data = {
                    "soar_server": self.soar_server,
                    "active_check": active_check,
                    "assets_allow_list": assets_allow_list,
                    "assets_block_list": assets_block_list,
                }

                response = session.post(
                    target_url, headers=headers, verify=False, data=json.dumps(data)
                )

                if response.status_code == 200:  # we strictly expect a 200 HTTP code
                    response_json = response.json()  # our response is always json
                    response_soar = response_json.get(
                        "response"
                    )  # get response inside response
                    logging.debug(
                        f'response_soar="{json.dumps(response_soar)}"'
                    )  # debug

                    for el in response_soar:  # loop and parse
                        yield {
                            "_time": el.get("mtime_epoch"),
                            "_raw": el,
                            "id": el.get("id"),
                            "message": el.get("message"),
                            "time": el.get("mtime_human"),
                            "name": el.get("name"),
                            "status": el.get("status"),
                            "type": el.get("type"),
                        }

                else:
                    error_msg = f'request has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    logging.error(error_msg)
                    yield {
                        "_time": time.time(),
                        "_raw": {
                            "action": "failed",
                            "response": response.text,
                            "http_status_code": response.status_code,
                        },
                        "action": "failed",
                        "response": response.text,
                        "http_status_code": response.status_code,
                    }

            #
            # SOAR health services status
            #

            elif self.action == "soar_health_status":
                try:
                    # Use helper method to fetch and validate health response
                    response_soar = self._fetch_and_validate_health_response(session, headers, root_url)
                    
                    # Extract and render health services status
                    health_status = response_soar.get("status")

                    # Validate health_status is not None and is iterable (dict or list)
                    if health_status is None:
                        error_msg = (
                            f'Missing "status" field in SOAR health response, '
                            f'response_soar keys: {list(response_soar.keys())}'
                        )
                        logging.error(error_msg)
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "action": "failed",
                                "error": error_msg,
                                "response": str(response_soar),
                            },
                            "action": "failed",
                            "error": error_msg,
                        }
                    elif not isinstance(health_status, (dict, list)):
                        error_msg = (
                            f'Unexpected "status" type, expected dict or list but got {type(health_status).__name__}, '
                            f'health_status="{str(health_status)[:200]}"'
                        )
                        logging.error(error_msg)
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "action": "failed",
                                "error": error_msg,
                                "response": str(health_status),
                            },
                            "action": "failed",
                            "error": error_msg,
                        }
                    else:
                        # health_status is valid, iterate over it
                        if isinstance(health_status, dict):
                            # If it's a dict, iterate over keys
                            for el in health_status:
                                yield {
                                    "_time": time.time(),
                                    "_raw": {el: health_status.get(el)},
                                    "service": el,
                                    "status": health_status.get(el),
                                }
                        elif isinstance(health_status, list):
                            # If it's a list, iterate over elements
                            for el in health_status:
                                if isinstance(el, dict):
                                    # If element is a dict, use its structure directly
                                    yield {
                                        "_time": time.time(),
                                        "_raw": el,
                                        "service": el.get("service", "unknown"),
                                        "status": el.get("status", "unknown"),
                                    }
                                else:
                                    # If element is a primitive type, use it as-is
                                    yield {
                                        "_time": time.time(),
                                        "_raw": {"value": el},
                                        "service": str(el),
                                        "status": str(el),
                                    }
                except Exception as e:
                    error_msg = (
                        f'Error processing SOAR health_status, exception="{str(e)}"'
                    )
                    logging.error(error_msg)
                    yield {
                        "_time": time.time(),
                        "_raw": {
                            "action": "failed",
                            "error": error_msg,
                            "exception": str(e),
                        },
                        "action": "failed",
                        "error": error_msg,
                    }

            #
            # SOAR health memory usage
            #

            elif self.action == "soar_health_memory":
                try:
                    # Use helper method to fetch and validate health response
                    response_soar = self._fetch_and_validate_health_response(session, headers, root_url)
                    
                    # Extract and render health memory data
                    health_memory = response_soar.get("memory_data")

                    # Validate health_memory is not None and is a list
                    if health_memory is None:
                        error_msg = (
                            f'Missing "memory_data" field in SOAR health response, '
                            f'response_soar keys: {list(response_soar.keys())}'
                        )
                        logging.error(error_msg)
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "action": "failed",
                                "error": error_msg,
                                "response": str(response_soar),
                            },
                            "action": "failed",
                            "error": error_msg,
                        }
                    elif not isinstance(health_memory, list):
                        error_msg = (
                            f'Unexpected "memory_data" type, expected list but got {type(health_memory).__name__}, '
                            f'health_memory="{str(health_memory)[:200]}"'
                        )
                        logging.error(error_msg)
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "action": "failed",
                                "error": error_msg,
                                "response": str(health_memory),
                            },
                            "action": "failed",
                            "error": error_msg,
                        }
                    else:
                        # health_memory is valid, process it
                        mem_free = None
                        mem_used = None
                        mem_cached = None

                        for el in health_memory:  # this is a list
                            if isinstance(el, dict):
                                # Don't use default value - preserve None to detect missing values
                                # Only convert to int if value exists, otherwise leave as None
                                label = el.get("label")
                                value = el.get("value")  # No default - returns None if missing
                                
                                if label == "Free" and value is not None:
                                    mem_free = int(value)
                                elif label == "Used" and value is not None:
                                    mem_used = int(value)
                                elif label == "Cached" and value is not None:
                                    mem_cached = int(value)

                        # Validate we got the required values
                        # This check now correctly detects missing values (None) vs zero values (0)
                        if mem_free is None or mem_used is None:
                            error_msg = (
                                f'Missing required memory data fields (Free or Used), '
                                f'mem_free={mem_free}, mem_used={mem_used}, mem_cached={mem_cached}'
                            )
                            logging.error(error_msg)
                            yield {
                                "_time": time.time(),
                                "_raw": {
                                    "action": "failed",
                                    "error": error_msg,
                                    "health_memory": health_memory,
                                },
                                "action": "failed",
                                "error": error_msg,
                            }
                        else:
                            # we can calculate things!
                            mem_cached = mem_cached if mem_cached is not None else 0
                            mem_total = mem_used + mem_free
                            mem_used_pct = round(mem_used / mem_total * 100, 2) if mem_total > 0 else 0
                            mem_cached_pct = round(mem_cached / mem_total * 100, 2) if mem_total > 0 else 0

                            mem_summary = {
                                "mem_free": mem_free,
                                "mem_used": mem_used,
                                "mem_cached": mem_cached,
                                "mem_used_pct": mem_used_pct,
                                "mem_cached_pct": mem_cached_pct,
                            }

                            yield {
                                "_time": time.time(),
                                "_raw": mem_summary,
                                "mem_free": mem_free,
                                "mem_used": mem_used,
                                "mem_cached": mem_cached,
                                "mem_used_pct": mem_used_pct,
                                "mem_cached_pct": mem_cached_pct,
                            }
                except Exception as e:
                    error_msg = (
                        f'Error processing SOAR health_memory, exception="{str(e)}"'
                    )
                    logging.error(error_msg)
                    yield {
                        "_time": time.time(),
                        "_raw": {
                            "action": "failed",
                            "error": error_msg,
                            "exception": str(e),
                        },
                        "action": "failed",
                        "error": error_msg,
                    }

            #
            # SOAR health cpu load
            #

            elif self.action == "soar_health_load":
                try:
                    # Use helper method to fetch and validate health response
                    response_soar = self._fetch_and_validate_health_response(session, headers, root_url)
                    
                    # Extract and render health load data
                    health_load = response_soar.get("load_data")

                    # Validate health_load is not None and is a list
                    if health_load is None:
                        error_msg = (
                            f'Missing "load_data" field in SOAR health response, '
                            f'response_soar keys: {list(response_soar.keys())}'
                        )
                        logging.error(error_msg)
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "action": "failed",
                                "error": error_msg,
                                "response": str(response_soar),
                            },
                            "action": "failed",
                            "error": error_msg,
                        }
                    elif not isinstance(health_load, list):
                        error_msg = (
                            f'Unexpected "load_data" type, expected list but got {type(health_load).__name__}, '
                            f'health_load="{str(health_load)[:200]}"'
                        )
                        logging.error(error_msg)
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "action": "failed",
                                "error": error_msg,
                                "response": str(health_load),
                            },
                            "action": "failed",
                            "error": error_msg,
                        }
                    else:
                        # health_load is valid, process it
                        load_summary = {}
                        count = 0

                        for el in health_load:  # this is a list, load come in order from 1 to 15min
                            if isinstance(el, dict):
                                count += 1
                                load_value = el.get("load")
                                if count == 1:
                                    load_summary["load_1min"] = load_value
                                if count == 2:
                                    load_summary["load_5min"] = load_value
                                if count == 3:
                                    load_summary["load_15min"] = load_value

                        yield {
                            "_time": time.time(),
                            "_raw": load_summary,
                            "load_1min": load_summary.get("load_1min"),
                            "load_5min": load_summary.get("load_5min"),
                            "load_15min": load_summary.get("load_15min"),
                        }
                except Exception as e:
                    error_msg = (
                        f'Error processing SOAR health_load, exception="{str(e)}"'
                    )
                    logging.error(error_msg)
                    yield {
                        "_time": time.time(),
                        "_raw": {
                            "action": "failed",
                            "error": error_msg,
                            "exception": str(e),
                        },
                        "action": "failed",
                        "error": error_msg,
                    }

            #
            # get query against a SOAR endpoint
            #

            elif self.action == "soar_get":
                target_url = f"{root_url}/soar_get_endpoint"

                data = {
                    "soar_server": self.soar_server,
                    "endpoint": action_data.get("endpoint"),
                }

                # if extra params are provided, add them to the data
                if action_params:
                    data["params"] = action_params

                response = session.post(
                    target_url, headers=headers, verify=False, data=json.dumps(data)
                )

                if response.status_code == 200:  # we strictly expect a 200 HTTP code
                    response_json = response.json()  # our response is always json
                    response_soar = response_json.get(
                        "response"
                    )  # get response inside response
                    logging.debug(
                        f'response_soar="{json.dumps(response_soar)}"'
                    )  # debug

                    if isinstance(response_soar, dict):
                        yield {
                            "_time": time.time(),
                            "_raw": response_soar,
                        }

                    elif isinstance(response_soar, list):
                        if len(response_soar) > 0:  # if not an empty list
                            for el in response_soar:  # this is a list
                                yield {
                                    "_time": time.time(),
                                    "_raw": el,
                                }
                        else:
                            yield {
                                "_time": time.time(),
                                "_raw": {
                                    "response": "REST API call was successful, but an empty response was received.",
                                    "response.status_code": response.status_code,
                                    "response.text": response.text,
                                },  # return index as key and element as value
                            }

                    else:  # something else
                        yield {
                            "_time": time.time(),
                            "_raw": response_soar,
                        }

                else:
                    error_msg = f'request has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    logging.error(error_msg)
                    yield {
                        "_time": time.time(),
                        "_raw": {
                            "action": "failed",
                            "response": response.text,
                            "http_status_code": response.status_code,
                        },
                        "action": "failed",
                        "response": response.text,
                        "http_status_code": response.status_code,
                    }

            #
            # post query against a SOAR endpoint
            #

            elif self.action == "soar_post":
                target_url = f"{root_url}/admin/soar_post_endpoint"

                data = {
                    "soar_server": self.soar_server,
                    "endpoint": action_data.get("endpoint"),
                    "data": action_data.get("data"),
                }

                # if extra params are provided, add them to the data
                if action_params:
                    data["params"] = action_params

                response = session.post(
                    target_url, headers=headers, verify=False, data=json.dumps(data)
                )

                if response.status_code == 200:  # we strictly expect a 200 HTTP code
                    response_json = response.json()  # our response is always json
                    response_soar = response_json.get(
                        "response"
                    )  # get response inside response
                    logging.debug(
                        f'response_soar="{json.dumps(response_soar)}"'
                    )  # debug

                    if isinstance(response_soar, list):  # if the response is a list
                        if len(response_soar) > 0:  # if response if not empty list
                            for idx, el in enumerate(
                                response_soar
                            ):  # enumerate to keep track of index
                                yield {
                                    "_time": time.time(),
                                    "_raw": {
                                        idx: el
                                    },  # return index as key and element as value
                                }
                        else:
                            yield {
                                "_time": time.time(),
                                "_raw": {
                                    "response": "REST API call was successful, but an empty response was received, this can be expected if there were no operations to be performed.",
                                    "response.status_code": response.status_code,
                                    "response.text": response.text,
                                },  # return index as key and element as value
                            }

                    elif isinstance(
                        response_soar, dict
                    ):  # if the response is a dictionary
                        yield {
                            "_time": time.time(),
                            "_raw": response_soar,
                        }
                    else:  # if the response is neither a list nor a dictionary
                        logging.error(
                            f"Unexpected response_soar type: {type(response_soar)}"
                        )

                else:
                    error_msg = f'request has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    logging.error(error_msg)
                    yield {
                        "_time": time.time(),
                        "_raw": {
                            "action": "failed",
                            "response": response.text,
                            "http_status_code": response.status_code,
                        },
                        "action": "failed",
                        "response": response.text,
                        "http_status_code": response.status_code,
                    }

            #
            # Automation Broker advanced management
            #

            elif self.action == "soar_automation_broker_manage":
                target_url = f"{root_url}/admin/soar_automation_broker_manage"

                data = {
                    "soar_server": self.soar_server,
                }

                # optional
                if action_data:
                    mode = action_data.get("mode", None)
                    if mode:
                        data["mode"] = mode

                    #
                    # pool definition
                    #

                    automation_brokers_pool_members = action_data.get(
                        "automation_brokers_pool_members", None
                    )
                    if automation_brokers_pool_members:
                        data["automation_brokers_pool_members"] = (
                            automation_brokers_pool_members
                        )

                    #
                    # active1/active2, these options are deprecated and left for compatibility purposes
                    #

                    automation_active1_broker_name = action_data.get(
                        "automation_active1_broker_name", None
                    )
                    if automation_active1_broker_name:
                        data["automation_active1_broker_name"] = (
                            automation_active1_broker_name
                        )

                    automation_active2_broker_name = action_data.get(
                        "automation_active2_broker_name", None
                    )
                    if automation_active2_broker_name:
                        data["automation_active2_broker_name"] = (
                            automation_active2_broker_name
                        )

                    assets_update_forbidden_fields = action_data.get(
                        "assets_update_forbidden_fields", None
                    )
                    if assets_update_forbidden_fields:
                        data["assets_update_forbidden_fields"] = (
                            assets_update_forbidden_fields
                        )

                    assets_update_forbidden_fields_extra = action_data.get(
                        "assets_update_forbidden_fields_extra", None
                    )
                    if assets_update_forbidden_fields_extra:
                        data["assets_update_forbidden_fields_extra"] = (
                            assets_update_forbidden_fields_extra
                        )

                    # Forward only when the key is explicitly set in action_data so an
                    # operator passing False (to disable schema detection) is honoured.
                    if "enable_app_schema_secret_detection" in action_data:
                        data["enable_app_schema_secret_detection"] = action_data[
                            "enable_app_schema_secret_detection"
                        ]

                response = session.post(
                    target_url, headers=headers, verify=False, data=json.dumps(data)
                )

                if response.status_code == 200:  # we strictly expect a 200 HTTP code
                    response_json = response.json()  # our response is always json
                    response_soar = response_json.get(
                        "response"
                    )  # get response inside response
                    logging.debug(
                        f'response_soar="{json.dumps(response_soar)}"'
                    )  # debug

                    if isinstance(response_soar, list):  # if the response is a list
                        if len(response_soar) > 0:  # if response if not empty list
                            for el in response_soar:
                                yield {
                                    "_time": time.time(),
                                    "_raw": el,
                                }
                        else:
                            yield {
                                "_time": time.time(),
                                "_raw": {
                                    "response": "REST API call was successful, but an empty response was received, this can be expected if there were no operations to be performed.",
                                    "response.status_code": response.status_code,
                                    "response.text": response.text,
                                },  # return index as key and element as value
                            }

                    elif isinstance(
                        response_soar, dict
                    ):  # if the response is a dictionary
                        yield {
                            "_time": time.time(),
                            "_raw": response_soar,
                        }
                    else:  # if the response is neither a list nor a dictionary
                        logging.error(
                            f"Unexpected response_soar type: {type(response_soar)}"
                        )

                else:
                    error_msg = f'request has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    logging.error(error_msg)
                    yield {
                        "_time": time.time(),
                        "_raw": {
                            "action": "failed",
                            "response": response.text,
                            "http_status_code": response.status_code,
                        },
                        "action": "failed",
                        "response": response.text,
                        "http_status_code": response.status_code,
                    }

            #
            # Playbook status
            #

            elif self.action == "soar_playbook_status":
                from datetime import datetime, timedelta, timezone

                target_url = f"{root_url}/soar_get_endpoint"

                # Set default page_size
                page_size = 1000
                # Override page_size if specified in action_params
                if action_params and "page_size" in action_params:
                    try:
                        page_size = int(action_params.get("page_size"))
                        logging.debug(f"Using custom page_size: {page_size}")
                    except (ValueError, TypeError) as e:
                        logging.error(
                            f"Invalid page_size value in action_params: {str(e)}"
                        )
                        # Keep default page_size if invalid value provided

                # Set default max_age_sec
                max_age_sec = 300
                # Override max_age_sec if specified in action_params
                if action_params and "max_age_sec" in action_params:
                    try:
                        max_age_sec = int(action_params.get("max_age_sec"))
                        logging.debug(f"Using custom max_age_sec: {max_age_sec}")
                    except (ValueError, TypeError) as e:
                        logging.error(
                            f"Invalid max_age_sec value in action_params: {str(e)}"
                        )
                        # Keep default max_age_sec if invalid value provided
                # define cutoff time
                cutoff_time = datetime.now(timezone.utc) - timedelta(
                    seconds=max_age_sec
                )
                filter_update_time_gt = (
                    f"\"{cutoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')}\""
                )
                logging.info(
                    f"Applying max_age_sec filter: update_time > {filter_update_time_gt}"
                )

                # init page
                page = 0

                # Start with known statuses
                known_statuses = [
                    "success",
                    "failed",
                    "running",
                    "pending",
                    "cancelled",
                    "waiting",
                ]
                status_summary = {status: 0 for status in known_statuses}

                # process loop
                while True:
                    params = {"page_size": page_size, "page": page}
                    if filter_update_time_gt:
                        params["_filter_update_time__gt"] = filter_update_time_gt

                    data = {
                        "soar_server": self.soar_server,
                        "endpoint": "playbook_run",
                        "params": params,
                    }

                    response = session.post(
                        target_url, headers=headers, verify=False, data=json.dumps(data)
                    )

                    if response.status_code != 200:
                        logging.error(
                            f"Playbook run fetch failed on page {page}: {response.status_code}, {response.text}"
                        )
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "action": "failed",
                                "response": response.text,
                                "http_status_code": response.status_code,
                            },
                            "action": "failed",
                            "response": response.text,
                            "http_status_code": response.status_code,
                        }
                        return

                    response_json = response.json()
                    response_data = response_json.get("response", [])

                    if not isinstance(response_data, list):
                        logging.error(
                            f"Unexpected response format: {type(response_data)}"
                        )
                        yield {
                            "_time": time.time(),
                            "_raw": {
                                "action": "failed",
                                "response": response_json,
                                "error": "Unexpected response structure (not a list)",
                            },
                        }
                        return

                    if not response_data:
                        break  # No more data

                    for pb in response_data:
                        status = pb.get("status", "unknown")
                        if status not in status_summary:
                            status_summary[status] = 0  # Dynamically track unknowns
                        status_summary[status] += 1

                    if len(response_data) < page_size:
                        break
                    page += 1

                yield {"_time": time.time(), "_raw": status_summary, **status_summary}

        # Log the run time
        logging.info(
            f"trackmesoar has terminated, run_time={round(time.time() - start, 3)}"
        )


dispatch(TrackMeRestHandler, sys.argv, sys.stdin, sys.stdout, __name__)

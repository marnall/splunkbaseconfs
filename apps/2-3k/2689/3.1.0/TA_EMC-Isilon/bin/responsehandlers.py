from __future__ import print_function

# add your custom response handler class to this module
from builtins import str
from builtins import range
from builtins import object
import json
import traceback
import datetime
import re
import sys
import const

SPLUNK_INGESTION_MESSAGE = "message=ingested_event_count | Successfully ingested {} events into Splunk."


class IsilonEventResponseHandler(object):
    """Class for managing data ingestion to Splunk."""

    def __init__(self):
        """Isilon Event Response Handler."""
        pass

    def __call__(
        self, raw_response_output, response_type, node, endpoint, ew, helper, index, logger
    ):
        """Parses the JSON response."""
        try:
            output = json.loads(raw_response_output)
            json_type = type(output)
            if json_type == list:
                output = self._parse_json_list(
                    node, endpoint, output, ew, helper, index, logger
                )
            if json_type == dict:
                output = self._parse_json_dict(
                    node, endpoint, output, ew, helper, index, logger
                )
        except Exception:
            logger.error("message=error_while_processing |"
                         " Error occured while processing data for ingestion in Splunk.\n{}"
                         .format(traceback.format_exc()))

    # Parse JSON Response - Dictionary objects
    def _parse_json_dict(self, node, path, response_json, ew, helper, index, logger):
        """Parses the dictionary response and ingests data into Splunk."""
        logger.debug("message=data_ingestion_details | Ingesting data into Splunk.")
        count = 0
        listdataKeys = list(response_json.keys())
        currentTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
        for j in range(len(listdataKeys)):
            if listdataKeys[j] == "eventlists":
                for element in response_json[listdataKeys[j]]:
                    event_element = element.get("events", None)
                    response_event_json = {}
                    for event in event_element:
                        response_event_json = {
                            "events": event,
                            "timestamp": currentTime,
                            "node": node,
                            "namespace": "event",
                        }
                        event = helper.new_event(
                            index=index,
                            sourcetype=const.SOURCETYPE,
                            data=json.dumps(response_event_json),
                        )
                        ew.write_event(event)
                        count = count + 1
        if count != 0:
            logger.info(SPLUNK_INGESTION_MESSAGE.format(count))


class IsilonResponseHandler(object):
    """Class for managing data ingestion to Splunk."""

    def __init__(self):
        """Isilon Response Handler."""
        pass

    def __call__(
        self, raw_response_output, response_type, node, endpoint, ew, helper, index, logger
    ):
        """Parses the JSON response."""
        try:
            namespace = self._get_namespace(endpoint, logger)
            output = json.loads(raw_response_output)
            json_type = type(output)
            if json_type == list:
                output = self._parse_json_list(node, endpoint, output, namespace, ew, helper, index, logger)
            if json_type == dict:
                output = self._parse_json_dict(node, endpoint, output, namespace, ew, helper, index, logger)
        except Exception:
            logger.error("message=error_while_processing |"
                         " Error occured while processing data for ingestion in Splunk.\n{}"
                         .format(traceback.format_exc()))

    # Gets namespace from the path

    def _get_namespace(self, path, logger):
        """Returns namespace from the path."""
        logger.debug("message=get_namespace | Getting namespace for endpoint - '{}'".format(path))
        regex_obj = re.search(r"""\/platform\/\d+\/(\w+)(\/\w+)?""", path, re.I)
        namespace = None
        if regex_obj:
            namespace = regex_obj.group(1)
            logger.debug("message=namespace_value | Namespace is '{}'.".format(namespace))
        else:
            logger.error(
                "message=namespace_error | Not able to get namespace for path = {}".format(str(path))
            )
        return namespace

    # Parse JSON Response -  List

    def _parse_json_list(self, node, path, response_json, namespace, ew, helper, index, logger):
        """Parses the list response and ingests data into Splunk."""
        logger.debug("message=data_ingestion_details | Ingesting data into Splunk.")
        count = 0
        currentTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
        path = path.split("/platform")
        path = "/platform" + path[1] if path and len(path) > 0 else None
        if path == "/platform/1/cluster/external-ips":
            array_length = len(response_json)
            for j in range(array_length):
                response_dict = {
                    "timestamp": currentTime,
                    "devId": j + 1,
                    "ipAddress": response_json[j],
                    "node": node,
                    "namespace": namespace,
                }
                event = helper.new_event(
                    index=index,
                    sourcetype=const.SOURCETYPE,
                    data=json.dumps(response_dict),
                )
                ew.write_event(event)
                count = count + 1
        else:
            event = helper.new_event(
                index=index,
                sourcetype=const.SOURCETYPE,
                data=json.dumps(response_json),
            )
            ew.write_event(event)
            count = count + 1
        if count != 0:
            logger.info(SPLUNK_INGESTION_MESSAGE.format(count))

    # Parse JSON Response - Dictionary objects
    def _parse_json_dict(self, node, path, response_json, namespace, ew, helper, index, logger):
        """Parses the dictionary response and ingests data into Splunk."""
        logger.debug("message=data_ingestion_details | Ingesting data into Splunk.")
        count = 0
        dataKeys = list(response_json.keys())
        response_dict = {}
        currentTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
        if namespace in [
            "statistics",
            "shares",
            "storagepool",
            "protocols",
            "zones",
            "event",
            "license",
            "auth",
        ]:
            for i in range(len(dataKeys)):
                if dataKeys[i] != "resume":
                    key = response_json[dataKeys[i]]
                    check_type = type(key)
                    if check_type != list:
                        response_dict = {
                            "timestamp": currentTime,
                            dataKeys[i]: (response_json[dataKeys[i]]),
                            "node": node,
                            "namespace": namespace,
                        }
                        event = helper.new_event(
                            index=index,
                            sourcetype=const.SOURCETYPE,
                            data=json.dumps(response_dict),
                        )
                        ew.write_event(event)
                        count = count + 1

                    if check_type == list:
                        array_length = len(response_json[dataKeys[i]])
                        for j in range(array_length):
                            response_dict = {
                                "timestamp": currentTime,
                                dataKeys[i]: (response_json[dataKeys[i]])[j],
                                "node": node,
                                "namespace": namespace,
                            }
                            event = helper.new_event(
                                index=index,
                                sourcetype=const.SOURCETYPE,
                                data=json.dumps(response_dict),
                            )
                            ew.write_event(event)
                            count = count + 1
        else:
            response_json["timestamp"] = currentTime
            response_json["node"] = node
            response_json["namespace"] = namespace
            event = helper.new_event(
                index=index,
                sourcetype=const.SOURCETYPE,
                data=json.dumps(response_json),
            )
            ew.write_event(event)
            count = count + 1
        if count != 0:
            logger.info(SPLUNK_INGESTION_MESSAGE.format(count))


def _decode_list(data):
    """Decodes the values present in list."""
    rv = []
    for item in data:
        if isinstance(item, str) and sys.version_info[0] < 3:
            item = item.encode("utf-8")
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv


def _decode_dict(data):
    """Decodes the values present in dictionary."""
    rv = {}
    for key, value in data.items():
        if isinstance(key, str) and sys.version_info[0] < 3:
            key = key.encode("utf-8")
        if isinstance(value, str) and sys.version_info[0] < 3:
            value = value.encode("utf-8")
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv

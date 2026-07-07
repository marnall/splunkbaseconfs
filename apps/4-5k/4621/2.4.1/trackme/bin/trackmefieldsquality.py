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

import os
import sys
import time
from datetime import datetime, timezone
import json
import logging
import re
from logging.handlers import RotatingFileHandler
import urllib3
import hashlib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_trackmefieldsquality.log" % splunkhome,
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

# import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

# import trackme libs
from trackme_libs import (
    trackme_reqinfo,
    run_splunk_search,
)

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces, strict_interpret_boolean


@Configuration(distributed=False)
class TrackMeFieldsQuality(StreamingCommand):

    fields_to_check_list = Option(
        doc="""
        **Syntax:** **fields_to_check_list=****
        **Description:** The list of fields to verified, provided as an argument to the command in a comma separated list.""",
        require=False,
        default=None,
        validate=validators.Match("fields_to_check_list", r"^.*$"),
    )

    fields_to_check_search_command = Option(
        doc="""
        **Syntax:** **fields_to_check_search_command=****
        **Description:** The search command to use to generate the dictionary of fields to check.""",
        require=False,
        default=None,
        validate=validators.Match("fields_to_check_search_command", r"^.*$"),
    )

    fields_to_check_fieldname = Option(
        doc="""
        **Syntax:** **fields_to_check_fieldname=****
        **Description:** Alternatively, the name of the field containing the list of fields to check, provided in a comma separated list.""",
        require=False,
        default=None,
        validate=validators.Match("fields_to_check_fieldname", r"^.*$"),
    )

    fields_to_check_dict = Option(
        doc="""
        **Syntax:** **fields_to_check_dict=****
        **Description:** A JSON string containing a dictionary of fields to check with optional regex patterns and validation settings.
        Example: {"field1": {"name": "field1", "regex": "^[A-Z]+$", "allow_unknown": true, "allow_empty_or_missing": false}, "field2": {"name": "field2"}}""",
        require=False,
        default=None,
        validate=validators.Match("fields_to_check_dict", r"^.*$"),
    )

    fields_to_check_dict_path = Option(
        doc="""
        **Syntax:** **fields_to_check_dict_path=****
        **Description:** Path to a JSON file containing a dictionary of fields to check with optional regex patterns and validation settings.
        Example: $SPLUNK_HOME/etc/apps/trackme/lookups/fields_config.json""",
        require=False,
        default=None,
        validate=validators.Match("fields_to_check_dict_path", r"^.*$"),
    )

    fields_to_check_dict_fieldname = Option(
        doc="""
        **Syntax:** **fields_to_check_dict_fieldname=****
        **Description:** The name of the field containing a JSON string with a dictionary of fields to check with optional regex patterns and validation settings.
        """,
        require=False,
        default=None,
        validate=validators.Match("fields_to_check_dict_fieldname", r"^.*$"),
    )

    include_field_values = Option(
        doc="""
        **Syntax:** **include_field_values=****
        **Description:** Boolean option to include field values in the JSON summary.
        """,
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    pretty_print_json = Option(
        doc="""
        **Syntax:** **pretty_print_json=****
        **Description:** Boolean option to pretty print the JSON summary. Default is True.
        """,
        require=False,
        default=True,
        validate=validators.Boolean(),
    )

    output_mode = Option(
        doc="""
        **Syntax:** **output_mode=****
        **Description:** The mode to output the results. Default is json, valid options are json and raw.
        """,
        require=False,
        default="json",
        validate=validators.Match("output_mode", r"^json|raw$"),
    )

    metadata_fields = Option(
        doc="""
        **Syntax:** **metadata_fields=****
        **Description:** A CSV list of metadata fields to include in the metadata section of the JSON when using output_mode=json. index/sourcetype/host/source are always included, you can add others to be included in the metadata section.
        """,
        require=False,
        default="index,sourcetype,host,source",
        validate=validators.Match("metadata_fields", r"^.*$"),
    )

    summary_fieldname = Option(
        doc="""
        **Syntax:** **summary_fieldname=****
        **Description:** Defines the name of the summary field. Default is 'summary'.
        """,
        require=False,
        default="summary",
        validate=validators.Match("summary_fieldname", r"^.*$"),
    )

    metadata_fieldname = Option(
        doc="""
        **Syntax:** **metadata_fieldname=****
        **Description:** Defines the name of the metadata field added to the summary JSON. Default is 'metadata'.
        """,
        require=False,
        default="metadata",
        validate=validators.Match("metadata_fieldname", r"^.*$"),
    )

    # status will be statically defined as imported

    def stream(self, records):

        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # check license state
        try:
            check_license = trackme_check_license(
                reqinfo["server_rest_uri"], self._metadata.searchinfo.session_key
            )
            license_is_valid = check_license.get("license_is_valid")
            logging.debug(
                f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
            )

        except Exception as e:
            license_is_valid = 0
            logging.error(f'function check_license exception="{str(e)}"')

        # check restricted components
        if license_is_valid != 1:
            logging.error(
                f'The requested component is restricted to the Full and Trial edition mode, its execution cannot be accepted, check_license="{json.dumps(check_license, indent=2)}"'
            )
            raise Exception(
                f"The requested component is restricted to the Full and Trial edition mode, its execution cannot be accepted, please contact your Splunk administrator."
            )

        # either fields_to_check_list or fields_to_check_fieldname must be provided, but not both
        if (
            sum(
                1
                for x in [
                    self.fields_to_check_list,
                    self.fields_to_check_fieldname,
                    self.fields_to_check_dict,
                    self.fields_to_check_dict_path,
                    self.fields_to_check_dict_fieldname,
                    self.fields_to_check_search_command,
                ]
                if x
            )
            > 1
        ):
            raise ValueError(
                "Only one of fields_to_check_list, fields_to_check_fieldname, fields_to_check_dict, fields_to_check_dict_path, fields_to_check_dict_fieldname or fields_to_check_search_command can be provided"
            )

        # if fields_to_check_search_command is provided, run the search command, load the json_dict field from the results and use it as the fields_to_check_dict
        json_dict = None
        if self.fields_to_check_search_command:
            try:
                reader = run_splunk_search(
                    self.service,
                    remove_leading_spaces(self.fields_to_check_search_command),
                    {
                        "earliest_time": "-5m",
                        "latest_time": "now",
                        "preview": "false",
                        "output_mode": "json",
                        "count": 0,
                    },
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):

                        # raise an exception if the json_dict field is not present
                        if "json_dict" not in item:
                            raise ValueError(
                                f"json_dict field not found in the search results for search command: {self.fields_to_check_search_command}"
                            )

                        # load the json_dict field
                        json_dict = json.loads(item["json_dict"])

                        # only one result is expected
                        break

            except Exception as e:
                error_msg = f'context="error", trackmefieldsquality has failed with exception="{str(e)}"'
                logging.error(error_msg)
                raise Exception(error_msg)

        # Loop in the results
        records_count = 0
        for record in records:
            records_count += 1

            yield_record = {}
            json_summary = {"time": float(record.get("_time", time.time()))}

            # Get the list of fields from fields_to_check_list
            if self.fields_to_check_list:
                fields_to_check = self.fields_to_check_list.split(",")
                fields_dict = {
                    field.strip(): {"name": field.strip()} for field in fields_to_check
                }

            # Get the list of fields from fields_to_check_fieldname
            elif self.fields_to_check_fieldname:
                fields_to_check = record.get(self.fields_to_check_fieldname)
                # check if fields_to_check is a list, if so keep the first item only
                if isinstance(fields_to_check, list):
                    fields_to_check = fields_to_check[0]
                fields_to_check = fields_to_check.split(",")
                fields_dict = {
                    field.strip(): {"name": field.strip()} for field in fields_to_check
                }

            # Get fields from fields_to_check_dict
            elif self.fields_to_check_dict:
                try:
                    fields_dict = json.loads(self.fields_to_check_dict)
                    # Validate the structure
                    for field_name, field_info in fields_dict.items():
                        if not isinstance(field_info, dict):
                            raise ValueError(f"Field {field_name} must be a dictionary")
                        if "name" not in field_info:
                            raise ValueError(
                                f"Field {field_name} must have a 'name' property"
                            )
                        if not isinstance(field_info["name"], str):
                            raise ValueError(
                                f"Field {field_name} name must be a string"
                            )
                        if "regex" in field_info and not isinstance(
                            field_info["regex"], str
                        ):
                            raise ValueError(
                                f"Field {field_name} regex must be a string if provided"
                            )
                except json.JSONDecodeError:
                    raise ValueError(
                        f"Invalid JSON format in fields_to_check_dict: {self.fields_to_check_dict}"
                    )

            # Get fields from fields_to_check_dict_path
            elif self.fields_to_check_dict_path:
                try:
                    # Handle relative paths from SPLUNK_HOME
                    if not os.path.isabs(self.fields_to_check_dict_path):
                        file_path = os.path.join(
                            splunkhome, self.fields_to_check_dict_path
                        )
                    else:
                        file_path = self.fields_to_check_dict_path

                    if not os.path.exists(file_path):
                        raise ValueError(f"JSON file not found: {file_path}")

                    with open(file_path, "r") as f:
                        fields_dict = json.load(f)

                    # Validate the structure
                    for field_name, field_info in fields_dict.items():
                        if not isinstance(field_info, dict):
                            raise ValueError(f"Field {field_name} must be a dictionary")
                        if "name" not in field_info:
                            raise ValueError(
                                f"Field {field_name} must have a 'name' property"
                            )
                        if not isinstance(field_info["name"], str):
                            raise ValueError(
                                f"Field {field_name} name must be a string"
                            )
                        if "regex" in field_info and not isinstance(
                            field_info["regex"], str
                        ):
                            raise ValueError(
                                f"Field {field_name} regex must be a string if provided"
                            )
                except json.JSONDecodeError:
                    raise ValueError(
                        f"Invalid JSON format in file: {self.fields_to_check_dict_path}"
                    )
                except IOError as e:
                    raise ValueError(f"Error reading JSON file: {str(e)}")

            # Get fields from fields_to_check_dict_fieldname
            elif self.fields_to_check_dict_fieldname:
                try:
                    json_string = record.get(self.fields_to_check_dict_fieldname)
                    # check if json_string is a list, if so keep the first item only
                    if isinstance(json_string, list):
                        json_string = json_string[0]
                    fields_dict = json.loads(json_string)
                    # Validate the structure
                    for field_name, field_info in fields_dict.items():
                        if not isinstance(field_info, dict):
                            raise ValueError(f"Field {field_name} must be a dictionary")
                        if "name" not in field_info:
                            raise ValueError(
                                f"Field {field_name} must have a 'name' property"
                            )
                        if not isinstance(field_info["name"], str):
                            raise ValueError(
                                f"Field {field_name} name must be a string"
                            )
                        if "regex" in field_info and not isinstance(
                            field_info["regex"], str
                        ):
                            raise ValueError(
                                f"Field {field_name} regex must be a string if provided"
                            )
                except json.JSONDecodeError:
                    raise ValueError(
                        f"Invalid JSON format in fields_to_check_dict_fieldname with field_name: {self.fields_to_check_dict_fieldname} and json_string: {json_string}"
                    )

            elif self.fields_to_check_search_command:
                fields_dict = json_dict

            else:
                fields_dict = {}

            # Initialize counters for summary
            total_fields_checked = 0
            total_fields_failed = 0
            total_fields_passed = 0
            list_fields_passed = []
            list_fields_failed = []

            # Check each field in the dictionary
            for field_info in fields_dict.values():
                field = field_info["name"]
                
                # Handle reserved fields by renaming them to orig_<field_name>
                # This prevents conflicts with internal reserved fields used for processing output
                reserved_fields = ["metadata", "event_id", "summary"]
                output_field_name = field
                if field in reserved_fields:
                    output_field_name = f"orig_{field}"
                    logging.info(f'context="reserved_field", field="{field}" renamed to "{output_field_name}"')
                
                regex_pattern = field_info.get("regex")
                allow_unknown = strict_interpret_boolean(field_info.get("allow_unknown", False))
                allow_empty_or_missing = strict_interpret_boolean(field_info.get("allow_empty_or_missing", False))
                field_value = record.get(field)
                total_fields_checked += 1

                # Initialize flags
                is_missing = field_value is None
                is_empty = False
                is_unknown = False
                regex_failure = False

                # Check if field is missing and allow_empty_or_missing is True
                if is_missing:
                    if allow_empty_or_missing:
                        field_summary = {
                            "status": "success",
                            "description": "Field does not exist but is allowed to be missing.",
                            "is_missing": is_missing,
                            "is_empty": is_empty,
                            "is_unknown": is_unknown,
                        }
                        if regex_pattern:
                            field_summary["regex_failure"] = regex_failure
                            field_summary["regex_expression"] = regex_pattern
                        if self.include_field_values:
                            field_summary["value"] = field_value
                        json_summary[output_field_name] = field_summary
                        total_fields_passed += 1
                        list_fields_passed.append(output_field_name)
                        continue
                    else:
                        reason = "does not exist"
                        field_summary = {
                            "status": "failure",
                            "description": f"Field {reason}.",
                            "is_missing": is_missing,
                            "is_empty": is_empty,
                            "is_unknown": is_unknown,
                        }
                        if regex_pattern:
                            field_summary["regex_failure"] = regex_failure
                            field_summary["regex_expression"] = regex_pattern
                        if self.include_field_values:
                            field_summary["value"] = field_value
                        json_summary[output_field_name] = field_summary
                        total_fields_failed += 1
                        list_fields_failed.append(output_field_name)
                        continue

                if isinstance(field_value, list):
                    # Check each item in the list
                    all_items_valid = True
                    for item in field_value:
                        if isinstance(item, str) and item.lower() == "unknown":
                            if not allow_unknown:
                                all_items_valid = False
                                reason = "contains 'unknown'"
                                is_unknown = True
                                break
                        elif regex_pattern and not re.match(regex_pattern, str(item)):
                            # If allow_unknown is True and the value is "unknown", override regex failure
                            if allow_unknown and isinstance(item, str) and item.lower() == "unknown":
                                continue
                            all_items_valid = False
                            reason = "one or more values in the list do not match the required pattern"
                            regex_failure = True
                            break

                    if not all_items_valid:
                        field_summary = {
                            "status": "failure",
                            "description": f"Field exists but {reason}.",
                            "is_missing": is_missing,
                            "is_empty": is_empty,
                            "is_unknown": is_unknown,
                        }
                        if regex_pattern:
                            field_summary["regex_failure"] = regex_failure
                            field_summary["regex_expression"] = regex_pattern
                        if self.include_field_values:
                            field_summary["value"] = field_value
                        json_summary[output_field_name] = field_summary
                        total_fields_failed += 1
                        list_fields_failed.append(output_field_name)
                        continue
                else:
                    # Original behavior for non-list values
                    if field_value == "":
                        if allow_empty_or_missing:
                            field_summary = {
                                "status": "success",
                                "description": "Field is empty but is allowed to be empty.",
                                "is_missing": is_missing,
                                "is_empty": True,
                                "is_unknown": is_unknown,
                            }
                            if regex_pattern:
                                field_summary["regex_failure"] = regex_failure
                                field_summary["regex_expression"] = regex_pattern
                            if self.include_field_values:
                                field_summary["value"] = field_value
                            json_summary[output_field_name] = field_summary
                            total_fields_passed += 1
                            list_fields_passed.append(output_field_name)
                            continue
                        else:
                            reason = "is empty"
                            is_empty = True
                            field_summary = {
                                "status": "failure",
                                "description": f"Field {reason}.",
                                "is_missing": is_missing,
                                "is_empty": is_empty,
                                "is_unknown": is_unknown,
                            }
                            if regex_pattern:
                                field_summary["regex_failure"] = regex_failure
                                field_summary["regex_expression"] = regex_pattern
                            if self.include_field_values:
                                field_summary["value"] = field_value
                            json_summary[output_field_name] = field_summary
                            total_fields_failed += 1
                            list_fields_failed.append(output_field_name)
                            continue
                    elif (
                        isinstance(field_value, str)
                        and field_value.lower() == "unknown"
                    ):
                        if not allow_unknown:
                            reason = "is 'unknown'"
                            is_unknown = True
                            field_summary = {
                                "status": "failure",
                                "description": f"Field {reason}.",
                                "is_missing": is_missing,
                                "is_empty": is_empty,
                                "is_unknown": is_unknown,
                            }
                            if regex_pattern:
                                field_summary["regex_failure"] = regex_failure
                                field_summary["regex_expression"] = regex_pattern
                            if self.include_field_values:
                                field_summary["value"] = field_value
                            json_summary[output_field_name] = field_summary
                            total_fields_failed += 1
                            list_fields_failed.append(output_field_name)
                            continue
                    elif regex_pattern and not re.match(
                        regex_pattern, str(field_value)
                    ):
                        # If allow_unknown is True and the value is "unknown", override regex failure
                        if allow_unknown and isinstance(field_value, str) and field_value.lower() == "unknown":
                            # This case should have been handled above, but just in case
                            pass
                        else:
                            reason = "value does not match the required pattern"
                            regex_failure = True
                            field_summary = {
                                "status": "failure",
                                "description": f"Field exists but {reason}.",
                                "is_missing": is_missing,
                                "is_empty": is_empty,
                                "is_unknown": is_unknown,
                                "regex_failure": regex_failure,
                                "regex_expression": regex_pattern,
                            }
                            if self.include_field_values:
                                field_summary["value"] = field_value
                            json_summary[output_field_name] = field_summary
                            total_fields_failed += 1
                            list_fields_failed.append(output_field_name)
                            continue

                # Mark as success if field exists, has a value, is not 'unknown', and regex matches (if specified)
                field_summary = {
                    "status": "success",
                    "description": "Field exists and is valid.",
                    "is_missing": is_missing,
                    "is_empty": is_empty,
                    "is_unknown": is_unknown,
                }
                if regex_pattern:
                    field_summary["regex_failure"] = regex_failure
                    field_summary["regex_expression"] = regex_pattern
                if self.include_field_values:
                    field_summary["value"] = field_value
                json_summary[output_field_name] = field_summary
                total_fields_passed += 1
                list_fields_passed.append(output_field_name)

            # Determine overall status
            overall_status = "success" if total_fields_failed == 0 else "failure"

            # Guard against an empty fields_dict (e.g. trackmefieldsqualitygendict
            # resolving to no fields for a non-CIM datamodel). Without fields to
            # evaluate there is nothing to fail on, so report 0% for both ratios.
            if total_fields_checked > 0:
                percentage_failed = round(
                    total_fields_failed / total_fields_checked * 100, 2
                )
                percentage_passed = round(
                    total_fields_passed / total_fields_checked * 100, 2
                )
            else:
                percentage_failed = 0
                percentage_passed = 0

            # Add summary to JSON
            json_summary[self.summary_fieldname] = {
                "overall_status": overall_status,
                "total_fields_checked": total_fields_checked,
                "total_fields_failed": total_fields_failed,
                "total_fields_passed": total_fields_checked - total_fields_failed,
                "percentage_failed": percentage_failed,
                "percentage_passed": percentage_passed,
                "list_fields_passed": list_fields_passed,
                "list_fields_failed": list_fields_failed,
            }

            # Modify the JSON dumping based on the pretty_print_json option
            indent_value = 4 if self.pretty_print_json else None
            yield_record["json_summary"] = json.dumps(json_summary, indent=indent_value)

            #
            # output_mode=raw
            #

            if self.output_mode == "raw":
                # for each key value in record, add to yield_record
                for k, v in record.items():
                    yield_record[k] = v

                # add an event_id as the sha256 hash of yield_record
                yield_record["event_id"] = hashlib.sha256(
                    json.dumps(json_summary).encode("utf-8")
                ).hexdigest()

                yield yield_record

            #
            # output_mode=json
            #

            elif self.output_mode == "json":

                metadata_json = {}

                # get event_time
                event_time = float(record.get("_time", time.time()))

                # add the _time (epoch) and the human readable (%c %Z) as time_human
                metadata_json["time_epoch"] = event_time
                metadata_json["time_human"] = datetime.fromtimestamp(
                    event_time,
                    tz=timezone.utc,
                ).strftime("%c %Z")

                # always add index, sourcetype, host, source to the metadata field
                metadata_json["index"] = record.get("index")
                metadata_json["sourcetype"] = record.get("sourcetype")
                metadata_json["host"] = record.get("host")
                metadata_json["source"] = record.get("source")

                #
                # output_mode=json

                # handle metadata_fields
                if self.metadata_fields:
                    metadata_fields_list = self.metadata_fields.split(",")
                    for field in metadata_fields_list:
                        field = field.strip()
                        if field in record and field != "json_summary":
                            metadata_json[field] = record[field]

                # Add the metadata to the json_summary
                json_summary[self.metadata_fieldname] = metadata_json
                event_id = hashlib.sha256(
                    json.dumps(json_summary).encode("utf-8")
                ).hexdigest()
                json_summary["event_id"] = event_id

                # init yield_record
                yield_record = {}

                # handle the yield record
                yield_record["_time"] = event_time
                yield_record["_raw"] = json_summary
                yield_record["json_summary"] = json_summary

                # always add index, sourcetype, host, source to the main results
                yield_record["index"] = record.get("index")
                yield_record["sourcetype"] = record.get("sourcetype")
                yield_record["host"] = record.get("host")
                yield_record["source"] = record.get("source")

                # finally yield the record
                yield yield_record

        # Log the run time
        logging.info(
            f'context="perf", trackmefieldsquality has terminated, records_count="{records_count}", run_time="{round((time.time() - start), 3)}"'
        )


dispatch(TrackMeFieldsQuality, sys.argv, sys.stdin, sys.stdout, __name__)

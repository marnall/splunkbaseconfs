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
import json
import logging
from logging.handlers import RotatingFileHandler
import urllib3
import hashlib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_trackmepushdatasource.log" % splunkhome,
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

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces, decode_unicode

# import trackme libs get data
from trackme_libs_get_data import get_full_kv_collection_by_object


@Configuration(distributed=False)
class TrackMePushDataSource(StreamingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** The component to use (dsm or dhm).""",
        require=True,
        validate=validators.Match("component", r"^(dsm|dhm)$"),
    )

    search_type = Option(
        doc="""
        **Syntax:** **search_type=****
        **Description:** The type of search to perform (tstats or raw).""",
        require=True,
        validate=validators.Match("search_type", r"^(tstats|raw)$"),
    )

    show_search_query = Option(
        doc="""
        **Syntax:** **show_search_query=****
        **Description:** If true, includes the search query in the summary output.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    show_search_results = Option(
        doc="""
        **Syntax:** **show_search_results=****
        **Description:** If true, includes the search results in the summary output.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    pretend_latest = Option(
        doc="""
        **Syntax:** **pretend_latest=****
        **Description:** Relative time value in Splunk format for data_last_time_seen. Default is -24h.""",
        require=False,
        default="-24h",
        validate=validators.Match("pretend_latest", r"^.*$"),
    )

    def stream(self, records):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # instance id for logging (random sha256 hash)
        instance_id = hashlib.sha256(
            f"{time.time()}{self.tenant_id}{self.component}{self.search_type}{self.show_search_query}{self.show_search_results}{self.pretend_latest}".encode()
        ).hexdigest()

        # log start
        logging.info(
            f"tenant_id={self.tenant_id}, component={self.component}, instance_id={instance_id}, trackmepushdatasource is starting processing, search_type={self.search_type}, show_search_query={self.show_search_query}, show_search_results={self.show_search_results}, pretend_latest={self.pretend_latest}"
        )

        # Initialize counters and storage
        records_count = 0
        missing_records = []
        existing_records = 0
        objects_added = []
        rejected_records = []

        # Get the KV store collection for the tenant
        kv_collection_name = f"kv_trackme_{self.component}_tenant_{self.tenant_id}"
        kv_collection = self.service.kvstore[kv_collection_name]

        # get the full collection
        try:
            kv_collection_records, kv_collection_objects, kv_collection_dict = (
                get_full_kv_collection_by_object(kv_collection, kv_collection_name)
            )
        except Exception as e:
            log.error(
                f"tenant_id={self.tenant_id}, component={self.component}, instance_id={instance_id}, error getting full collection: {str(e)}"
            )
            yield {"error": str(e)}
            return

        # Loop through records
        for record in records:
            records_count += 1

            # Extract required fields
            try:
                object_name = decode_unicode(record.get("object"))
            except Exception as e:
                object_name = None

            try:
                index = decode_unicode(record.get("index"))
            except Exception as e:
                index = None

            try:
                sourcetype = decode_unicode(record.get("sourcetype"))
            except Exception as e:
                sourcetype = None

            try:
                host = decode_unicode(record.get("host"))  # only for dhm
            except Exception as e:
                host = None

            # lower all of them
            if object_name:
                object_name = object_name.lower()
            if index:
                index = index.lower()
            if sourcetype:
                sourcetype = sourcetype.lower()

            # orig_host, for dhm only
            orig_host = None

            # Validate index and sourcetype based on component type
            if self.component == "dsm":
                if not index:
                    log.error(
                        f"Missing required index for DSM component in record: {record}"
                    )
                    rejected_records.append(
                        {
                            "record": record,
                            "reason": "Missing required index for DSM component",
                        }
                    )
                    continue
                if not sourcetype:
                    log.error(
                        f"Missing required sourcetype for DSM component in record: {record}"
                    )
                    rejected_records.append(
                        {
                            "record": record,
                            "reason": "Missing required sourcetype for DSM component",
                        }
                    )
                    continue

                # unless object is specified, for dsm we will compose it as index:sourcetype
                if not object_name:
                    object_name = f"{index}:{sourcetype}"

            elif self.component == "dhm":
                if not host:
                    log.error(
                        f"Missing required host field for DHM component in record: {record}"
                    )
                    rejected_records.append(
                        {
                            "record": record,
                            "reason": "Missing required host field for DHM component",
                        }
                    )
                    continue
                else:
                    # for dhm, the object is the host with the prefix key:host| - if the prefix is not present, add it
                    orig_host = record.get("host")
                    if not host.startswith("key:host|"):
                        host = f"key:host|{host}"
                    object_name = host

            # Validate sourcetype based on component type
            if self.component == "dsm":
                if not sourcetype:
                    log.error(
                        f"Missing required sourcetype for DSM component in record: {record}"
                    )
                    rejected_records.append(
                        {
                            "record": record,
                            "reason": "Missing required sourcetype for DSM component",
                        }
                    )
                    continue

            elif self.component == "dhm":

                # Validate index and sourcetype based on component type
                if index:
                    # if index is a list, convert it to CSV string
                    if isinstance(index, list):
                        index = ",".join(index)
                    # If index is not a list, keep it as is
                    record["index"] = index

                if sourcetype:
                    # If sourcetype is a list, convert it to CSV string
                    if isinstance(sourcetype, list):
                        sourcetype = ",".join(sourcetype)
                    # If sourcetype is not a list, keep it as is
                    record["sourcetype"] = sourcetype

            # Check if object exists in KV store
            if object_name not in kv_collection_objects:

                # Object doesn't exist, add to missing records
                record_to_add = {}
                if self.component == "dsm":
                    record_to_add["object"] = object_name
                    record_to_add["index"] = index
                    record_to_add["sourcetype"] = sourcetype

                if self.component == "dhm":

                    host = record.get("host")
                    # if host does not start with key:host|, add it and make it lower case
                    if not host.startswith("key:host|"):
                        host = f"key:host|{host}".lower()
                    record_to_add["host"] = host
                    record_to_add["alias"] = (
                        orig_host  # alias should be defined for dhm
                    )
                    # index and sourcetype are optional for dhm
                    if index:
                        record_to_add["index"] = index
                    if sourcetype:
                        record_to_add["sourcetype"] = sourcetype

                missing_records.append(record_to_add)
                logging.info(
                    f"tenant_id={self.tenant_id}, component={self.component}, instance_id={instance_id}, collection={kv_collection_name}, Adding record to missing records: {json.dumps(record_to_add)}"
                )

            else:
                existing_records += 1

        # Process missing records if any
        if missing_records:
            try:
                # Create the search string
                data_strings = []
                for record in missing_records:
                    if self.component == "dsm":
                        data_strings.append(
                            f"\"object\": \"{record['object']}\", \"data_index\": \"{record['index']}\", \"data_sourcetype\": \"{record['sourcetype']}\""
                        )
                    elif self.component == "dhm":
                        host = record.get("host")
                        alias = record.get("alias")
                        index = record.get("index", "")
                        sourcetype = record.get("sourcetype", "")
                        data_strings.append(
                            f'"index": "{index}", "sourcetype": "{sourcetype}", '
                            f'"host": "{host}", '
                            f'"alias": "{alias}", '
                            f'"data_eventcount": 0, '
                            f'"avg_eventcount_5m": 0, "latest_eventcount_5m": 0, "perc95_eventcount_5m": 0, '
                            f'"avg_latency_5m": 0, "latest_latency_5m": 0, "perc95_latency_5m": 0, '
                            f'"stdev_latency_5m": 0, "stdev_eventcount_5m": 0, '
                            f'"data_first_time_seen": 0, '
                            f'"data_last_ingestion_lag_seen": 0'
                        )

                # escape double quotes in data_strings
                data_strings = [
                    data_string.replace('"', '\\"') for data_string in data_strings
                ]

                search_query = remove_leading_spaces(
                    f"""
                | makeresults
                | eval data = "{'#'.join(data_strings)}"
                | eval data=split(data, "#")
                | mvexpand data
                | eval data = "{{" . data . "}}"
                | fields - _time
                | spath input=data
                | fields - data
                | eval data_last_time_seen=relative_time(now(), "{self.pretend_latest}"), data_last_ingest=relative_time(now(), "{self.pretend_latest}")
                {f"| " if self.component == "dhm" else ""}`trackme_{self.component}_tracker_abstract({self.tenant_id}, {self.search_type})`
                | `trackme_outputlookup(trackme_{self.component}_tenant_{self.tenant_id}, key)`
                """
                ).strip()

                # Execute the search using run_splunk_search
                kwargs = {
                    "earliest_time": "-5m",
                    "latest_time": "now",
                    "count": 0,
                    "output_mode": "json",
                }

                search_results = []
                try:
                    reader = run_splunk_search(
                        self.service,
                        search_query,
                        kwargs,
                        24,  # max_retries
                        5,  # retry_delay
                    )

                    for item in reader:
                        if isinstance(item, dict):
                            logging.debug(f'search_results="{item}"')
                            search_results.append(item)
                            objects_added.append(item.get("object"))

                    # Add summary to the output
                    yield_summary = {
                        "total_records_processed": records_count,
                        "existing_records": existing_records,
                        "new_records_added": len(missing_records),
                        "objects_added": objects_added,
                        "rejected_records": rejected_records,
                        "processing_time": round(time.time() - start, 2),
                    }

                    # Add search query to summary if requested
                    if self.show_search_query:
                        yield_summary["search_query"] = search_query

                    # Add search results to summary if requested
                    if self.show_search_results:
                        yield_summary["search_results"] = search_results

                    yield yield_summary

                except Exception as e:
                    log.error(f"Error executing search: {str(e)}")
                    yield {"error": str(e), "search": search_query}

            except Exception as e:
                log.error(f"Error preparing search: {str(e)}")
                yield {"error": str(e)}
        else:
            # No missing records, just return summary
            yield_summary = {
                "total_records_processed": records_count,
                "existing_records": existing_records,
                "new_records_added": 0,
                "objects_added": [],
                "rejected_records": rejected_records,
                "processing_time": round(time.time() - start, 2),
            }
            yield yield_summary

        # log end
        logging.info(
            f"tenant_id={self.tenant_id}, component={self.component}, instance_id={instance_id}, trackmepushdatasource processing completed, records_count={records_count}, existing_records={existing_records}, new_records_added={len(missing_records)}, objects_added={objects_added}, rejected_records={rejected_records}, processing_time={round(time.time() - start, 2)}"
        )


dispatch(TrackMePushDataSource, sys.argv, sys.stdin, sys.stdout, __name__)

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
import json
import hashlib
import time

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import requests
from requests.structures import CaseInsensitiveDict
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_fqm_parse.log" % splunkhome,
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

# Import TrackMe splk-fqm libs
from trackme_libs_splk_fqm import (
    trackme_fqm_gen_metrics_from_list,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo

# Import trackMe utils libs
from trackme_libs_utils import get_uuid

# import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

# import TrackMe get data libs
from trackme_libs_get_data import (
    get_full_kv_collection,
)


@Configuration(distributed=False)
class TrackMeSplkFqmParse(StreamingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    object_metadata_list = Option(
        doc="""
        **Syntax:** **object_metadata_list=****
        **Description:** The comma separated list of metadata fields used to generate the object value, in their order of precedence.""",
        require=True,
        default=None,
    )

    default_threshold_fields = Option(
        doc="""
        **Syntax:** **default_threshold_fields=****
        **Description:** The default threshold value for fields, defaults to 99. (integer or float value)""",
        require=False,
        default=99,
        validate=validators.Match("default_threshold_fields", r"^\d*\.?\d*$"),
    )

    default_threshold_global = Option(
        doc="""
        **Syntax:** **default_threshold_global=****
        **Description:** The default threshold value for the global entity, defaults to 100. (integer or float value)""",
        require=False,
        default=100,
        validate=validators.Match("default_threshold_global", r"^\d*\.?\d*$"),
    )

    default_score_fields = Option(
        doc="""
        **Syntax:** **default_score_fields=****
        **Description:** The default score (0-100) for field thresholds when breached, defaults to 100. (integer value)""",
        require=False,
        default=100,
        validate=validators.Match("default_score_fields", r"^\d+$"),
    )

    default_score_global = Option(
        doc="""
        **Syntax:** **default_score_global=****
        **Description:** The default score (0-100) for global entity thresholds when breached, defaults to 100. (integer value)""",
        require=False,
        default=100,
        validate=validators.Match("default_score_global", r"^\d+$"),
    )

    context = Option(
        doc="""
        **Syntax:** **context=****
        **Description:** The context is used for simulation purposes, defaults to live.""",
        require=False,
        default="live",
        validate=validators.Match("context", r"^(live|simulation)$"),
    )

    max_sec_inactive = Option(
        doc="""
        **Syntax:** **max_sec_inactive=****
        **Description:** The maximum number of seconds an entity can be inactive before it is considered inactive, defaults to 7 days.""",
        require=False,
        default=604800,
        validate=validators.Match("max_sec_inactive", r"^\d*$"),
    )

    tracker_name = Option(
        doc="""
        **Syntax:** **tracker_name=****
        **Description:** The name of the tracker.""",
        require=True,
        default=None,
    )

    tracker_index = Option(
        doc="""
        **Syntax:** **tracker_index=****
        **Description:** The index of the tracker.""",
        require=False,
        default=None,
    )

    def get_thresholds_collection(self):
        # connect to the KVstore
        collection_name = f"kv_trackme_fqm_thresholds_tenant_{self.tenant_id}"
        collection = self.service.kvstore[collection_name]

        # get all records
        get_collection_start = time.time()
        collection_records = []
        collection_records_keys = set()
        collection_records_dict = {}

        end = False
        skip_tracker = 0
        while end == False:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if len(process_collection_records) != 0:
                for item in process_collection_records:
                    if item.get("_key") not in collection_records_keys:
                        collection_records.append(item)
                        collection_records_keys.add(item.get("_key"))
                        threshold_value = item.get("value", 0)
                        try:
                            threshold_value = float(threshold_value)
                        except (TypeError, ValueError):
                            pass
                        
                        # Get score, default to 100 if not present (for backward compatibility)
                        score = item.get("score")
                        if score is None:
                            score = 100
                        else:
                            try:
                                score = int(score)
                            except (TypeError, ValueError):
                                score = 100
                        
                        collection_records_dict[item.get("object_id")] = {
                            "_key": item.get("_key"),
                            "metric_name": item.get("metric_name"),
                            "mtime": float(item.get("mtime", 0)),
                            "operator": item.get("operator"),
                            "value": threshold_value,
                            "condition_true": int(item.get("condition_true", 0)),
                            "comment": item.get("comment"),
                            "score": score,
                        }
                skip_tracker += len(process_collection_records)
            else:
                end = True

        logging.info(
            f'instance_id="{self.instance_id}", context="perf", get_thresholds_collection records, no_records="{len(collection_records)}", run_time="{round((time.time() - get_collection_start), 3)}", collection="{collection_name}"'
        )

        return collection_records_dict

    # get disruption queue collection
    def get_disruption_queue_collection(self):
        # connect to the KVstore
        collection_name = f"kv_trackme_common_disruption_queue_tenant_{self.tenant_id}"
        collection = self.service.kvstore[collection_name]

        # get all records
        get_collection_start = time.time()
        collection_records = []
        collection_records_keys = set()
        collection_records_dict = {}

        end = False
        skip_tracker = 0
        while end == False:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if len(process_collection_records) != 0:
                for item in process_collection_records:
                    if item.get("_key") not in collection_records_keys:
                        collection_records.append(item)
                        collection_records_keys.add(item.get("_key"))
                        collection_records_dict[item.get("_key")] = item

                skip_tracker += len(process_collection_records)
            else:
                end = True

        logging.info(
            f'instance_id="{self.instance_id}", context="perf", get_disruption_queue_collection records, no_records="{len(collection_records)}", run_time="{round((time.time() - get_collection_start), 3)}", collection="{collection_name}"'
        )

        return collection_records_dict, collection_records_keys

    def get_tenant_metric_idx(self):
        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % self._metadata.searchinfo.session_key,
            "Content-Type": "application/json",
        }

        # get the index conf for this tenant
        url = "%s/services/trackme/v2/vtenants/tenant_idx_settings" % (
            self._metadata.searchinfo.splunkd_uri
        )
        data = {"tenant_id": self.tenant_id, "idx_stanza": "trackme_metric_idx"}

        # Retrieve and set the tenant idx, if any failure, logs and use the global index
        try:
            response = requests.post(
                url,
                headers=header,
                data=json.dumps(data, indent=1),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                error_msg = f'instance_id="{self.instance_id}", failed to retrieve the tenant metric index, response.status_code="{response.status_code}", response.text="{response.text}"'
                logging.error(error_msg)
                raise Exception(error_msg)
            else:
                response_data = json.loads(json.dumps(response.json(), indent=1))
                tenant_trackme_metric_idx = response_data["trackme_metric_idx"]
        except Exception as e:
            error_msg = f'instance_id="{self.instance_id}", failed to retrieve the tenant metric index, exception="{str(e)}"'
            logging.error(error_msg)
            raise Exception(error_msg)

        return tenant_trackme_metric_idx

    def stream(self, records):
        # performance counter
        start = time.time()

        # Prepare separate lists for thresholds (initialize ONCE here)
        field_thresholds_object_ids = []
        global_thresholds_object_id = []

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # set instance_id
        self.instance_id = get_uuid()

        # log info
        logging.info(
            f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", context="{self.context}", TrackMeSplkFqmParse is starting'
        )

        #
        # some parameters inits
        #

        # get metric index
        metric_index = self.get_tenant_metric_idx()

        # counter
        count = 0

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "get_tenant_collection_records"

        # get the tenant KVstore collection
        tenant_collection_name = f"kv_trackme_fqm_tenant_{self.tenant_id}"
        tenant_collection = self.service.kvstore[tenant_collection_name]
        tenant_records, tenant_collection_keys, tenant_collection_dict = (
            get_full_kv_collection(tenant_collection, tenant_collection_name)
        )
        logging.debug(
            f'tenant_id="{self.tenant_id}", tenant_collection_dict="{json.dumps(tenant_collection_dict, indent=2)}"'
        )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id="{self.instance_id}", task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "get_thresholds_collection_records"

        # get thresholds collection
        try:
            thresholds_collection = self.get_thresholds_collection()
            logging.debug(
                f'tenant_id="{self.tenant_id}", thresholds_collection="{json.dumps(thresholds_collection, indent=2)}"'
            )
        except Exception as e:
            thresholds_collection = {}
            logging.error(
                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", failed to retrieve the thresholds collection, exception="{str(e)}"'
            )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id="{self.instance_id}", task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "get_disruption_queue_collection_records"

        # get disruption queue collection
        try:
            disruption_queue_collection, disruption_queue_collection_keys = (
                self.get_disruption_queue_collection()
            )
            logging.debug(
                f'tenant_id="{self.tenant_id}", disruption_queue_collection="{json.dumps(disruption_queue_collection, indent=2)}"'
            )
        except Exception as e:
            disruption_queue_collection = {}
            disruption_queue_collection_keys = {}
            logging.error(
                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", failed to retrieve the disruption queue collection, exception="{str(e)}"'
            )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id="{self.instance_id}", task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # Build header and target URL
        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Splunk {self._metadata.searchinfo.session_key}"
        headers["Content-Type"] = "application/json"

        # Create a requests session for better performance
        session = requests.Session()
        session.headers.update(headers)

        # metrics_list
        metrics_list = []

        # Loop in the results
        yield_records = []

        # turn the object_metadata_list into a list from csv
        object_metadata_list = self.object_metadata_list.split(",")

        # copy to object_metadata_list_with_fieldname
        object_metadata_list_with_fieldname = object_metadata_list.copy()
        # if fieldname is not in the list, add it
        if "fieldname" not in object_metadata_list_with_fieldname:
            object_metadata_list_with_fieldname.append("fieldname")

        # if fieldname is in the original list, remove it
        if "fieldname" in object_metadata_list:
            object_metadata_list.remove("fieldname")

        # meta entity: the meta entity is a parent entity that represents the global results
        # for the combination of metadata_datamodel, metadata_nodename, metadata_index, metadata_sourcetype
        # it is used to group the results by the combination of these fields

        # Dictionary to track meta entity aggregation data
        meta_entity_aggregation = {}

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_records"

        for record in records:
            # increment
            count += 1

            # define the yield_record
            yield_record = {}

            # add the metadata_datamodel field to the yield_record
            yield_record["metadata_datamodel"] = record.get("metadata.datamodel")

            # add the metadata_nodename field to the yield_record
            yield_record["metadata_nodename"] = record.get("metadata.nodename")

            # add the metadata_index field to the yield_record
            yield_record["metadata_index"] = record.get("metadata.index")

            # add the metadata_sourcetype field to the yield_record
            yield_record["metadata_sourcetype"] = record.get("metadata.sourcetype")

            # init fqm_type, here it is statically set to field
            yield_record["fqm_type"] = "field"

            # define the object value, using : as a separator between the metadata fields
            object_value = ""
            for metadata_field in object_metadata_list_with_fieldname:
                if metadata_field in record:
                    object_value += f"{record[metadata_field]}:"
            object_value = object_value.rstrip(":")
            yield_record["object"] = object_value

            # define the object_id as the sha256 of the object value
            object_id = hashlib.sha256(yield_record["object"].encode()).hexdigest()
            yield_record["object_id"] = object_id

            # if object_id is in tenant_collection_keys, get the monitored_state value from the dict
            if object_id in tenant_collection_keys:
                monitored_state = tenant_collection_dict[object_id].get(
                    "monitored_state", "enabled"
                )
            else:
                monitored_state = "enabled"

            # stop here if the monitored_state is disabled
            if monitored_state == "disabled":
                logging.info(
                    f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", object_id="{object_id}", monitored_state="{monitored_state}", skipping record'
                )
                continue

            # define the alias as the value of the field fieldname
            yield_record["alias"] = record.get("fieldname", "")

            # merge all metadata.* fields into a single JSON object metadata
            metadata_fields = {}
            for key, value in record.items():
                if key.startswith("metadata."):
                    # Remove the leading dot from the field name
                    field_name = key[8:]  # Remove "metadata." prefix
                    if field_name.startswith("."):
                        field_name = field_name[1:]  # Remove leading dot
                    metadata_fields[field_name] = value

            # calculate the percent_success as: count_success/count_total*100
            count_success = float(record.get("count_success", 0))
            count_total = float(record.get("count_total", 0))

            if count_total > 0:
                percent_success = round(count_success / count_total * 100, 2)
                # Convert to int if it's a whole number to avoid .0
                if percent_success == int(percent_success):
                    percent_success = int(percent_success)
            else:
                percent_success = 0
            yield_record["percent_success"] = percent_success

            # get percent_coverage
            try:
                percent_coverage = float(record.get("percent_coverage", 0))
            except (TypeError, ValueError):
                percent_coverage = 0
            if percent_coverage == int(percent_coverage):
                percent_coverage = int(percent_coverage)
            yield_record["percent_coverage"] = percent_coverage

            # lookup thresholds
            dynamic_thresholds = {}
            if object_id in thresholds_collection:
                dynamic_thresholds = thresholds_collection[object_id]

            logging.debug(
                f'dynamic_thresholds="{json.dumps(dynamic_thresholds, indent=2)}"'
            )

            # set the threshold_success based on the dynamic_thresholds record, access to the value for the metric_name "fields_quality.percent_success"
            # if not set yet, set it to the default_threshold
            if (
                dynamic_thresholds
                and dynamic_thresholds.get("metric_name")
                == "fields_quality.percent_success"
            ):
                threshold_success = dynamic_thresholds["value"]
            else:
                threshold_success = float(self.default_threshold_fields)
            if threshold_success == int(threshold_success):
                threshold_success = int(threshold_success)
            yield_record["threshold_success"] = threshold_success

            logging.debug(
                f'tenant_id="{self.tenant_id}", object_id="{object_id}", object_value="{object_value}", threshold_success="{threshold_success}"'
            )

            # set the fields_quality_summary field (JSON object)
            # determine field status based on percent_success vs threshold_success
            if percent_success >= threshold_success:
                field_status = "success"
            else:
                field_status = "failure"

            # get field_values (list)
            field_values = record.get("field_values", [])
            # convert the list to a string
            if isinstance(field_values, list):
                field_values = ", ".join(field_values)

            # get distinct_value_count
            try:
                distinct_value_count = int(record.get("distinct_value_count", 0))
            except Exception as e:
                distinct_value_count = 0

            # create the fields_quality_summary JSON object
            fields_quality_summary = {
                "@fieldname": record.get("fieldname", ""),
                "@fieldstatus": field_status,
                "quality_results_description": record.get("description", []),
                "count_failure": int(record.get("count_failure", 0)),
                "count_success": int(record.get("count_success", 0)),
                "count_total": int(record.get("count_total", 0)),
                "distinct_value_count": distinct_value_count,
                "field_values": field_values,
                "percent_coverage": percent_coverage,
                "percentage_success": percent_success,
                "threshold": threshold_success,
                "total_events": int(record.get("total_events", 0)),
            }

            # add regex_expression if available
            if "regex_expression" in record:
                fields_quality_summary["regex_expression"] = record["regex_expression"]

            # add metadata fields
            for key, value in metadata_fields.items():
                fields_quality_summary[f"metadata.{key}"] = value

            yield_record["fields_quality_summary"] = json.dumps(
                fields_quality_summary, indent=2
            )

            logging.debug(
                f'tenant_id="{self.tenant_id}", object_id="{object_id}", object_value="{object_value}", fields_quality_summary="{json.dumps(fields_quality_summary, indent=2)}"'
            )

            # create the metrics JSON object, based on:
            # count_total, count_success, count_failure, percent_coverage, distinct_value_count, total_events
            # with a prefix of "fields_quality."
            metrics_fields = {
                "fields_quality.count_total": int(record.get("count_total", 0)),
                "fields_quality.count_success": int(record.get("count_success", 0)),
                "fields_quality.count_failure": int(record.get("count_failure", 0)),
                "fields_quality.percent_coverage": percent_coverage,
                "fields_quality.percent_success": percent_success,
                "fields_quality.distinct_value_count": int(
                    record.get("distinct_value_count", 0)
                ),
                "fields_quality.total_events": int(record.get("total_events", 0)),
            }

            # add the metrics fields to the yield_record
            yield_record["metrics"] = json.dumps(metrics_fields)

            # add a record a record to the metrics_list
            metrics_list.append(
                {
                    "time": time.time(),
                    "object": object_value,
                    "object_id": object_id,
                    "metrics": metrics_fields,
                }
            )

            # add all other fields to the yield_record
            for key, value in record.items():
                if not key.startswith("metadata."):
                    yield_record[key] = value

            # add the metadata fields to the yield_record
            yield_record["metadata"] = json.dumps(metadata_fields)

            # add the tracker_runtime field to the yield_record (epochtime of the execution)
            yield_record["tracker_runtime"] = int(time.time())

            # add the tracker_name field to the yield_record
            yield_record["tracker_name"] = self.tracker_name

            # add the tracker_index field to the yield_record
            if self.tracker_index:
                yield_record["tracker_index"] = self.tracker_index

            # add the max_sec_inactive field to the yield_record
            yield_record["max_sec_inactive"] = int(self.max_sec_inactive)

            # add the yield_record to the yield_records list
            yield_records.append(yield_record)

            ####################################
            # Start Processing meta entity aggregation
            ####################################

            # Create meta entity key based on metadata combination
            meta_key = ":".join(
                [str(record.get(field, "")) for field in object_metadata_list]
            )

            if meta_key not in meta_entity_aggregation:
                meta_entity_aggregation[meta_key] = {
                    "metadata_datamodel": record.get("metadata.datamodel"),
                    "metadata_nodename": record.get("metadata.nodename"),
                    "metadata_index": record.get("metadata.index"),
                    "metadata_sourcetype": record.get("metadata.sourcetype"),
                    "total_fields_checked": 0,
                    "total_fields_passed": 0,
                    "total_fields_failed": 0,
                    "total_count_success": 0,
                    "total_count_failure": 0,
                    "total_count_total": 0,
                    "success_fields": [],
                    "failed_fields": [],
                    "record_count": 0,
                }

                # Store all metadata fields from object_metadata_list for later use in meta entity object construction
                for field in object_metadata_list:
                    meta_entity_aggregation[meta_key][field] = record.get(field, "")

            # Aggregate field-level metrics
            meta_entity_aggregation[meta_key]["total_fields_checked"] += 1
            fieldname = record.get("fieldname", "")
            meta_entity_aggregation[meta_key]["record_count"] += 1
            if percent_success >= threshold_success:
                meta_entity_aggregation[meta_key]["total_fields_passed"] += 1
                if fieldname:
                    meta_entity_aggregation[meta_key]["success_fields"].append(
                        fieldname
                    )
            else:
                meta_entity_aggregation[meta_key]["total_fields_failed"] += 1
                if fieldname:
                    meta_entity_aggregation[meta_key]["failed_fields"].append(fieldname)
            meta_entity_aggregation[meta_key]["total_count_success"] += int(
                record.get("count_success", 0)
            )
            meta_entity_aggregation[meta_key]["total_count_failure"] += int(
                record.get("count_failure", 0)
            )
            meta_entity_aggregation[meta_key]["total_count_total"] += int(
                record.get("count_total", 0)
            )

            ####################################
            # End Processing meta entity aggregation
            ####################################

            ####################################
            # Start Processing default threshold
            ####################################

            #
            # Add the default threshold calling the API endpoint if default threshold is provided and this entity does not have a threshold already
            #

            if self.context == "live":

                if object_id not in thresholds_collection:
                    field_thresholds_object_ids.append(object_id)

            ##################################
            # End Processing default threshold
            ##################################

        # render field-level records
        for yield_record in yield_records:
            yield yield_record

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id="{self.instance_id}", task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_meta_entity_records"

        #######################################
        # Process meta entity records
        #######################################

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_meta_entity_records"

        # Create meta entity records for each metadata combination
        for meta_key, meta_data in meta_entity_aggregation.items():
            # Calculate percentages
            total_fields_checked = meta_data["total_fields_checked"]
            total_fields_passed = meta_data["total_fields_passed"]
            total_fields_failed = meta_data["total_fields_failed"]

            if total_fields_checked > 0:
                percentage_passed = round(
                    total_fields_passed / total_fields_checked * 100, 2
                )
                percentage_failed = round(
                    total_fields_failed / total_fields_checked * 100, 2
                )
                # Convert to int if it's a whole number to avoid .0
                if percentage_passed == int(percentage_passed):
                    percentage_passed = int(percentage_passed)
                if percentage_failed == int(percentage_failed):
                    percentage_failed = int(percentage_failed)
            else:
                percentage_passed = 0
                percentage_failed = 0

            # Prepare success and failed fields as comma-separated strings
            success_fields = ",".join(meta_data.get("success_fields", []))
            failed_fields = ",".join(meta_data.get("failed_fields", []))

            # Create meta entity object value using object_metadata_list
            meta_object_value = (
                ":".join(
                    [str(meta_data.get(field, "")) for field in object_metadata_list]
                )
                + ":@global"
            )
            meta_object_id = hashlib.sha256(meta_object_value.encode()).hexdigest()

            # Ensure default threshold for meta entity
            if self.context == "live":
                if meta_object_id not in thresholds_collection:
                    global_thresholds_object_id.append(meta_object_id)

            # Create meta entity yield record
            meta_yield_record = {
                "metadata_datamodel": meta_data["metadata_datamodel"],
                "metadata_nodename": meta_data["metadata_nodename"],
                "metadata_index": meta_data["metadata_index"],
                "metadata_sourcetype": meta_data["metadata_sourcetype"],
                "fqm_type": "global",
                "object": meta_object_value,
                "object_id": meta_object_id,
                "alias": "@global",
                "percent_success": percentage_passed,
                "percent_coverage": 100,  # Global entities always have 100% coverage
                "threshold_success": float(self.default_threshold_global),
                "total_fields_checked": total_fields_checked,
                "total_fields_passed": total_fields_passed,
                "total_fields_failed": total_fields_failed,
                "percentage_passed": percentage_passed,
                "percentage_failed": percentage_failed,
                "tracker_runtime": int(time.time()),
                "tracker_name": self.tracker_name,
                "max_sec_inactive": int(self.max_sec_inactive),
                "success_fields": success_fields,
                "failed_fields": failed_fields,
            }

            # add index conditionally
            if self.tracker_index:
                meta_yield_record["tracker_index"] = self.tracker_index

            # Create metadata fields for meta entity
            meta_metadata_fields = {}
            for field in object_metadata_list:
                if field.startswith("metadata."):
                    # Remove the "metadata." prefix for the metadata object
                    field_name = field[9:]  # Remove "metadata." prefix
                    meta_metadata_fields[field_name] = meta_data.get(field, "")
                else:
                    # For non-metadata fields, keep as is
                    meta_metadata_fields[field] = meta_data.get(field, "")
            meta_yield_record["metadata"] = json.dumps(meta_metadata_fields)

            # Create fields_quality_summary for meta entity
            meta_fields_quality_summary = {
                "@fieldname": "@global",
                "@fieldstatus": (
                    "success"
                    if percentage_passed >= float(self.default_threshold_global)
                    else "failure"
                ),
                "count_failure": meta_data["total_count_failure"],
                "count_success": meta_data["total_count_success"],
                "count_total": meta_data["total_count_total"],
                "percentage_success": percentage_passed,
                "threshold": float(self.default_threshold_global),
                "total_fields_checked": total_fields_checked,
                "total_fields_passed": total_fields_passed,
                "total_fields_failed": total_fields_failed,
                "percentage_passed": percentage_passed,
                "percentage_failed": percentage_failed,
                "success_fields": success_fields,
                "failed_fields": failed_fields,
            }

            # Add all metadata fields to the fields_quality_summary
            for field in object_metadata_list:
                meta_fields_quality_summary[field] = meta_data.get(field, "")
            meta_yield_record["fields_quality_summary"] = json.dumps(
                meta_fields_quality_summary, indent=2
            )

            # Create metrics for meta entity
            meta_metrics_fields = {
                "fields_quality.count_total": meta_data["total_count_total"],
                "fields_quality.count_success": meta_data["total_count_success"],
                "fields_quality.count_failure": meta_data["total_count_failure"],
                "fields_quality.percent_success": percentage_passed,
                "fields_quality.total_fields_checked": total_fields_checked,
                "fields_quality.total_fields_passed": total_fields_passed,
                "fields_quality.total_fields_failed": total_fields_failed,
                "fields_quality.percentage_passed": percentage_passed,
                "fields_quality.percentage_failed": percentage_failed,
                "success_fields": success_fields,
                "failed_fields": failed_fields,
            }

            # Add all metadata fields to the metrics
            for field in object_metadata_list:
                meta_metrics_fields[field] = meta_data.get(field, "")
            meta_yield_record["metrics"] = json.dumps(meta_metrics_fields)

            # Add meta entity to metrics list for processing
            metrics_list.append(
                {
                    "time": time.time(),
                    "object": meta_object_value,
                    "object_id": meta_object_id,
                    "metrics": meta_metrics_fields,
                }
            )

            # Yield the meta entity record
            yield meta_yield_record

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id="{self.instance_id}", task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        #######################################
        # Process the thresholds records update
        #######################################

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_thresholds_records"

        # Prepare separate lists for thresholds
        # field_thresholds_object_ids = [] # This line is removed as it's now initialized at the start of the stream function
        # global_thresholds_object_id = None # This line is removed as it's now initialized at the start of the stream function

        # Process the thresholds records update in two separate operations
        endpoint = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_fqm/write/fqm_thresholds_add"

        if field_thresholds_object_ids and self.context == "live":
            # Get score, default to 100 if not provided (for backward compatibility)
            try:
                score_fields = int(self.default_score_fields)
                if score_fields < 0 or score_fields > 100:
                    score_fields = 100
            except (TypeError, ValueError):
                score_fields = 100
            
            data = {
                "tenant_id": self.tenant_id,
                "metric_name": "fields_quality.percent_success",
                "value": float(self.default_threshold_fields),
                "operator": ">=",
                "condition_true": 1,
                "comment": "default threshold",
                "score": score_fields,
                "keys_list": ",".join(field_thresholds_object_ids),
            }
            logging.info(
                f"Posting field thresholds: keys_list={data['keys_list']} value={data['value']}"
            )
            try:
                response = session.post(
                    endpoint,
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                response.raise_for_status()
                logging.info(
                    f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", default field thresholds added successfully for {len(field_thresholds_object_ids)} entities, http_status="{response.status_code}"'
                )
            except Exception as e:
                logging.error(
                    f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", failed to add the default field thresholds, exception="{str(e)}"'
                )

        if global_thresholds_object_id and self.context == "live":
            # Get score, default to 100 if not provided (for backward compatibility)
            try:
                score_global = int(self.default_score_global)
                if score_global < 0 or score_global > 100:
                    score_global = 100
            except (TypeError, ValueError):
                score_global = 100
            
            data = {
                "tenant_id": self.tenant_id,
                "metric_name": "fields_quality.percent_success",
                "value": float(self.default_threshold_global),
                "operator": ">=",
                "condition_true": 1,
                "comment": "default threshold (meta entity)",
                "score": score_global,
                "keys_list": ",".join(global_thresholds_object_id),
            }
            logging.info(
                f"Posting global threshold: keys_list={data['keys_list']} value={data['value']}"
            )
            try:
                response = session.post(
                    endpoint,
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                response.raise_for_status()
                logging.info(
                    f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", default field thresholds added successfully for {len(global_thresholds_object_id)} entities, http_status="{response.status_code}"'
                )
            except Exception as e:
                logging.error(
                    f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", failed to add the default field thresholds, exception="{str(e)}"'
                )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id="{self.instance_id}", task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        #######################################
        # Process the metrics records update
        #######################################

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_metrics_records"

        if metrics_list and self.context == "live":
            # trackme_fqm_gen_metrics_from_list(self.tenant_id, metrics_list)

            logging.debug(f'metrics_list="{json.dumps(metrics_list, indent=2)}"')

            try:
                trackme_fqm_gen_metrics_from_list(
                    self.tenant_id,
                    metric_index,
                    metrics_list,
                )

            except Exception as e:
                error_msg = f'Failed to process metrics_list with exception="{str(e)}"'
                logging.error(error_msg)
                # do not raise an exception, continue

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id="{self.instance_id}", task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # log info
        run_time = round(time.time() - start, 3)
        logging.info(
            f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", context="{self.context}", TrackMeSplkFqmParse has terminated successfully, turn debug mode on for more details, results_count="{count}", run_time={run_time}'
        )


dispatch(TrackMeSplkFqmParse, sys.argv, sys.stdin, sys.stdout, __name__)

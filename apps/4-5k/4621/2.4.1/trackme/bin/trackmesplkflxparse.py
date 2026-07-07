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
import re
import hashlib
import ast
import time
import concurrent.futures

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
    "%s/var/log/splunk/trackme_splk_flx_parse.log" % splunkhome,
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

# Import TrackMe splk-flx libs
from trackme_libs_splk_flx import (
    trackme_flx_gen_metrics,
    trackme_flx_gen_metrics_from_list,
    normalize_flx_tracker_name,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo

# Import trackMe utils libs
from trackme_libs_utils import decode_unicode, get_uuid

# Import trackMe kvstore batch libs
from trackme_libs_kvstore_batch import batch_update_worker

# import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)


# Structural / system fields that should NOT be considered as user-defined
# numeric metrics when scanning upstream records for metric-eligible fields.
_STRUCTURAL_FIELDS = frozenset({
    '_time', '_raw', '_serial', '_bkt', '_cd', '_si',
    'splunk_server', 'splunk_server_group',
    'host', 'source', 'sourcetype', 'index', 'linecount',
    'eventtype', 'punct', 'tag',
    'object', 'alias', 'group', 'subgroup', 'status',
    'priority', 'object_category', 'object_description',
    'status_description', 'status_description_short',
    'metrics', 'metrics_list', 'outliers_metrics',
    'extra_attributes', 'max_sec_inactive',
    'default_metric', 'default_threshold',
    'disruption_min_time_sec', 'drilldown_search',
    'drilldown_search_earliest', 'drilldown_search_latest',
    'tracker_name', 'count_entities',
})


def normalize_default_metric(value):
    """Normalize a default_metric value to a comma-separated string.

    Accepts:
      - A single metric name:  "ta_nix.p95_cpu_usage_pct"
      - A CSV string:          "ta_nix.p95_cpu_usage_pct,ta_nix.avg_cpu_usage_pct"
      - A JSON array:          ["ta_nix.p95_cpu_usage_pct", "ta_nix.avg_cpu_usage_pct"]
      - A Python-style list:   ['ta_nix.p95_cpu_usage_pct', 'ta_nix.avg_cpu_usage_pct']

    Returns a comma-separated string with whitespace trimmed per entry,
    or None if the value is empty/invalid.
    """
    if not value:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    # Try JSON array first (double-quoted)
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                items = [str(m).strip() for m in parsed if str(m).strip()]
                return ",".join(items) if items else None
        except (json.JSONDecodeError, ValueError):
            pass
        # Try Python-style list (single-quoted)
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, (list, tuple)):
                items = [str(m).strip() for m in parsed if str(m).strip()]
                return ",".join(items) if items else None
        except (ValueError, SyntaxError):
            pass

    # Already a single value or CSV string — trim each entry
    items = [m.strip() for m in raw.split(",") if m.strip()]
    return ",".join(items) if items else None


@Configuration(distributed=False)
class TrackMeSplkFlxParse(StreamingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    context = Option(
        doc="""
        **Syntax:** **context=****
        **Description:** The context is used for simulation purposes, defaults to live.""",
        require=False,
        default="live",
        validate=validators.Match("context", r"^(live|simulation)$"),
    )

    flx_type = Option(
        doc="""
        **Syntax:** **flx_type=****
        **Description:** The type of Flex Object.""",
        require=False,
        default="use_case",
        validate=validators.Match("flx_type", r"^(use_case|converging)$"),
    )

    remove_raw = Option(
        doc="""
        **Syntax:** **remove_raw=****
        **Description:** Remove the raw field from the results.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    remove_time = Option(
        doc="""
        **Syntax:** **remove_time=****
        **Description:** Remove the _time field from the results.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    def get_last_seen_collection(self):
        # connect to the KVstore
        collection_name = f"kv_trackme_flx_last_seen_activity_tenant_{self.tenant_id}"
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
                        collection_records_dict[item.get("_key")] = {
                            "_key": item.get("_key"),
                            "object": item.get("object"),
                            "last_seen_metrics": float(
                                item.get("last_seen_metrics", 0)
                            ),
                        }
                skip_tracker += len(process_collection_records)
            else:
                end = True

        logging.info(
            f'instance_id="{self.instance_id}", context="perf", get_last_seen_collection records, no_records="{len(collection_records)}", run_time="{round((time.time() - get_collection_start), 3)}", collection="{collection_name}"'
        )

        return collection_records_dict

    def get_thresholds_collection(self):
        # connect to the KVstore
        collection_name = f"kv_trackme_flx_thresholds_tenant_{self.tenant_id}"
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
                        
                        # Store thresholds keyed by object_id, then by metric_name to support multiple thresholds per entity
                        object_id = item.get("object_id")
                        metric_name = item.get("metric_name")
                        if object_id not in collection_records_dict:
                            collection_records_dict[object_id] = {}
                        collection_records_dict[object_id][metric_name] = {
                            "_key": item.get("_key"),
                            "metric_name": metric_name,
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

    # get drilldown searches collection
    def get_drilldown_searches_collection(self):
        # connect to the KVstore
        collection_name = f"kv_trackme_flx_drilldown_searches_tenant_{self.tenant_id}"
        collection = self.service.kvstore[collection_name]

        # get all records
        get_collection_start = time.time()
        collection_records = []
        collection_records_keys = set()
        collection_records_secondary_keys = set()
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
                        # add the field tracker_name as the secondary key
                        collection_records_secondary_keys.add(item.get("tracker_name"))
                        collection_records_dict[item.get("_key")] = item

                skip_tracker += len(process_collection_records)
            else:
                end = True

        logging.info(
            f'instance_id="{self.instance_id}", context="perf", get_drilldown_searches_collection records, no_records="{len(collection_records)}", run_time="{round((time.time() - get_collection_start), 3)}", collection="{collection_name}"'
        )

        return collection_records_dict, collection_records_keys, collection_records_secondary_keys

    # get default metrics collection
    def get_default_metrics_collection(self):
        # connect to the KVstore
        collection_name = f"kv_trackme_flx_default_metric_tenant_{self.tenant_id}"
        collection = self.service.kvstore[collection_name]

        # get all records
        get_collection_start = time.time()
        collection_records = []
        collection_records_keys = set()
        collection_records_secondary_keys = set()
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
                        # add the field tracker_name as the secondary key
                        collection_records_secondary_keys.add(item.get("tracker_name"))
                        collection_records_dict[item.get("_key")] = item

                skip_tracker += len(process_collection_records)
            else:
                end = True

        logging.info(
            f'instance_id="{self.instance_id}", context="perf", get_default_metrics_collection records, no_records="{len(collection_records)}", run_time="{round((time.time() - get_collection_start), 3)}", collection="{collection_name}"'
        )

        return collection_records_dict, collection_records_keys, collection_records_secondary_keys


    # batch KVstore update

    def normalize_time(self, record):

        try:
            flx_time = float(record.get("_time"))
            record["_time"] = flx_time
        except Exception as e:
            flx_time = None

        if flx_time is None:
            flx_time = time.time()
            record["_time"] = flx_time

        return flx_time, record

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
                error_msg = f'failed to retrieve the tenant metric index, response.status_code="{response.status_code}", response.text="{response.text}"'
                logging.error(f'instance_id="{self.instance_id}", {error_msg}')
                raise Exception(error_msg)
            else:
                response_data = json.loads(json.dumps(response.json(), indent=1))
                tenant_trackme_metric_idx = response_data["trackme_metric_idx"]
        except Exception as e:
            error_msg = (
                f'failed to retrieve the tenant metric index, exception="{str(e)}"'
            )
            logging.error(f'instance_id="{self.instance_id}", {error_msg}')
            raise Exception(error_msg)

        return tenant_trackme_metric_idx

    def stream(self, records):
        # performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Max multi thread workers
        max_multi_thread_workers = int(
            reqinfo["trackme_conf"]["trackme_general"]["max_multi_thread_workers"]
        )

        # set instance_id
        self.instance_id = get_uuid()

        # log info
        logging.info(
            f'tenant_id="{self.tenant_id}", context="{self.context}", instance_id="{self.instance_id}", TrackMeSplkFlxParse is starting'
        )

        # get metric index
        metric_index = self.get_tenant_metric_idx()

        # counter
        count = 0

        # get thresholds collection
        try:
            thresholds_collection = self.get_thresholds_collection()
            logging.debug(
                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", thresholds_collection="{json.dumps(thresholds_collection, indent=2)}"'
            )
        except Exception as e:
            thresholds_collection = {}
            logging.error(
                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", failed to retrieve the thresholds collection, exception="{str(e)}"'
            )

        # get disruption queue collection
        try:
            disruption_queue_collection, disruption_queue_collection_keys = (
                self.get_disruption_queue_collection()
            )
            logging.debug(
                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", disruption_queue_collection="{json.dumps(disruption_queue_collection, indent=2)}"'
            )
        except Exception as e:
            disruption_queue_collection = {}
            disruption_queue_collection_keys = []
            logging.error(
                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", failed to retrieve the disruption queue collection, exception="{str(e)}"'
            )

        # get drilldown searches collection
        try:
            drilldown_searches_collection, drilldown_searches_collection_keys, drilldown_searches_collection_secondary_keys = self.get_drilldown_searches_collection()
            logging.debug(
                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", drilldown_searches_collection="{json.dumps(drilldown_searches_collection, indent=2)}"'
            )
        except Exception as e:
            drilldown_searches_collection = {}
            drilldown_searches_collection_keys = []
            drilldown_searches_collection_secondary_keys = set()
            logging.error(
                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", failed to retrieve the drilldown searches collection, exception="{str(e)}"'
            )

        # get default metrics collection
        try:
            default_metrics_collection, default_metrics_collection_keys, default_metrics_collection_secondary_keys = self.get_default_metrics_collection()
            logging.debug(
                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", default_metrics_collection="{json.dumps(default_metrics_collection, indent=2)}"'
            )
        except Exception as e:
            default_metrics_collection = {}
            default_metrics_collection_keys = []
            default_metrics_collection_secondary_keys = set()
            logging.error(
                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", failed to retrieve the default metrics collection, exception="{str(e)}"'
            )

        # Build header and target URL
        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Splunk {self._metadata.searchinfo.session_key}"
        headers["Content-Type"] = "application/json"

        # Create a requests session for better performance
        session = requests.Session()
        session.headers.update(headers)

        # for thresholds, if defined we will initialize the base dict with the first entity result (all entities share the same threshold definition from the tracker point of view)
        thresholds_records_base_dict = {}

        # thresholds dict mapping metric_name to list of entity keys that need this specific metric threshold
        thresholds_records_keys_to_add = {}

        # disruption queue records to be added once we have iterated through the records
        disruption_queue_records_to_add = []

        # last seen metrics records to be added once we have iterated through the records
        last_seen_metrics_records_to_add = []

        # drilldown searches records to be added once we have iterated through the records
        drilldown_searches_records_to_add = []

        # default metrics records to be added once we have iterated through the records
        default_metrics_records_to_add = []

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "iterate_through_records"        

        # Loop in the results
        for record in records:
            # increment
            count += 1

            yield_record = {}
            flx_record = {}

            # Capture fields with numeric values from the upstream record before
            # we transform it.  These field names are exposed as "numeric_fields"
            # in simulation results so the UI can offer them as metric-eligible
            # choices even when the search doesn't pre-define a metrics object.
            numeric_field_names = []
            for _k, _v in record.items():
                if _k in _STRUCTURAL_FIELDS or _k.startswith('_'):
                    continue
                # Check if the value is numeric (int, float, or a string that looks numeric)
                if isinstance(_v, (int, float)):
                    numeric_field_names.append(_k)
                elif isinstance(_v, str):
                    try:
                        float(_v)
                        numeric_field_names.append(_k)
                    except (ValueError, TypeError):
                        pass
            numeric_field_names.sort()

            #
            # field: _time
            #

            flx_time, record = self.normalize_time(record)

            #
            # field: object
            # mandatory: try to get the object field
            #

            try:
                flx_object = record.get("object")
            except Exception as e:
                flx_object = None
            if not flx_object:
                logging.error(
                    f'instance_id="{self.instance_id}", The field object is mandatory and should be rendered as a part of the search results, the object field could not be found in result="{json.dumps(record, indent=2)}"'
                )
                raise Exception(
                    "The field object is mandatory and should be rendered as a part of the search results, the object field could not be found in search results"
                )
            flx_object = decode_unicode(flx_object)

            #
            # field: alias
            # optional: if provided in the upstream results, use it, otherwise alias will be set explicitly equal to the short version of the object
            #

            flx_alias = record.get("alias", flx_object)
            flx_record["alias"] = flx_alias

            #
            # field: priority
            # optional: if provided in the upstream results, use it, otherwise priority will be set automatically
            #

            flx_priority = record.get("priority", None)
            if flx_priority:
                flx_record["priority"] = flx_priority

            #
            # field: tracker_name
            # optional
            #

            try:
                flx_tracker_name = record.get("tracker_name")
                # Don't store tracker_name directly here - will be stored as JSON array later for concurrent tracker support
                # flx_record["tracker_name"] = flx_tracker_name
            except Exception as e:
                flx_tracker_name = None

            #
            # field: group
            # optional
            #

            try:
                flx_group = record.get("group")
            except Exception as e:
                flx_group = None

            #
            # manage group and object
            #

            # group: if not specified in the search logic, set it equal to tracker_name
            if not flx_group:
                flx_group = str(flx_tracker_name)
            # add to the flx_record
            flx_record["group"] = flx_group

            # object: concatenate group and object if the object does not contain the group name yet
            regex = r"^%s\:" % (str(flx_group))
            if not re.search(regex, flx_object):
                flx_object = str(flx_group) + ":" + str(flx_object)

            # subgroup: optional
            try:
                flx_subgroup = record.get("subgroup")
                flx_record["subgroup"] = flx_subgroup
            except Exception as e:
                flx_subgroup = None

            # add to the flx_record
            flx_record["object"] = flx_object

            # convert the flx_object into an sha256 sum, we use the same value when storing into the KVstore
            flx_sha256 = hashlib.sha256(flx_object.encode("utf-8")).hexdigest()

            #
            # field: status
            # try to get the status field
            #

            flx_status = record.get("status")
            if flx_status is None:
                logging.error(
                    f'instance_id="{self.instance_id}", The field status is mandatory and should be rendered as a part of the search results, the status field could not be found in result="{json.dumps(record, indent=2)}"'
                )
                raise Exception(
                    "The field status is mandatory and should be rendered as a part of the search results, the status field could not be found in search results"
                )

            # the status should be an integer in the valid range [1, 2, 3]
            try:
                flx_status = int(flx_status)
            except Exception as e:
                raise Exception(
                    f'The field status is not an integer, value="{flx_status}"'
                )
            
            # validate status is in valid range
            if flx_status not in [1, 2, 3]:
                raise Exception(
                    f'The field status must be 1, 2, or 3, got value="{flx_status}"'
                )

            #
            # field: status_description_short
            # try to get the status_description_short field
            #

            try:
                flx_status_description_short = record.get("status_description_short")
                flx_record["status_description_short"] = flx_status_description_short
            except Exception as e:
                flx_status_description_short = None

            #
            # field: status_description
            # try to get the status_description field
            #

            try:
                flx_status_description = record.get("status_description")
                flx_record["status_description"] = flx_status_description
            except Exception as e:
                flx_status_description = None

            # fallback, if flx_status_description_short is not defined, use the flx_status_description
            if not flx_status_description_short:
                flx_status_description_short = flx_status_description
                flx_record["status_description_short"] = flx_status_description_short

            #
            # field: object_description
            # try to get the object_description field
            #

            try:
                flx_object_description = record.get("object_description")
                flx_record["object_description"] = flx_object_description
            except Exception as e:
                flx_object_description = None

            #
            # field: check_last_seen (option to check for last seen metrics for dedup purposes)
            # optional, turn into a boolean, accepts true/false (case insensitive), 0 or 1
            #

            try:
                flx_check_last_seen = record.get("check_last_seen")
                if flx_check_last_seen:
                    flx_check_last_seen = flx_check_last_seen.lower()
                    if flx_check_last_seen == "true" or flx_check_last_seen == "1":
                        flx_check_last_seen = True
                    else:
                        flx_check_last_seen = False

            except Exception as e:
                flx_check_last_seen = False

            # if check_last_seen is enabled, get the last seen collection
            if flx_check_last_seen:
                last_seen_collection_dict = self.get_last_seen_collection()

            #
            # field: metrics
            # try to get and parse the metrics
            #

            try:
                flx_metrics = record.get("metrics")
                flx_record["metrics"] = flx_metrics
            except Exception as e:
                flx_metrics = None

            # Extract or generate metrics
            flx_metrics_parsed = False
            flx_metrics_parsed_msg = None

            if flx_metrics:
                # store the exception, if any
                flx_metrics_parsed_exception = None

                # attempt json.loads
                try:
                    flx_metrics = json.loads(record.get("metrics"))
                    flx_metrics_parsed = True
                    flx_metrics_parsed_msg = (
                        "Metrics JSON were submitted and successfully parsed"
                    )
                except Exception as e:
                    flx_metrics_parsed = False
                    flx_metrics_parsed_exception = str(e)

                # attempt ast (if json is submitted with single quotes)
                if not flx_metrics_parsed:
                    try:
                        flx_metrics = ast.literal_eval(record.get("metrics"))
                        flx_metrics_parsed = True
                        flx_metrics_parsed_msg = (
                            "Metrics JSON were submitted and successfully parsed"
                        )
                    except Exception as e:
                        flx_metrics_parsed = False
                        flx_metrics_parsed_exception = str(e)

                if flx_metrics and not flx_metrics_parsed:
                    logging.error(
                        f'instance_id="{self.instance_id}", failed to load the submitted metrics as a JSON object, verify it is properly JSON encoded using single or double quotes delimiters, exception="{flx_metrics_parsed_exception}"'
                    )
                    flx_metrics = {}
                    flx_metrics_parsed_msg = f'Metrics JSON were submitted but could not be parsed properly, verify the JSON syntax, properties should be enquoted with single or double quotes, exception="{flx_metrics_parsed_exception}"'

            # if no metrics, the status will be generated by the decision maker
            else:
                flx_metrics = {}

                # if metrics_list is provided, update the message
                if "metrics_list" in record:
                    flx_metrics_parsed_msg = "Metrics were provided in metrics_list."
                else:
                    flx_metrics_parsed_msg = "There were no metrics provided, the status will be generated by the decision maker"

            #
            # field: metrics_list
            # try to get and parse the metrics stored in a list
            #
            flx_metrics_list_in_record = False
            flx_metrics_list = None

            # identify if metrics_list is in the record
            if "metrics_list" in record:
                flx_metrics_list_in_record = True

            # process only if needed
            if flx_metrics_list_in_record:

                try:
                    flx_metrics_list = record.get("metrics_list")

                    # check if not empty
                    if not len(flx_metrics_list) > 0:
                        flx_metrics_list = None

                    # If we have a list but the items are strings, parse each item
                    if isinstance(flx_metrics_list, list):
                        parsed_list = []
                        for item in flx_metrics_list:
                            if isinstance(item, str):
                                try:
                                    parsed_item = json.loads(item)
                                    parsed_list.append(parsed_item)
                                except json.JSONDecodeError as je:
                                    logging.warning(
                                        f'instance_id="{self.instance_id}", Failed to parse metrics list item: "{item}", error: {str(je)}'
                                    )
                                    continue
                            else:
                                # If it's already a dict, keep it as is
                                parsed_list.append(item)
                        flx_metrics_list = parsed_list

                    elif isinstance(
                        flx_metrics_list, str
                    ):  # if from the upstream stats a single point of metrics is returned, this would be a proper record
                        flx_metrics_list = [flx_metrics_list]

                        parsed_list = []
                        for item in flx_metrics_list:
                            if isinstance(item, str):
                                try:
                                    parsed_item = json.loads(item)
                                    parsed_list.append(parsed_item)
                                except json.JSONDecodeError as je:
                                    logging.warning(
                                        f'instance_id="{self.instance_id}", Failed to parse metrics list item: "{item}", error: {str(je)}'
                                    )
                                    continue
                            else:
                                # If it's already a dict, keep it as is
                                parsed_list.append(item)
                        flx_metrics_list = parsed_list

                    else:
                        flx_metrics_list = None

                    if flx_metrics_list:
                        flx_record["metrics_list"] = flx_metrics_list

                except Exception as e:
                    logging.error(f'instance_id="{self.instance_id}", Error processing metrics_list: {str(e)}')
                    flx_metrics_list = None

            if flx_metrics_list:

                # store the exception, if any
                flx_metrics_list_parsed = False
                flx_metrics_list_parsed_msg = None
                flx_metrics_list_parsed_exception = None

                if not isinstance(flx_metrics_list, list):
                    error_msg = f'The field metrics_list should be a list, value="{flx_metrics_list}"'
                    logging.error(f'instance_id="{self.instance_id}", {error_msg}')
                    flx_metrics_list_parsed_msg = error_msg
                    flx_metrics_list_parsed_exception = error_msg
                else:
                    flx_metrics_list_parsed = True
                    flx_metrics_list_parsed_msg = (
                        "Metrics list JSON were submitted and successfully parsed"
                    )

                if flx_metrics_list and not flx_metrics_list_parsed:
                    error_msg = f'failed to load the submitted metrics_list as a JSON object, verify it is properly JSON encoded using single or double quotes delimiters, exception="{flx_metrics_list_parsed_exception}"'
                    logging.error(f'instance_id="{self.instance_id}", {error_msg}')
                    flx_metrics_list_parsed_msg = error_msg

                else:  # we will verify the last seen metrics record if requested

                    #
                    # check last seen metrics
                    #

                    if flx_check_last_seen:

                        # to store the last seen metrics in metrics_list
                        last_seen_epoch_in_metrics_list = None

                        # get record from the last seen collection, if any
                        last_seen_collection_entity_record = (
                            last_seen_collection_dict.get(flx_sha256, {})
                        )

                        collection_last_seen_epoch = float(
                            last_seen_collection_entity_record.get(
                                "last_seen_metrics", 0
                            )
                        )

                        # iterate over the metrics_list
                        for flx_metrics_list_item in flx_metrics_list:

                            # get the epoch time (field time)
                            flx_metrics_list_item_epoch = float(
                                flx_metrics_list_item.get("time")
                            )

                            # debug logging
                            logging.debug(
                                f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", object="{flx_object}", object_id="{flx_sha256}", flx_metrics_list_item_epoch="{flx_metrics_list_item_epoch}" ({time.strftime("%c", time.gmtime(flx_metrics_list_item_epoch))}), record="{json.dumps(flx_metrics_list_item, indent=2)}"'
                            )

                            # track the maximum epoch time seen in metrics_list
                            if (
                                last_seen_epoch_in_metrics_list is None
                                or flx_metrics_list_item_epoch
                                > last_seen_epoch_in_metrics_list
                            ):
                                last_seen_epoch_in_metrics_list = (
                                    flx_metrics_list_item_epoch
                                )

                            # check if the epoch time is bigger than the last seen epoch, if not remove from the list
                            if (
                                not flx_metrics_list_item_epoch
                                > collection_last_seen_epoch
                            ):
                                logging.info(
                                    f'instance_id="{self.instance_id}", tenant_id="{self.tenant_id}", object="{flx_object}", object_id="{flx_sha256}", action="skipped", collection_last_seen_epoch="{collection_last_seen_epoch}" ({time.strftime("%c", time.gmtime(collection_last_seen_epoch))}) is bigger than flx_metrics_list_item_epoch="{flx_metrics_list_item_epoch}" ({time.strftime("%c", time.gmtime(flx_metrics_list_item_epoch))}), skipping record="{json.dumps(flx_metrics_list_item, indent=2)}"'
                                )
                                flx_metrics_list.remove(flx_metrics_list_item)

                        # create the updated kvstore record
                        last_seen_collection_entity_new_record = {
                            flx_sha256: {
                                "object": flx_object,
                                "last_seen_metrics": last_seen_epoch_in_metrics_list,
                            }
                        }

            ###################
            # default threshold
            ###################

            try:
                flx_default_threshold = record.get("default_threshold")
                flx_record["default_threshold"] = flx_default_threshold
            except Exception as e:
                flx_default_threshold = None

            # Initialize before the conditional block so they are always defined
            flx_default_threshold_parsed = False
            flx_default_threshold_parsed_msg = None

            if flx_default_threshold:
                flx_default_threshold_parsed_exception = None

                # attempt json.loads
                try:
                    flx_default_threshold = json.loads(flx_default_threshold)
                    flx_default_threshold_parsed = True
                    flx_default_threshold_parsed_msg = (
                        "Default threshold JSON was submitted and successfully parsed"
                    )
                except Exception as e:
                    flx_default_threshold_parsed = False
                    flx_default_threshold_parsed_exception = str(e)

                # attempt ast (if json is submitted with single quotes)
                if not flx_default_threshold_parsed:
                    try:
                        flx_default_threshold = ast.literal_eval(flx_default_threshold)
                        flx_default_threshold_parsed = True
                        flx_default_threshold_parsed_msg = "Default threshold JSON was submitted and successfully parsed"
                    except Exception as e:
                        flx_default_threshold_parsed = False
                        flx_default_threshold_parsed_exception = str(e)

                if "default_threshold" in record and not flx_default_threshold_parsed:
                    logging.error(
                        f'instance_id="{self.instance_id}", failed to load the submitted default threshold as a JSON object, verify it is properly JSON encoded using single or double quotes delimiters, exception="{flx_default_threshold_parsed_exception}"'
                    )
                    flx_default_threshold_parsed_msg = f'Default threshold JSON was submitted but could not be parsed properly, verify the JSON syntax, properties should be enquoted with single or double quotes, exception="{flx_default_threshold_parsed_exception}"'

                # Convert single threshold to list format for consistent processing
                if flx_default_threshold_parsed and not isinstance(
                    flx_default_threshold, list
                ):
                    flx_default_threshold = [flx_default_threshold]

                # check the structure of each default threshold
                if flx_default_threshold_parsed:
                    for threshold in flx_default_threshold:
                        if (
                            not "metric_name" in threshold
                            or not "operator" in threshold
                            or not "value" in threshold
                            or not "condition_true" in threshold
                        ):
                            logging.error(
                                f'instance_id="{self.instance_id}", the default threshold is missing one or more required properties, metric_name, operator, value, condition_true'
                            )
                            flx_default_threshold_parsed_msg = "the default threshold is missing one or more required properties, metric_name, operator, value, condition_true"
                            flx_default_threshold_parsed = False
                            break

            # if simulation mode, add an informational message related to the default threshold
            if self.context == "simulation" and "default_threshold" in record:
                if flx_default_threshold_parsed:
                    flx_record["default_threshold"] = flx_default_threshold
                else:
                    flx_record["default_threshold_message"] = (
                        flx_default_threshold_parsed_msg
                    )
                flx_record["default_threshold_message"] = (
                    flx_default_threshold_parsed_msg
                )

            ###################
            # disruption min time
            ###################

            try:
                flx_disruption_min_time_sec = record.get("disruption_min_time_sec")
                flx_record["disruption_min_time_sec"] = flx_disruption_min_time_sec
            except Exception as e:
                flx_disruption_min_time_sec = None

            if flx_disruption_min_time_sec is not None:
                try:
                    flx_disruption_min_time_sec = int(flx_disruption_min_time_sec)
                    if flx_disruption_min_time_sec < 0:
                        logging.error(
                            f'instance_id="{self.instance_id}", The field disruption_min_time_sec must be a positive integer or zero, value="{flx_disruption_min_time_sec}"'
                        )
                        flx_disruption_min_time_sec = None
                except Exception as e:
                    logging.error(
                        f'instance_id="{self.instance_id}", The field disruption_min_time_sec must be a positive integer or zero, value="{flx_disruption_min_time_sec}"'
                    )
                    flx_disruption_min_time_sec = None

            ###################
            # max_sec_inactive
            ###################

            try:
                flx_max_sec_inactive = record.get("max_sec_inactive", None)
            except Exception as e:
                flx_max_sec_inactive = None

            if flx_max_sec_inactive is not None:
                try:
                    # Handle tracker-keyed JSON format (from concurrent trackers)
                    if isinstance(flx_max_sec_inactive, str):
                        try:
                            parsed = json.loads(flx_max_sec_inactive)
                            if isinstance(parsed, dict):
                                # Tracker-keyed format: extract minimum value (excluding 0)
                                non_zero_values = [int(float(v)) for v in parsed.values() if int(float(v)) > 0]
                                if non_zero_values:
                                    flx_max_sec_inactive = min(non_zero_values)
                                else:
                                    # All values are 0, use 0 (disabled)
                                    flx_max_sec_inactive = 0
                            else:
                                # Not a dict, treat as simple numeric string
                                flx_max_sec_inactive = int(float(flx_max_sec_inactive))
                        except (json.JSONDecodeError, TypeError, ValueError):
                            # Not JSON, treat as simple numeric string
                            flx_max_sec_inactive = int(float(flx_max_sec_inactive))
                    elif isinstance(flx_max_sec_inactive, dict):
                        # Already a dict (tracker-keyed format)
                        non_zero_values = [int(float(v)) for v in flx_max_sec_inactive.values() if int(float(v)) > 0]
                        if non_zero_values:
                            flx_max_sec_inactive = min(non_zero_values)
                        else:
                            flx_max_sec_inactive = 0
                    else:
                        # Simple numeric value
                        flx_max_sec_inactive = int(flx_max_sec_inactive)
                    
                    if flx_max_sec_inactive < 0:
                        logging.error(
                            f'instance_id="{self.instance_id}", The field max_sec_inactive must be a positive integer or zero, value="{flx_max_sec_inactive}"'
                        )
                        flx_max_sec_inactive = None
                except Exception as e:
                    logging.error(
                        f'instance_id="{self.instance_id}", The field max_sec_inactive must be a positive integer or zero, value="{flx_max_sec_inactive}", exception="{str(e)}"'
                    )
                    flx_max_sec_inactive = None

            # if simulation mode, add an informational message related to the disruption min time
            if self.context == "simulation" and "disruption_min_time_sec" in record:
                if flx_disruption_min_time_sec is not None:
                    flx_record["disruption_min_time_sec"] = flx_disruption_min_time_sec
                    flx_record["disruption_min_time_sec_message"] = (
                        "Disruption min time was submitted and successfully parsed"
                    )
                else:
                    flx_record["disruption_min_time_sec_message"] = (
                        "The field disruption_min_time_sec must be a positive integer or zero"
                    )

            ####################
            # Drilldown searches
            ####################

            # Drilldown search
            try:
                drilldown_search = record.get("drilldown_search")
            except Exception as e:
                drilldown_search = None

            if drilldown_search:
                # try to get drilldown_search_earliest and drilldown_search_latest
                try:
                    drilldown_search_earliest = record.get("drilldown_search_earliest")
                    drilldown_search_latest = record.get("drilldown_search_latest")
                except Exception as e:
                    drilldown_search_earliest = None
                    drilldown_search_latest = None

                # if earliest or latest is not provided, set to default values (-24h, now)
                if not drilldown_search_earliest:
                    drilldown_search_earliest = "-24h"
                if not drilldown_search_latest:
                    drilldown_search_latest = "now"

                # Store drilldown search in flx_record so it gets yielded in simulation results
                flx_record["drilldown_search"] = drilldown_search
                flx_record["drilldown_search_earliest"] = drilldown_search_earliest
                flx_record["drilldown_search_latest"] = drilldown_search_latest

            # if mode is live, verify if the tracker_name is in the drilldown_searches_collection_secondary_keys, if not add a record with:
            # tracker_name, drilldown_search, drilldown_search_earliest, drilldown_search_latest
            if self.context == "live" and drilldown_search:
                # normalize the tracker name for consistent comparison
                normalized_tracker_name = normalize_flx_tracker_name(self.tenant_id, flx_tracker_name)
                if normalized_tracker_name not in drilldown_searches_collection_secondary_keys:
                    drilldown_searches_records_to_add.append({
                        "tracker_name": normalized_tracker_name,
                        "drilldown_search": drilldown_search,
                        "drilldown_search_earliest": drilldown_search_earliest,
                        "drilldown_search_latest": drilldown_search_latest,
                    })
                    # add the normalized name to secondary keys to prevent duplicates within the same run
                    drilldown_searches_collection_secondary_keys.add(normalized_tracker_name)

            ####################
            # Default metrics
            ####################

            # Default metric — normalize to a consistent CSV string
            # Accepts a single metric name, a CSV list, or a JSON/Python array
            try:
                default_metric = normalize_default_metric(record.get("default_metric"))
            except Exception as e:
                default_metric = None

            # Store default_metric in the output record so it is available in simulation results
            if default_metric:
                flx_record["default_metric"] = default_metric

            # if mode is live, verify if the tracker_name is in the default_metrics_collection_secondary_keys, if not add a record with:
            # tracker_name, metric_name
            if self.context == "live" and default_metric:
                # normalize the tracker name for consistent comparison
                normalized_tracker_name = normalize_flx_tracker_name(self.tenant_id, flx_tracker_name)
                if normalized_tracker_name not in default_metrics_collection_secondary_keys:
                    # Split CSV into a proper list so the endpoint creates one record per metric
                    metric_names_list = [m.strip() for m in default_metric.split(",") if m.strip()]
                    default_metrics_records_to_add.append({
                        "tracker_name": normalized_tracker_name,
                        "metric_name": metric_names_list,
                    })
                    # add the normalized name to secondary keys to prevent duplicates within the same run
                    default_metrics_collection_secondary_keys.add(normalized_tracker_name)

            ##################
            # Outliers metrics
            ##################

            #
            # field: outliers_metrics
            # try to get and parse the ML outliers metrics
            #

            try:
                flx_outliers_metrics = record.get("outliers_metrics")
                flx_record["outliers_metrics"] = flx_outliers_metrics
            except Exception as e:
                flx_outliers_metrics = None

            # Extract or generate metrics
            flx_outliers_metrics_parsed = False
            flx_outliers_metrics_parsed_msg = None

            if flx_outliers_metrics:
                # store the exception, if any
                flx_outliers_metrics_parsed_exception = None

                # attempt json.loads
                try:
                    flx_outliers_metrics = json.loads(record.get("outliers_metrics"))
                    flx_outliers_metrics_parsed = True

                    # test extracting values
                    for flx_outliers_metric in flx_outliers_metrics:
                        kpi_name = f"splk.flx.{flx_outliers_metric}"
                        kpi_dict = flx_outliers_metrics[flx_outliers_metric]
                        value_alert_lower_breached = kpi_dict.get(
                            "alert_lower_breached"
                        )
                        value_alert_upper_breached = kpi_dict.get(
                            "alert_upper_breached"
                        )
                        logging.debug(
                            f'instance_id="{self.instance_id}", Extracting outliers_metrics, kpi_name="{kpi_name}", alert_lower_breached="{value_alert_lower_breached}", alert_upper_breached="{value_alert_upper_breached}"'
                        )

                    flx_outliers_metrics_parsed_msg = (
                        "Outliers Metrics JSON were submitted and successfully parsed"
                    )
                except Exception as e:
                    flx_outliers_metrics_parsed = False
                    flx_outliers_metrics_parsed_exception = str(e)

                # attempt ast (if json is submitted with single quotes)
                if not flx_outliers_metrics_parsed:
                    try:
                        flx_outliers_metrics = ast.literal_eval(
                            record.get("outliers_metrics")
                        )
                        flx_outliers_metrics_parsed = True

                        # test extracting values
                        for flx_outliers_metric in flx_outliers_metrics:
                            kpi_name = f"splk.flx.{flx_outliers_metric}"
                            kpi_dict = flx_outliers_metrics[flx_outliers_metric]
                            value_alert_lower_breached = kpi_dict.get(
                                "alert_lower_breached"
                            )
                            value_alert_upper_breached = kpi_dict.get(
                                "alert_upper_breached"
                            )
                            logging.debug(
                                f'instance_id="{self.instance_id}", Extracting outliers_metrics, kpi_name="{kpi_name}", alert_lower_breached="{value_alert_lower_breached}", alert_upper_breached="{value_alert_upper_breached}"'
                            )

                        flx_outliers_metrics_parsed_msg = "Outliers Metrics JSON were submitted and successfully parsed"
                    except Exception as e:
                        flx_outliers_metrics_parsed = False
                        flx_outliers_metrics_parsed_exception = str(e)

                if flx_outliers_metrics and not flx_outliers_metrics_parsed:
                    logging.error(
                        f'instance_id="{self.instance_id}", failed to load the submitted outliers metrics as a JSON object, verify it is properly JSON encoded using single or double quotes delimitors'
                    )
                    flx_outliers_metrics = flx_outliers_metrics
                    flx_outliers_metrics_parsed_msg = f'Outliers Metrics JSON were submitted but could not be parsed properly, verify the JSON syntax, properties should be enquoted with single or double quotes, exception="{flx_outliers_metrics_parsed_exception}"'

            # if no metrics, include the message only only
            else:
                flx_outliers_metrics = {}
                flx_outliers_metrics_parsed_msg = (
                    "There were no outliers metrics provided"
                )

            #
            # Generate and index metrics
            # if not in simulation mode, ingest metrics now
            #

            if self.context == "live":

                # process metrics if no metrics_list is provided
                if not flx_metrics_list:
                    try:
                        trackme_flx_gen_metrics(
                            flx_time,
                            self.tenant_id,
                            flx_object,
                            flx_sha256,
                            metric_index,
                            json.dumps(flx_metrics),
                        )
                    except Exception as e:
                        error_msg = f'Failed to convert the results to metrics with exception="{str(e)}"'
                        logging.error(f'instance_id="{self.instance_id}", {error_msg}')
                        # do not raise an exception, continue

                # process metrics_list, if any
                if flx_metrics_list:

                    try:
                        trackme_flx_gen_metrics_from_list(
                            self.tenant_id,
                            flx_object,
                            flx_sha256,
                            metric_index,
                            flx_metrics_list,
                        )

                    except Exception as e:
                        error_msg = (
                            f'Failed to process metrics_list with exception="{str(e)}"'
                        )
                        logging.error(f'instance_id="{self.instance_id}", {error_msg}')
                        # do not raise an exception, continue

                    # update the last seen metrics in the KVstore
                    if flx_check_last_seen:
                        try:
                            # Add to the list instead of updating immediately
                            last_seen_metrics_records_to_add.append(
                                last_seen_collection_entity_new_record
                            )
                        except Exception as e:
                            error_msg = f'Failed to add last seen metrics record to batch list with exception="{str(e)}"'
                            logging.error(f'instance_id="{self.instance_id}", {error_msg}')

            ########################
            # End Processing metrics
            ########################

            ####################################
            # Start Processing default threshold
            ####################################

            #
            # Add the default threshold calling the API endpoint if default threshold is provided and this entity does not have a threshold already
            #

            if self.context == "live":

                if flx_default_threshold and (flx_metrics or flx_metrics_list):
                    # Process each threshold in the list
                    for threshold in flx_default_threshold:
                        metric_name = threshold.get("metric_name")
                        
                        # Skip if metric_name is missing or empty
                        if not metric_name:
                            logging.warning(
                                f'instance_id="{self.instance_id}", skipping threshold with missing or empty metric_name for entity="{flx_sha256}", threshold="{json.dumps(threshold)}"'
                            )
                            continue
                        
                        # Check if this specific threshold (entity + metric_name) already exists
                        threshold_exists = False
                        if flx_sha256 in thresholds_collection:
                            entity_thresholds = thresholds_collection[flx_sha256]
                            # thresholds_collection is now nested: dict[object_id][metric_name]
                            # Check if it's the new nested format (dict of dicts) or old format (single dict)
                            if isinstance(entity_thresholds, dict):
                                # New format: nested dict[object_id][metric_name] - check if metric_name is a key
                                if metric_name and metric_name in entity_thresholds:
                                    threshold_exists = True
                                    logging.debug(
                                        f'instance_id="{self.instance_id}", found existing threshold for entity="{flx_sha256}", metric_name="{metric_name}", skipping addition of default threshold'
                                    )
                                # Old format: single threshold dict with metric_name as a value field
                                # Only check old format if metric_name is not None to avoid None == None false matches
                                elif metric_name is not None and entity_thresholds.get("metric_name") == metric_name:
                                    threshold_exists = True
                                    logging.debug(
                                        f'instance_id="{self.instance_id}", found existing threshold for entity="{flx_sha256}", metric_name="{metric_name}" (old format), skipping addition of default threshold'
                                    )
                        
                        if not threshold_exists:
                            data = {
                                "tenant_id": self.tenant_id,
                                "metric_name": metric_name,
                                "value": threshold.get("value"),
                                "operator": threshold.get("operator"),
                                "condition_true": threshold.get("condition_true"),
                            }
                            threshold_comment = threshold.get(
                                "comment", "default threshold"
                            )
                            data["comment"] = threshold_comment

                            # Pass through variable threshold fields if provided
                            if threshold.get("variable_threshold_enabled"):
                                data["variable_threshold_enabled"] = str(threshold["variable_threshold_enabled"]).lower()
                            if threshold.get("variable_threshold_default") is not None:
                                try:
                                    data["variable_threshold_default"] = float(threshold["variable_threshold_default"])
                                except (ValueError, TypeError):
                                    pass  # Skip non-numeric values, matching REST handler pattern
                            if threshold.get("variable_threshold_slots") is not None:
                                # Normalize and validate slots before storing
                                slots = threshold["variable_threshold_slots"]
                                if isinstance(slots, (dict, list)):
                                    slots_json = json.dumps(slots)
                                else:
                                    slots_json = slots
                                try:
                                    slots_parsed = json.loads(slots_json) if isinstance(slots_json, str) else slots_json
                                    from trackme_libs_decisionmaker import validate_variable_threshold_slots
                                    slot_errors = validate_variable_threshold_slots(slots_parsed)
                                    if not slot_errors:
                                        data["variable_threshold_slots"] = slots_json
                                    else:
                                        logger.warning(f"Invalid variable_threshold_slots in tracker config: {'; '.join(slot_errors)}, skipping")
                                except (json.JSONDecodeError, TypeError) as e:
                                    logger.warning(f"Failed to parse variable_threshold_slots: {str(e)}, skipping")

                            # add to the list of records to be added if this particular threshold is not already in the list
                            if (
                                metric_name
                                not in thresholds_records_base_dict
                            ):
                                thresholds_records_base_dict[
                                    metric_name
                                ] = data

                            # add to the list of keys for this specific metric
                            if metric_name not in thresholds_records_keys_to_add:
                                thresholds_records_keys_to_add[metric_name] = []
                            if flx_sha256 not in thresholds_records_keys_to_add[metric_name]:
                                thresholds_records_keys_to_add[metric_name].append(flx_sha256)

            ##################################
            # End Processing default threshold
            ##################################

            ####################################
            # Start Processing disruption min time
            ####################################

            # Note: disruption_min_time_sec is now stored as tracker-keyed JSON in the main FLX collection
            # The disruption queue record will be updated in trackmedecisionmaker.py using the aggregated maximum value
            # We no longer create disruption queue records here to avoid conflicts with concurrent trackers
            # The disruption queue will be managed in trackmedecisionmaker.py after aggregation

            ##################################
            # End Processing disruption min time
            ##################################

            # get a _raw, if any, otherwise build
            try:
                raw = record.get("_raw")
                if raw and not self.remove_raw:
                    flx_record["_raw"] = raw
                elif self.remove_raw and "_raw" in flx_record:
                    # remove _raw from flx_record if remove_raw is True
                    del flx_record["_raw"]
            except Exception as e:
                raw = {}
                for k in record:
                    raw[k] = record[k]

            # finally
            yield_record[flx_object] = flx_record

            # Normalize tracker_name for consistent storage
            normalized_tracker_name = None
            if flx_tracker_name:
                normalized_tracker_name = normalize_flx_tracker_name(self.tenant_id, flx_tracker_name)

            # Store tracker_name as JSON array for concurrent tracker support
            # Store metrics, status_description, and status_description_short as JSON objects keyed by tracker_name
            # for concurrent tracker support
            if normalized_tracker_name:
                # Store tracker_name as JSON array (will be merged in trackmepersistentfields)
                flx_record["tracker_name"] = json.dumps([normalized_tracker_name])
                # Convert metrics to tracker-keyed JSON object
                if isinstance(flx_metrics, dict):
                    metrics_by_tracker = {normalized_tracker_name: flx_metrics}
                    flx_record["metrics"] = json.dumps(metrics_by_tracker)
                else:
                    # If metrics is not a dict, store empty dict for this tracker
                    metrics_by_tracker = {normalized_tracker_name: {}}
                    flx_record["metrics"] = json.dumps(metrics_by_tracker)
                
                # Convert status_description to tracker-keyed JSON object
                # Only create entry if we have actual content (not empty/None)
                if flx_status_description:
                    status_description_by_tracker = {normalized_tracker_name: flx_status_description}
                    flx_record["status_description"] = json.dumps(status_description_by_tracker)
                # If empty, don't create the field (will be preserved from existing record if present)
                
                # Convert status_description_short to tracker-keyed JSON object
                # Only create entry if we have actual content (not empty/None)
                if flx_status_description_short:
                    status_description_short_by_tracker = {normalized_tracker_name: flx_status_description_short}
                    flx_record["status_description_short"] = json.dumps(status_description_short_by_tracker)
                # If empty, don't create the field (will be preserved from existing record if present)
                
                # Convert object_description to tracker-keyed JSON object
                # Only create entry if we have actual content (not empty/None)
                if flx_object_description:
                    object_description_by_tracker = {normalized_tracker_name: flx_object_description}
                    flx_record["object_description"] = json.dumps(object_description_by_tracker)
                # If empty, don't create the field (will be preserved from existing record if present)
                
                # Convert disruption_min_time_sec to tracker-keyed JSON object
                # Only create entry if we have actual content (not empty/None)
                if flx_disruption_min_time_sec is not None:
                    disruption_min_time_by_tracker = {normalized_tracker_name: flx_disruption_min_time_sec}
                    flx_record["disruption_min_time_sec"] = json.dumps(disruption_min_time_by_tracker)
                # If empty, don't create the field (will be preserved from existing record if present)
                
                # Convert max_sec_inactive to tracker-keyed JSON object
                # Only create entry if we have actual content (not empty/None)
                if flx_max_sec_inactive is not None:
                    max_sec_inactive_by_tracker = {normalized_tracker_name: flx_max_sec_inactive}
                    flx_record["max_sec_inactive"] = json.dumps(max_sec_inactive_by_tracker)
                # If empty, don't create the field (will be preserved from existing record if present)
                
                # Convert status to tracker-keyed JSON object
                # Status is mandatory, so always create entry
                if flx_status is not None:
                    status_by_tracker = {normalized_tracker_name: flx_status}
                    flx_record["status"] = json.dumps(status_by_tracker)
            else:
                # No tracker name, store as-is (backward compatibility)
                flx_record["metrics"] = flx_metrics
                flx_record["status_description"] = flx_status_description
                flx_record["status_description_short"] = flx_status_description_short
                flx_record["object_description"] = flx_object_description
                # Store status as-is for backward compatibility (no tracker name)
                flx_record["status"] = flx_status
                # Store tracker_name as-is for backward compatibility (not as JSON array)
                if flx_tracker_name:
                    flx_record["tracker_name"] = flx_tracker_name
                # max_sec_inactive stored as-is for backward compatibility (no tracker name)
                # disruption_min_time_sec stored as-is for backward compatibility (no tracker name)

            # add outliers_metrics
            flx_record["outliers_metrics"] = flx_outliers_metrics

            # extra_attibutes, this is optional
            flx_extra_attributes = record.get("extra_attributes", None)
            flx_record["extra_attributes"] = flx_extra_attributes

            # max_sec_inactive is already assigned earlier (before tracker-keyed JSON conversion)

            # if in simulation, add an informational message related to the metrics management
            if self.context == "simulation":
                # add metrics_message
                flx_record["metrics_message"] = flx_metrics_parsed_msg

                # add metrics_list_message, if any
                if flx_metrics_list:
                    flx_record["metrics_list_message"] = flx_metrics_list_parsed_msg

                # add outliers_metrics_message
                flx_record["outliers_metrics_message"] = flx_outliers_metrics_parsed_msg

                # yield
                # In simulation mode, use raw scalar values (not tracker-keyed JSON)
                # so the UI can parse them directly for pre-population
                yield_record = {
                    "group": flx_group,
                    "object": flx_object,
                    "alias": flx_alias,
                    "object_category": "splk-flx",
                    "status": flx_status,
                    "metrics": flx_record.get("metrics", flx_metrics),
                    "metrics_message": flx_metrics_parsed_msg,
                    "outliers_metrics": flx_outliers_metrics,
                    "outliers_metrics_message": flx_outliers_metrics_parsed_msg,
                    "extra_attributes": flx_extra_attributes,
                    "max_sec_inactive": flx_max_sec_inactive,
                }
                # Only include status_description, status_description_short, and object_description if they have content
                if "status_description" in flx_record:
                    yield_record["status_description"] = flx_record["status_description"]
                if "status_description_short" in flx_record:
                    yield_record["status_description_short"] = flx_record["status_description_short"]
                if "object_description" in flx_record:
                    yield_record["object_description"] = flx_record["object_description"]

                # conditionally include _time and _raw
                if not self.remove_time:
                    yield_record["_time"] = flx_time
                if not self.remove_raw:
                    yield_record["_raw"] = flx_record

                # add metrics_list_message, if any
                if flx_metrics_list:
                    yield_record["metrics_list_message"] = flx_metrics_list_parsed_msg

                # Include tracker option fields so they appear as top-level fields in simulation results
                if "default_metric" in flx_record:
                    yield_record["default_metric"] = flx_record["default_metric"]
                if "default_threshold" in flx_record:
                    yield_record["default_threshold"] = flx_record["default_threshold"]
                if "default_threshold_message" in flx_record:
                    yield_record["default_threshold_message"] = flx_record["default_threshold_message"]
                # Use raw scalar value for disruption_min_time_sec (not tracker-keyed JSON)
                if flx_disruption_min_time_sec is not None:
                    yield_record["disruption_min_time_sec"] = flx_disruption_min_time_sec
                if "disruption_min_time_sec_message" in flx_record:
                    yield_record["disruption_min_time_sec_message"] = flx_record["disruption_min_time_sec_message"]
                if "drilldown_search" in flx_record:
                    yield_record["drilldown_search"] = flx_record["drilldown_search"]
                if "drilldown_search_earliest" in flx_record:
                    yield_record["drilldown_search_earliest"] = flx_record["drilldown_search_earliest"]
                if "drilldown_search_latest" in flx_record:
                    yield_record["drilldown_search_latest"] = flx_record["drilldown_search_latest"]

                # Include the list of upstream numeric fields so the UI can
                # offer them as choices for field name / default metric
                if numeric_field_names:
                    yield_record["numeric_fields"] = ",".join(numeric_field_names)

                # conditional additions to the final result
                if flx_priority:
                    yield_record["priority"] = flx_priority

                # add subgroup, if any
                if flx_subgroup:
                    yield_record["subgroup"] = flx_subgroup

                yield yield_record

            else:
                # yield
                # Use the tracker-keyed JSON objects from flx_record
                yield_record = {
                    "group": flx_group,
                    "object": flx_object,
                    "alias": flx_alias,
                    "object_category": "splk-flx",
                    "status": flx_status,
                    "metrics": flx_record.get("metrics", flx_metrics),
                    "outliers_metrics": flx_outliers_metrics,
                    "extra_attributes": flx_extra_attributes,
                    "max_sec_inactive": flx_record.get("max_sec_inactive", flx_max_sec_inactive),
                    "flx_type": self.flx_type,
                }
                # Only include status_description, status_description_short, and object_description if they have content
                if "status_description" in flx_record:
                    yield_record["status_description"] = flx_record["status_description"]
                if "status_description_short" in flx_record:
                    yield_record["status_description_short"] = flx_record["status_description_short"]
                if "object_description" in flx_record:
                    yield_record["object_description"] = flx_record["object_description"]
                # Include tracker option fields for consistency with simulation yield path
                if "default_metric" in flx_record:
                    yield_record["default_metric"] = flx_record["default_metric"]
                if "default_threshold" in flx_record:
                    yield_record["default_threshold"] = flx_record["default_threshold"]
                if "default_threshold_message" in flx_record:
                    yield_record["default_threshold_message"] = flx_record["default_threshold_message"]
                if "disruption_min_time_sec" in flx_record:
                    yield_record["disruption_min_time_sec"] = flx_record["disruption_min_time_sec"]
                if "disruption_min_time_sec_message" in flx_record:
                    yield_record["disruption_min_time_sec_message"] = flx_record["disruption_min_time_sec_message"]
                if "drilldown_search" in flx_record:
                    yield_record["drilldown_search"] = flx_record["drilldown_search"]
                if "drilldown_search_earliest" in flx_record:
                    yield_record["drilldown_search_earliest"] = flx_record["drilldown_search_earliest"]
                if "drilldown_search_latest" in flx_record:
                    yield_record["drilldown_search_latest"] = flx_record["drilldown_search_latest"]

                # conditionally include _time and _raw
                if not self.remove_time:
                    yield_record["_time"] = flx_time
                if not self.remove_raw:
                    yield_record["_raw"] = flx_record

                # conditional additions to the final result
                if flx_priority:
                    yield_record["priority"] = flx_priority

                # add subgroup, if any
                if flx_subgroup:
                    yield_record["subgroup"] = flx_subgroup

                yield yield_record

            # log info
            logging.debug(
                f'tenant_id="{self.tenant_id}", context="{self.context}", processed result="{json.dumps(flx_record, indent=2)}"'
            )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_thresholds_records"

        # process the thresholds records update limiting to one rest call per threshold rule
        endpoint = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_flx/write/flx_thresholds_add"

        if thresholds_records_keys_to_add:

            # Iterate through each metric name in the base dict
            for metric_name, data in thresholds_records_base_dict.items():
                # add keys_list to the data (only include keys for this specific metric)
                if metric_name in thresholds_records_keys_to_add:
                    data["keys_list"] = ",".join(thresholds_records_keys_to_add[metric_name])
                else:
                    # Skip this metric if no entities need it
                    continue

                try:
                    response = session.post(
                        endpoint,
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    response.raise_for_status()
                    logging.info(
                        f'tenant_id="{self.tenant_id}", default threshold added successfully for metric {metric_name} and {len(thresholds_records_keys_to_add[metric_name])} entities, http_status="{response.status_code}", data="{json.dumps(data, indent=2)}"'
                    )
                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", failed to add the default threshold, exception="{str(e)}", data="{json.dumps(data, indent=2)}"'
                    )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_disruption_queue_records"

        # process the disruption queue records batch update
        if disruption_queue_records_to_add:
            try:
                batch_update_worker(
                    f"kv_trackme_common_disruption_queue_tenant_{self.tenant_id}",
                    self.service.kvstore[f"kv_trackme_common_disruption_queue_tenant_{self.tenant_id}"],
                    disruption_queue_records_to_add,
                    self.instance_id,
                    get_uuid(),
                    task_name="disruption_queue_update",
                    max_multi_thread_workers=max_multi_thread_workers,
                )
                logging.info(
                    f'tenant_id="{self.tenant_id}", disruption queue records batch update completed successfully for {len(disruption_queue_records_to_add)} records'
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", failed to process the disruption queue records batch update, exception="{str(e)}"'
                )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_drilldown_searches_records"

        # process the drilldown searches records if needed, run a single POST call to the endpoint
        if drilldown_searches_records_to_add:

            # endpoint
            endpoint = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_flx/write/flx_update_drilldown_searches"

            # try the call
            try:
                response = session.post(
                    endpoint,
                    data=json.dumps({
                        "tenant_id": self.tenant_id,
                        "drilldown_records": drilldown_searches_records_to_add,
                    }),
                    verify=False,
                    timeout=600,
                )
                response.raise_for_status()
                logging.info(
                    f'tenant_id="{self.tenant_id}", drilldown searches records batch update completed successfully for {len(drilldown_searches_records_to_add)} records, http_status="{response.status_code}", data="{json.dumps(drilldown_searches_records_to_add, indent=2)}"'
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", failed to process the drilldown searches records batch update, exception="{str(e)}", data="{json.dumps(drilldown_searches_records_to_add, indent=2)}"'
                )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_default_metrics_records"

        # process the default metrics records if needed, run a single POST call to the endpoint
        if default_metrics_records_to_add:

            # endpoint
            endpoint = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_flx/write/flx_update_default_metrics"

            # try the call
            try:
                response = session.post(
                    endpoint,
                    data=json.dumps({
                        "tenant_id": self.tenant_id,
                        "default_metric_records": default_metrics_records_to_add,
                    }),
                    verify=False,
                    timeout=600,
                )
                response.raise_for_status()
                logging.info(
                    f'tenant_id="{self.tenant_id}", default metrics records batch update completed successfully for {len(default_metrics_records_to_add)} records, http_status="{response.status_code}", data="{json.dumps(default_metrics_records_to_add, indent=2)}"'
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", failed to process the default metrics records batch update, exception="{str(e)}", data="{json.dumps(default_metrics_records_to_add, indent=2)}"'
                )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_last_seen_metrics_records"

        # process the last seen metrics records batch update
        if last_seen_metrics_records_to_add:
            try:
                # Convert nested structure to flat dictionary format for batch_update_worker
                last_seen_metrics_dict = {}
                for record in last_seen_metrics_records_to_add:
                    last_seen_metrics_dict.update(record)
                
                batch_update_worker(
                    f"kv_trackme_flx_last_seen_activity_tenant_{self.tenant_id}",
                    self.service.kvstore[f"kv_trackme_flx_last_seen_activity_tenant_{self.tenant_id}"],
                    last_seen_metrics_dict,
                    self.instance_id,
                    get_uuid(),
                    task_name="last_seen_activity_update",
                    max_multi_thread_workers=max_multi_thread_workers,
                )
                logging.info(
                    f'tenant_id="{self.tenant_id}", last seen metrics records batch update completed successfully for {len(last_seen_metrics_records_to_add)} records'
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", failed to process the last seen metrics records batch update, exception="{str(e)}"'
                )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # log info
        run_time = round(time.time() - start, 3)
        logging.info(
            f'tenant_id="{self.tenant_id}", context="{self.context}", instance_id="{self.instance_id}", TrackMeSplkFlxParse has terminated successfully, turn debug mode on for more details, results_count="{count}", run_time={run_time}'
        )


dispatch(TrackMeSplkFlxParse, sys.argv, sys.stdin, sys.stdout, __name__)

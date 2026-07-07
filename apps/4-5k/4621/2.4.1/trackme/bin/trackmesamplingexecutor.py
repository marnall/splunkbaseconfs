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
import re
import json
import hashlib
import fnmatch

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_sampling_executor.log" % splunkhome,
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
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# import trackme libs
from trackme_libs import (
    trackme_reqinfo,
    trackme_vtenant_account,
    trackme_register_tenant_object_summary,
    trackme_vtenant_component_info,
    run_splunk_search,
    trackme_handler_events,
)

# import trackme libs croniter
from trackme_libs_croniter import cron_to_seconds

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import data sampling libs (renamed in #1717 to follow the
# `trackme_libs_*` naming convention).
from trackme_libs_datasampling_ootb_regex import ootb_regex_list

# import TrackMe get data libs
from trackme_libs_get_data import (
    get_full_kv_collection,
)

# import TrackMe feeds libs
from trackme_libs_splk_feeds import (
    trackme_splk_dsm_data_sampling_gen_metrics,
    trackme_splk_dsm_data_sampling_total_run_time_gen_metrics,
)

# import TrackMe decision maker libs
from trackme_libs_decisionmaker import convert_epoch_to_datetime


_GLOBAL_FLAG_RE = re.compile(r"\(\?([aiLmsux]+)\)")


def sanitize_regex_global_flags(pattern):
    """
    Move standalone global inline flags to the start of the pattern.
    Python 3.13+ raises PatternError when global flags like (?i)
    appear anywhere other than position 0 (e.g. ``^(?i)...``).
    Scoped flags such as ``(?i:...)`` are unaffected.
    """
    found = _GLOBAL_FLAG_RE.findall(pattern)
    if not found:
        return pattern
    cleaned = _GLOBAL_FLAG_RE.sub("", pattern)
    combined = "".join(dict.fromkeys("".join(found)))
    return f"(?{combined}){cleaned}"


@Configuration(distributed=False)
class DataSamplingExecutor(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    mode = Option(
        doc="""
        **Syntax:** **mode=****
        **Description:** The data sampling executor mode, valid options are: run_sampling | get_samples""",
        require=False,
        default="run_sampling",
        validate=validators.Match(
            "mode",
            r"^(run_sampling|test_sampling|test_model|get_samples|get_live_samples|show_kvrecord)$",
        ),
    )

    object = Option(
        doc="""
        **Syntax:** **mode=****
        **Description:** The object target, only used if mode is get_samples""",
        require=False,
        default="*",
        validate=validators.Match("object", r"^.*$"),
    )

    earliest = Option(
        doc="""
        **Syntax:** **earliest=****
        **Description:** The earliest time quantifier.""",
        require=False,
        default="-24h",
    )

    latest = Option(
        doc="""
        **Syntax:** **latest=****
        **Description:** The latest time quantifier.""",
        require=False,
        default="now",
    )

    max_runtime = Option(
        doc="""
        **Syntax:** **max_runtime=****
        **Description:** The max runtime for the job in seconds, defaults to 15 minutes less 120 seconds of margin.""",
        require=False,
        default="900",
        validate=validators.Match("max_runtime", r"^\d*$"),
    )

    get_samples_max_count = Option(
        doc="""
        **Syntax:** **get_samples_max_count=****
        **Description:** The max number of events to be sampled in get sample mode, default to 10k events.""",
        require=False,
        default="10000",
        validate=validators.Match("get_samples_max_count", r"^\d*$"),
    )

    regex_expression = Option(
        doc="""
        **Syntax:** **regex_expression=****
        **Description:** If using test_model, the regex expression and model_type should be provided.""",
        require=False,
        default=None,
        validate=validators.Match("regex_expression", r"^.*"),
    )

    model_type = Option(
        doc="""
        **Syntax:** **model_type=****
        **Description:** If using test_model, the regex expression, model_type, model_name and sourcetype_scope should be provided.""",
        require=False,
        default=None,
        validate=validators.Match("model_type", r"^(inclusive|exclusive)$"),
    )

    model_name = Option(
        doc="""
        **Syntax:** **model_name=****
        **Description:** If using test_model, the regex expression, model_type, model_name and sourcetype_scope should be provided.""",
        require=False,
        default=None,
        validate=validators.Match("model_name", r"^.*$"),
    )

    sourcetype_scope = Option(
        doc="""
        **Syntax:** **sourcetype_scope=****
        **Description:** If using test_model, the regex expression, model_type, model_name and sourcetype_scope should be provided.""",
        require=False,
        default=None,
        validate=validators.Match("sourcetype_scope", r"^.*$"),
    )

    """
    Function to return the tenant metric index.
    """

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
                logging.error(error_msg)
                raise Exception(error_msg)
            else:
                response_data = json.loads(json.dumps(response.json(), indent=1))
                tenant_trackme_metric_idx = response_data["trackme_metric_idx"]
        except Exception as e:
            error_msg = (
                f'failed to retrieve the tenant metric index, exception="{str(e)}"'
            )
            logging.error(error_msg)
            raise Exception(error_msg)

        return tenant_trackme_metric_idx

    """
    Functions to return the entity_info for a given object_id.
    
    """

    def get_entity_info(self, object_field, value):

        if object_field == "object_id":
            json_data = {
                "tenant_id": self.tenant_id,
                "object_id": value,
            }

        elif object_field == "object":
            json_data = {
                "tenant_id": self.tenant_id,
                "object": value,
            }

        else:
            raise Exception(f'object_field="{object_field}" is not supported')

        try:

            target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_dsm/ds_entity_info"

            entity_info_response = requests.post(
                target_url,
                headers={
                    "Authorization": f"Splunk {self._metadata.searchinfo.session_key}",
                    "Content-Type": "application/json",
                },
                verify=False,
                data=json.dumps(json_data),
                timeout=600,
            )

            if entity_info_response.status_code not in (200, 201, 204):
                error_msg = f'failed to retrieve the entity info, data="{json.dumps(json_data, indent=2)}", response.status_code="{entity_info_response.status_code}", response.text="{entity_info_response.text}"'
                logging.error(error_msg)
                raise Exception(error_msg)

            else:
                return entity_info_response.json()

        except Exception as e:
            error_msg = f'tenant_id="{self.tenant_id}", function get_entity_info, object requested using object_field="{object_field}" with value="{value}" could not be found, exception="{str(e)}"'
            logging.error(error_msg)
            raise Exception(error_msg)

    """
    Function to get sampling system settings
    """

    def get_sampling_system_settings(self, reqinfo):

        # Minimum time in seconds between two iterations of sampling per entity
        splk_data_sampling_min_time_btw_iterations_seconds = int(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_min_time_btw_iterations_seconds"
            ]
        )

        # number of records to be sampled per entity
        splk_data_sampling_no_records_per_entity = int(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_no_records_per_entity"
            ]
        )

        # number of records to be stored in the KVstore for inspection purposes
        splk_data_sampling_no_records_saved_kvrecord = int(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_no_records_saved_kvrecord"
            ]
        )

        # max char size of the raw sample to be stored in the KVstore
        splk_data_sampling_records_kvrecord_truncate_size = int(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_records_kvrecord_truncate_size"
            ]
        )

        # Min inclusive model matched percentage (float)
        splk_data_sampling_pct_min_major_inclusive_model_match = float(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_pct_min_major_inclusive_model_match"
            ]
        )

        # Max exclusive model matched percentage (float)
        splk_data_sampling_pct_max_exclusive_model_match = float(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_pct_max_exclusive_model_match"
            ]
        )

        # The relative time window size in seconds
        splk_data_sampling_relative_time_window_seconds = int(
            reqinfo["trackme_conf"]["splk_data_sampling"][
                "splk_data_sampling_relative_time_window_seconds"
            ]
        )

        return (
            splk_data_sampling_min_time_btw_iterations_seconds,
            splk_data_sampling_no_records_per_entity,
            splk_data_sampling_no_records_saved_kvrecord,
            splk_data_sampling_records_kvrecord_truncate_size,
            splk_data_sampling_pct_min_major_inclusive_model_match,
            splk_data_sampling_pct_max_exclusive_model_match,
            splk_data_sampling_relative_time_window_seconds,
        )

    """
    Function to get sampling entity settings
    """

    def get_sampling_entity_settings(
        self,
        kvrecord,
        splk_data_sampling_pct_min_major_inclusive_model_match,
        splk_data_sampling_pct_max_exclusive_model_match,
        splk_data_sampling_min_time_btw_iterations_seconds,
        splk_data_sampling_no_records_per_entity,
        splk_data_sampling_relative_time_window_seconds,
    ):

        # min inclusive model matched percentage
        try:
            pct_min_major_inclusive_model_match = float(
                kvrecord.get(
                    "pct_min_major_inclusive_model_match",
                    splk_data_sampling_pct_min_major_inclusive_model_match,
                )
            )
        except Exception as e:
            pct_min_major_inclusive_model_match = (
                splk_data_sampling_pct_min_major_inclusive_model_match
            )

        # max exclusive model matched percentage
        try:
            pct_max_exclusive_model_match = float(
                kvrecord.get(
                    "pct_max_exclusive_model_match",
                    splk_data_sampling_pct_max_exclusive_model_match,
                )
            )
        except Exception as e:
            pct_max_exclusive_model_match = (
                splk_data_sampling_pct_max_exclusive_model_match
            )

        # Minimum time in seconds between two iterations of sampling per entity
        try:
            min_time_btw_iterations_seconds = int(
                kvrecord.get(
                    "min_time_btw_iterations_seconds",
                    splk_data_sampling_min_time_btw_iterations_seconds,
                )
            )
        except Exception as e:
            min_time_btw_iterations_seconds = (
                splk_data_sampling_min_time_btw_iterations_seconds
            )

        # max_events_per_sampling_iteration (integer)
        try:
            max_events_per_sampling_iteration = int(
                kvrecord.get(
                    "max_events_per_sampling_iteration",
                    splk_data_sampling_no_records_per_entity,
                )
            )
        except Exception as e:
            max_events_per_sampling_iteration = splk_data_sampling_no_records_per_entity

        # relative_time_window_seconds (integer)
        try:
            relative_time_window_seconds = int(
                kvrecord.get(
                    "relative_time_window_seconds",
                    splk_data_sampling_relative_time_window_seconds,
                )
            )
        except Exception as e:
            relative_time_window_seconds = (
                splk_data_sampling_relative_time_window_seconds
            )

        return (
            pct_min_major_inclusive_model_match,
            pct_max_exclusive_model_match,
            min_time_btw_iterations_seconds,
            max_events_per_sampling_iteration,
            relative_time_window_seconds,
        )

    """
    Function to get the upstream search definition
    """

    def get_upstream_search_definition(
        self, splk_data_sampling_relative_time_window_seconds
    ):

        if self.object != "*":
            upstream_search_string = remove_leading_spaces(
                f"""\
                | inputlookup trackme_dsm_tenant_{self.tenant_id} where object="{self.object}"
                | eval key=_key
                | lookup trackme_dsm_data_sampling_tenant_{self.tenant_id} object OUTPUT data_sample_feature, relative_time_window_seconds, data_sample_last_entity_epoch_processed
                | fields object, key, data_last_time_seen, *
                | eval earliest_target=if(isnum(relative_time_window_seconds), data_last_time_seen-relative_time_window_seconds, data_last_time_seen-{splk_data_sampling_relative_time_window_seconds})
                | eval latest_target=if(isnum(relative_time_window_seconds), earliest_target+relative_time_window_seconds, earliest_target+{splk_data_sampling_relative_time_window_seconds})
                """
            )

        else:
            upstream_search_string = remove_leading_spaces(
                f"""\
                | inputlookup trackme_dsm_tenant_{self.tenant_id} where monitored_state="enabled"
                | eval key=_key
                | `trackme_exclude_badentities`
                | where data_last_time_seen>relative_time(now(), "-24h")
                | lookup trackme_dsm_data_sampling_tenant_{self.tenant_id} object OUTPUT data_sample_feature, relative_time_window_seconds, data_sample_last_entity_epoch_processed, min_time_btw_iterations_seconds, data_sample_mtime
                ``` only consider entities where the last processed epoch (data_sample_last_entity_epoch_processed) is older than data_last_time_seen, or null (entities has not been processed yet) ```
                | where (isnull(data_sample_last_entity_epoch_processed) OR data_sample_last_entity_epoch_processed<data_last_time_seen)
                | eval data_sample_feature=if(isnull(data_sample_feature), "enabled", data_sample_feature) | where (data_sample_feature!="disabled")
                ``` only consider entities where the min_time_btw_iterations_seconds is older than the current time (bigger or equal to the time spent since last run, or null for new entities) ```
                | eval time_spent_since_last_run=now()-data_sample_mtime
                | where (isnull(min_time_btw_iterations_seconds) OR time_spent_since_last_run>=min_time_btw_iterations_seconds)
                ``` define a priority rank, entities that have been set as disabled_auto should be processed last compared to entities in disabled_audo ```
                | eval priority_rank=if(data_sample_feature=="enabled", 1, 2)
                ``` order ```
                | sort limit=0 priority_rank, data_sample_mtime
                | fields object, key, data_last_time_seen, *
                | eval earliest_target=if(isnum(relative_time_window_seconds), data_last_time_seen-relative_time_window_seconds, data_last_time_seen-{splk_data_sampling_relative_time_window_seconds})
                | eval latest_target=if(isnum(relative_time_window_seconds), earliest_target+relative_time_window_seconds, earliest_target+{splk_data_sampling_relative_time_window_seconds})
                """
            )

        logging.debug(f'upstream_search_string="{upstream_search_string}"')

        return upstream_search_string

    """
    Function to return the models for test
    """

    def get_test_models(self):

        merged_models_inclusive = []
        merged_models_exclusive = []

        if self.model_type == "inclusive":
            # append the test model to the inclusive list
            merged_models_inclusive.append(
                {
                    "model_name": self.model_name,
                    "model_regex": self.regex_expression,
                    "model_type": self.model_type,
                    "model_id": hashlib.sha256(
                        self.model_name.encode("utf-8")
                    ).hexdigest(),
                    "sourcetype_scope": self.sourcetype_scope,
                }
            )
        elif self.model_type == "exclusive":
            # append the test model to the exclusive list
            merged_models_exclusive.append(
                {
                    "model_name": self.model_name,
                    "model_regex": self.regex_expression,
                    "model_type": self.model_type,
                    "model_id": hashlib.sha256(
                        self.model_name.encode("utf-8")
                    ).hexdigest(),
                    "sourcetype_scope": self.sourcetype_scope,
                }
            )

        return merged_models_inclusive, merged_models_exclusive

    """
    Function to return the models for run
    """

    def get_run_models(self, custom_models_records):

        merged_models_inclusive = []
        merged_models_exclusive = []

        for custom_model in custom_models_records:
            model_name = custom_model.get("model_name")
            model_regex = custom_model.get("model_regex")
            model_type = custom_model.get("model_type")
            model_id = custom_model.get("model_id")
            sourcetype_scope = custom_model.get("sourcetype_scope")

            if model_type == "inclusive":
                merged_models_inclusive.append(
                    {
                        "model_name": model_name,
                        "model_regex": model_regex,
                        "model_type": model_type,
                        "model_id": model_id,
                        "sourcetype_scope": sourcetype_scope,
                    }
                )

            elif model_type == "exclusive":
                merged_models_exclusive.append(
                    {
                        "model_name": model_name,
                        "model_regex": model_regex,
                        "model_type": model_type,
                        "model_id": model_id,
                        "sourcetype_scope": sourcetype_scope,
                    }
                )

        # Append ootb models to the inclusive list
        for ootb_model in ootb_regex_list:
            model_name = ootb_model.get("label")
            model_regex = ootb_model.get("regex")
            merged_models_inclusive.append(
                {
                    "model_name": model_name,
                    "model_regex": model_regex,
                    "model_type": "inclusive",
                    "model_id": hashlib.sha256(model_name.encode("utf-8")).hexdigest(),
                    "sourcetype_scope": "*",
                }
            )

        return merged_models_inclusive, merged_models_exclusive

    """
    Function to call the disable sampling endpoint
    """

    def disable_sampling(self, object_key, object_value, reason):

        try:
            json_data = {
                "tenant_id": self.tenant_id,
                "keys_list": object_key,
                "action": "disable",
                "update_comment": reason,
            }
            target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_dsm/write/ds_manage_data_sampling"

            response = requests.post(
                target_url,
                headers={
                    "Authorization": f"Splunk {self._metadata.searchinfo.session_key}",
                    "Content-Type": "application/json",
                },
                verify=False,
                data=json.dumps(json_data),
                timeout=600,
            )

            if response.status_code in (200, 201, 204):
                logging.info(
                    f'tenant_id="{self.tenant_id}", object="{object_value}", object_id="{object_key}", auto-disablement of sampling was successful, response="{response.text}"'
                )
                return True

            else:
                logging.error(
                    f'tenant_id="{self.tenant_id}", object="{object_value}", object_id="{object_key}", could not disable data sampling, response.status_code="{response.status_code}", response="{response.text}"'
                )
                return False

        except Exception as e:
            logging.error(
                f'tenant_id="{self.tenant_id}", object="{object_value}", object_id="{object_key}", could not disable data sampling, exception="{str(e)}"'
            )
            return False

    """
    Function to init entity metadata
    """

    def init_entity_metadata(self, kvrecord):

        current_detected_format = []
        current_detected_format_dcount = 0
        current_detected_format_id = []
        current_detected_major_format = None

        # previous key information are stored as current_<key> in the record
        previous_detected_format = kvrecord.get("current_detected_format", [])
        previous_detected_format_dcount = kvrecord.get(
            "current_detected_format_dcount", 0
        )
        previous_detected_format_id = kvrecord.get("current_detected_format_id", [])
        previous_detected_major_format = kvrecord.get(
            "current_detected_major_format", None
        )

        data_sample_anomaly_detected = kvrecord.get(
            "data_sample_anomaly_detected", False
        )

        data_sample_anomaly_reason = kvrecord.get("data_sample_anomaly_reason", "N/A")

        data_sample_feature = kvrecord.get("data_sample_feature", "enabled")

        data_sample_iteration = kvrecord.get("data_sample_iteration", None)
        if not data_sample_iteration:
            data_sample_iteration = 1
        else:
            data_sample_iteration = int(data_sample_iteration)
            data_sample_iteration += 1

        data_sample_mtime = kvrecord.get("data_sample_mtime", time.time())
        data_sample_status_colour = None
        data_sample_status_message = {}
        multiformat_detected = False
        exclusive_match_anomaly = False

        # return
        return (
            current_detected_format,
            current_detected_format_dcount,
            current_detected_format_id,
            current_detected_major_format,
            previous_detected_format,
            previous_detected_format_dcount,
            previous_detected_format_id,
            previous_detected_major_format,
            data_sample_anomaly_detected,
            data_sample_anomaly_reason,
            data_sample_feature,
            data_sample_iteration,
            data_sample_mtime,
            data_sample_status_colour,
            data_sample_status_message,
            multiformat_detected,
            exclusive_match_anomaly,
        )

    """ 
    Function to return entity_search_string
    """

    def get_entity_search_string(
        self,
        entity_info,
        object_value,
        object_key,
        splk_dsm_sampling_search,
        splk_data_sampling_no_records_per_entity,
    ):

        # handle number of records to be sampled per entity
        if self.mode in ("run_sampling", "test_sampling"):

            # replace the number of records to be sampled
            if entity_info.get("account") != "local":
                search_string = splk_dsm_sampling_search.replace(
                    "head 1000",
                    f"head {splk_data_sampling_no_records_per_entity}",
                )
            else:
                search_string = (
                    splk_dsm_sampling_search
                    + f" | head {splk_data_sampling_no_records_per_entity}"
                )

            # add the key
            search_string = remove_leading_spaces(
                f"""\
                {search_string}
                | eval key="{str(object_key)}", object="{str(object_value)}"
                | rename _raw as raw_sample, sourcetype as data_sourcetype
                | table key, object, data_sourcetype, raw_sample
                """
            )

        elif self.mode == "test_model":

            # replace the number of records to be sampled
            if entity_info.get("account") != "local":
                search_string = splk_dsm_sampling_search.replace(
                    "head 1000",
                    f"head {self.get_samples_max_count}",
                )
            else:
                search_string = (
                    f"{splk_dsm_sampling_search} | head {self.get_samples_max_count}"
                )

            # add the key
            search_string = remove_leading_spaces(
                f"""\
                {search_string}
                | eval key="{object_key}", object="{object_value}"
                | rename _raw as raw_sample, sourcetype as data_sourcetype
                | table key, object, data_sourcetype, raw_sample
                """
            )

            logging.debug(f'splk_dsm_sampling_search="{splk_dsm_sampling_search}"')

        return search_string

    """
    Function to return the entity search kwargs
    """

    def get_entity_search_kwargs(
        self, object_value, object_key, search_string, earliest_target, latest_target
    ):

        # in mode run_sampling and test_sampling, we use the earliest_target
        if self.mode in ("run_sampling", "test_sampling"):
            kwargs_samplesearch = {
                "earliest_time": earliest_target,
                "latest_time": latest_target,
                "count": 0,
                "output_mode": "json",
            }
            logging.info(
                f'tenant_id="{self.tenant_id}", object="{object_value}", object_id="{object_key}", Executing data sampling resulting search="{search_string}", earliest="{earliest_target}", latest="{latest_target}"'
            )

        # in mode test_model, we use the earliest and latest
        elif self.mode == "test_model":
            kwargs_samplesearch = {
                "earliest_time": self.earliest,
                "latest_time": self.latest,
                "count": 0,
                "output_mode": "json",
            }
            logging.info(
                f'tenant_id="{self.tenant_id}", object="{object_value}", object_id="{object_key}", Executing data sampling resulting search="{search_string}", earliest="{earliest_target}", latest="{latest_target}"'
            )

        return kwargs_samplesearch

    """
    Function to retrieve the sampling kvrecord
    """

    def get_sampling_kvrecord(self, collection, object_field, object_value):

        # check if we have a KVrecord already for this object
        query_string = {
            "$and": [
                {
                    object_field: object_value,
                }
            ]
        }
        try:
            # try get to get the key
            kvrecord = collection.data.query(query=(json.dumps(query_string)))[0]
            key = kvrecord.get("_key")
        except Exception as e:
            kvrecord = {}
            key = None

        return kvrecord, key

    def generate(self, **kwargs):

        # performance counter
        start = time.time()

        # Track execution times
        average_execution_time = 0

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
        )
        log.setLevel(reqinfo["logging_level"])

        # Get Virtual Tenant account
        vtenant_account = trackme_vtenant_account(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )

        # if mode is test_model, regex_expression should be provided
        if self.mode == "test_model":
            if (
                not self.regex_expression
                or not self.model_type
                or not self.model_name
                or not self.sourcetype_scope
            ):
                raise Exception(
                    f'if mode is test_model, the regex expression, model_type, model_name and sourcetype_scope, mode="{self.mode}", regex_expression="{self.regex_expression}", model_type="{self.model_type}", model_name="{self.model_name}", sourcetype_scope="{self.sourcetype_scope}"'
                )

        # get metric index
        metric_index = self.get_tenant_metric_idx()

        # Retrieve custom models, if any.
        custom_models_collection_name = (
            f"kv_trackme_dsm_data_sampling_custom_models_tenant_{self.tenant_id}"
        )
        custom_models_collection = self.service.kvstore[custom_models_collection_name]
        (
            custom_models_records,
            custom_models_collection_keys,
            custom_models_collection_dict,
        ) = get_full_kv_collection(
            custom_models_collection, custom_models_collection_name
        )
        logging.debug(
            f'custom_models_records="{json.dumps(custom_models_records, indent=2)}"'
        )

        #
        # Step: merge the custom models with the OOTB models
        #

        merged_models_inclusive = []
        merged_models_exclusive = []

        if self.mode == "test_model":
            merged_models_inclusive, merged_models_exclusive = self.get_test_models()

        else:
            merged_models_inclusive, merged_models_exclusive = self.get_run_models(
                custom_models_records
            )

        logging.debug(
            f'merged_models_inclusive="{json.dumps(merged_models_inclusive, indent=2)}"'
        )

        logging.debug(
            f'merged_models_exclusive="{json.dumps(merged_models_exclusive, indent=2)}"'
        )

        # max runtime
        max_runtime = int(self.max_runtime)

        # Retrieve the search cron schedule
        savedsearch_name = f"trackme_dsm_data_sampling_tracker_tenant_{self.tenant_id}"
        savedsearch = self.service.saved_searches[savedsearch_name]
        savedsearch_cron_schedule = savedsearch.content["cron_schedule"]

        # get the cron_exec_sequence_sec
        try:
            cron_exec_sequence_sec = int(cron_to_seconds(savedsearch_cron_schedule))
        except Exception as e:
            logging.error(
                f'tenant_id="{self.tenant_id}", component="dsm", failed to convert the cron schedule to seconds, error="{str(e)}"'
            )
            cron_exec_sequence_sec = max_runtime

        # the max_runtime cannot be bigger than the cron_exec_sequence_sec
        if max_runtime > cron_exec_sequence_sec:
            max_runtime = cron_exec_sequence_sec

        logging.info(
            f'tenant_id={self.tenant_id}, max_runtime="{max_runtime}",  savedsearch_name="{savedsearch_name}", savedsearch_cron_schedule="{savedsearch_cron_schedule}", cron_exec_sequence_sec="{cron_exec_sequence_sec}"'
        )

        #
        # system wide settings for data sampling
        #

        (
            splk_data_sampling_min_time_btw_iterations_seconds,
            splk_data_sampling_no_records_per_entity,
            splk_data_sampling_no_records_saved_kvrecord,
            splk_data_sampling_records_kvrecord_truncate_size,
            splk_data_sampling_pct_min_major_inclusive_model_match,
            splk_data_sampling_pct_max_exclusive_model_match,
            splk_data_sampling_relative_time_window_seconds,
        ) = self.get_sampling_system_settings(reqinfo)

        # init
        upstream_search_string = None

        # counter
        count = 0

        # Get the session key
        session_key = self._metadata.searchinfo.session_key

        # Data collection
        collection_name = f"kv_trackme_dsm_data_sampling_tenant_{self.tenant_id}"
        collection = self.service.kvstore[collection_name]

        # get the upstream search definition
        upstream_search_string = self.get_upstream_search_definition(
            splk_data_sampling_relative_time_window_seconds
        )

        # Set kwargs
        kwargs_upstream_search = {
            "earliest_time": self.earliest,
            "latest_time": self.latest,
            "count": 0,
            "output_mode": "json",
        }

        logging.info(
            f'tenant_id={self.tenant_id}, Executing upstream definition search to define the list of entities to be sampled by order of priority, search="{upstream_search_string}"'
        )

        # get vtenant component info
        vtenant_component_info = trackme_vtenant_component_info(
            session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )
        logging.debug(
            f'vtenant_component_info="{json.dumps(vtenant_component_info, indent=2)}"'
        )

        # get sampling, if set 0 then sampling is disabled for the tenant, 1 we can proceed
        sampling_feature_enabled = True
        try:
            if int(vtenant_account.get("sampling")) == 0:
                sampling_feature_enabled = False
        except Exception as e:
            sampling_feature_enabled = True

        # check schema version migration state
        try:
            schema_version = int(vtenant_component_info["schema_version"])
            schema_version_upgrade_in_progress = bool(
                int(vtenant_component_info["schema_version_upgrade_in_progress"])
            )
            logging.debug(
                f'schema_version_upgrade_in_progress="{schema_version_upgrade_in_progress}"'
            )
        except Exception as e:
            schema_version = 0
            schema_version_upgrade_in_progress = False
            logging.error(
                f'failed to retrieve schema_version_upgrade_in_progress=, exception="{str(e)}"'
            )

        # Do not proceed if the schema version upgrade is in progress
        if schema_version_upgrade_in_progress:
            yield_json = {
                "_time": time.time(),
                "tenant_id": self.tenant_id,
                "response": f'tenant_id="{self.tenant_id}", schema upgrade is currently in progress, we will wait until the process is completed before proceeding, the schema upgrade is handled by the health_tracker of the tenant and is completed once the schema_version field of the Virtual Tenants KVstore (trackme_virtual_tenants) matches TrackMe\'s version, schema_version="{schema_version}", schema_version_upgrade_in_progress="{schema_version_upgrade_in_progress}"',
                "schema_version": schema_version,
                "schema_version_upgrade_in_progress": schema_version_upgrade_in_progress,
            }
            logging.info(
                f"tenant_id={self.tenant_id}, {json.dumps(yield_json, indent=2)}"
            )
            yield {
                "_time": yield_json["_time"],
                "_raw": yield_json,
            }

        # Do not proceed if the sampling feature is disabled
        if not sampling_feature_enabled:
            yield_json = {
                "_time": time.time(),
                "tenant_id": self.tenant_id,
                "response": f'tenant_id="{self.tenant_id}", data sampling feature is disabled for this tenant, sampling="{sampling_feature_enabled}"',
                "sampling_feature_enabled": sampling_feature_enabled,
            }
            logging.info(
                f"tenant_id={self.tenant_id}, {json.dumps(yield_json, indent=2)}"
            )
            yield {
                "_time": yield_json["_time"],
                "_raw": yield_json,
            }

        # available modes
        # - run_sampling: run the full sampling process, as expected per schedule
        # - test_model: test a model against a sample event
        # - test_sampling: same as run_sampling but dot not update the KVstore, used for testing purposes
        # - get_samples: get samples for simulation or inline search purposes (from KVstore)
        # - get_live_samples: get samples for simulation or inline search purposes (from live data)

        if self.mode in ("get_samples", "get_live_samples", "show_kvrecord"):

            # object is required
            if not self.object or self.object == "*":
                raise Exception(f"object is required in mode={self.mode}")

            # get the kvrecord and key
            kvrecord, key = self.get_sampling_kvrecord(
                collection, "object", self.object
            )

            # run the main report, every result is a Splunk search to be executed on its own thread
            if not key:
                raise Exception(
                    "this entity was not found in the collection or data sampling has not been executed yet for this entity."
                )

            #
            # run
            #

            if self.mode in ("get_live_samples"):

                # get the entity info
                try:
                    entity_info = self.get_entity_info("object", self.object)
                except Exception as e:
                    raise Exception(
                        f'function get_entity_info, called with arguments: object_field="object", object_value="{self.object}", could not retrieve entity info data sampling search, this entity was not found, exception="{str(e)}"'
                    )

                #
                # from entity_info, get splk_dsm_sampling_search and inspect the type of entity
                #

                splk_dsm_sampling_search = entity_info.get(
                    "splk_dsm_sampling_search", None
                )

                # run the main report, every result is a Splunk search to be executed on its own thread
                if not splk_dsm_sampling_search:
                    raise Exception(
                        "could not retrieve entity info data sampling search, this entity was not found"
                    )

                else:
                    # replace the number of records to be sampled
                    if entity_info.get("account") == "local":
                        live_sample_search_string = f"{splk_dsm_sampling_search} | head {self.get_samples_max_count}"

                    else:
                        live_sample_search_string = splk_dsm_sampling_search.replace(
                            "head 1000",
                            f"head {self.get_samples_max_count}",
                        )

                    # add the key
                    live_sample_search_string = remove_leading_spaces(
                        f"""\
                        {live_sample_search_string}
                        | eval key="{str(key)}", object="{str(self.object)}"
                        | rename _raw as raw_sample, sourcetype as data_sourcetype
                        """
                    )

                    # Set kwargs
                    kwargs_live_sample_search = {
                        "earliest_time": self.earliest,
                        "latest_time": self.latest,
                        "count": 0,
                        "output_mode": "json",
                    }

                    try:
                        subreader = run_splunk_search(
                            self.service,
                            live_sample_search_string,
                            kwargs_live_sample_search,
                            24,
                            5,
                        )

                        for item in subreader:
                            if isinstance(item, dict):
                                logging.debug(f'search_results="{item}"')

                                raw_sample = item.get("raw_sample")
                                if raw_sample:
                                    raw_sample = raw_sample.rstrip(
                                        "\n"
                                    )  # Removes the newline only if it's at the end
                                    item["raw_sample"] = raw_sample

                                data_sourcetype = item.get("data_sourcetype")
                                # if data_sourcetype is a list, take the first element
                                if isinstance(data_sourcetype, list):
                                    data_sourcetype = data_sourcetype[0]

                                data = {
                                    "_time": time.time(),
                                    "key": item.get("key"),
                                    "object": item.get("object"),
                                    "_raw": raw_sample,
                                    "data_sourcetype": data_sourcetype,
                                }
                                yield data

                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}" search failed with exception="{str(e)}"'
                        )

            elif self.mode == "show_kvrecord":

                # yield the kvrecord
                yield_record = {}
                yield_record["_time"] = time.time()
                for k, v in kvrecord.items():
                    yield_record[k] = v
                yield_record["_raw"] = json.dumps(kvrecord)

                yield yield_record

            elif self.mode == "get_samples":

                # get the raw_sample_list
                raw_sample_list = kvrecord.get("raw_sample")

                # loop through the raw_sample_list
                for record in raw_sample_list:

                    # load as an object
                    record = json.loads(record)

                    # yield the kvrecord
                    yield_record = {}
                    yield_record["_time"] = time.time()
                    for k, v in record.items():
                        yield_record[k] = v
                    yield_record["_raw"] = json.dumps(record)

                    yield yield_record

        elif (
            self.mode in ("run_sampling", "test_sampling", "test_model")
            and not schema_version_upgrade_in_progress
            and sampling_feature_enabled
        ):
            # report name for logging purposes
            report_name = f"trackme_dsm_data_sampling_tracker_tenant_{self.tenant_id}"

            # run the main report, every result is a Splunk search to be executed on its own thread
            objects_list = []

            # From the vtenant account, get the value of Sampling obfuscation
            data_sampling_obfuscation = vtenant_component_info.get(
                "data_sampling_obfuscation"
            )

            #
            # run the upstream search
            #

            try:
                reader = run_splunk_search(
                    self.service,
                    upstream_search_string,
                    kwargs_upstream_search,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        logging.debug(f'search_results="{item}"')
                        # append to the list of searches

                        objects_list.append(
                            {
                                "object": item.get("object"),
                                "key": item.get("key"),
                                "earliest_target": item.get("earliest_target"),
                                "latest_target": item.get("latest_target"),
                                "data_last_time_seen": item.get("data_last_time_seen"),
                            }
                        )

            except Exception as e:

                if self.mode == "run_sampling":
                    # Call the component register
                    trackme_register_tenant_object_summary(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        "splk-dsm",
                        f"trackme_dsm_data_sampling_tracker_tenant_{self.tenant_id}",
                        "failure",
                        time.time(),
                        str(time.time() - start),
                        str(e),
                        "-24h",
                        "now",
                    )
                msg = f'tenant_id="{self.tenant_id}", component="dsm", search failed with exception="{str(e)}"'
                logging.error(msg)
                raise Exception(
                    msg
                )  # if failed, the jobs exists and is tagged as failed in the component register

            # loop
            logging.debug(f'objects_list="{json.dumps(objects_list, indent=2)}"')

            # Initialize sum of execution times and count of iterations
            total_execution_time = 0
            iteration_count = 0

            # Other initializations
            max_runtime = int(self.max_runtime)
            entities_count = 0

            #
            # Loop through entities to be processed
            #

            for object_dict in objects_list:
                entities_count += 1
                object_value = object_dict.get("object")
                object_key = object_dict.get("key")
                earliest_target = object_dict.get("earliest_target")
                latest_target = object_dict.get("latest_target")
                data_last_time_seen = object_dict.get("data_last_time_seen")

                logging.info(
                    f'tenant_id="{self.tenant_id}", processing entity object="{object_value}", object_id="{object_key}"'
                )

                # iteration start
                iteration_start_time = time.time()

                # get the kvrecord and key
                kvrecord, key = self.get_sampling_kvrecord(
                    collection, "_key", object_key
                )

                #
                # is_eligible boolean, is_eligible_reason string
                #

                is_eligible = True
                is_eligible_reason = "N/A"

                #
                # entity info
                #

                # get the entity info
                try:
                    entity_info = self.get_entity_info("object_id", object_key)
                except Exception as e:
                    entity_info = {}

                #
                # from entity_info, get splk_dsm_sampling_search and inspect the type of entity
                #

                splk_dsm_sampling_search = entity_info.get(
                    "splk_dsm_sampling_search", None
                )
                if splk_dsm_sampling_search:  # handle if N/A
                    if splk_dsm_sampling_search == "N/A":
                        splk_dsm_sampling_search = None

                is_elastic = int(entity_info.get("is_elastic", 0))
                search_mode = entity_info.get("search_mode", "unknown")

                logging.debug(
                    f'tenant_id="{self.tenant_id}", object="{object_value}", object_id="{object_key}", splk_dsm_sampling_search="{splk_dsm_sampling_search}", is_elastic="{is_elastic}", search_mode="{search_mode}"'
                )

                # inspect the entity type

                if is_elastic == 1 and search_mode in (
                    "mstats",
                    "mpreview",
                    "from",
                ):

                    # disable sampling for non eligible elastic search entities
                    is_eligible = False
                    is_eligible_reason = "elastic_search_entity"

                    logging.info(
                        f'tenant_id="{self.tenant_id}", object="{object_value}", object_id="{object_key}", is_eligible="{is_eligible}", is_eligible_reason="{is_eligible_reason}", processing with auto-disablement of sampling'
                    )

                    self.disable_sampling(
                        object_key,
                        object_value,
                        "auto-disablement of sampling for elastic search entities",
                    )

                elif not splk_dsm_sampling_search or splk_dsm_sampling_search == "N/A":

                    # disable sampling for entities returning non available sampling search
                    is_eligible = False
                    is_eligible_reason = "no_sampling_search"

                    logging.info(
                        f'tenant_id="{self.tenant_id}", object="{object_value}", object_id="{object_key}", is_eligible="{is_eligible}", is_eligible_reason="{is_eligible_reason}", processing with auto-disablement of sampling'
                    )

                    self.disable_sampling(
                        object_key,
                        object_value,
                        "auto-disablement of sampling for entities without sampling search identified",
                    )

                #
                # process entity sampling
                #

                if not is_eligible:
                    continue  # stop processing this entity

                # get the entity settings
                (
                    pct_min_major_inclusive_model_match,
                    pct_max_exclusive_model_match,
                    min_time_btw_iterations_seconds,
                    max_events_per_sampling_iteration,
                    relative_time_window_seconds,
                ) = self.get_sampling_entity_settings(
                    kvrecord,
                    splk_data_sampling_pct_min_major_inclusive_model_match,
                    splk_data_sampling_pct_max_exclusive_model_match,
                    splk_data_sampling_min_time_btw_iterations_seconds,
                    splk_data_sampling_no_records_per_entity,
                    splk_data_sampling_relative_time_window_seconds,
                )

                # call init function
                (
                    current_detected_format,
                    current_detected_format_dcount,
                    current_detected_format_id,
                    current_detected_major_format,
                    previous_detected_format,
                    previous_detected_format_dcount,
                    previous_detected_format_id,
                    previous_detected_major_format,
                    data_sample_anomaly_detected,
                    data_sample_anomaly_reason,
                    data_sample_feature,
                    data_sample_iteration,
                    data_sample_mtime,
                    data_sample_status_colour,
                    data_sample_status_message,
                    multiformat_detected,
                    exclusive_match_anomaly,
                ) = self.init_entity_metadata(kvrecord)

                # call get_entity_search_string
                search_string = self.get_entity_search_string(
                    entity_info,
                    object_value,
                    object_key,
                    splk_dsm_sampling_search,
                    splk_data_sampling_no_records_per_entity,
                )

                # a list to store the results
                sample_data_list = []
                sample_events_list = []

                # run search
                try:
                    # start
                    entity_search_start = time.time()

                    # get kwargs
                    kwargs_samplesearch = self.get_entity_search_kwargs(
                        object_value,
                        object_key,
                        search_string,
                        earliest_target,
                        latest_target,
                    )

                    reader = run_splunk_search(
                        self.service,
                        search_string,
                        kwargs_samplesearch,
                        24,
                        5,
                    )

                    count += 1

                    for item in reader:
                        if isinstance(item, dict):
                            logging.debug(
                                f'search_results="{json.dumps(item, indent=2)}"'
                            )

                            raw_sample = item.get("raw_sample")
                            if raw_sample:
                                raw_sample = raw_sample.rstrip(
                                    "\n"
                                )  # Removes the newline only if it's at the end
                                item["raw_sample"] = raw_sample

                            data_sourcetype = item.get("data_sourcetype")
                            # if data_sourcetype is a list, take the first element
                            if isinstance(data_sourcetype, list):
                                data_sourcetype = data_sourcetype[0]

                            data = {
                                "_time": time.time(),
                                "key": item.get("key"),
                                "object": item.get("object"),
                                "raw_sample": raw_sample,
                                "data_sourcetype": data_sourcetype,
                            }

                            # add to the list
                            sample_data_list.append(data)

                    logging.info(
                        f'tenant_id="{self.tenant_id}" search successfully executed in {round(time.time() - entity_search_start, 3)} seconds'
                    )

                except Exception as e:
                    # Call the component register
                    msg = f'tenant_id="{self.tenant_id}" search failed with exception="{str(e)}"'
                    logging.error(msg)
                    continue  # stop processing this entity

                #
                # Investigate results for this entity
                #

                # events_count
                events_count = len(sample_data_list)

                # model_split_dict
                model_split_dict = {}

                for record in sample_data_list:

                    yield_record = {}
                    raw_sample = record.get("raw_sample")
                    raw_sample_id = hashlib.sha256(
                        raw_sample.encode("utf-8")
                    ).hexdigest()
                    data_sourcetype = record.get("data_sourcetype")

                    # model_match boolean
                    model_match = False

                    # result_sampling_json_list
                    result_sampling_json_list = []

                    # loop through custom models, if any

                    #
                    # inclusive models
                    #

                    for model in merged_models_inclusive:

                        # extract
                        model_name = model.get("model_name")
                        model_regex = model.get("model_regex")
                        model_type = model.get("model_type")
                        model_id = model.get("model_id")
                        sourcetype_scope = model.get("sourcetype_scope")
                        sourcetype_scope = sourcetype_scope.split(
                            ","
                        )  # support comma separated sourcetypes

                        # init model counters
                        model_count_matched = 0

                        logging.debug(
                            f'testing inclusive_model: model_name="{model_name}", model_type="{model_type}", model_id="{model_id}", sourcetype_scope="{sourcetype_scope}"'
                        )

                        if any(
                            fnmatch.fnmatch(data_sourcetype, sourcetype.strip())
                            for sourcetype in sourcetype_scope
                        ):

                            model_regex = sanitize_regex_global_flags(model_regex)

                            logging.debug(
                                f"testing regex: {model_regex} against event_id: {raw_sample_id}, event: {raw_sample}"
                            )

                            if re.search(model_regex, raw_sample):

                                model_match = True
                                model_count_matched += 1

                                logging.debug(
                                    f'raw_sample_id="{raw_sample_id}", model_name="{model_name}", model_type="{model_type}", model_id="{model_id}", sourcetype_scope="{sourcetype_scope}" has a positive match with the sample event'
                                )

                                # add the model_name to current_detected_format_name, if not already in the list
                                if model_name not in current_detected_format:
                                    current_detected_format.append(model_name)

                                # add the model_id to current_detected_format_id, if not already in the list
                                if model_id not in current_detected_format_id:
                                    current_detected_format_id.append(model_id)

                                # check if the model is inclusive or exclusive
                                if model_type == "exclusive":
                                    exclusive_match_anomaly = True

                                result_sampling = {
                                    "raw_sample_id": raw_sample_id,
                                    "model_match": model_match,
                                    "model_name": model_name,
                                    "model_type": model_type,
                                    "model_id": model_id,
                                    "sourcetype_scope": sourcetype_scope,
                                    "exclusive_match_anomaly": exclusive_match_anomaly,
                                    "message": "positive match found for event",
                                }

                                # if mode is test_sampling, add the model_regex to the result_sampling
                                if self.mode == "test_sampling":
                                    result_sampling["model_regex"] = model_regex

                                result_sampling_json_list.append(result_sampling)

                                # if model has a positive match:
                                # - if not already in the model_split_dict, add it and add the model_count_matched as well as model_name and model_id
                                # - if already in the model_split_dict, increment the model_count_matched
                                if model_match:
                                    if model_id not in model_split_dict:
                                        model_split_dict[model_id] = {
                                            "model_count_matched": model_count_matched,
                                            "model_name": model_name,
                                            "model_type": model_type,
                                        }
                                    else:
                                        model_split_dict[model_id][
                                            "model_count_matched"
                                        ] += model_count_matched

                                # break at first positive match for this event
                                break

                            else:
                                logging.debug(
                                    f'model_name="{model_name}", model_type="{model_type}", model_id="{model_id}", sourcetype_scope="{sourcetype_scope}" no match found for event'
                                )

                    #
                    # exclusive models
                    #

                    for model in merged_models_exclusive:

                        # extract
                        model_name = model.get("model_name")
                        model_regex = model.get("model_regex")
                        model_type = model.get("model_type")
                        model_id = model.get("model_id")
                        sourcetype_scope = model.get("sourcetype_scope")
                        sourcetype_scope = sourcetype_scope.split(
                            ","
                        )  # support comma separated sourcetypes

                        logging.debug(
                            f'testing exclusive_model: model_name="{model_name}", model_type="{model_type}", model_id="{model_id}", sourcetype_scope="{sourcetype_scope}", model_regex="{model_regex}", raw_sample="{raw_sample}"'
                        )

                        if any(
                            fnmatch.fnmatch(data_sourcetype, sourcetype.strip())
                            for sourcetype in sourcetype_scope
                        ):

                            model_regex = sanitize_regex_global_flags(model_regex)

                            logging.debug(
                                f"testing regex: {model_regex} against event: {raw_sample}"
                            )

                            if re.search(model_regex, raw_sample):

                                model_match = True

                                logging.debug(
                                    f'raw_sample_id="{raw_sample_id}", model_name="{model_name}", model_type="{model_type}", model_id="{model_id}", sourcetype_scope="{sourcetype_scope}" has a positive match with the sample event'
                                )

                                # add the model_name to current_detected_format_name, if not already in the list
                                if model_name not in current_detected_format:
                                    current_detected_format.append(model_name)

                                # add the model_id to current_detected_format_id, if not already in the list
                                if model_id not in current_detected_format_id:
                                    current_detected_format_id.append(model_id)

                                # check if the model is inclusive or exclusive
                                if model_type == "exclusive":
                                    exclusive_match_anomaly = True

                                result_sampling = {
                                    "raw_sample_id": raw_sample_id,
                                    "model_match": model_match,
                                    "model_name": model_name,
                                    "model_type": model_type,
                                    "model_id": model_id,
                                    "sourcetype_scope": sourcetype_scope,
                                    "exclusive_match_anomaly": exclusive_match_anomaly,
                                    "message": "positive match found for event",
                                }

                                # if mode is test_sampling, add the model_regex to the result_sampling
                                if self.mode == "test_sampling":
                                    result_sampling["model_regex"] = model_regex

                                result_sampling_json_list.append(result_sampling)

                                # if model has a positive match:
                                # - if not already in the model_split_dict, add it and add the model_count_matched as well as model_name and model_id
                                # - if already in the model_split_dict, increment the model_count_matched
                                if model_match:
                                    if model_id not in model_split_dict:
                                        model_split_dict[model_id] = {
                                            "model_count_matched": model_count_matched,
                                            "model_name": model_name,
                                            "model_type": model_type,
                                        }
                                    else:
                                        model_split_dict[model_id][
                                            "model_count_matched"
                                        ] += model_count_matched

                                # no break for exclusive models, we need to check all of them

                            else:
                                logging.debug(
                                    f'model_name="{model_name}", model_type="{model_type}", model_id="{model_id}", sourcetype_scope="{sourcetype_scope}" no match found for event'
                                )

                    # if not match, generate a negative result
                    if model_match:
                        record["result_sampling"] = result_sampling_json_list

                    else:
                        result_sampling = {
                            "raw_sample_id": raw_sample_id,
                            "model_match": model_match,
                            "model_name": "N/A",
                            "model_type": "N/A",
                            "model_id": "N/A",
                            "sourcetype_scope": "N/A",
                            "exclusive_match_anomaly": "N/A",
                            "message": "no positive match found for event",
                        }
                        record["result_sampling"] = [result_sampling]

                    # add the event to the sample events list
                    sample_events_list_object = {
                        "event_id": raw_sample_id,
                        "model_name": current_detected_format,
                        "model_id": current_detected_format_id,
                        "result_sampling": result_sampling,
                    }
                    if data_sampling_obfuscation == 0:
                        # if the event is longer than the limit, add event_is_truncated = True, otherwise event_is_truncated = False
                        if (
                            len(raw_sample)
                            > splk_data_sampling_records_kvrecord_truncate_size
                        ):
                            sample_events_list_object["event_is_truncated"] = True
                        else:
                            sample_events_list_object["event_is_truncated"] = False
                        sample_events_list_object["event"] = raw_sample[
                            :splk_data_sampling_records_kvrecord_truncate_size
                        ]
                        # add event_is_obfuscated = False
                        sample_events_list_object["event_is_obfuscated"] = False

                    else:
                        # add event_is_obfuscated = True
                        sample_events_list_object["event_is_obfuscated"] = True

                    sample_events_list.append(json.dumps(sample_events_list_object))

                    # yield the record
                    yield_model_match = []
                    yield_model_name = []
                    yield_model_type = []
                    yield_model_id = []
                    yield_model_regex = []
                    yield_sourcetype_scope = []
                    yield_exclusive_match_anomaly = []
                    yield_message = []

                    for k, v in record.items():
                        yield_record[k] = v

                        # get the content of result_sampling (list)
                        if k == "result_sampling":

                            logging.debug(
                                f'result_sampling="{v}", its type is {type(v)}'
                            )

                            for item in v:
                                yield_model_match.append(item.get("model_match"))
                                yield_model_name.append(item.get("model_name"))
                                yield_model_type.append(item.get("model_type"))
                                yield_model_id.append(item.get("model_id"))
                                # if mode is test_sampling, add the model_regex to the yield
                                if self.mode == "test_sampling":
                                    yield_model_regex.append(item.get("model_regex"))
                                yield_sourcetype_scope.append(
                                    item.get("sourcetype_scope")
                                )
                                yield_exclusive_match_anomaly.append(
                                    item.get("exclusive_match_anomaly")
                                )
                                yield_message.append(item.get("message"))
                            # now add our list to yield_record
                            yield_record["model_match"] = yield_model_match
                            yield_record["model_name"] = yield_model_name
                            yield_record["model_type"] = yield_model_type
                            yield_record["model_id"] = yield_model_id
                            # if mode is test_sampling, add the model_regex to the yield
                            if self.mode == "test_sampling":
                                yield_record["model_regex"] = yield_model_regex

                            yield_record["sourcetype_scope"] = yield_sourcetype_scope
                            yield_record["exclusive_match_anomaly"] = (
                                yield_exclusive_match_anomaly
                            )
                            yield_record["message"] = yield_message

                    # add the _raw
                    yield_record["_raw"] = json.dumps(record)

                    # finally yield the record expect in run_sampling mode to reduce processing costs
                    if self.mode != "run_sampling":
                        yield yield_record

                #
                # investigate results
                #

                if len(current_detected_format) > 1:
                    multiformat_detected = True

                # model_split_dict:
                # for each model matched in model_split_dict, calculate the percentage of the model match and add to the dict
                max_model_pct_match = 0  # Track the highest percentage of matches
                major_model_id = None  # Track the model ID with the highest matches
                major_model_name = None  # Track the model name with the highest matches

                for model_id, model_dict in model_split_dict.items():
                    model_count_matched = model_dict.get("model_count_matched")
                    model_name = model_dict.get("model_name")
                    model_type = model_dict.get("model_type")
                    model_pct_match = round(
                        (model_count_matched / events_count) * 100, 2
                    )
                    model_split_dict[model_id]["model_pct_match"] = model_pct_match
                    # add the total events as modeL_count_parsed
                    model_split_dict[model_id]["model_count_parsed"] = events_count

                    # Determine if this model is the major model
                    if model_pct_match > max_model_pct_match:
                        max_model_pct_match = model_pct_match
                        major_model_id = model_id
                        major_model_name = model_name

                # Now, mark the major model and others
                for model_id in model_split_dict:
                    if model_id == major_model_id:
                        model_split_dict[model_id]["model_is_major"] = True
                    else:
                        model_split_dict[model_id]["model_is_major"] = False

                # set the current major detected format
                current_detected_major_format = major_model_name

                # List of fields to be managed in the sampling record:
                # object
                # raw_sample
                # data_sample_mtime: epochtime
                # data_sample_last_entity_epoch_processed: epochtime
                # data_sample_feature: string, enabled | disabled | disabled_auto
                # data_sample_iteration: integer
                # data_sample_anomaly_reason: string
                # data_sample_status_colour: string
                # data_sample_anomaly_detected: boolean
                # data_sample_status_message: dict
                # multiformat_detected: boolean
                # current_detected_format: list
                # current_detected_format_id: list
                # current_detected_format_dcount: integer
                # current_detected_major_format: string
                # previous_detected_format: list
                # previous_detected_format_id: list
                # previous_detected_format_dcount: integer
                # previous_detected_major_format: string
                # exclusive_match_anomaly: boolean
                # raw_sample: list

                # uc: exclusive match anomaly detected:

                # uc: exclusive match anomaly detected:
                # - if in the list of matched models in model_split_dict, an exclusive model is detected and its percentage is higher than the max allowed, set True

                #
                # exclusive match anomaly detected:
                #

                exclusive_match_anomaly = False

                for model_id, model_dict in model_split_dict.items():
                    model_pct_match = model_dict.get("model_pct_match")
                    model_type = model_dict.get("model_type")
                    if (
                        model_type == "exclusive"
                        and model_pct_match > pct_max_exclusive_model_match
                    ):
                        exclusive_match_anomaly = True

                #
                # inclusive match anomaly detected:
                #

                inclusive_match_anomaly = False

                for model_id, model_dict in model_split_dict.items():
                    model_pct_match = model_dict.get("model_pct_match")
                    model_type = model_dict.get("model_type")
                    model_is_major = model_dict.get("model_is_major")
                    if (
                        model_type == "inclusive"
                        and model_is_major
                        and model_pct_match < pct_min_major_inclusive_model_match
                    ):
                        inclusive_match_anomaly = True

                # create a model_summary_list based on the model_split_dict:
                # for each model in model_split_dict, add a record with:
                # model_name | pct_match: percentage of match | model_type: inclusive or exclusive | model_is_major: boolean
                model_summary_list = []
                for model_id, model_dict in model_split_dict.items():
                    model_summary_record = f'{model_dict.get("model_name")} | pct_match: {model_dict.get("model_pct_match")} | type: {model_dict.get("model_type")}'
                    model_summary_list.append(model_summary_record)

                #
                # define the status of the feature
                #

                if exclusive_match_anomaly:
                    data_sample_epoch = time.time()
                    data_sample_model_matched_summary = model_split_dict
                    data_sample_anomaly_reason = "exclusive_rule_match"
                    data_sample_feature = "enabled"
                    data_sample_anomaly_detected = 1
                    data_sample_status_colour = "red"
                    data_sample_status_message = {
                        "state": "red",
                        "desc": "Anomalies detected, one or more exclusive rules have been matched.",
                        "remediation": "Exclusive matches mean that regular expressions have matched forbidden content in one or more events, review the latest sample events to identify the root cause. Once the issue is fixed, click on clear state & run sampling.",
                        "last_run": f"{convert_epoch_to_datetime(data_sample_epoch)}",
                        "anomaly_reason": data_sample_anomaly_reason,
                        "multiformat": multiformat_detected,
                        "events_count": events_count,
                        "min_time_btw_iterations_seconds": min_time_btw_iterations_seconds,
                        "pct_min_major_inclusive_model_match": pct_min_major_inclusive_model_match,
                        "pct_max_exclusive_model_match": pct_max_exclusive_model_match,
                        "max_events_per_sampling_iteration": max_events_per_sampling_iteration,
                        "relative_time_window_seconds": relative_time_window_seconds,
                        "current_detected_major_format": current_detected_major_format,
                        "models_summary": model_summary_list,
                    }

                # inclusive match anomaly detected at the time of the discovery with multiple formats detected:
                # - Disable the feature to avoid generating false positive, in the sense that most likely this feed
                # is not a good candidate for data sampling
                # - However, we still want to attempt processing this feed in the case of a change in conditions, but keep disabled_auto
                # so we do not influence the entity status

                elif (
                    inclusive_match_anomaly
                    and data_sample_iteration == 1
                    and multiformat_detected
                ):
                    data_sample_epoch = time.time()
                    data_sample_model_matched_summary = model_split_dict
                    data_sample_anomaly_reason = "anomalies_at_discovery"
                    data_sample_feature = "disabled_auto"
                    data_sample_anomaly_detected = 2
                    data_sample_status_colour = "orange"
                    data_sample_status_message = {
                        "state": "orange",
                        "desc": "Anomalies were detected since the entity discovery, multiple formats were detected and the major model is under the acceptable threshold of percentage of events matched by the major model. The data sampling feature was automatically disabled (disabled_auto) to avoid generating false positive for this entity (the feature will not be allowed to influence the entity status), however TrackMe will continue attempting to process in case conditions for this feed change.",
                        "last_run": f"{convert_epoch_to_datetime(data_sample_epoch)}",
                        "anomaly_reason": data_sample_anomaly_reason,
                        "multiformat": multiformat_detected,
                        "events_count": events_count,
                        "min_time_btw_iterations_seconds": min_time_btw_iterations_seconds,
                        "pct_min_major_inclusive_model_match": pct_min_major_inclusive_model_match,
                        "pct_max_exclusive_model_match": pct_max_exclusive_model_match,
                        "max_events_per_sampling_iteration": max_events_per_sampling_iteration,
                        "relative_time_window_seconds": relative_time_window_seconds,
                        "current_detected_major_format": current_detected_major_format,
                        "models_summary": model_summary_list,
                    }

                # inclusive match anomaly detected at the time of the discovery and next iterations
                # - Disable the feature to avoid generating false positive, in the sense that most likely this feed
                # is not a good candidate for data sampling
                # - However, we still want to attempt processing this feed in the case of a change in conditions, but keep disabled_auto
                # so we do not influence the entity status

                elif (
                    inclusive_match_anomaly
                    and data_sample_iteration > 1
                    and multiformat_detected
                    and data_sample_feature == "disabled_auto"
                ):
                    data_sample_epoch = time.time()
                    data_sample_model_matched_summary = model_split_dict
                    data_sample_anomaly_reason = "anomalies_since_discovery"
                    data_sample_feature = "disabled_auto"
                    data_sample_anomaly_detected = 2
                    data_sample_status_colour = "orange"
                    data_sample_status_message = {
                        "state": "orange",
                        "desc": "Anomalies were detected since the entity discovery, multiple formats were detected and the major model is under the acceptable threshold of percentage of events matched by the major model. The data sampling feature was automatically disabled (disabled_auto) to avoid generating false positive for this entity (the feature will not be allowed to influence the entity status), however TrackMe will continue attempting to process in case conditions for this feed change.",
                        "remediation": "Review events generated for this feed, when TrackMe first discover the entity and finds multiple format that would generate an inclusive anomaly (the percentage of events for the major format goes below the minimal acceptable percentage of events), the feature is automatically disabled. The issue can be addressed by the creation of a custom model that is more adapted to the feed context, or may need to remain disabled if the feed is not a right candidate for the sampling feature, such as a sourcetype with poor event quality, or a sourcetype where many various events formats are expected and accepted.",
                        "last_run": f"{convert_epoch_to_datetime(data_sample_epoch)}",
                        "anomaly_reason": data_sample_anomaly_reason,
                        "multiformat": multiformat_detected,
                        "events_count": events_count,
                        "min_time_btw_iterations_seconds": min_time_btw_iterations_seconds,
                        "pct_min_major_inclusive_model_match": pct_min_major_inclusive_model_match,
                        "pct_max_exclusive_model_match": pct_max_exclusive_model_match,
                        "max_events_per_sampling_iteration": max_events_per_sampling_iteration,
                        "relative_time_window_seconds": relative_time_window_seconds,
                        "current_detected_major_format": current_detected_major_format,
                        "models_summary": model_summary_list,
                    }

                # inclusive match anomaly after discovery and enablement
                elif inclusive_match_anomaly:
                    data_sample_epoch = time.time()
                    data_sample_model_matched_summary = model_split_dict
                    data_sample_anomaly_reason = "inclusive_rule_match"
                    data_sample_feature = "enabled"
                    data_sample_anomaly_detected = 1
                    data_sample_status_colour = "red"
                    data_sample_status_message = {
                        "state": "red",
                        "desc": "Anomalies detected, quality issues were detected, the min percentage of the major model matched does not meet requirements which indicates that a too large number of events do not share the same format that than the majority of events.",
                        "remediation": "Inclusive matches mean that regular expressions have not matched the expected content in one or more events, review the latest sample events to identify the root cause. Once the issue is fixed, click on clear state & run sampling.",
                        "last_run": f"{convert_epoch_to_datetime(data_sample_epoch)}",
                        "anomaly_reason": data_sample_anomaly_reason,
                        "multiformat": multiformat_detected,
                        "events_count": events_count,
                        "min_time_btw_iterations_seconds": min_time_btw_iterations_seconds,
                        "pct_min_major_inclusive_model_match": pct_min_major_inclusive_model_match,
                        "pct_max_exclusive_model_match": pct_max_exclusive_model_match,
                        "max_events_per_sampling_iteration": max_events_per_sampling_iteration,
                        "relative_time_window_seconds": relative_time_window_seconds,
                        "current_detected_major_format": current_detected_major_format,
                        "models_summary": model_summary_list,
                    }

                # uc: major format has changed
                elif (
                    data_sample_iteration > 1
                    and current_detected_major_format
                    and previous_detected_major_format
                    and current_detected_major_format != previous_detected_major_format
                    and previous_detected_major_format != "raw_not_identified"
                ):

                    data_sample_epoch = time.time()
                    data_sample_model_matched_summary = model_split_dict
                    data_sample_anomaly_reason = "format_change"
                    data_sample_feature = "enabled"
                    data_sample_anomaly_detected = 1
                    data_sample_status_colour = "red"
                    data_sample_status_message = {
                        "state": "red",
                        "desc": f"The major event format (the format previously detected for the majority of events) has changed from {previous_detected_major_format} to {current_detected_major_format}, this might indicate a non expected quality issue or condition change in the ingest of this feed in Splunk.",
                        "remediation": "Review the latest sample events to identify the root cause. Once the issue is fixed, click on clear state & run sampling.",
                        "last_run": f"{convert_epoch_to_datetime(data_sample_epoch)}",
                        "anomaly_reason": data_sample_anomaly_reason,
                        "multiformat": multiformat_detected,
                        "events_count": events_count,
                        "min_time_btw_iterations_seconds": min_time_btw_iterations_seconds,
                        "pct_min_major_inclusive_model_match": pct_min_major_inclusive_model_match,
                        "pct_max_exclusive_model_match": pct_max_exclusive_model_match,
                        "max_events_per_sampling_iteration": max_events_per_sampling_iteration,
                        "relative_time_window_seconds": relative_time_window_seconds,
                        "current_detected_major_format": current_detected_major_format,
                        "models_summary": model_summary_list,
                    }

                # no format detected, do not raise an alert
                elif current_detected_major_format == "raw_not_identified":
                    data_sample_epoch = time.time()
                    data_sample_model_matched_summary = model_split_dict
                    data_sample_anomaly_reason = "no_anomalies_detected"
                    data_sample_feature = "enabled"
                    data_sample_anomaly_detected = 2
                    data_sample_status_colour = "orange"
                    data_sample_status_message = {
                        "state": "orange",
                        "desc": "No events format were detected for this entity. (raw_not_identified)",
                        "remediation": "Review events in this feed, you can address this condition by creating a custom model for these events, you can set the sourcetype scope to be matching especially this entity sourcetype or set the sourcetype scope to be eligible for other feeds too.",
                        "last_run": f"{convert_epoch_to_datetime(data_sample_epoch)}",
                        "anomaly_reason": data_sample_anomaly_reason,
                        "multiformat": multiformat_detected,
                        "events_count": events_count,
                        "min_time_btw_iterations_seconds": min_time_btw_iterations_seconds,
                        "pct_min_major_inclusive_model_match": pct_min_major_inclusive_model_match,
                        "pct_max_exclusive_model_match": pct_max_exclusive_model_match,
                        "max_events_per_sampling_iteration": max_events_per_sampling_iteration,
                        "relative_time_window_seconds": relative_time_window_seconds,
                        "current_detected_major_format": current_detected_major_format,
                        "models_summary": model_summary_list,
                    }

                # else, we have no anomalies detected
                else:
                    data_sample_epoch = time.time()
                    data_sample_model_matched_summary = model_split_dict
                    data_sample_anomaly_reason = "no_anomalies_detected"
                    data_sample_feature = "enabled"
                    data_sample_anomaly_detected = 0
                    data_sample_status_colour = "green"
                    data_sample_status_message = {
                        "state": "green",
                        "desc": "No anomalies were detected during the last data sampling iteration.",
                        "remediation": "N/A.",
                        "last_run": f"{convert_epoch_to_datetime(data_sample_epoch)}",
                        "anomaly_reason": data_sample_anomaly_reason,
                        "multiformat": multiformat_detected,
                        "events_count": events_count,
                        "min_time_btw_iterations_seconds": min_time_btw_iterations_seconds,
                        "pct_min_major_inclusive_model_match": pct_min_major_inclusive_model_match,
                        "pct_max_exclusive_model_match": pct_max_exclusive_model_match,
                        "max_events_per_sampling_iteration": max_events_per_sampling_iteration,
                        "relative_time_window_seconds": relative_time_window_seconds,
                        "current_detected_major_format": current_detected_major_format,
                        "models_summary": model_summary_list,
                    }

                # log results
                logging.info(
                    f'tenant_id={self.tenant_id}, Data sampling terminated, object="{object_value}", key="{object_key}", events_count="{events_count}", current_detected_format="{current_detected_format}", data_sample_epoch="{data_sample_epoch}", data_sample_model_matched_summary="{json.dumps(model_split_dict, indent=2)}", data_sample_feature="{data_sample_feature}", data_sample_iteration="{data_sample_iteration}", data_sample_anomaly_reason="{data_sample_anomaly_reason}", data_sample_status_colour="{data_sample_status_colour}", data_sample_anomaly_detected="{data_sample_anomaly_detected}", data_sample_status_message="{json.dumps(data_sample_status_message, indent=2)}", multiformat_detected="{multiformat_detected}", current_detected_format="{current_detected_format}", current_detected_format_id="{current_detected_format_id}", current_detected_format_dcount="{len(current_detected_format)}", previous_detected_format="{previous_detected_format}", previous_detected_format_id="{previous_detected_format_id}", previous_detected_format_dcount="{previous_detected_format_dcount}", exclusive_match_anomaly="{exclusive_match_anomaly}"'
                )

                # insert or update the KVstore record (list of fields in List of fields to be managed in the sampling record)
                if self.mode == "run_sampling":

                    #
                    # restrict samples stored in the KVstore to x events per model match according to system wide configuration
                    #

                    # Group sample events by model match
                    events_by_model = {}

                    for event in sample_events_list:
                        event_data = json.loads(event)
                        model_id = tuple(
                            event_data.get("model_id")
                        )  # Convert model_id list to a tuple

                        # Initialize the list for this model_id if it doesn't exist
                        if model_id not in events_by_model:
                            events_by_model[model_id] = []

                        # Append the event to the corresponding model_id list
                        events_by_model[model_id].append(event_data)

                    # Limit to x events per model match
                    limited_sample_events_list = []
                    for model_id, events in events_by_model.items():
                        # Take events for each model match according to system wide configuration
                        limited_events = events[
                            :splk_data_sampling_no_records_saved_kvrecord
                        ]
                        limited_sample_events_list.extend(limited_events)

                    # Serialize the limited sample events list, considering obfuscation
                    serialized_sample_events_list = []
                    for event in limited_sample_events_list:
                        if data_sampling_obfuscation == 0:
                            # Include raw event data if obfuscation is not enabled
                            serialized_sample_events_list.append(json.dumps(event))
                        else:
                            # Exclude the raw event data if obfuscation is enabled
                            event.pop("event", None)  # Remove the raw event data
                            serialized_sample_events_list.append(json.dumps(event))

                    #
                    # KVstore record update/insert
                    #

                    kvrecord_updated = False

                    try:

                        if not key:

                            # insert
                            collection.data.insert(
                                json.dumps(
                                    {
                                        "_key": object_key,
                                        "object": object_value,
                                        "min_time_btw_iterations_seconds": min_time_btw_iterations_seconds,
                                        "pct_min_major_inclusive_model_match": pct_min_major_inclusive_model_match,
                                        "pct_max_exclusive_model_match": pct_max_exclusive_model_match,
                                        "max_events_per_sampling_iteration": max_events_per_sampling_iteration,
                                        "relative_time_window_seconds": relative_time_window_seconds,
                                        "events_count": events_count,
                                        "data_sample_mtime": data_sample_epoch,
                                        "data_sample_last_entity_epoch_processed": data_last_time_seen,
                                        "data_sample_model_matched_summary": model_split_dict,
                                        "data_sample_feature": data_sample_feature,
                                        "data_sample_iteration": data_sample_iteration,
                                        "data_sample_anomaly_reason": data_sample_anomaly_reason,
                                        "data_sample_status_colour": data_sample_status_colour,
                                        "data_sample_anomaly_detected": data_sample_anomaly_detected,
                                        "data_sample_status_message": data_sample_status_message,
                                        "multiformat_detected": multiformat_detected,
                                        "current_detected_format": current_detected_format,
                                        "current_detected_format_id": current_detected_format_id,
                                        "current_detected_format_dcount": len(
                                            current_detected_format
                                        ),
                                        "current_detected_major_format": current_detected_major_format,
                                        "previous_detected_format": previous_detected_format,
                                        "previous_detected_format_id": previous_detected_format_id,
                                        "previous_detected_format_dcount": previous_detected_format_dcount,
                                        "previous_detected_major_format": previous_detected_major_format,
                                        "exclusive_match_anomaly": exclusive_match_anomaly,
                                        "raw_sample": serialized_sample_events_list,
                                    }
                                )
                            )
                            kvrecord_updated = True

                        else:  # update

                            collection.data.update(
                                key,
                                json.dumps(
                                    {
                                        "_key": key,
                                        "object": object_value,
                                        "min_time_btw_iterations_seconds": min_time_btw_iterations_seconds,
                                        "pct_min_major_inclusive_model_match": pct_min_major_inclusive_model_match,
                                        "pct_max_exclusive_model_match": pct_max_exclusive_model_match,
                                        "max_events_per_sampling_iteration": max_events_per_sampling_iteration,
                                        "relative_time_window_seconds": relative_time_window_seconds,
                                        "events_count": events_count,
                                        "data_sample_mtime": data_sample_epoch,
                                        "data_sample_last_entity_epoch_processed": data_last_time_seen,
                                        "data_sample_model_matched_summary": model_split_dict,
                                        "data_sample_feature": data_sample_feature,
                                        "data_sample_iteration": data_sample_iteration,
                                        "data_sample_anomaly_reason": data_sample_anomaly_reason,
                                        "data_sample_status_colour": data_sample_status_colour,
                                        "data_sample_anomaly_detected": data_sample_anomaly_detected,
                                        "data_sample_status_message": data_sample_status_message,
                                        "multiformat_detected": multiformat_detected,
                                        "current_detected_format": current_detected_format,
                                        "current_detected_format_id": current_detected_format_id,
                                        "current_detected_format_dcount": len(
                                            current_detected_format
                                        ),
                                        "current_detected_major_format": current_detected_major_format,
                                        "previous_detected_format": previous_detected_format,
                                        "previous_detected_format_id": previous_detected_format_id,
                                        "previous_detected_format_dcount": previous_detected_format_dcount,
                                        "previous_detected_major_format": previous_detected_major_format,
                                        "exclusive_match_anomaly": exclusive_match_anomaly,
                                        "raw_sample": serialized_sample_events_list,
                                    }
                                ),
                            )

                            kvrecord_updated = True

                            logging.info(
                                f'tenant_id="{self.tenant_id}", component="dsm", successfully updated the KVstore record'
                            )

                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", component="dsm", failed to insert or update the KVstore record, exception="{str(e)}"'
                        )

                    # yield a simple summary record
                    yield_record = {
                        "_time": time.time(),
                        "object": object_value,
                        "events_count": events_count,
                        "data_sample_status_message": data_sample_status_message,
                        "data_sample_model_matched_summary": model_split_dict,
                        "kvrecord_updated": kvrecord_updated,
                        "run_time": round(time.time() - iteration_start_time, 2),
                    }
                    yield_record["_raw"] = json.dumps(yield_record)
                    yield yield_record

                # gen models metrics
                try:
                    trackme_splk_dsm_data_sampling_gen_metrics(
                        self.tenant_id,
                        metric_index,
                        object_value,
                        object_key,
                        model_split_dict,
                    )
                except Exception as e:
                    error_msg = f'tenant_id="{self.tenant_id}", object="{object_value}", object_id="{key}", failed to stream events to metrics with exception="{str(e)}"'
                    logging.error(error_msg)

                # gen metrics
                entity_total_elapsed_time = time.time() - entity_search_start
                try:
                    trackme_splk_dsm_data_sampling_total_run_time_gen_metrics(
                        self.tenant_id,
                        metric_index,
                        object_value,
                        object_key,
                        entity_total_elapsed_time,
                        events_count,
                    )
                except Exception as e:
                    error_msg = f'tenant_id="{self.tenant_id}", object="{object_value}", object_id="{key}", failed to stream events to metrics with exception="{str(e)}"'
                    logging.error(error_msg)

                # notification event
                try:
                    trackme_handler_events(
                        session_key=self._metadata.searchinfo.session_key,
                        splunkd_uri=self._metadata.searchinfo.splunkd_uri,
                        tenant_id=self.tenant_id,
                        sourcetype="trackme:handler",
                        source=f"trackme:handler:{self.tenant_id}",
                        handler_events=[
                            {
                                "object": object_value,
                                "object_id": object_key,
                                "object_category": f"splk-dsm",
                                "handler": f"trackme_dsm_data_sampling_tracker_tenant_{self.tenant_id}",
                                "handler_message": "Data sampling was performed for this entity.",
                                "handler_troubleshoot_search": f'index=_internal sourcetype=trackme:custom_commands:trackmesamplingexecutortenant_id={self.tenant_id} object="{object_value}"',
                                "handler_time": time.time(),
                            }
                        ],
                    )
                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", component="dsm", could not send notification event, exception="{e}"'
                    )

                # Calculate the execution time for this iteration
                iteration_end_time = time.time()
                execution_time = iteration_end_time - iteration_start_time

                # Update total execution time and iteration count
                total_execution_time += execution_time
                iteration_count += 1

                # Calculate average execution time
                if iteration_count > 0:
                    average_execution_time = total_execution_time / iteration_count
                else:
                    average_execution_time = 0

                # Check if there is enough time left to continue
                elapsed_time = time.time() - start

                if elapsed_time + average_execution_time + 120 >= max_runtime:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="dsm", max_runtime="{max_runtime}" is about to be reached, current_runtime="{elapsed_time}", job will be terminated now'
                    )
                    break

            # end of the main loop
            if entities_count == 0:

                # yield a simple summary record
                yield_record = {
                    "_time": time.time(),
                    "result": "There are no entities to process at this time.",
                    "search": upstream_search_string,
                }
                yield_record["_raw"] = json.dumps(yield_record)
                yield yield_record

            # end
            logging.info(
                f'tenant_id="{self.tenant_id}" data sampling job successfully executed, status="success", run_time="{round(time.time() - start, 3)}", report_name="{str(report_name)}", entities_count="{str(count)}"'
            )

            # Call the component register
            if self.mode == "run_sampling":
                trackme_register_tenant_object_summary(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    "splk-dsm",
                    f"trackme_dsm_data_sampling_tracker_tenant_{self.tenant_id}",
                    "success",
                    time.time(),
                    str(time.time() - start),
                    "The report was executed successfully",
                    "-24h",
                    "now",
                )


dispatch(DataSamplingExecutor, sys.argv, sys.stdin, sys.stdout, __name__)

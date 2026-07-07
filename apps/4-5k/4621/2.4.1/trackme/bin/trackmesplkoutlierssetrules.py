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
import hashlib
import json
import ast
import logging
import os
import random
import sys
import time
import concurrent.futures
from logging.handlers import RotatingFileHandler

# Third-party imports
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_outliers_set_rules.log" % splunkhome,
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

# Import trackme libs
from trackme_libs import trackme_reqinfo, trackme_vtenant_account
from trackme_libs_mloutliers import (
    is_outliers_eligible_for_entity,
    get_effective_outliers_volume_kpi,
)

# Import trackme libs
from trackme_libs_utils import get_uuid

# import TrackMe get data libs
from trackme_libs_get_data import (
    search_kv_collection_restmode,
    search_kv_collection_searchmode,
    search_kv_collection_sdkmode,
)

# Import trackMe kvstore batch libs
from trackme_libs_kvstore_batch import batch_update_worker

# Import collections data for default values
from collections_data import vtenant_account_default


@Configuration(distributed=False)
class SplkOutliersSetRules(StreamingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The value for tenant_id.""",
        require=True,
        validate=validators.Match("tenant_id", r"^.*$"),
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** The component category.""",
        require=True,
        default=None,
        validate=validators.Match("component", r"^(?:dsm|dhm|flx|fqm|wlk)$"),
    )

    def get_impact_score(self, vtenant_account, field_name, default_value):
        """
        Helper function to get impact score from vtenant_account with fallback to default.
        
        Args:
            vtenant_account: Dictionary containing virtual tenant account configuration
            field_name: Name of the impact score field to retrieve
            default_value: Default value to use if field is not found
        
        Returns:
            Integer impact score value
        """
        if vtenant_account and isinstance(vtenant_account, dict):
            value = vtenant_account.get(field_name)
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    pass
        # Fallback to vtenant_account_default if available
        default = vtenant_account_default.get(field_name, default_value)
        try:
            return int(default)
        except (ValueError, TypeError):
            return default_value


    def stream(self, records):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get virtual tenant account
        vtenant_conf = trackme_vtenant_account(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )

        # Early exit: if outliers are globally disabled or disabled for this component, passthrough
        # Default to 1 (enabled) matching vtenant_account_default and REST handler behavior
        try:
            mloutliers_global = int(vtenant_conf.get("mloutliers", 1))
        except (ValueError, TypeError):
            mloutliers_global = 1
        try:
            mloutliers_component = int(vtenant_conf.get(f"mloutliers_{self.component}", 1))
        except (ValueError, TypeError):
            mloutliers_component = 1

        if not mloutliers_global or not mloutliers_component:
            init_run_time = round(time.time() - start, 3)
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                f"outliers disabled (mloutliers={mloutliers_global}, "
                f"mloutliers_{self.component}={mloutliers_component}), "
                f"skipping outliers rules processing, passthrough mode, "
                f"run_time={init_run_time}"
            )
            for record in records:
                yield record
            return

        # Max multi thread workers
        max_multi_thread_workers = int(
            reqinfo["trackme_conf"]["trackme_general"]["max_multi_thread_workers"]
        )

        # set instance_id
        self.instance_id = get_uuid()

        # Get app level config
        splk_outliers_detection = reqinfo["trackme_conf"]["splk_outliers_detection"]

        # Assign
        splk_outliers_score_default = self.get_impact_score(vtenant_conf, "impact_score_outliers_default", 36)
        splk_outliers_detection_disable_default = splk_outliers_detection[
            "splk_outliers_detection_disable_default"
        ]
        splk_outliers_calculation_default = splk_outliers_detection[
            "splk_outliers_calculation_default"
        ]
        splk_outliers_density_lower_threshold_default = splk_outliers_detection[
            "splk_outliers_density_lower_threshold_default"
        ]
        splk_outliers_density_upper_threshold_default = splk_outliers_detection[
            "splk_outliers_density_upper_threshold_default"
        ]
        splk_outliers_alert_lower_threshold_volume_default = splk_outliers_detection[
            "splk_outliers_alert_lower_threshold_volume_default"
        ]
        splk_outliers_alert_upper_threshold_volume_default = splk_outliers_detection[
            "splk_outliers_alert_upper_threshold_volume_default"
        ]
        splk_outliers_alert_lower_threshold_latency_default = splk_outliers_detection[
            "splk_outliers_alert_lower_threshold_latency_default"
        ]
        splk_outliers_alert_upper_threshold_latency_default = splk_outliers_detection[
            "splk_outliers_alert_upper_threshold_latency_default"
        ]
        splk_outliers_detection_period_default = splk_outliers_detection[
            "splk_outliers_detection_period_default"
        ]
        splk_outliers_detection_period_latest_default = splk_outliers_detection[
            "splk_outliers_detection_period_latest_default"
        ]
        splk_outliers_detection_timefactor_default = splk_outliers_detection[
            "splk_outliers_detection_timefactor_default"
        ]
        splk_outliers_detection_latency_kpi_metric_default = splk_outliers_detection[
            "splk_outliers_detection_latency_kpi_metric_default"
        ]
        splk_outliers_detection_volume_kpi_metric_default = splk_outliers_detection[
            "splk_outliers_detection_volume_kpi_metric_default"
        ]
        # Tenant-level volume KPI override (2.3.22): falls back to the global
        # default if unset, and is ignored entirely for flx/fqm/wlk components.
        effective_volume_kpi = get_effective_outliers_volume_kpi(
            vtenant_conf,
            self.component,
            splk_outliers_detection_volume_kpi_metric_default,
        )
        splk_outliers_perc_min_lowerbound_deviation_default = splk_outliers_detection[
            "splk_outliers_perc_min_lowerbound_deviation_default"
        ]
        splk_outliers_perc_min_upperbound_deviation_default = splk_outliers_detection[
            "splk_outliers_perc_min_upperbound_deviation_default"
        ]
        splk_outliers_mltk_algorithms_default = splk_outliers_detection.get(
            "splk_outliers_mltk_algorithms_default", "DensityFunction"
        )
        splk_outliers_boundaries_extraction_macro_default = splk_outliers_detection.get(
            "splk_outliers_boundaries_extraction_macro_default",
            "splk_outliers_extract_boundaries",
        )
        splk_outliers_fit_extra_attributes_default = splk_outliers_detection.get(
            "splk_outliers_fit_extra_parameters", None
        )
        splk_outliers_apply_extra_attributes_default = splk_outliers_detection.get(
            "splk_outliers_apply_extra_parameters", None
        )
        splk_outliers_static_lower_threshold_default = splk_outliers_detection.get(
            "splk_outliers_static_lower_threshold", None
        )
        splk_outliers_static_upper_threshold_default = splk_outliers_detection.get(
            "splk_outliers_static_upper_threshold", None
        )
        splk_outliers_auto_correct = splk_outliers_detection[
            "splk_outliers_auto_correct"
        ]
        splk_outliers_native_model_storage_default = splk_outliers_detection.get(
            "splk_outliers_native_model_storage", "kvstore"
        )

        #
        # Outliers rules collection
        #

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "get_outliers_rules_collection_records"

        collection_outliers_name = (
            f"kv_trackme_{self.component}_outliers_entity_rules_tenant_{self.tenant_id}"
        )
        collection_outliers = self.service.kvstore[collection_outliers_name]

        # get records array and dict
        (
            collection_outliers_records,
            collection_outliers_records_keys,
            collection_outliers_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logging,
            self.service,
            collection_outliers_name,
            page=1,
            page_count=0,
            orderby="keyid",
        )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        #
        # Data collection
        #

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "get_data_collection_records"

        collection_data_name = f"kv_trackme_{self.component}_tenant_{self.tenant_id}"
        collection_data = self.service.kvstore[collection_data_name]

        # get records array and dict
        (
            collection_data_records,
            collection_data_records_keys,
            collection_data_dict,
            last_page,
        ) = search_kv_collection_sdkmode(
            logging,
            self.service,
            collection_data_name,
            page=1,
            page_count=0,
            orderby="keyid",
        )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated.'
        )

        # final records to be batched processed in the KVstore
        final_records = []

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "process_records"

        # Counters for entities that are eligible for outliers rule creation
        # but excluded by the tenant-level filter (priority + expression DSL,
        # 2.3.22). Existing rules on already-trained entities are intentionally
        # NOT removed — the trainhelper's gate stops them from training, and
        # leaving rules in place lets a tenant widen the filter without losing
        # historical rule configuration.
        skipped_priority_filter = 0
        skipped_filter_expression = 0
        skipped_filter_expression_invalid = 0

        # Loop in the results
        for record in records:
            # check if outliers models are defined already
            outliers_models_defined = (
                hashlib.sha256(record["object"].encode("utf-8")).hexdigest()
                in collection_outliers_records_keys
            )

            # Create a new outliers rules record if necessary
            check_for_creation = False

            # Tenant-level ML Outliers eligibility gate (2.3.22): skip rule
            # creation for entities the tenant's priority filter or filter
            # expression excludes. The pre-existing rule (if any) is left
            # untouched. The record still passes through to downstream
            # commands via the yield at the bottom of the loop.
            outliers_eligible, outliers_skip_reason = is_outliers_eligible_for_entity(
                vtenant_conf, record
            )
            if not outliers_eligible:
                if outliers_skip_reason == "priority_filter":
                    skipped_priority_filter += 1
                elif outliers_skip_reason == "filter_expression":
                    skipped_filter_expression += 1
                elif outliers_skip_reason == "filter_expression_invalid":
                    skipped_filter_expression_invalid += 1
                logging.debug(
                    f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                    f'component="{self.component}", object="{record.get("object")}", '
                    f'priority="{record.get("priority")}", '
                    f'skipped from ML Outliers rule creation by tenant filter, '
                    f'reason="{outliers_skip_reason}"'
                )
                # Skip rule creation. The yield-passthrough at the bottom of
                # the loop still runs; any existing rule record remains.
                yield_record = {k: record[k] for k in record}
                yield yield_record
                continue

            # for splk-flx, splk-fqm, splk-wlk, we expect a value for the field outliers_metrics which contains the definition of the models to be managed, otherwise we have nothing to verify
            if self.component in ("flx", "fqm", "wlk"):
                # get the value for outliers_metrics
                record_object = record.get("object")
                record_outliers_metrics = record.get("outliers_metrics", None)

                # verify
                if record_outliers_metrics:
                    try:
                        record_outliers_metrics = json.loads(record_outliers_metrics)
                        check_for_creation = True
                    except ValueError:
                        try:
                            record_outliers_metrics = ast.literal_eval(
                                record_outliers_metrics
                            )
                            check_for_creation = True
                        except Exception as e:
                            logging.info(
                                f'instance_id={self.instance_id}, object="{record_object}", failed to extract outliers_metrics definition, outliers_metrics="{record_outliers_metrics}", exception="{str(e)}"'
                            )

            # for other components, we create models if these are not defined yet
            else:
                check_for_creation = True

            #
            # procced if required
            #

            if not outliers_models_defined and check_for_creation:
                # Insert a new kvrecord
                try:
                    # Set rules
                    if self.component in ("dsm", "dhm"):

                        def create_model(
                            kpi_metric, alert_lower_breached, alert_upper_breached
                        ):
                            return {
                                "model_"
                                + str(random.getrandbits(48)): {
                                    "is_disabled": 0,
                                    "score": splk_outliers_score_default,
                                    "kpi_metric": kpi_metric,
                                    "kpi_span": "10m",
                                    "method_calculation": splk_outliers_calculation_default,
                                    "density_lowerthreshold": splk_outliers_density_lower_threshold_default,
                                    "density_upperthreshold": splk_outliers_density_upper_threshold_default,
                                    "alert_lower_breached": alert_lower_breached,
                                    "alert_upper_breached": alert_upper_breached,
                                    "period_calculation": splk_outliers_detection_period_default,
                                    "period_calculation_latest": splk_outliers_detection_period_latest_default,
                                    "time_factor": splk_outliers_detection_timefactor_default,
                                    "auto_correct": splk_outliers_auto_correct,
                                    "perc_min_lowerbound_deviation": splk_outliers_perc_min_lowerbound_deviation_default,
                                    "perc_min_upperbound_deviation": splk_outliers_perc_min_upperbound_deviation_default,
                                    "min_value_for_lowerbound_breached": 0,
                                    "min_value_for_upperbound_breached": 0,
                                    "period_exclusions": [],
                                    "algorithm": splk_outliers_mltk_algorithms_default,
                                    "model_storage": splk_outliers_native_model_storage_default if splk_outliers_mltk_algorithms_default == "TrackMeNativeDensityFunction" else "file",
                                    "extract_boundaries_macro": splk_outliers_boundaries_extraction_macro_default,
                                    "fit_extra_parameters": splk_outliers_fit_extra_attributes_default,
                                    "apply_extra_parameters": splk_outliers_apply_extra_attributes_default,
                                    "static_lower_threshold": splk_outliers_static_lower_threshold_default,
                                    "static_upper_threshold": splk_outliers_static_upper_threshold_default,
                                    "ml_model_gen_search": "pending",
                                    "ml_model_render_search": "pending",
                                    "ml_model_summary_search": "pending",
                                    "rules_access_search": "pending",
                                    "ml_model_filename": "pending",
                                    "ml_model_filesize": "pending",
                                    "ml_model_lookup_share": "pending",
                                    "ml_model_lookup_owner": "pending",
                                    "last_exec": "pending",
                                }
                            }

                        if self.component in ("dsm", "dhm"):
                            new_entity_outliers = {}

                            if (
                                splk_outliers_detection_latency_kpi_metric_default
                                != "None"
                            ):
                                model = create_model(
                                    splk_outliers_detection_latency_kpi_metric_default,
                                    splk_outliers_alert_lower_threshold_latency_default,
                                    splk_outliers_alert_upper_threshold_latency_default,
                                )
                                new_entity_outliers.update(model)

                            if effective_volume_kpi != "None":
                                model = create_model(
                                    effective_volume_kpi,
                                    splk_outliers_alert_lower_threshold_volume_default,
                                    splk_outliers_alert_upper_threshold_volume_default,
                                )
                                new_entity_outliers.update(model)

                        new_kvrecord = {
                            "_key": hashlib.sha256(
                                record["object"].encode("utf-8")
                            ).hexdigest(),
                            "object": record["object"],
                            "object_category": "splk-" + self.component,
                            "mtime": time.time(),
                            "is_disabled": splk_outliers_detection_disable_default,
                            "entities_outliers": json.dumps(
                                new_entity_outliers, indent=4
                            ),
                            "last_exec": "pending",
                            "confidence": "low",
                            "confidence_reason": "pending",
                        }

                        final_records.append(new_kvrecord)
                        logging.info(
                            f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", Outliers rules new record created, record="{json.dumps(new_kvrecord, indent=4)}"'
                        )

                    # for splk-flx/splk-fqm/splk-wlk
                    elif self.component in ("flx", "fqm", "wlk"):
                        record_object = record.get("object")
                        record_outliers_metrics = record.get("outliers_metrics", None)
                        record_definition_is_valid = False

                        try:
                            record_outliers_metrics = json.loads(
                                record_outliers_metrics
                            )
                            record_definition_is_valid = True
                        except ValueError:
                            try:
                                record_outliers_metrics = ast.literal_eval(
                                    record_outliers_metrics
                                )
                                record_definition_is_valid = True
                            except Exception as e:
                                logging.info(
                                    f'instance_id={self.instance_id}, object="{record_object}", failed to extract outliers_metrics definition, outliers_metrics="{record_outliers_metrics}", exception="{str(e)}"'
                                )

                        # if record_outliers_metrics is an empty dict, record_definition_is_valid must be False
                        if not record_outliers_metrics:
                            record_definition_is_valid = False

                        if record_definition_is_valid:
                            # set an empty record, we may have nothing to define here
                            new_entity_outliers = {}

                            # Assuming defaults are defined earlier in the code
                            defaults_outliers_settings = {
                                "is_disabled": 0,
                                "score": splk_outliers_score_default,
                                "kpi_span": "10m",
                                "method_calculation": splk_outliers_calculation_default,
                                "period_calculation": splk_outliers_detection_period_default,
                                "period_calculation_latest": splk_outliers_detection_period_latest_default,
                                "time_factor": splk_outliers_detection_timefactor_default,
                                "density_lowerthreshold": splk_outliers_density_lower_threshold_default,
                                "density_upperthreshold": splk_outliers_density_upper_threshold_default,
                                "alert_lower_breached": 1,
                                "alert_upper_breached": 1,
                                "auto_correct": splk_outliers_auto_correct,
                                "min_value_for_lowerbound_breached": 0,
                                "min_value_for_upperbound_breached": 0,
                                "algorithm": splk_outliers_mltk_algorithms_default,
                                "model_storage": splk_outliers_native_model_storage_default if splk_outliers_mltk_algorithms_default == "TrackMeNativeDensityFunction" else "file",
                                "extract_boundaries_macro": splk_outliers_boundaries_extraction_macro_default,
                                "fit_extra_parameters": splk_outliers_fit_extra_attributes_default,
                                "apply_extra_parameters": splk_outliers_apply_extra_attributes_default,
                                "static_lower_threshold": splk_outliers_static_lower_threshold_default,
                                "static_upper_threshold": splk_outliers_static_upper_threshold_default,
                            }

                            # loop through the list of default metrics to be added
                            for outliers_metric in record_outliers_metrics:

                                # get the kpi_dict
                                kpi_dict = record_outliers_metrics[outliers_metric]

                                # Simplified handling of optional keys with defaults

                                # is_disabled (integer, 0 or 1)
                                splk_outliers_detection_disable_default = kpi_dict.get(
                                    "is_disabled",
                                    defaults_outliers_settings["is_disabled"],
                                )
                                if not isinstance(
                                    splk_outliers_detection_disable_default, int
                                ) or splk_outliers_detection_disable_default not in [
                                    0,
                                    1,
                                ]:
                                    # Handle invalid value here, such as setting a default value or raising an exception
                                    splk_outliers_detection_disable_default = (
                                        defaults_outliers_settings["is_disabled"]
                                    )

                                # kpi_span
                                splk_outliers_detection_kpi_span = kpi_dict.get(
                                    "kpi_span", defaults_outliers_settings["kpi_span"]
                                )

                                # method_calculation
                                splk_outliers_detection_method_calculation = (
                                    kpi_dict.get(
                                        "method_calculation",
                                        defaults_outliers_settings[
                                            "method_calculation"
                                        ],
                                    )
                                )
                                if splk_outliers_detection_method_calculation not in [
                                    "avg",
                                    "max",
                                    "stdev",
                                    "perc95",
                                    "latest",
                                ]:
                                    # Handle invalid value here, such as setting a default value or raising an exception
                                    splk_outliers_detection_method_calculation = (
                                        defaults_outliers_settings["method_calculation"]
                                    )

                                # period_calculation
                                splk_outliers_detection_period_default = kpi_dict.get(
                                    "period_calculation",
                                    defaults_outliers_settings["period_calculation"],
                                )

                                # period_calculation_latest
                                splk_outliers_detection_period_latest_default = (
                                    kpi_dict.get(
                                        "period_calculation_latest",
                                        defaults_outliers_settings[
                                            "period_calculation_latest"
                                        ],
                                    )
                                )

                                # lower density threshold
                                splk_outliers_density_lower_threshold = kpi_dict.get(
                                    "density_lowerthreshold",
                                    defaults_outliers_settings[
                                        "density_lowerthreshold"
                                    ],
                                )
                                if not isinstance(
                                    splk_outliers_density_lower_threshold, float
                                ):
                                    # Handle invalid value here, such as setting a default value or raising an exception
                                    splk_outliers_density_lower_threshold = (
                                        defaults_outliers_settings[
                                            "density_lowerthreshold"
                                        ]
                                    )

                                # upper density threshold
                                splk_outliers_density_upper_threshold = kpi_dict.get(
                                    "density_upperthreshold",
                                    defaults_outliers_settings[
                                        "density_upperthreshold"
                                    ],
                                )
                                if not isinstance(
                                    splk_outliers_density_upper_threshold, float
                                ):
                                    # Handle invalid value here, such as setting a default value or raising an exception
                                    splk_outliers_density_upper_threshold = (
                                        defaults_outliers_settings[
                                            "density_upperthreshold"
                                        ]
                                    )

                                # time factor
                                splk_outliers_detection_timefactor = kpi_dict.get(
                                    "time_factor",
                                    defaults_outliers_settings["time_factor"],
                                )

                                # alert_lower_breached
                                splk_outliers_alert_lower_breached = kpi_dict.get(
                                    "alert_lower_breached",
                                    defaults_outliers_settings["alert_lower_breached"],
                                )
                                if not isinstance(
                                    splk_outliers_alert_lower_breached, int
                                ) or splk_outliers_alert_lower_breached not in [0, 1]:
                                    # Handle invalid value here, such as setting a default value or raising an exception
                                    splk_outliers_alert_lower_breached = (
                                        defaults_outliers_settings[
                                            "alert_lower_breached"
                                        ]
                                    )

                                # alert_upper_breached
                                splk_outliers_alert_upper_breached = kpi_dict.get(
                                    "alert_upper_breached",
                                    defaults_outliers_settings["alert_upper_breached"],
                                )
                                if not isinstance(
                                    splk_outliers_alert_upper_breached, int
                                ) or splk_outliers_alert_upper_breached not in [0, 1]:
                                    splk_outliers_alert_upper_breached = (
                                        defaults_outliers_settings[
                                            "alert_upper_breached"
                                        ]
                                    )

                                # auto_correct (integer, 0 or 1)
                                splk_outliers_auto_correct = kpi_dict.get(
                                    "auto_correct",
                                    defaults_outliers_settings["auto_correct"],
                                )
                                if not isinstance(
                                    splk_outliers_auto_correct, int
                                ) or splk_outliers_auto_correct not in [0, 1]:
                                    defaults_outliers_settings["auto_correct"]

                                # min value for lowerbound breached
                                splk_outliers_detection_min_value_for_lowerbound_breached = kpi_dict.get(
                                    "min_value_for_lowerbound_breached",
                                    defaults_outliers_settings[
                                        "min_value_for_lowerbound_breached"
                                    ],
                                )
                                if not isinstance(
                                    splk_outliers_detection_min_value_for_lowerbound_breached,
                                    (float, int),
                                ):
                                    # Handle invalid value here
                                    splk_outliers_detection_min_value_for_lowerbound_breached = defaults_outliers_settings[
                                        "min_value_for_lowerbound_breached"
                                    ]

                                # min value for upperbound breached
                                splk_outliers_detection_min_value_for_upperbound_breached = kpi_dict.get(
                                    "min_value_for_upperbound_breached",
                                    defaults_outliers_settings[
                                        "min_value_for_upperbound_breached"
                                    ],
                                )
                                if not isinstance(
                                    splk_outliers_detection_min_value_for_upperbound_breached,
                                    (float, int),
                                ):
                                    # Handle invalid value here
                                    splk_outliers_detection_min_value_for_upperbound_breached = defaults_outliers_settings[
                                        "min_value_for_upperbound_breached"
                                    ]

                                # static_lower_threshold
                                splk_outliers_static_lower_threshold = kpi_dict.get(
                                    "static_lower_threshold",
                                    defaults_outliers_settings[
                                        "static_lower_threshold"
                                    ],
                                )
                                if not isinstance(
                                    splk_outliers_static_lower_threshold, (float, int)
                                ):
                                    # Handle invalid value here
                                    splk_outliers_static_lower_threshold = (
                                        defaults_outliers_settings[
                                            "static_lower_threshold"
                                        ]
                                    )

                                # static_upper_threshold
                                splk_outliers_static_upper_threshold = kpi_dict.get(
                                    "static_upper_threshold",
                                    defaults_outliers_settings[
                                        "static_upper_threshold"
                                    ],
                                )
                                if not isinstance(
                                    splk_outliers_static_upper_threshold, (float, int)
                                ):
                                    # Handle invalid value here
                                    splk_outliers_static_upper_threshold = (
                                        defaults_outliers_settings[
                                            "static_upper_threshold"
                                        ]
                                    )

                                # algorithm
                                splk_outliers_mltk_algorithms = kpi_dict.get(
                                    "algorithm",
                                    defaults_outliers_settings["algorithm"],
                                )

                                # extract_boundaries_macro
                                splk_outliers_boundaries_extraction_macro = (
                                    kpi_dict.get(
                                        "extract_boundaries_macro",
                                        defaults_outliers_settings[
                                            "extract_boundaries_macro"
                                        ],
                                    )
                                )

                                # fit_extra_parameters
                                splk_outliers_fit_extra_attributes = kpi_dict.get(
                                    "fit_extra_parameters",
                                    defaults_outliers_settings["fit_extra_parameters"],
                                )

                                # apply_extra_parameters
                                splk_outliers_apply_extra_attributes = kpi_dict.get(
                                    "apply_extra_parameters",
                                    defaults_outliers_settings[
                                        "apply_extra_parameters"
                                    ],
                                )

                                # score
                                splk_outliers_score = kpi_dict.get(
                                    "score",
                                    defaults_outliers_settings["score"],
                                )
                                # Validate score (must be integer between 0 and 100)
                                try:
                                    splk_outliers_score = int(splk_outliers_score)
                                    if splk_outliers_score < 0 or splk_outliers_score > 100:
                                        # Handle invalid value here
                                        splk_outliers_score = defaults_outliers_settings[
                                            "score"
                                        ]
                                except (ValueError, TypeError):
                                    # Handle invalid value here
                                    splk_outliers_score = defaults_outliers_settings[
                                        "score"
                                    ]

                                # Constructing the new entity outlier dictionary more efficiently
                                new_entity_outliers[
                                    "model_" + str(random.getrandbits(48))
                                ] = {
                                    "is_disabled": splk_outliers_detection_disable_default,
                                    "kpi_metric": f"splk.{self.component}.{outliers_metric}",
                                    "kpi_span": splk_outliers_detection_kpi_span,
                                    "method_calculation": splk_outliers_detection_method_calculation,
                                    "density_lowerthreshold": splk_outliers_density_lower_threshold,
                                    "density_upperthreshold": splk_outliers_density_upper_threshold,
                                    "alert_lower_breached": splk_outliers_alert_lower_breached,
                                    "alert_upper_breached": splk_outliers_alert_upper_breached,
                                    "period_calculation": splk_outliers_detection_period_default,
                                    "period_calculation_latest": splk_outliers_detection_period_latest_default,
                                    "time_factor": splk_outliers_detection_timefactor,
                                    "auto_correct": splk_outliers_auto_correct,
                                    "perc_min_lowerbound_deviation": splk_outliers_perc_min_lowerbound_deviation_default,
                                    "perc_min_upperbound_deviation": splk_outliers_perc_min_upperbound_deviation_default,
                                    "min_value_for_lowerbound_breached": splk_outliers_detection_min_value_for_lowerbound_breached,
                                    "min_value_for_upperbound_breached": splk_outliers_detection_min_value_for_upperbound_breached,
                                    "static_lower_threshold": splk_outliers_static_lower_threshold,
                                    "static_upper_threshold": splk_outliers_static_upper_threshold,
                                    "period_exclusions": [],
                                    "algorithm": splk_outliers_mltk_algorithms,
                                    "model_storage": splk_outliers_native_model_storage_default if splk_outliers_mltk_algorithms == "TrackMeNativeDensityFunction" else "file",
                                    "extract_boundaries_macro": splk_outliers_boundaries_extraction_macro,
                                    "fit_extra_parameters": splk_outliers_fit_extra_attributes,
                                    "apply_extra_parameters": splk_outliers_apply_extra_attributes,
                                    "score": splk_outliers_score,
                                    "ml_model_gen_search": "pending",
                                    "ml_model_render_search": "pending",
                                    "ml_model_summary_search": "pending",
                                    "rules_access_search": "pending",
                                    "ml_model_filename": "pending",
                                    "ml_model_filesize": "pending",
                                    "ml_model_lookup_share": "pending",
                                    "ml_model_lookup_owner": "pending",
                                    "last_exec": "pending",
                                }

                                # Constructing the new kvrecord dictionary
                                new_kvrecord = {
                                    "_key": hashlib.sha256(
                                        record["object"].encode("utf-8")
                                    ).hexdigest(),
                                    "object": record["object"],
                                    "object_category": "splk-" + self.component,
                                    "mtime": time.time(),
                                    "is_disabled": splk_outliers_detection_disable_default,
                                    "entities_outliers": json.dumps(
                                        new_entity_outliers, indent=4
                                    ),
                                    "last_exec": "pending",
                                    "confidence": "low",
                                    "confidence_reason": "pending",
                                }

                            final_records.append(new_kvrecord)
                            logging.info(
                                f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", Outliers rules new record created, record="{json.dumps(new_kvrecord, indent=4)}"'
                            )

                except Exception as e:
                    logging.error(
                        f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", Outliers rules creation failed with exception="{str(e)}"'
                    )

            # yield original record
            yield_record = {}

            # loop through the fields, add to the dict record
            for k in record:
                yield_record[k] = record[k]

            yield yield_record

        # Summarise tenant-filter skips so operators can correlate "fewer
        # rules created than expected" with the configured ML Outliers scope.
        if (
            skipped_priority_filter
            or skipped_filter_expression
            or skipped_filter_expression_invalid
        ):
            logging.info(
                f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                f'component="{self.component}", '
                f'ML Outliers tenant filter skipped rule creation: '
                f'priority_filter={skipped_priority_filter}, '
                f'filter_expression={skipped_filter_expression}, '
                f'filter_expression_invalid={skipped_filter_expression_invalid}'
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
        task_name = "kvstore_batch_update"

        # Execute batch update synchronously
        batch_update_worker(
            collection_outliers_name,
            collection_outliers,
            final_records,
            self.instance_id,
            task_instance_id,
            task_name=task_name,
            max_multi_thread_workers=max_multi_thread_workers,
        )

        # end task
        #
        task_end = time.time()
        task_run_time = round((task_end - task_start), 3)
        logging.info(
            f'instance_id={self.instance_id}, task="{task_name}", task_instance_id={task_instance_id}, task_run_time="{task_run_time}", task_end=1, task has terminated. no_records="{len(final_records)}", collection="{collection_outliers_name}"'
        )

        # Log the run time
        logging.info(
            f'instance_id={self.instance_id}, trackmesplkoutlierssetrules has terminated, tenant_id="{self.tenant_id}", component="{self.component}", run_time={round(time.time() - start, 3)}'
        )


dispatch(SplkOutliersSetRules, sys.argv, sys.stdin, sys.stdout, __name__)

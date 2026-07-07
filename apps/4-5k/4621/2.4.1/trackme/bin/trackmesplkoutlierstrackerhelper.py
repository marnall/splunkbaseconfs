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
import json
import hashlib

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_outliers_tracker_helper.log" % splunkhome,
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
    trackme_vtenant_component_info,
    trackme_register_tenant_component_summary,
    trackme_register_tenant_object_summary,
    run_splunk_search,
    trackme_handler_events,
    trackme_idx_for_tenant,
    trackme_gen_state,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces, decode_unicode

# import trackme libs croniter
from trackme_libs_croniter import cron_to_seconds

# import trackme libs scoring
from trackme_libs_scoring import trackme_scoring_gen_metrics

@Configuration(distributed=False)
class SplkOutliersTracker(GeneratingCommand):
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
        **Description:** The component category.""",
        require=True,
        default=None,
        validate=validators.Match("component", r"^(?:dsm|dhm|flx|fqm|wlk)$"),
    )

    object = Option(
        doc="""
        **Syntax:** **object=****
        **Description:** Optional, The value for object.""",
        require=False,
        default="*",
        validate=validators.Match("object", r"^.*$"),
    )

    object_id = Option(
        doc="""
        **Syntax:** **object_id=****
        **Description:** Optional, The value for object id.""",
        require=False,
        default="*",
        validate=validators.Match("object_id", r"^.*$"),
    )

    max_runtime = Option(
        doc="""
        **Syntax:** **max_runtime=****
        **Description:** Optional, The max value in seconds for the total runtime of the job, defaults to 900 (15 min) which is subtracted by 120 sec of margin. Once the job reaches this, it gets terminated""",
        require=False,
        default="900",
        validate=validators.Match("object", r"^\d*$"),
    )

    def _get_log_object_ref(self, object_value=None, object_id_value=None):
        """Helper function to get object reference for logging (includes object_id when available)."""
        object_id_ref = f'object_id="{object_id_value}"' if object_id_value else ""
        object_ref = f'object="{object_value}"' if object_value else ""
        if object_id_ref and object_ref:
            return f'{object_id_ref}, {object_ref}'
        elif object_id_ref:
            return object_id_ref
        elif object_ref:
            return object_ref
        else:
            return 'object="*"'

    force_run = Option(
        doc="""
        **Syntax:** **force_run=****
        **Description:** Optional, force run monitor, if set to True we will not honour the minimal time between two monitor execution.""",
        require=False,
        default="False",
        validate=validators.Match("force_run", r"^(?:True|False)$"),
    )

    allow_auto_train = Option(
        doc="""
        **Syntax:** **allow_auto_train=****
        **Description:** Allows automated ML training if not trained since more than system wide parameter.""",
        require=False,
        default=True,
    )

    def generate(self, **kwargs):
        # performance counter
        start = time.time()

        # Track execution times
        execution_times = []
        average_execution_time = 0

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get Virtual Tenant account
        vtenant_account = trackme_vtenant_account(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )

        # get vtenant component info
        vtenant_component_info = trackme_vtenant_component_info(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )
        logging.debug(
            f'vtenant_component_info="{json.dumps(vtenant_component_info, indent=2)}"'
        )

        # Get the tenant indexes
        tenant_indexes = trackme_idx_for_tenant(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )        

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
                "component": self.component,
                "response": f'tenant_id="{self.tenant_id}", schema upgrade is currently in progress, we will wait until the process is completed before proceeding, the schema upgrade is handled by the health_tracker of the tenant and is completed once the schema_version field of the Virtual Tenants KVstore (trackme_virtual_tenants) matches TrackMe\'s version, schema_version="{schema_version}", schema_version_upgrade_in_progress="{schema_version_upgrade_in_progress}"',
                "schema_version": schema_version,
                "schema_version_upgrade_in_progress": schema_version_upgrade_in_progress,
            }
            logging.info(json.dumps(yield_json, indent=2))
            yield {
                "_time": yield_json["_time"],
                "_raw": yield_json,
            }

        # Default to True (ML Outliers enabled)
        outliers_feature_enabled = True

        # Define the valid components
        valid_components = {"dsm", "dhm", "flx", "fqm", "wlk"}

        # Construct the key dynamically
        key = f"mloutliers_{self.component}"

        # Check if the component is valid and handle exceptions
        if self.component in valid_components:
            try:
                if int(vtenant_account.get(key, 1)) == 0:
                    outliers_feature_enabled = False
            except (ValueError, TypeError):
                outliers_feature_enabled = True

        if not outliers_feature_enabled or schema_version_upgrade_in_progress:

            if not outliers_feature_enabled:
                # yield and log
                results_dict = {
                    "tenant_id": self.tenant_id,
                    "action": "success",
                    "results": "ML Anomaly Detection feature is disabled for the tenant and component, no action taken",
                    "vtenant_account": vtenant_account,
                }
                yield {"_time": time.time(), "_raw": results_dict}

        else:  # process

            # Get app level config
            splk_outliers_time_monitor_mlmodels_default = reqinfo["trackme_conf"][
                "splk_outliers_detection"
            ]["splk_outliers_time_monitor_mlmodels_default"]

            # counter
            count = 0

            # scoring metrics records
            scoring_metrics_records = []            

            # Get the session key
            session_key = self._metadata.searchinfo.session_key

            # Outliers rules storage collection
            collection_rules_name = f"kv_trackme_{self.component}_outliers_entity_rules_tenant_{str(self.tenant_id)}"
            collection_rule = self.service.kvstore[collection_rules_name]

            # Outliers data storage collection
            collection_data_name = f"kv_trackme_{self.component}_outliers_entity_data_tenant_{str(self.tenant_id)}"
            collection_data = self.service.kvstore[collection_data_name]

            # Get data
            kwargs_oneshot = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            #
            # RUN
            #

            # report name for logging purposes
            report_name = f"trackme_{self.component}_outliers_mlmonitor_tracker_tenant_{self.tenant_id}"

            # max runtime
            max_runtime = int(self.max_runtime)

            # Retrieve the search cron schedule
            savedsearch = self.service.saved_searches[report_name]
            savedsearch_cron_schedule = savedsearch.content["cron_schedule"]

            # get the cron_exec_sequence_sec
            try:
                cron_exec_sequence_sec = int(cron_to_seconds(savedsearch_cron_schedule))
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", failed to convert the cron schedule to seconds, error="{str(e)}"'
                )
                cron_exec_sequence_sec = max_runtime

            # the max_runtime cannot be bigger than the cron_exec_sequence_sec
            if max_runtime > cron_exec_sequence_sec:
                max_runtime = cron_exec_sequence_sec

            logging.info(
                f'max_runtime="{max_runtime}",  savedsearch_name="{report_name}", savedsearch_cron_schedule="{savedsearch_cron_schedule}", cron_exec_sequence_sec="{cron_exec_sequence_sec}"'
            )

            # If object_id is provided, resolve it to object value for the macro
            object_for_search = self.object
            if self.object_id != "*" and self.object == "*":
                # Query KVstore to get object value from object_id
                try:
                    query_string_filter = {
                        "object_category": f"splk-{self.component}",
                        "_key": self.object_id,
                    }
                    query_string = {"$and": [query_string_filter]}
                    records_outliers_rules = collection_rule.data.query(
                        query=json.dumps(query_string)
                    )
                    if records_outliers_rules:
                        record_outliers_rules = records_outliers_rules[0]
                        object_for_search = record_outliers_rules.get("object", "*")
                        logging.debug(
                            f'Resolved object_id="{self.object_id}" to object="{object_for_search}"'
                        )
                    else:
                        logging.warning(
                            f'Could not resolve object_id="{self.object_id}" to object value, using "*"'
                        )
                        object_for_search = "*"
                except Exception as e:
                    logging.error(
                        f'Failed to resolve object_id="{self.object_id}" to object value, exception="{str(e)}", using "*"'
                    )
                    object_for_search = "*"

            # Define the search providing the list of entities which models need to be monitored
            if self.force_run == "False":
                search_query = remove_leading_spaces(
                    f"""
                    | `get_splk_outliers_entities("{self.tenant_id}", "{self.component}", "{object_for_search}")`
                    | eval duration_since_last=if(isnum(last_exec_monitor), now()-last_exec_monitor, 0)
                    | where duration_since_last=0 OR duration_since_last>={splk_outliers_time_monitor_mlmodels_default}
                    | sort - duration_since_last
                """
                )

            else:
                search_query = remove_leading_spaces(
                    f"""
                    | `get_splk_outliers_entities("{self.tenant_id}", "{self.component}", "{object_for_search}")`
                    | eval duration_since_last=if(isnum(last_exec_monitor), now()-last_exec_monitor, 0)
                    | sort - duration_since_last
                """
                )

            logging.debug(f'search_query="{search_query}"')

            # run search
            try:
                reader = run_splunk_search(
                    self.service,
                    search_query,
                    kwargs_oneshot,
                    24,
                    5,
                )

                # loop through the results, and train models per entity

                # store processed entities in a list
                processed_entities = []

                # Initialize sum of execution times and count of iterations
                total_execution_time = 0
                iteration_count = 0

                # Other initializations
                max_runtime = int(self.max_runtime)

                for item in reader:
                    logging.debug(f'search_results="{item}"')

                    current_time = time.time()
                    elapsed_time = current_time - start

                    if isinstance(item, dict):

                        # iteration start
                        iteration_start_time = time.time()

                        # run the resulting search
                        object_value = decode_unicode(item.get("object"))
                        model_ids = item.get("model_id")

                        # set the global_isOutlier
                        global_isOutlier = 0
                        global_models_in_anomaly = []
                        global_isOutlierReason = []

                        # Define the KV query
                        query_string_filter = {
                            "object_category": f"splk-{self.component}",
                            "object": object_value,
                        }

                        query_string = {"$and": [query_string_filter]}

                        # Get the current record
                        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only
                        key = None
                        rules_key = None  # Store rules key for logging purposes

                        try:
                            records_outliers_rules = collection_rule.data.query(
                                query=json.dumps(query_string)
                            )
                            record_outliers_rules = records_outliers_rules[0]
                            key = record_outliers_rules.get("_key")
                            rules_key = key  # Store for logging

                        except Exception as e:
                            key = None
                            rules_key = None
                            record_outliers_rules = None

                        # if no records, log a warning message and break
                        if not key:
                            object_ref = self._get_log_object_ref(object_value=self.object)
                            msg = f'tenant_id="{self.tenant_id}", object_category="splk-{self.component}", {object_ref} outliers rules record cannot be found or are not yet available for this entity.'
                            logging.warn(msg)
                            break

                        #
                        # ML confidence
                        #

                        # retrieve the values for confidence and confidence_reason from the rules KVstore
                        ml_confidence = record_outliers_rules.get("confidence", "low")

                        # log debug
                        logging.debug(
                            f'record_outliers_rules="{record_outliers_rules}"'
                        )

                        # Get the JSON outliers rules object
                        entities_outliers = record_outliers_rules.get(
                            "entities_outliers"
                        )

                        # Load as a dict
                        try:
                            entities_outliers = json.loads(
                                record_outliers_rules.get("entities_outliers")
                            )
                        except Exception as e:
                            msg = f'Failed to load entities_outliers with exception="{str(e)}"'

                        # log debug
                        logging.debug(f'entities_outliers="{entities_outliers}"')

                        # Load the general enablement
                        try:
                            outliers_is_disabled = int(
                                record_outliers_rules.get("is_disabled")
                            )
                            logging.debug(f'is_disabled="{outliers_is_disabled}"')

                        except Exception as e:
                            msg = 'Failed to extract one or more expected settings from the entity, is this record corrupted? Exception="{}"'
                            logging.error(msg)
                            outliers_is_disabled = 1

                        # process the entity if general outliers is enabled
                        if outliers_is_disabled == 0:
                            # Process all ML models per entity
                            processed_entity_models = {}

                            if model_ids:
                                model_ids = model_ids.split(",")

                                # loop through each model per entity
                                for model_id in model_ids:
                                    # model configuration
                                    try:
                                        model_config = entities_outliers[model_id]
                                    except Exception as e:
                                        model_config = None

                                    if model_config:

                                        logging.debug(
                                            f'configuration for model_id="{model_id}" config="{json.dumps(model_config, indent=4)}"'
                                        )

                                        # If the model is enabled
                                        if int(model_config["is_disabled"]) == 0:
                                            # Get conf from the model
                                            alert_lower_breached = int(
                                                model_config["alert_lower_breached"]
                                            )
                                            alert_upper_breached = int(
                                                model_config["alert_upper_breached"]
                                            )

                                            # get the kpi metric name and value
                                            kpi_metric_name = model_config["kpi_metric"]
                                            logging.debug(
                                                f'kpi_metric_name="{kpi_metric_name}"'
                                            )

                                            # retrieve the score from the model configuration
                                            try:
                                                score = int(model_config.get("score", 36))
                                            except (ValueError, TypeError):
                                                score = 36

                                            # Set the initial state for that model
                                            isOutlier = 0
                                            isOutlierReason = "None"

                                            # Set the search - use object_id if available, otherwise fall back to object
                                            if key:
                                                object_param = f'object_id="{key}"'
                                            else:
                                                object_param = f'object="{object_value}"'
                                            
                                            model_render_search = remove_leading_spaces(
                                                f"""\
                                                | trackmesplkoutliersrender tenant_id="{self.tenant_id}" component="{self.component}" {object_param} earliest="-24h" latest="now" model_id="{model_id}" allow_auto_train="{self.allow_auto_train}"
                                                | table _time, *, LowerBound, UpperBound
                                                | sort 0 - _time | head 1
                                                """
                                            )
                                            logging.info(
                                                f'tenant_id="{self.tenant_id}", {self._get_log_object_ref(object_value=object_value, object_id_value=rules_key)}, model_id="{model_id}", Executing resulting search="{model_render_search}"'
                                            )

                                            # set kwargs
                                            kwargs_oneshot = {
                                                "earliest_time": "-24h",
                                                "latest_time": "now",
                                                "search_mode": "normal",
                                                "preview": False,
                                                "count": 0,
                                                "output_mode": "json",
                                            }

                                            # Performance timer
                                            substart = time.time()

                                            # Run the search
                                            search_results = None
                                            try:
                                                reader = run_splunk_search(
                                                    self.service,
                                                    model_render_search,
                                                    kwargs_oneshot,
                                                    24,
                                                    5,
                                                )

                                                # loop through the reader results
                                                for item in reader:
                                                    if isinstance(item, dict):
                                                        search_results = item

                                                        # raw results logged only in debug
                                                        logging.debug(
                                                            f'search_results="{search_results}"'
                                                        )

                                                        # Inspect results
                                                        time_outlier = search_results[
                                                            "_time"
                                                        ]

                                                        # get rejectedLowerboundOutlier / rejectedUpperboundOutlier / rejectedLowerboundOutlierReason / rejectedUpperboundOutlierReason
                                                        try:
                                                            rejectedLowerboundOutlier = int(
                                                                (
                                                                    search_results[
                                                                        "rejectedLowerboundOutlier"
                                                                    ]
                                                                )
                                                            )
                                                        except Exception as e:
                                                            rejectedLowerboundOutlier = (
                                                                0
                                                            )

                                                        try:
                                                            rejectedUpperboundOutlier = int(
                                                                (
                                                                    search_results[
                                                                        "rejectedUpperboundOutlier"
                                                                    ]
                                                                )
                                                            )
                                                        except Exception as e:
                                                            rejectedUpperboundOutlier = (
                                                                0
                                                            )

                                                        try:
                                                            rejectedLowerboundOutlierReason = search_results[
                                                                "rejectedLowerboundOutlierReason"
                                                            ]
                                                        except Exception as e:
                                                            rejectedLowerboundOutlierReason = (
                                                                "N/A"
                                                            )

                                                        try:
                                                            rejectedUpperboundOutlierReason = search_results[
                                                                "rejectedUpperboundOutlierReason"
                                                            ]
                                                        except Exception as e:
                                                            rejectedUpperboundOutlierReason = (
                                                                "N/A"
                                                            )

                                                        # try to get the LowerBound and UpperBound
                                                        try:
                                                            LowerBound = search_results[
                                                                "LowerBound"
                                                            ]
                                                        except Exception as e:
                                                            LowerBound = None
                                                            logging.warning(
                                                                f'Could not retrieve a LowerBound value from item="{item}"'
                                                            )

                                                        try:
                                                            UpperBound = search_results[
                                                                "UpperBound"
                                                            ]
                                                        except Exception as e:
                                                            UpperBound = None
                                                            logging.warning(
                                                                f'Could not retrieve a UpperBound value from item="{item}"'
                                                            )

                                                        try:
                                                            kpi_metric_value = (
                                                                search_results[
                                                                    kpi_metric_name
                                                                ]
                                                            )
                                                            logging.debug(
                                                                f'kpi_metric_value="{kpi_metric_value}"'
                                                            )
                                                        except Exception as e:
                                                            kpi_metric_value = None
                                                            logging.warning(
                                                                f'Could not retrieve the kpi_metric_value from item="{item}"'
                                                            )

                                                        # Define the outliers status
                                                        if (
                                                            kpi_metric_value
                                                            and LowerBound
                                                            and UpperBound
                                                        ):
                                                            if int(
                                                                alert_lower_breached
                                                            ) == 1 and float(
                                                                kpi_metric_value
                                                            ) < float(
                                                                LowerBound
                                                            ):

                                                                # Enforce policy for rejected lowerBound outliers
                                                                if (
                                                                    rejectedLowerboundOutlier
                                                                    == 1
                                                                ):
                                                                    isOutlier = 0
                                                                    isOutlierReason = f'Outliers ML for kpi="{kpi_metric_name}", model_id="{model_id}", LowerBound="{round(float(LowerBound), 3)}" has been rejected, rejectedLowerboundOutlierReason="{rejectedLowerboundOutlierReason}", kpi_metric_value="{round(float(kpi_metric_value), 3)}" at time="{time_outlier}", Outlier will not be considered.'

                                                                # Accept Outlier
                                                                else:
                                                                    isOutlier = 1
                                                                    pct_decrease = (
                                                                        (
                                                                            float(
                                                                                LowerBound
                                                                            )
                                                                            - float(
                                                                                kpi_metric_value
                                                                            )
                                                                        )
                                                                        / float(
                                                                            LowerBound
                                                                        )
                                                                    ) * 100
                                                                    isOutlierReason = f'Outliers ML for kpi="{kpi_metric_name}", model_id="{model_id}", LowerBound="{round(float(LowerBound), 3)}" breached with kpi_metric_value="{round(float(kpi_metric_value), 3)}" at time="{time_outlier}", pct_decrease="{round(float(pct_decrease), 2)}"'

                                                                    # add to scoring metrics records only if the ML confidence allows it
                                                                    if ml_confidence != "low":
                                                                        scoring_metrics_records.append(
                                                                            {
                                                                                "tenant_id": self.tenant_id,
                                                                                "object_id": key,
                                                                                "object": object_value,
                                                                                "object_category": self.component,
                                                                                "score_source": f"lowerbound_outlier|model_id={model_id}",
                                                                                "metrics_event": {"score": score, "pct_decrease": round(float(pct_decrease), 2)},
                                                                            }
                                                                        )

                                                            elif int(
                                                                alert_upper_breached
                                                            ) == 1 and float(
                                                                kpi_metric_value
                                                            ) > float(
                                                                UpperBound
                                                            ):

                                                                # Enforce policy for rejected upperBound outliers
                                                                if (
                                                                    rejectedUpperboundOutlier
                                                                    == 1
                                                                ):
                                                                    isOutlier = 0
                                                                    isOutlierReason = f'Outliers ML for kpi="{kpi_metric_name}", model_id="{model_id}", UpperBound="{round(float(UpperBound), 3)}" has been rejected, rejectedUpperboundOutlierReason="{rejectedUpperboundOutlierReason}", kpi_metric_value="{round(float(kpi_metric_value), 3)}" at time="{time_outlier}", Outlier will not be considered.'

                                                                # Accept Outlier
                                                                else:
                                                                    isOutlier = 1
                                                                    pct_increase = (
                                                                        (
                                                                            float(
                                                                                kpi_metric_value
                                                                            )
                                                                            - float(
                                                                                UpperBound
                                                                            )
                                                                        )
                                                                        / float(
                                                                            UpperBound
                                                                        )
                                                                    ) * 100
                                                                    isOutlierReason = f'Outliers ML for kpi="{kpi_metric_name}", model_id="{model_id}", UpperBound="{round(float(UpperBound), 3)}" breached with kpi_metric_value="{round(float(kpi_metric_value), 3)}" at time="{time_outlier}", pct_increase="{round(float(pct_increase), 2)}"'

                                                                    # add to scoring metrics records only if the ML confidence allows it
                                                                    if ml_confidence != "low":
                                                                        scoring_metrics_records.append(
                                                                            {
                                                                                "tenant_id": self.tenant_id,
                                                                                "object_id": key,
                                                                                "object": object_value,
                                                                                "object_category": self.component,
                                                                                "score_source": f"upperbound_outlier|model_id={model_id}",
                                                                                "metrics_event": {"score": score, "pct_increase": round(float(pct_increase), 2)},
                                                                            }
                                                                        )

                                                            else:
                                                                isOutlier = 0
                                                                isOutlierReason = "No outliers anomalies were detected"

                                                            # impact the global_isOutlier accordingly
                                                            if isOutlier == 1:
                                                                # only if the confidence allows it
                                                                if (
                                                                    ml_confidence
                                                                    != "low"
                                                                ):
                                                                    global_isOutlier = 1
                                                                    global_models_in_anomaly.append(
                                                                        model_id
                                                                    )
                                                                    global_isOutlierReason.append(
                                                                        isOutlierReason
                                                                    )

                                            except Exception as e:
                                                error_msg = f'tenant_id="{self.tenant_id}", object_category="{self.component}", {self._get_log_object_ref(object_value=object_value, object_id_value=rules_key)}, model_id="{model_id}", search has failed with the following exception="{str(e)}", search="{model_render_search}"'
                                                logging.error(error_msg)

                                            # Performance timer
                                            model_search_runtime = round(
                                                float(time.time()) - float(substart), 3
                                            )

                                            # try loading search results and define a message if did not produce any results
                                            try:
                                                summary_search_results = {
                                                    "time": search_results["_time"],
                                                    "_raw": json.loads(
                                                        search_results["_raw"]
                                                    ),
                                                    "model_render_search": model_render_search,
                                                }
                                            except Exception as e:
                                                summary_search_results = "Outliers search did not produce any results"

                                            # Insert the summary record
                                            model_summary = {
                                                "isOutlier": isOutlier,
                                                "isOutlierReason": isOutlierReason,
                                                "alert_lower_breached": alert_lower_breached,
                                                "alert_upper_breached": alert_upper_breached,
                                                "summary_search_results": summary_search_results,
                                                "search_run_time": model_search_runtime,
                                                "time_exec": time.time(),
                                                "time_human": time.strftime(
                                                    "%c", time.localtime(time.time())
                                                ),
                                            }
                                            processed_entity_models[model_id] = (
                                                model_summary
                                            )

                                            # log info
                                            logging.info(
                                                f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref(object_value=object_value, object_id_value=rules_key)}, model_summary="{json.dumps(model_summary, indent=4)}"'
                                            )

                                # summary record for that entity
                                processed_entity_record = {
                                    "entity": object_value,
                                    "processed_model_ids": processed_entity_models,
                                }

                                # append
                                processed_entities.append(processed_entity_record)

                                # increment the entity counter
                                count += 1

                                #
                                # Finally, update the outliers data KVstore
                                #

                                # Define the KV query
                                query_string_filter = {
                                    "object_category": f"splk-{self.component}",
                                    "object": object_value,
                                }

                                query_string = {"$and": [query_string_filter]}

                                # Get the current record
                                # Notes: the record is returned as an array, as we search for a specific record, we expect one record only
                                key = None
                                record_outliers_data = None

                                try:
                                    records_outliers_data = collection_data.data.query(
                                        query=json.dumps(query_string)
                                    )
                                    record_outliers_data = records_outliers_data[0]
                                    key = record_outliers_data.get("_key")

                                except Exception as e:
                                    key = None

                                # Asymmetric write for the lastIsOutlierReason* cache fields:
                                # - On a cycle where this entity has at least one active outlier model
                                #   (global_isOutlier == 1 with a non-empty global_isOutlierReason list),
                                #   refresh the cache to mirror the current snapshot.
                                # - On a cleared cycle (no current outlier), preserve the existing cache
                                #   values from the prior write so the decision maker can still surface
                                #   the breach details while score_outliers (24h cumulative) remains > 0.
                                # See trackme_libs_decisionmaker.build_outlier_reason_status_message
                                # for the consumer side.
                                if global_isOutlier == 1 and global_isOutlierReason:
                                    last_outlier_reason = global_isOutlierReason
                                    last_outlier_models = global_models_in_anomaly
                                    last_outlier_mtime = str(time.time())
                                elif record_outliers_data is not None:
                                    last_outlier_reason = record_outliers_data.get(
                                        "lastIsOutlierReason", ""
                                    )
                                    last_outlier_models = record_outliers_data.get(
                                        "lastIsOutlierReason_models", ""
                                    )
                                    last_outlier_mtime = record_outliers_data.get(
                                        "lastIsOutlierReason_mtime", ""
                                    )
                                else:
                                    last_outlier_reason = ""
                                    last_outlier_models = ""
                                    last_outlier_mtime = ""

                                if not key:
                                    # new record
                                    try:
                                        collection_data.data.insert(
                                            json.dumps(
                                                {
                                                    "_key": hashlib.sha256(
                                                        object_value.encode("utf-8")
                                                    ).hexdigest(),
                                                    "object": str(object_value),
                                                    "object_category": f"splk-{self.component}",
                                                    "mtime": str(time.time()),
                                                    "isOutlier": global_isOutlier,
                                                    "isOutlierReason": global_isOutlierReason,
                                                    "models_in_anomaly": global_models_in_anomaly,
                                                    "models_summary": json.dumps(
                                                        processed_entity_models,
                                                        indent=4,
                                                    ),
                                                    "lastIsOutlierReason": last_outlier_reason,
                                                    "lastIsOutlierReason_models": last_outlier_models,
                                                    "lastIsOutlierReason_mtime": last_outlier_mtime,
                                                }
                                            )
                                        )

                                    except Exception as e:
                                        logging.error(
                                            f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref(object_value=object_value, object_id_value=rules_key)}, failed to insert a new KVstore record with exception="{str(e)}"'
                                        )

                                else:
                                    try:
                                        # update existing record
                                        collection_data.data.update(
                                            str(key),
                                            json.dumps(
                                                {
                                                    "object": str(object_value),
                                                    "object_category": f"splk-{self.component}",
                                                    "mtime": str(time.time()),
                                                    "isOutlier": global_isOutlier,
                                                    "isOutlierReason": global_isOutlierReason,
                                                    "models_in_anomaly": global_models_in_anomaly,
                                                    "models_summary": json.dumps(
                                                        processed_entity_models,
                                                        indent=4,
                                                    ),
                                                    "lastIsOutlierReason": last_outlier_reason,
                                                    "lastIsOutlierReason_models": last_outlier_models,
                                                    "lastIsOutlierReason_mtime": last_outlier_mtime,
                                                }
                                            ),
                                        )

                                    except Exception as e:
                                        logging.error(
                                            f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref(object_value=object_value, object_id_value=rules_key)}, failed to update a KVstore record with exception="{str(e)}"'
                                        )

                        # Calculate the execution time for this iteration
                        iteration_end_time = time.time()
                        execution_time = iteration_end_time - iteration_start_time

                        # Update total execution time and iteration count
                        total_execution_time += execution_time
                        iteration_count += 1

                        # Calculate average execution time
                        if iteration_count > 0:
                            average_execution_time = (
                                total_execution_time / iteration_count
                            )
                        else:
                            average_execution_time = 0

                        # Check if there is enough time left to continue
                        current_time = time.time()
                        elapsed_time = current_time - start
                        if elapsed_time + average_execution_time + 120 >= max_runtime:
                            logging.info(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", max_runtime="{max_runtime}" is about to be reached, current_runtime="{elapsed_time}", job will be terminated now'
                            )
                            break

                # end
                if int(count) > 0:
                    logging.info(
                        f'tenant_id="{self.tenant_id}" outliers tracker job successfully executed, status="success", run_time="{round(time.time() - start, 3)}", report="{str(report_name)}", entities_count="{str(count)}"'
                    )
                    # yield
                    results_dict = {
                        "tenant_id": self.tenant_id,
                        "action": "success",
                        "results": "outliers tracker job successfully executed",
                        "run_time": round((time.time() - start), 3),
                        "entities_count": str(count),
                        "processed_entities": processed_entities,
                        "upstream_search_query": search_query,
                    }
                    yield {"_time": time.time(), "_raw": results_dict}

                    # handler event
                    handler_events_records = []
                    for object_record in processed_entities:
                        handler_events_records.append(
                            {
                                "object": object_record.get("entity"),
                                "object_id": hashlib.sha256(
                                    object_record.get("entity").encode("utf-8")
                                ).hexdigest(),
                                "object_category": f"splk-{self.component}",
                                "handler": f"trackme_{self.component}_outliers_mlmonitor_tracker_tenant_{self.tenant_id}",
                                "handler_message": "Entity was rendered for ML Outliers.",
                                "handler_troubleshoot_search": f"index=_internal sourcetype=trackme:custom_commands:trackmesplkoutliersrender tenant_id={self.tenant_id} object=\"{object_record.get('entity')}\"",
                                "handler_time": time.time(),
                            }
                        )

                    # notification event
                    try:
                        trackme_handler_events(
                            session_key=self._metadata.searchinfo.session_key,
                            splunkd_uri=self._metadata.searchinfo.splunkd_uri,
                            tenant_id=self.tenant_id,
                            sourcetype="trackme:handler",
                            source=f"trackme:handler:{self.tenant_id}",
                            handler_events=handler_events_records,
                        )
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", could not send notification event, exception="{e}"'
                        )

                    # call the scoring gen metrics function
                    scoring_metrics_gen_start = time.time()
                    try:
                        scoring_metrics = trackme_scoring_gen_metrics(
                            self.tenant_id,
                            tenant_indexes.get("trackme_metric_idx"),
                            scoring_metrics_records,
                        )
                        logging.info(
                            f'context="scoring_gen_metrics", tenant_id="{self.tenant_id}", function trackme_scoring_gen_metrics success {scoring_metrics}, run_time={round(time.time()-scoring_metrics_gen_start, 3)}, no_entities={len(scoring_metrics_records)}'
                        )
                    except Exception as e:
                        logging.error(
                            f'context="scoring_gen_metrics", tenant_id="{self.tenant_id}", function trackme_scoring_gen_metrics failed with exception {str(e)}'
                        )

                    # also generate events for the score
                    for score_event in scoring_metrics_records:
                        try:
                            trackme_gen_state(
                                index=tenant_indexes.get("trackme_summary_idx"),
                                sourcetype="trackme:score",
                                source=f"trackme_{self.component}_outliers_mlmonitor_tracker_tenant_{self.tenant_id}",
                                event=score_event,
                            )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", failed to generate score state event, exception="{str(e)}"'
                            )

                else:
                    logging.info(
                        f'tenant_id="{self.tenant_id}" outliers tracker job successfully executed but there were no entities to be tracked at this time, status="success", run_time="{round(time.time() - start, 3)}", report="{str(report_name)}", entities_count="{str(count)}"'
                    )
                    # yield
                    results_dict = {
                        "tenant_id": self.tenant_id,
                        "action": "success",
                        "results": "outliers tracker job successfully executed but there were no entities to be tracked at this time",
                        "run_time": round((time.time() - start), 3),
                        "entities_count": str(count),
                        "upstream_search_query": search_query,
                    }
                    yield {"_time": time.time(), "_raw": results_dict}

                # Call the component register
                trackme_register_tenant_object_summary(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    f"splk-{self.component}",
                    f"trackme_{self.component}_outliers_mlmonitor_tracker_tenant_{str(self.tenant_id)}",
                    "success",
                    time.time(),
                    round(time.time() - start, 3),
                    "The report was executed successfully",
                    "-24h",
                    "now",
                )

                # Refresh tenant component summary cache (drives the
                # Single Value cards on Tenant Home). The outliers
                # tracker writes score events that the decision maker
                # consumes via the score cache, so the recount picks
                # up the new state. Called synchronously because
                # Splunk's dispatch() terminates the process after the
                # generator yields, killing daemon threads. Wrapped in
                # try/except so a refresh failure doesn't fail the
                # tracker cycle (audit + scoring already succeeded).
                try:
                    trackme_register_tenant_component_summary(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        self.component,
                    )
                except Exception as ex:
                    logging.warning(
                        f'task="refresh_component_summary_after_outliers_tracker" failed, '
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'exception="{str(ex)}"'
                    )

            except Exception as e:
                trackme_register_tenant_object_summary(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    f"splk-{self.component}",
                    f"trackme_{self.component}_outliers_mlmonitor_tracker_tenant_{str(self.tenant_id)}",
                    "failure",
                    time.time(),
                    round(time.time() - start, 3),
                    str(e),
                    "-24h",
                    "now",
                )
                msg = f'tenant_id="{self.tenant_id}", permanent search failure, exception="{str(e)}", search_query="{search_query}", search_kwargs="{kwargs_oneshot}"'
                logging.error(msg)
                raise Exception(msg)


dispatch(SplkOutliersTracker, sys.argv, sys.stdin, sys.stdout, __name__)

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
    "%s/var/log/splunk/trackme_splk_outliers_train_helper.log" % splunkhome,
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
    trackme_idx_for_tenant,
    trackme_register_tenant_object_summary,
    run_splunk_search,
    trackme_handler_events,
)

# import trackme libs croniter
from trackme_libs_croniter import cron_to_seconds

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import the outliers eligibility helper (tenant-level priority + filter expression)
from trackme_libs_mloutliers import is_outliers_eligible_for_entity


@Configuration(distributed=False)
class SplkOutliersExecutor(GeneratingCommand):
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

    max_runtime_sec = Option(
        doc="""
        **Syntax:** **max_runtime_sec=****
        **Description:** The max runtime for the job in seconds, defaults to 60 minutes less 120 seconds of margin.""",
        require=False,
        default="3600",
        validate=validators.Match("max_runtime_sec", r"^\d*$"),
    )

    def generate(self, **kwargs):
        # performance counter
        start = time.time()

        # Track execution times
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

        # get mloutliers, if set 0 then ML Outliers is disabled for the tenant, 1 we can proceed

        # Default to True (ML Outliers enabled)
        outliers_feature_enabled = True

        # Define the valid components
        valid_components = {"dsm", "dhm", "flx", "fqm", "wlk"}

        # Construct the key dynamically
        key = f"mloutliers_{self.component}"

        # Check if the component is valid and handle exceptions
        if self.component in valid_components:
            try:
                logging.debug(
                    f'checking if the key "{key}" exists in the vtenant_account'
                )

                outliers_enablement = int(vtenant_account.get(key, 1))
                logging.debug(
                    f'vtenant_account="{json.dumps(vtenant_account, indent=2)}", component="{self.component}", key="{key}", outliers_enablement="{outliers_enablement}"'
                )

                if outliers_enablement == 0:
                    outliers_feature_enabled = False
                    logging.debug(
                        f'the key "{key}" exists in the vtenant_account and is set to 0, ML Outliers is disabled for the tenant'
                    )
            except (ValueError, TypeError):
                outliers_feature_enabled = True

        else:
            logging.error(
                f'component="{self.component}" is not valid, valid components are {valid_components}'
            )

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

            # max runtime
            max_runtime = int(self.max_runtime_sec)

            # Retrieve the search cron schedule
            savedsearch_name = f"trackme_{self.component}_outliers_mltrain_tracker_tenant_{self.tenant_id}"
            savedsearch = self.service.saved_searches[savedsearch_name]
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
                f'max_runtime="{max_runtime}",  savedsearch_name="{savedsearch_name}", savedsearch_cron_schedule="{savedsearch_cron_schedule}", cron_exec_sequence_sec="{cron_exec_sequence_sec}"'
            )

            # Get app level config
            splk_outliers_time_train_mlmodels_default = reqinfo["trackme_conf"][
                "splk_outliers_detection"
            ]["splk_outliers_time_train_mlmodels_default"]
            splk_outliers_max_runtime_train_mlmodels_default = reqinfo["trackme_conf"][
                "splk_outliers_detection"
            ]["splk_outliers_max_runtime_train_mlmodels_default"]

            # Get cooldown settings for outlier score events
            try:
                splk_outliers_train_cooldown_after_score_events = int(
                    reqinfo["trackme_conf"]["splk_outliers_detection"].get(
                        "splk_outliers_train_cooldown_after_score_events", 172800
                    )
                )
            except (ValueError, TypeError):
                splk_outliers_train_cooldown_after_score_events = 172800

            try:
                splk_outliers_train_max_delay_since_last_train = int(
                    reqinfo["trackme_conf"]["splk_outliers_detection"].get(
                        "splk_outliers_train_max_delay_since_last_train", 1209600
                    )
                )
            except (ValueError, TypeError):
                splk_outliers_train_max_delay_since_last_train = 1209600

            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                f'splk_outliers_train_cooldown_after_score_events="{splk_outliers_train_cooldown_after_score_events}", '
                f'splk_outliers_train_max_delay_since_last_train="{splk_outliers_train_max_delay_since_last_train}"'
            )

            # Get the session key
            session_key = self._metadata.searchinfo.session_key

            # Get data
            kwargs_oneshot = {
                "earliest_time": self.earliest,
                "latest_time": self.latest,
                "output_mode": "json",
                "count": 0,
            }

            #
            # Build cooldown filter for the SPL query
            # If enabled, a join is added to check for recent outlier score events
            # and exclude entities in cooldown (unless the hard cap is exceeded)
            #

            cooldown_join = ""
            if splk_outliers_train_cooldown_after_score_events > 0:
                try:
                    tenant_indexes = trackme_idx_for_tenant(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                    )
                    tenant_summary_idx = tenant_indexes.get(
                        "trackme_summary_idx", "trackme_summary"
                    )
                    cooldown_join = remove_leading_spaces(
                        f"""\
                        | join type=left object [
                            search index="{tenant_summary_idx}" sourcetype="trackme:score"
                                source="trackme_{self.component}_outliers_mlmonitor_tracker_tenant_{self.tenant_id}"
                                earliest=-{splk_outliers_train_cooldown_after_score_events}s latest=now
                            | search score_source="*lowerbound_outlier*" OR score_source="*upperbound_outlier*"
                            | stats max(_time) as last_outlier_score_time by object
                        ]
                        | eval has_recent_outlier=if(isnotnull(last_outlier_score_time), 1, 0)
                        | eval force_train=if(duration_since_last>={splk_outliers_train_max_delay_since_last_train} OR duration_since_last=0, 1, 0)
                        | where has_recent_outlier=0 OR force_train=1
                        """
                    )
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'cooldown filter enabled: cooldown={splk_outliers_train_cooldown_after_score_events}s, '
                        f'max_delay={splk_outliers_train_max_delay_since_last_train}s, '
                        f'tenant_summary_idx="{tenant_summary_idx}"'
                    )
                except Exception as e:
                    logging.warning(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'failed to build cooldown filter, proceeding without it: exception="{str(e)}"'
                    )
                    cooldown_join = ""

            #
            # RUN
            #

            # Define the search providing the list of entities which models need to be trained

            # note: do not allow crap entities, sometimes users get very fancy, entities with double quotes in the value
            # are not expected nor desirable, do not allow crap to get in

            # Note: the lookup OUTPUT list pulls the entity attributes the tenant-level
            # ML Outliers eligibility filter (priority + filter expression DSL,
            # introduced in 2.3.22) needs to evaluate per entity. Missing fields
            # on a given component (e.g. data_index/data_sourcetype on wlk) are
            # treated as empty by the filter engine and fail closed — same
            # semantics as Virtual Groups.
            if self.component in ("dsm", "dhm", "flx", "fqm"):
                search_query = remove_leading_spaces(
                    f"""\
                        | inputlookup trackme_{self.component}_outliers_entity_rules_tenant_{self.tenant_id} where object_category="splk-{self.component}"
                        | `trackme_exclude_badentities`
                        | lookup local=t trackme_{self.component}_tenant_{self.tenant_id} object OUTPUT monitored_state, priority, tags, labels, data_index, data_sourcetype
                        | where monitored_state="enabled"
                        | eval duration_since_last=if(last_exec!="pending", now()-last_exec, 0)
                        | where duration_since_last=0 OR duration_since_last>={splk_outliers_time_train_mlmodels_default}
                        {cooldown_join}
                        | sort - duration_since_last
                    """
                )

            elif self.component in ("wlk"):
                search_query = remove_leading_spaces(
                    f"""\
                        | inputlookup trackme_{self.component}_outliers_entity_rules_tenant_{self.tenant_id} where object_category="splk-{self.component}"
                        | `trackme_exclude_badentities`
                        | lookup local=t trackme_{self.component}_tenant_{self.tenant_id} object OUTPUT app, monitored_state, priority, tags, labels
                        | lookup local=t trackme_{self.component}_apps_enablement_tenant_{self.tenant_id} app OUTPUT enabled as app_enabled
                        | where monitored_state="enabled" AND app_enabled="True"
                        | eval duration_since_last=if(last_exec!="pending", now()-last_exec, 0)
                        | where duration_since_last=0 OR duration_since_last>={splk_outliers_time_train_mlmodels_default}
                        {cooldown_join}
                        | sort - duration_since_last
                    """
                )

            logging.debug(
                f'tenant_id="{self.tenant_id}", component="{self.component}", retrieving the list of entities to be trained from the upstream search="{search_query}"'
            )

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

                # Store various key information
                processed_entities = []
                failures_entities = []
                failures_entities_object_list = []
                searches_toprocess = []
                # Counters for entities skipped by the tenant-level ML Outliers
                # eligibility filter (priority filter + filter expression DSL).
                skipped_priority_filter = 0
                skipped_filter_expression = 0
                skipped_filter_expression_invalid = 0

                for item in reader:
                    logging.debug(f'search_results="{item}"')

                    current_time = time.time()
                    elapsed_time = current_time - start

                    if isinstance(item, dict):
                        # break if reaching the max run time less 30 seconds of margin
                        if (time.time() - int(start)) - 30 >= int(
                            splk_outliers_max_runtime_train_mlmodels_default
                        ):
                            logging.info(
                                f'tenant_id="{self.tenant_id}" max_runtime="{splk_outliers_max_runtime_train_mlmodels_default}" for ML models was reached with current_runtime="{start}", job will be terminated now'
                            )
                            break

                        # Tenant-level ML Outliers eligibility gate (2.3.22):
                        # skip entities whose priority is excluded by the
                        # tenant's priority filter, or that do not match the
                        # tenant's filter expression. Read-time fallbacks in
                        # is_outliers_eligible_for_entity preserve pre-2.3.22
                        # behaviour (all priorities, no filter) when a tenant
                        # row is missing the new keys.
                        eligible, reason = is_outliers_eligible_for_entity(
                            vtenant_account, item
                        )
                        if not eligible:
                            if reason == "priority_filter":
                                skipped_priority_filter += 1
                            elif reason == "filter_expression":
                                skipped_filter_expression += 1
                            elif reason == "filter_expression_invalid":
                                skipped_filter_expression_invalid += 1
                            logging.debug(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                                f'object="{item.get("object")}", priority="{item.get("priority")}", '
                                f'skipped from ML Outliers training by tenant filter, reason="{reason}"'
                            )
                            continue

                        # set the search depending on the component
                        search_train = f'| trackmesplkoutlierstrain tenant_id="{self.tenant_id}" component="{self.component}" object="{item.get("object")}"'

                        # append to our list
                        searches_toprocess.append(
                            {
                                "object_category": item.get("object_category"),
                                "object": item.get("object"),
                                "search": search_train,
                            }
                        )

                        logging.debug(
                            f'entity_dict="{json.dumps({"object_category": item.get("object_category"), "object": item.get("object"), "search": search_train}, indent=2)}"'
                        )

                # Emit a summary log line whenever any entity was skipped, so
                # operators can quickly correlate "fewer trainings than expected"
                # with tenant filter scope.
                if (
                    skipped_priority_filter
                    or skipped_filter_expression
                    or skipped_filter_expression_invalid
                ):
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'ML Outliers tenant filter skipped entities: '
                        f'priority_filter={skipped_priority_filter}, '
                        f'filter_expression={skipped_filter_expression}, '
                        f'filter_expression_invalid={skipped_filter_expression_invalid}'
                    )

            except Exception as e:
                msg = f'tenant_id="{self.tenant_id}", main search failed with exception="{str(e)}"'
                logging.error(msg)
                raise Exception(msg)

            #
            # Process
            #

            logging.debug(
                f'searched to be processed="{json.dumps(searches_toprocess, indent=2)}"'
            )

            # errors counter
            search_errors_count = 0

            # Initialize sum of execution times and count of iterations
            total_execution_time = 0
            iteration_count = 0

            # Other initializations
            max_runtime = int(self.max_runtime_sec) - 120

            # run
            if len(searches_toprocess) > 0:
                #
                # process searches
                #

                for search_record in searches_toprocess:
                    search = search_record.get("search")
                    object_category = search_record.get("object_category")
                    object_value = search_record.get("object")
                    results_entity = []

                    # iteration start
                    iteration_start_time = time.time()

                    logging.debug(
                        f'tenant_id="{self.tenant_id}" Executing resulting search="{search}"'
                    )

                    # run search
                    substart = time.time()
                    try:
                        reader = run_splunk_search(
                            self.service,
                            search,
                            kwargs_oneshot,
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                logging.debug(f'search_results="{item}"')
                                results_entity.append(item)

                        # don't be too noisy
                        if reqinfo["logging_level"] == "DEBUG":
                            processed_entities.append(
                                {
                                    "object_category": object_category,
                                    "object": object_value,
                                    "results_entity": results_entity,
                                    "search": search,
                                    "runtime": str(time.time() - substart),
                                }
                            )
                        else:
                            processed_entities.append(
                                {
                                    "object_category": object_category,
                                    "object": object_value,
                                    "search": search,
                                    "runtime": str(time.time() - substart),
                                }
                            )

                        # only in debug
                        logging.debug(
                            f'tenant_id="{self.tenant_id}" search successfully executed in {time.time() - substart} seconds'
                        )

                    except Exception as e:
                        msg = f'tenant_id="{self.tenant_id}", component="{self.component}", search="{search}", main search failed with exception="{str(e)}"'
                        logging.error(msg)
                        search_errors_count += 1
                        failures_entities.append(
                            {
                                "object_category": object_category,
                                "object": object_value,
                                "results_entity": {
                                    "action": "failure",
                                    "search": search,
                                    "exception": str(e),
                                },
                            }
                        )
                        failures_entities_object_list.append(
                            {"object": object_value, "exception": str(e)}
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
                    current_time = time.time()
                    elapsed_time = current_time - start
                    if elapsed_time + average_execution_time + 120 >= max_runtime:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", max_runtime="{max_runtime}" is about to be reached, current_runtime="{elapsed_time}", job will be terminated now'
                        )
                        break

                #
                # end process searches loop
                #

                # yield and log
                results_dict = {
                    "tenant_id": self.tenant_id,
                    "action": "success",
                    "results": "outliers models training job successfully executed",
                    "run_time": round((time.time() - start), 3),
                    "entities_count": len(searches_toprocess),
                    "processed_entities": processed_entities,
                    "failures_entities": failures_entities,
                    "search_errors_count": search_errors_count,
                    "upstream_search_query": search_query,
                }
                yield {"_time": time.time(), "_raw": results_dict}
                logging.info(json.dumps(results_dict, indent=2))

                # handler event
                handler_events_records = []
                for object_record in processed_entities:
                    handler_events_records.append(
                        {
                            "object": object_record.get("object"),
                            "object_id": hashlib.sha256(
                                object_record.get("object").encode("utf-8")
                            ).hexdigest(),
                            "object_category": f"splk-{self.component}",
                            "handler": f"trackme_{self.component}_outliers_mltrain_tracker_tenant_{self.tenant_id}",
                            "handler_message": "Entity was trained for ML Outliers.",
                            "handler_troubleshoot_search": f"index=_internal (sourcetype=trackme:custom_commands:trackmesplkoutlierstrain) tenant_id={self.tenant_id} object=\"{object_record.get('object')}\"",
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

            else:
                # yield and log
                results_dict = {
                    "tenant_id": self.tenant_id,
                    "action": "success",
                    "results": "outliers models training job successfully executed but there were no entities to be trained at this time",
                    "run_time": round((time.time() - start), 3),
                    "entities_count": len(searches_toprocess),
                    "upstream_search_query": search_query,
                }
                yield {"_time": time.time(), "_raw": results_dict}
                logging.info(json.dumps(results_dict, indent=2))

            # Call the component register
            report_name = f"trackme_{self.component}_outliers_mltrain_tracker_tenant_{self.tenant_id}"
            if search_errors_count == 0:
                trackme_register_tenant_object_summary(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    f"splk-{self.component}",
                    report_name,
                    "success",
                    time.time(),
                    round(time.time() - start, 3),
                    "The report was executed successfully",
                    "-24h",
                    "now",
                )

            else:
                trackme_register_tenant_object_summary(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    f"splk-{self.component}",
                    report_name,
                    "failure",
                    time.time(),
                    round(time.time() - start, 3),
                    failures_entities_object_list,
                    "-24h",
                    "now",
                )


dispatch(SplkOutliersExecutor, sys.argv, sys.stdin, sys.stdout, __name__)

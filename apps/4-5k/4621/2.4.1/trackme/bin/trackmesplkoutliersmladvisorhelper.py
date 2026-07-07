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
    "%s/var/log/splunk/trackme_splk_outliers_mladvisor_helper.log" % splunkhome,
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

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import the outliers eligibility helper (tenant-level priority + filter expression)
# Same gate applied by trackmesplkoutlierstrainhelper / setrules in the 2.3.22
# ML Outliers tenant-scoping series — see issue #1408. Without it, the
# automated ML Advisor would still inspect entities the tenant has explicitly
# scoped out of ML Outliers, returning per-entity recommendations to the AI
# Agent (and any user the agent explains a model to) for entities that do not
# carry an ML model in the first place. The agent UI and the analyst path
# (/trackme/v2/ai_ml_advisor/ml_advisor) stay gate-free intentionally — those
# are user-initiated lookups, not automated batch reasoning.
from trackme_libs_mloutliers import (
    is_outliers_eligible_for_entity,
    is_ai_automated_eligible_for_entity,
    get_ai_automated_priority_filter,
    get_ai_automated_filter_expression,
)
from collections_data import get_vtenant_mladvisor_field, get_ml_model_mladvisor_disabled


@Configuration(distributed=False)
class SplkOutliersMlAdvisorExecutor(GeneratingCommand):
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
        validate=validators.Match("component", r"^(?:dsm|dhm|flx)$"),
    )

    def generate(self, **kwargs):
        # Python version check - AI ML Advisor requires Python 3.13+
        import sys

        if sys.version_info < (3, 13):
            yield {
                "_raw": json.dumps(
                    {
                        "status": "error",
                        "message": f"AI ML Advisor automated inspection requires Python 3.13+. This instance is running Python {sys.version_info.major}.{sys.version_info.minor}.",
                    }
                )
            }
            return

        # Deferred imports - only available on Python 3.13+
        from trackme_libs_ai_agents import (
            start_ml_advisor_from_search_context,
            get_agent_job_status,
        )

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

        # Get the session key and splunkd_uri
        session_key = self._metadata.searchinfo.session_key
        splunkd_uri = self._metadata.searchinfo.splunkd_uri

        # Get server name
        try:
            server_name = self._metadata.searchinfo.server_name
        except Exception:
            server_name = "unknown"

        #
        # Pre-flight check 1: system-level enable_ai_assistant
        #

        try:
            trackme_settings = self.service.confs["trackme_settings"]
            for stanza in trackme_settings:
                if stanza.name == "trackme_general":
                    if stanza.content.get("enable_ai_assistant", "1") == "0":
                        yield {
                            "_time": time.time(),
                            "_raw": json.dumps(
                                {
                                    "status": "error",
                                    "message": "AI features are disabled by the administrator. "
                                    "Enable AI features in the TrackMe configuration page (General > Artificial Intelligence).",
                                }
                            ),
                        }
                        return
                    break
        except Exception as e:
            logging.warning(f"Could not check AI feature toggle: {e}")

        # Get Virtual Tenant account
        vtenant_account = trackme_vtenant_account(
            session_key,
            splunkd_uri,
            self.tenant_id,
        )

        # get vtenant component info
        vtenant_component_info = trackme_vtenant_component_info(
            session_key,
            splunkd_uri,
            self.tenant_id,
        )
        logging.debug(
            f'vtenant_component_info="{json.dumps(vtenant_component_info, indent=2)}"'
        )

        #
        # Pre-flight check 2: tenant-level ai_mladvisor_enabled
        #

        try:
            ai_mladvisor_enabled = int(
                get_vtenant_mladvisor_field(vtenant_account, "enabled", 0)
            )
        except (ValueError, TypeError):
            ai_mladvisor_enabled = 0

        if ai_mladvisor_enabled == 0:
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "tenant_id": self.tenant_id,
                        "status": "info",
                        "message": "AI ML Advisor automated inspection is disabled for this tenant (ai_mladvisor_enabled=0).",
                    }
                ),
            }
            return

        #
        # Pre-flight check 3: component-level mloutliers_{component}
        #

        key = f"mloutliers_{self.component}"
        try:
            outliers_enablement = int(vtenant_account.get(key, 1))
        except (ValueError, TypeError):
            outliers_enablement = 1

        if outliers_enablement == 0:
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "tenant_id": self.tenant_id,
                        "component": self.component,
                        "status": "info",
                        "message": f"ML Anomaly Detection feature is disabled for the tenant and component ({key}=0), no action taken.",
                    }
                ),
            }
            return

        #
        # Pre-flight check 4: schema migration not in progress
        #

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
            return

        #
        # Read configuration from vtenant_account
        #

        ai_mladvisor_mode = str(get_vtenant_mladvisor_field(vtenant_account, "mode", "inspect"))
        ai_mladvisor_provider_name = str(
            get_vtenant_mladvisor_field(vtenant_account, "provider_name", "")
        )
        provider_name = ai_mladvisor_provider_name if ai_mladvisor_provider_name else None

        try:
            ai_mladvisor_max_runtime_sec = int(
                get_vtenant_mladvisor_field(vtenant_account, "max_runtime_sec", 14400)
            )
        except (ValueError, TypeError):
            ai_mladvisor_max_runtime_sec = 14400

        try:
            ai_mladvisor_min_days_between_reviews = int(
                get_vtenant_mladvisor_field(
                    vtenant_account, "min_days_between_reviews", 30
                )
            )
        except (ValueError, TypeError):
            ai_mladvisor_min_days_between_reviews = 30

        # Shared AI automated-action filter — applied to BOTH ML Advisor
        # (this helper) AND every Components Advisor batch.  Read-time
        # defaults: priority="critical,high", filter_expression="".
        # The CSV is consumed two ways: (a) as the cheap SPL pre-filter
        # ``| where priority IN (...)`` clause below, and (b) as the
        # Python post-filter via ``is_ai_automated_eligible_for_entity``.
        # Both must agree on the priority set — otherwise the SPL pre-
        # filter could let entities through that the Python gate then
        # silently skips (or vice versa). Interactive launches via the
        # REST handlers ignore this filter entirely.
        priority_filter_raw = get_ai_automated_priority_filter(vtenant_account)
        priority_filter_list = [p.strip().lower() for p in priority_filter_raw.split(",") if p.strip()]
        filter_expression_raw = get_ai_automated_filter_expression(vtenant_account)

        max_runtime = ai_mladvisor_max_runtime_sec

        logging.info(
            f'tenant_id="{self.tenant_id}", component="{self.component}", '
            f'ai_mladvisor_mode="{ai_mladvisor_mode}", '
            f'ai_mladvisor_provider_name="{ai_mladvisor_provider_name}", '
            f'ai_mladvisor_max_runtime_sec="{ai_mladvisor_max_runtime_sec}", '
            f'ai_mladvisor_min_days_between_reviews="{ai_mladvisor_min_days_between_reviews}", '
            f'ai_automated_priority_filter="{priority_filter_raw}", '
            f'ai_automated_filter_expression="{filter_expression_raw}"'
        )

        #
        # Build the entity selection SPL query
        #

        # Resolve the tenant summary index for the recently-reviewed filter
        try:
            tenant_indexes = trackme_idx_for_tenant(
                session_key,
                splunkd_uri,
                self.tenant_id,
            )
            tenant_summary_idx = tenant_indexes.get(
                "trackme_summary_idx", "trackme_summary"
            )
        except Exception as e:
            logging.warning(
                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                f'failed to resolve tenant index, falling back to default: exception="{str(e)}"'
            )
            tenant_summary_idx = "trackme_summary"

        # Priority filter clause — skip entities whose `priority` is not in
        # the shared `ai_automated_priority_filter` list.  Empty list =
        # no SPL pre-filter applied (the Python post-filter still runs
        # the match-all path via ``is_ai_automated_eligible_for_entity``).
        if priority_filter_list:
            quoted = ", ".join(f'"{p}"' for p in priority_filter_list)
            priority_clause = f'\n                | where priority IN ({quoted})'
        else:
            priority_clause = ""

        # Build entity selection query
        # When min_days_between_reviews is 0, skip the review history filter
        # to inspect as many entities as possible within the max runtime window
        #
        # The `table` clause surfaces every field the tenant-level ML Outliers
        # eligibility filter (priority + filter expression DSL, introduced in
        # 2.3.22) needs to evaluate per entity. `data_index` and
        # `data_sourcetype` may be missing on flx records — that's fine, the
        # filter engine treats absent fields as empty (CONDITION evaluates
        # False, fail-closed; same semantics as Virtual Groups). Issue #1408
        # — apply the same gate the trainhelper / setrules apply, so the
        # AI ML Advisor never reasons about entities the tenant has scoped
        # out of ML Outliers.
        base_query = f"""\
                | trackmegetcoll tenant_id="{self.tenant_id}" component="{self.component}"
                | where monitored_state="enabled"{priority_clause}
                | table keyid, object, priority, tags, labels, data_index, data_sourcetype, isOutlier
                | lookup trackme_{self.component}_outliers_entity_data_tenant_{self.tenant_id} _key as keyid OUTPUT mtime as last_monitored
                | lookup trackme_{self.component}_outliers_entity_rules_tenant_{self.tenant_id} _key as keyid OUTPUT entities_outliers"""

        if ai_mladvisor_min_days_between_reviews > 0:
            review_filter = f"""
                | join type=left object [
                    search index="{tenant_summary_idx}" sourcetype="trackme:ai_agent:ml_advisor:*"
                        earliest=-{ai_mladvisor_min_days_between_reviews}d latest=now
                        tenant_id="{self.tenant_id}" component="{self.component}" automated=true
                    | stats max(_time) as last_review_time by object
                ]
                | where isnull(last_review_time)"""
        else:
            review_filter = ""

        search_query = remove_leading_spaces(
            base_query + review_filter + """
                | sort - isOutlier, - last_monitored
            """
        )

        logging.debug(
            f'tenant_id="{self.tenant_id}", component="{self.component}", '
            f'entity selection query="{search_query}"'
        )

        #
        # RUN - Execute entity selection query
        #

        kwargs_oneshot = {
            "earliest_time": "-24h",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        try:
            reader = run_splunk_search(
                self.service,
                search_query,
                kwargs_oneshot,
                24,
                5,
            )

            entities_toprocess = []
            # Counters for entities skipped by the tenant-level ML Outliers
            # eligibility filter (priority filter + filter expression DSL).
            # Mirrors the per-cycle skip summary the trainhelper /
            # setrules emit, so operators can correlate "fewer ML Advisor
            # inspections than expected" with the tenant's outliers scope.
            skipped_mlo_priority_filter = 0
            skipped_mlo_filter_expression = 0
            skipped_mlo_filter_expression_invalid = 0
            # Counters for entities skipped by the shared AI automated-
            # action filter (priority + filter expression DSL). Distinct
            # from the ML Outliers gate above — an entity must pass BOTH
            # to be inspected.
            skipped_ai_priority_filter = 0
            skipped_ai_filter_expression = 0
            skipped_ai_filter_expression_invalid = 0

            for item in reader:
                if isinstance(item, dict):
                    logging.debug(f'entity_selection_result="{item}"')

                    # Gate 1: Tenant-level ML Outliers eligibility (2.3.22 +
                    # issue #1408). Skip entities scoped out of the tenant's
                    # ML Outliers feature (a related-but-distinct concept
                    # from the AI Advisor automated scope below).
                    eligible, reason = is_outliers_eligible_for_entity(
                        vtenant_account, item
                    )
                    if not eligible:
                        if reason == "priority_filter":
                            skipped_mlo_priority_filter += 1
                        elif reason == "filter_expression":
                            skipped_mlo_filter_expression += 1
                        elif reason == "filter_expression_invalid":
                            skipped_mlo_filter_expression_invalid += 1
                        logging.debug(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", '
                            f'object="{item.get("object")}", priority="{item.get("priority")}", '
                            f'skipped from ML Advisor inspection by ML Outliers tenant filter, reason="{reason}"'
                        )
                        continue

                    # Gate 2: Shared AI Agent automated-action filter
                    # (priority + filter expression DSL). Same gate the
                    # four Components Advisor batches apply, so an
                    # operator who narrows the AI scope at the tenant
                    # level sees consistent behaviour across every
                    # automated advisor.
                    eligible, reason = is_ai_automated_eligible_for_entity(
                        vtenant_account, item
                    )
                    if not eligible:
                        if reason == "priority_filter":
                            skipped_ai_priority_filter += 1
                        elif reason == "filter_expression":
                            skipped_ai_filter_expression += 1
                        elif reason == "filter_expression_invalid":
                            skipped_ai_filter_expression_invalid += 1
                        logging.debug(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", '
                            f'object="{item.get("object")}", priority="{item.get("priority")}", '
                            f'skipped from ML Advisor inspection by AI automated filter, reason="{reason}"'
                        )
                        continue

                    entities_toprocess.append(item)

            # Emit a summary log line whenever any entity was skipped, so
            # operators can quickly correlate "fewer inspections than expected"
            # with tenant filter scope.
            if (
                skipped_mlo_priority_filter
                or skipped_mlo_filter_expression
                or skipped_mlo_filter_expression_invalid
            ):
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'ML Outliers tenant filter skipped entities from ML Advisor inspection: '
                    f'priority_filter={skipped_mlo_priority_filter}, '
                    f'filter_expression={skipped_mlo_filter_expression}, '
                    f'filter_expression_invalid={skipped_mlo_filter_expression_invalid}'
                )
            if (
                skipped_ai_priority_filter
                or skipped_ai_filter_expression
                or skipped_ai_filter_expression_invalid
            ):
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'AI automated-action filter skipped entities from ML Advisor inspection: '
                    f'priority_filter={skipped_ai_priority_filter}, '
                    f'filter_expression={skipped_ai_filter_expression}, '
                    f'filter_expression_invalid={skipped_ai_filter_expression_invalid}'
                )

        except Exception as e:
            msg = f'tenant_id="{self.tenant_id}", entity selection search failed with exception="{str(e)}"'
            logging.error(msg)
            raise Exception(msg)

        #
        # Process entities - synchronous loop with agent calls
        #

        processed_entities = []
        failures_entities = []
        failures_entities_object_list = []
        search_errors_count = 0

        # Initialize sum of execution times and count of iterations
        total_execution_time = 0
        iteration_count = 0

        if len(entities_toprocess) > 0:
            for entity_record in entities_toprocess:
                object_value = entity_record.get("object", "")
                object_id = entity_record.get("keyid", "")
                entities_outliers_raw = entity_record.get("entities_outliers", "")

                # Parse entities_outliers JSON; skip if ALL models have ai_mladvisor_disabled == 1
                try:
                    if entities_outliers_raw:
                        entities_outliers = json.loads(entities_outliers_raw) if isinstance(entities_outliers_raw, str) else entities_outliers_raw
                        if isinstance(entities_outliers, dict):
                            all_disabled = all(
                                get_ml_model_mladvisor_disabled(m) == 1
                                for m in entities_outliers.values()
                                if isinstance(m, dict)
                            )
                            if all_disabled:
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                                    f'object="{object_value}" - all models have ai_mladvisor_disabled=1, skipping'
                                )
                                continue
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    logging.warning(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'object="{object_value}" - failed to parse entities_outliers: {e}, proceeding anyway'
                    )

                # iteration start
                iteration_start_time = time.time()

                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'starting ML Advisor for object="{object_value}", mode="{ai_mladvisor_mode}"'
                )

                try:
                    # Start the ML Advisor agent
                    agent_result = start_ml_advisor_from_search_context(
                        service=self.service,
                        session_key=session_key,
                        splunkd_uri=splunkd_uri,
                        server_name=server_name,
                        tenant_id=self.tenant_id,
                        component=self.component,
                        object_id=object_id,
                        object_name=object_value,
                        mode=ai_mladvisor_mode,
                        provider_name=provider_name,
                        vtenant_account=vtenant_account,
                    )

                    job_id = agent_result.get("job_id")
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'object="{object_value}", agent job started, job_id="{job_id}"'
                    )

                    # Poll for completion - 5s interval, 15-min timeout per entity
                    entity_timeout = 900  # 15 minutes
                    poll_start = time.time()

                    while True:
                        time.sleep(5)

                        job_status = get_agent_job_status(self.service, job_id)
                        if job_status is None:
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", job_id="{job_id}", '
                                f'object="{object_value}" - job status not found, breaking'
                            )
                            break

                        status = job_status.get("status", "unknown")

                        if status in ("complete", "completed"):
                            logging.info(
                                f'tenant_id="{self.tenant_id}", job_id="{job_id}", '
                                f'object="{object_value}" - agent completed successfully'
                            )
                            break

                        if status in ("error", "failed"):
                            error_msg = job_status.get("error", "unknown error")
                            logging.error(
                                f'tenant_id="{self.tenant_id}", job_id="{job_id}", '
                                f'object="{object_value}" - agent failed: {error_msg}'
                            )
                            break

                        # Check per-entity timeout
                        if time.time() - poll_start >= entity_timeout:
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", job_id="{job_id}", '
                                f'object="{object_value}" - entity timeout ({entity_timeout}s) reached'
                            )
                            break

                    entity_runtime = round(time.time() - iteration_start_time, 3)
                    processed_entities.append(
                        {
                            "object_category": f"splk-{self.component}",
                            "object": object_value,
                            "job_id": job_id,
                            "status": status if job_status else "unknown",
                            "runtime": str(entity_runtime),
                        }
                    )

                except Exception as e:
                    entity_runtime = round(time.time() - iteration_start_time, 3)
                    msg = (
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'object="{object_value}", ML Advisor failed with exception="{str(e)}"'
                    )
                    logging.error(msg)
                    search_errors_count += 1
                    failures_entities.append(
                        {
                            "object_category": f"splk-{self.component}",
                            "object": object_value,
                            "exception": str(e),
                            "runtime": str(entity_runtime),
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
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'max_runtime="{max_runtime}" is about to be reached, '
                        f'current_runtime="{elapsed_time}", job will be terminated now'
                    )
                    break

            #
            # end process entities loop
            #

            # yield and log
            results_dict = {
                "tenant_id": self.tenant_id,
                "component": self.component,
                "action": "success",
                "results": "AI ML Advisor inspection job successfully executed",
                "run_time": round((time.time() - start), 3),
                "mode": ai_mladvisor_mode,
                "entities_count": len(entities_toprocess),
                "processed_count": len(processed_entities),
                "processed_entities": processed_entities,
                "failures_entities": failures_entities,
                "search_errors_count": search_errors_count,
                "upstream_search_query": search_query,
            }
            yield {"_time": time.time(), "_raw": results_dict}
            logging.info(json.dumps(results_dict, indent=2))

            # handler events
            handler_events_records = []
            for object_record in processed_entities:
                handler_events_records.append(
                    {
                        "object": object_record.get("object"),
                        "object_id": hashlib.sha256(
                            object_record.get("object").encode("utf-8")
                        ).hexdigest(),
                        "object_category": f"splk-{self.component}",
                        "handler": f"trackme_{self.component}_outliers_mladvisor_tracker_tenant_{self.tenant_id}",
                        "handler_message": "Entity was reviewed by AI ML Advisor.",
                        "handler_troubleshoot_search": f'index=_internal (sourcetype=trackme:custom_commands:trackmesplkoutliersmladvisor) tenant_id={self.tenant_id} object="{object_record.get("object")}"',
                        "handler_time": time.time(),
                    }
                )

            # notification event
            try:
                trackme_handler_events(
                    session_key=session_key,
                    splunkd_uri=splunkd_uri,
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
                "component": self.component,
                "action": "success",
                "results": "AI ML Advisor inspection job successfully executed but there were no entities to review at this time",
                "run_time": round((time.time() - start), 3),
                "mode": ai_mladvisor_mode,
                "entities_count": 0,
                "upstream_search_query": search_query,
            }
            yield {"_time": time.time(), "_raw": results_dict}
            logging.info(json.dumps(results_dict, indent=2))

        # Call the component register
        report_name = f"trackme_{self.component}_outliers_mladvisor_tracker_tenant_{self.tenant_id}"
        if search_errors_count == 0:
            trackme_register_tenant_object_summary(
                session_key,
                splunkd_uri,
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
                splunkd_uri,
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


dispatch(SplkOutliersMlAdvisorExecutor, sys.argv, sys.stdin, sys.stdout, __name__)

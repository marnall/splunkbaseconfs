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
import hashlib

import logging
from logging.handlers import RotatingFileHandler

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

splunkhome = os.environ["SPLUNK_HOME"]

filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_feed_lifecycle_advisor_helper.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()
for hdlr in log.handlers[:]:
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)
log.setLevel(logging.INFO)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import import_declare_test

from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

from trackme_libs import (
    trackme_reqinfo,
    trackme_vtenant_account,
    trackme_vtenant_component_info,
    trackme_idx_for_tenant,
    trackme_register_tenant_object_summary,
    run_splunk_search,
    trackme_handler_events,
)

from trackme_libs_utils import remove_leading_spaces

# Shared AI Agent automated-action filter — applied uniformly across the
# ML Advisor (mladvisor) and every Components Advisor batch (this helper
# included). See trackme_libs_mloutliers.is_ai_automated_eligible_for_entity.
from trackme_libs_mloutliers import (
    is_ai_automated_eligible_for_entity,
    get_ai_automated_priority_filter,
    get_ai_automated_filter_expression,
)

# Threshold-lock predicate — the automated Feed Lifecycle batch must NOT retune
# an entity whose operator has pinned its delay/lag thresholds (same
# "automation keeps out" contract honoured by the mechanical adaptive-delay and
# variable-delay reviewers). Interactive advisor runs are not filtered.
from trackme_libs_threshold_intent import is_delay_threshold_locked


@Configuration(distributed=False)
class SplkFeedLifecycleAdvisorExecutor(GeneratingCommand):
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
        **Description:** The component category: dsm or dhm.""",
        require=True,
        default=None,
        validate=validators.Match("component", r"^(?:dsm|dhm)$"),
    )

    def generate(self, **kwargs):
        # Python version check — Feed Lifecycle Advisor requires Python 3.13+
        if sys.version_info < (3, 13):
            yield {
                "_raw": json.dumps(
                    {
                        "status": "error",
                        "message": (
                            f"AI Feed Lifecycle Advisor requires Python 3.13+. "
                            f"This instance is running Python {sys.version_info.major}.{sys.version_info.minor}."
                        ),
                    }
                )
            }
            return

        # Deferred imports — only available on Python 3.13+
        from trackme_libs_ai_feed_lifecycle import (
            start_feed_lifecycle_advisor_from_search_context,
        )
        from trackme_libs_ai_agents import get_agent_job_status

        # Performance counter
        start = time.time()
        average_execution_time = 0

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
        )
        log.setLevel(reqinfo["logging_level"])

        session_key = self._metadata.searchinfo.session_key
        splunkd_uri = self._metadata.searchinfo.splunkd_uri

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
                                    "message": (
                                        "AI features are disabled by the administrator. "
                                        "Enable AI features in the TrackMe configuration page "
                                        "(General > Artificial Intelligence)."
                                    ),
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

        vtenant_component_info = trackme_vtenant_component_info(
            session_key,
            splunkd_uri,
            self.tenant_id,
        )
        logging.debug(f'vtenant_component_info="{json.dumps(vtenant_component_info, indent=2)}"')

        #
        # Pre-flight check 2: tenant-level ai_components_advisor_enabled
        #
        # Single switch across the four component-level advisors (Feed
        # Lifecycle, FLX Threshold, FQM Advisor, Component Health).  The
        # previous per-advisor flag (ai_feedlifecycle_enabled) was retired
        # in favour of this unified field — see the schema migration.
        #

        try:
            ai_components_advisor_enabled = int(vtenant_account.get("ai_components_advisor_enabled", 0))
        except (ValueError, TypeError):
            ai_components_advisor_enabled = 0

        if ai_components_advisor_enabled == 0:
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "tenant_id": self.tenant_id,
                        "status": "info",
                        "message": "AI Components Advisor automated inspection is disabled for this tenant (ai_components_advisor_enabled=0).",
                    }
                ),
            }
            return

        #
        # Pre-flight check 2.b: this component is in ai_components_advisor_list
        #
        # The per-tenant component list narrows automated runs to a subset
        # of the six monitoring components.  Default is "all six".  A
        # tenant that has, say, only DSM in the list will see Feed
        # Lifecycle batches run on DSM and silently no-op on DHM.
        #

        components_list_raw = str(vtenant_account.get("ai_components_advisor_list", "dsm,dhm,mhm,flx,fqm,wlk"))
        components_list = [c.strip().lower() for c in components_list_raw.split(",") if c.strip()]
        if self.component.lower() not in components_list:
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "tenant_id": self.tenant_id,
                        "component": self.component,
                        "status": "info",
                        "message": (
                            f"Component '{self.component}' is not in ai_components_advisor_list "
                            f"({components_list_raw!r}); skipping."
                        ),
                    }
                ),
            }
            return

        #
        # Pre-flight check 3: component enabled for the tenant
        #

        component_info_key = f"component_splk_{self.component}"
        try:
            component_enabled = int(vtenant_component_info.get(component_info_key, 0))
        except (ValueError, TypeError):
            component_enabled = 0

        if component_enabled == 0:
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "tenant_id": self.tenant_id,
                        "component": self.component,
                        "status": "info",
                        "message": f"Component {self.component} is disabled for this tenant ({component_info_key}=0), no action taken.",
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
        except Exception as e:
            schema_version = 0
            schema_version_upgrade_in_progress = False
            logging.error(f'failed to retrieve schema_version_upgrade_in_progress, exception="{str(e)}"')

        if schema_version_upgrade_in_progress:
            yield_json = {
                "_time": time.time(),
                "tenant_id": self.tenant_id,
                "component": self.component,
                "response": (
                    f'tenant_id="{self.tenant_id}", schema upgrade is currently in progress, '
                    f'will wait until completed. schema_version="{schema_version}"'
                ),
                "schema_version": schema_version,
                "schema_version_upgrade_in_progress": schema_version_upgrade_in_progress,
            }
            logging.info(json.dumps(yield_json, indent=2))
            yield {"_time": yield_json["_time"], "_raw": yield_json}
            return

        #
        # Read configuration from vtenant_account
        #

        # Read unified ai_components_advisor_* configuration.
        ai_components_advisor_mode = str(vtenant_account.get("ai_components_advisor_mode", "inspect"))
        ai_components_advisor_provider_name = str(vtenant_account.get("ai_components_advisor_provider_name", ""))
        provider_name = ai_components_advisor_provider_name if ai_components_advisor_provider_name else None

        try:
            ai_components_advisor_max_runtime_sec = int(vtenant_account.get("ai_components_advisor_max_runtime_sec", 14400))
        except (ValueError, TypeError):
            ai_components_advisor_max_runtime_sec = 14400

        try:
            ai_components_advisor_min_days_between_reviews = int(
                vtenant_account.get("ai_components_advisor_min_days_between_reviews", 30)
            )
        except (ValueError, TypeError):
            ai_components_advisor_min_days_between_reviews = 30

        # Shared AI Agent automated-action filter — same gate as ML Advisor
        # and every other Components Advisor batch. The CSV is consumed
        # twice: as the cheap SPL pre-filter ``| where priority IN (...)``
        # clause below, and as the Python post-filter via
        # ``is_ai_automated_eligible_for_entity``. Both must agree on the
        # priority set. Interactive launches via the REST handlers ignore
        # this filter.
        priority_filter_raw = get_ai_automated_priority_filter(vtenant_account)
        priority_filter_list = [p.strip().lower() for p in priority_filter_raw.split(",") if p.strip()]
        filter_expression_raw = get_ai_automated_filter_expression(vtenant_account)

        # Aliases used downstream for backward-compatible naming.
        ai_feedlifecycle_mode = ai_components_advisor_mode
        max_runtime = ai_components_advisor_max_runtime_sec

        logging.info(
            f'tenant_id="{self.tenant_id}", component="{self.component}", '
            f'ai_components_advisor_mode="{ai_components_advisor_mode}", '
            f'ai_components_advisor_provider_name="{ai_components_advisor_provider_name}", '
            f'ai_components_advisor_max_runtime_sec="{ai_components_advisor_max_runtime_sec}", '
            f'ai_components_advisor_min_days_between_reviews="{ai_components_advisor_min_days_between_reviews}", '
            f'ai_automated_priority_filter="{priority_filter_raw}", '
            f'ai_automated_filter_expression="{filter_expression_raw}"'
        )

        #
        # Resolve tenant summary index for review history filter
        #

        try:
            tenant_indexes = trackme_idx_for_tenant(session_key, splunkd_uri, self.tenant_id)
            tenant_summary_idx = tenant_indexes.get("trackme_summary_idx", "trackme_summary")
        except Exception as e:
            logging.warning(
                f'tenant_id="{self.tenant_id}", failed to resolve tenant index, '
                f'falling back to default: exception="{str(e)}"'
            )
            tenant_summary_idx = "trackme_summary"

        #
        # Build entity selection SPL query
        #

        # Priority filter clause — skip entities whose `priority` field is
        # not in the shared `ai_automated_priority_filter` list. Empty list
        # = no SPL pre-filter applied; the Python post-filter still runs
        # via ``is_ai_automated_eligible_for_entity`` below.
        if priority_filter_list:
            quoted = ", ".join(f'"{p}"' for p in priority_filter_list)
            priority_clause = f'\n                | where priority IN ({quoted})'
        else:
            priority_clause = ""

        # The `table` clause surfaces every field the AI automated-action
        # filter expression may reference. `tags`, `labels`, `data_index`
        # and `data_sourcetype` may be empty on some entities; the filter
        # engine treats absent fields as empty (CONDITION evaluates False,
        # fail-closed) — same semantics as Virtual Groups.
        # Threshold-lock exclusion: a locked entity has operator-pinned delay/lag
        # thresholds and is under manual lifecycle control — the automated batch
        # must skip it (the Python guard below is defence in depth). isnull keeps
        # pre-lock and legacy records (no flag) eligible.
        base_query = f"""\
                | trackmegetcoll tenant_id="{self.tenant_id}" component="{self.component}"
                | where monitored_state="enabled"{priority_clause}
                | where (isnull(data_max_delay_allowed_locked) OR data_max_delay_allowed_locked!="true")
                | table keyid, object, object_state, priority, tags, labels, data_index, data_sourcetype, data_max_delay_allowed_locked"""

        if ai_components_advisor_min_days_between_reviews > 0:
            review_filter = f"""
                | join type=left object [
                    search index={tenant_summary_idx} sourcetype="trackme:ai_agent:feed_lifecycle_advisor:*"
                        earliest=-{ai_components_advisor_min_days_between_reviews}d latest=now
                        tenant_id="{self.tenant_id}" component="{self.component}" automated="true"
                    | stats max(_time) as last_review_time by object
                ]
                | where isnull(last_review_time)"""
        else:
            review_filter = ""

        # Sort: RED entities first, then by most recently monitored
        search_query = remove_leading_spaces(
            base_query + review_filter + """
                | eval state_priority=if(object_state="red", 0, if(object_state="orange", 1, 2))
                | sort state_priority, object
            """
        )

        logging.debug(
            f'tenant_id="{self.tenant_id}", component="{self.component}", '
            f'entity selection query="{search_query}"'
        )

        #
        # Execute entity selection query
        #

        kwargs_oneshot = {
            "earliest_time": "-24h",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        try:
            reader = run_splunk_search(self.service, search_query, kwargs_oneshot, 24, 5)

            entities_toprocess = []
            # Counters for entities skipped by the shared AI automated-
            # action filter. Each is emitted to the per-cycle summary log
            # so operators can correlate "fewer reviews than expected"
            # with their tenant filter scope.
            skipped_ai_priority_filter = 0
            skipped_ai_filter_expression = 0
            skipped_ai_filter_expression_invalid = 0
            skipped_threshold_locked = 0
            for item in reader:
                if isinstance(item, dict):
                    logging.debug(f'entity_selection_result="{item}"')

                    # Threshold lock: operator has pinned this entity's
                    # delay/lag thresholds and taken manual lifecycle control —
                    # the automated batch must not retune it. The SPL pre-filter
                    # already excludes these; this is defence in depth in case
                    # the field was not surfaced. Interactive runs are NOT
                    # filtered (this gate lives only in the automated helper).
                    if is_delay_threshold_locked(item):
                        skipped_threshold_locked += 1
                        logging.debug(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", '
                            f'object="{item.get("object")}", skipped from Feed Lifecycle '
                            f'Advisor: threshold locked'
                        )
                        continue

                    # Shared AI Agent automated-action gate (priority +
                    # filter expression DSL). Same gate every other
                    # automated advisor applies; an operator who narrows
                    # the AI scope at the tenant level sees consistent
                    # behaviour across the board.
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
                            f'skipped from Feed Lifecycle Advisor by AI automated filter, reason="{reason}"'
                        )
                        continue

                    entities_toprocess.append(item)

            if (
                skipped_ai_priority_filter
                or skipped_ai_filter_expression
                or skipped_ai_filter_expression_invalid
                or skipped_threshold_locked
            ):
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'AI automated-action filter skipped entities from Feed Lifecycle Advisor: '
                    f'priority_filter={skipped_ai_priority_filter}, '
                    f'filter_expression={skipped_ai_filter_expression}, '
                    f'filter_expression_invalid={skipped_ai_filter_expression_invalid}, '
                    f'threshold_locked={skipped_threshold_locked}'
                )

        except Exception as e:
            msg = f'tenant_id="{self.tenant_id}", entity selection search failed with exception="{str(e)}"'
            logging.error(msg)
            raise Exception(msg)

        #
        # Process entities — synchronous loop with agent calls
        #

        processed_entities = []
        failures_entities = []
        failures_entities_object_list = []
        search_errors_count = 0

        total_execution_time = 0
        iteration_count = 0

        if len(entities_toprocess) > 0:
            for entity_record in entities_toprocess:
                object_value = entity_record.get("object", "")
                object_id = entity_record.get("keyid", "")

                iteration_start_time = time.time()

                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'starting Feed Lifecycle Advisor for object="{object_value}", mode="{ai_feedlifecycle_mode}"'
                )

                status = "unknown"
                job_id = None
                try:
                    agent_result = start_feed_lifecycle_advisor_from_search_context(
                        service=self.service,
                        session_key=session_key,
                        splunkd_uri=splunkd_uri,
                        server_name=server_name,
                        tenant_id=self.tenant_id,
                        component=self.component,
                        object_id=object_id,
                        object_name=object_value,
                        mode=ai_feedlifecycle_mode,
                        provider_name=provider_name,
                        vtenant_account=vtenant_account,
                    )

                    job_id = agent_result.get("job_id")
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'object="{object_value}", agent job started, job_id="{job_id}"'
                    )

                    # Poll for completion — 5s interval, 15-min timeout per entity
                    entity_timeout = 900
                    poll_start = time.time()

                    while True:
                        time.sleep(5)

                        job_status = get_agent_job_status(self.service, job_id)
                        if job_status is None:
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", job_id="{job_id}", '
                                f'object="{object_value}" - job status not found, breaking'
                            )
                            status = "unknown"
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

                        if time.time() - poll_start >= entity_timeout:
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", job_id="{job_id}", '
                                f'object="{object_value}" - entity timeout ({entity_timeout}s) reached'
                            )
                            status = "timeout"
                            break

                    entity_runtime = round(time.time() - iteration_start_time, 3)
                    processed_entities.append(
                        {
                            "object_category": f"splk-{self.component}",
                            "object": object_value,
                            "job_id": job_id,
                            "status": status,
                            "runtime": str(entity_runtime),
                        }
                    )

                except Exception as e:
                    entity_runtime = round(time.time() - iteration_start_time, 3)
                    msg = (
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'object="{object_value}", Feed Lifecycle Advisor failed with exception="{str(e)}"'
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

                # Track timing
                iteration_end_time = time.time()
                execution_time = iteration_end_time - iteration_start_time
                total_execution_time += execution_time
                iteration_count += 1

                if iteration_count > 0:
                    average_execution_time = total_execution_time / iteration_count

                # Time-bounded early exit
                current_time = time.time()
                elapsed_time = current_time - start
                if elapsed_time + average_execution_time + 120 >= max_runtime:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'max_runtime="{max_runtime}" is about to be reached, '
                        f'current_runtime="{elapsed_time}", job will be terminated now'
                    )
                    break

            # Yield results
            results_dict = {
                "tenant_id": self.tenant_id,
                "component": self.component,
                "action": "success",
                "results": "AI Feed Lifecycle Advisor job successfully executed",
                "run_time": round((time.time() - start), 3),
                "mode": ai_feedlifecycle_mode,
                "entities_count": len(entities_toprocess),
                "processed_count": len(processed_entities),
                "processed_entities": processed_entities,
                "failures_entities": failures_entities,
                "search_errors_count": search_errors_count,
                "upstream_search_query": search_query,
            }
            yield {"_time": time.time(), "_raw": results_dict}
            logging.info(json.dumps(results_dict, indent=2))

            # Handler events
            handler_events_records = []
            for object_record in processed_entities:
                handler_events_records.append(
                    {
                        "object": object_record.get("object"),
                        "object_id": hashlib.sha256(
                            object_record.get("object").encode("utf-8")
                        ).hexdigest(),
                        "object_category": f"splk-{self.component}",
                        "handler": f"trackme_{self.component}_feed_lifecycle_advisor_tracker_tenant_{self.tenant_id}",
                        "handler_message": "Entity was reviewed by AI Feed Lifecycle Advisor.",
                        "handler_troubleshoot_search": (
                            f'index=_internal '
                            f'(sourcetype=trackme:custom_commands:trackmesplkfeedlifecycleadvisorhelper) '
                            f'tenant_id={self.tenant_id} object="{object_record.get("object")}"'
                        ),
                        "handler_time": time.time(),
                    }
                )

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
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'could not send notification event, exception="{e}"'
                )

        else:
            results_dict = {
                "tenant_id": self.tenant_id,
                "component": self.component,
                "action": "success",
                "results": "AI Feed Lifecycle Advisor job executed but there were no entities to review at this time",
                "run_time": round((time.time() - start), 3),
                "mode": ai_feedlifecycle_mode,
                "entities_count": 0,
                "upstream_search_query": search_query,
            }
            yield {"_time": time.time(), "_raw": results_dict}
            logging.info(json.dumps(results_dict, indent=2))

        # Register component summary
        report_name = f"trackme_{self.component}_feed_lifecycle_advisor_tracker_tenant_{self.tenant_id}"
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


dispatch(SplkFeedLifecycleAdvisorExecutor, sys.argv, sys.stdin, sys.stdout, __name__)

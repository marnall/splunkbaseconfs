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
import uuid
import threading
import hashlib
from logging.handlers import RotatingFileHandler

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
    f"{splunkhome}/var/log/splunk/trackme_tracker_health.log",
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
import splunklib.results as results

# import trackme libs
from trackme_libs import (
    trackme_reqinfo,
    trackme_register_tenant_object_summary,
    trackme_delete_tenant_object_summary,
    trackme_vtenant_account,
    trackme_idx_for_tenant,
    trackme_state_event,
    trackme_register_tenant_component_summary,
    trackme_handler_events,
    trackme_manage_report_schedule,
    trackme_get_version,
    get_splunkd_timeout,
)

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license

# import trackme libs
from trackme_libs import (
    trackme_report_update_enablement,
    run_splunk_search,
    trackme_gen_state,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces, decode_unicode

# import trackme libs logical groups
from trackme_libs_logicalgroup import (
    get_logical_groups_collection_records,
    logical_group_remove_object_from_groups,
    logical_group_delete_group_by_name,
)

# import TrackMe get data libs
from trackme_libs_get_data import (
    get_full_kv_collection,
    batch_find_records_by_key,
)

# import default vtenant account settings
from collections_data import vtenant_account_default

# import trackme libs sla
from trackme_libs_sla import trackme_sla_gen_metrics

# import trackme libs scoring
from trackme_libs_scoring import trackme_impact_score_gen_metrics

# import trackme libs schema
from trackme_libs_schema import trackme_schema_format_version

# import trackme AI libs (provider-presence check for advisor scheduling gates)
from trackme_libs_ai import list_ai_providers

# import shadow copy libs
from trackme_libs_shadow import (
    should_use_shadow,
    read_shadow_records,
)

# import global cache libs
from trackme_libs_global_cache import (
    global_cache_get,
    global_cache_set,
)

# import concurrent.futures for parallel task execution
from concurrent.futures import ThreadPoolExecutor, as_completed


class TaskFrequencyManager:
    """
    Manages task execution frequency for the health tracker.

    Tasks are classified into four tiers:
      - Tier 1 (every_cycle): Critical tasks that run on every cycle
      - Tier 2 (periodic): Maintenance tasks that run every N cycles (default: 6 = ~30 min)
      - Tier 3 (offpeak): Infrequent cleanup tasks that run every M cycles (default: 72 = ~6 hours)
      - Tier 4 (daily): Rare housekeeping tasks that run every P cycles (default: 288 = ~24 hours)

    State is persisted in the kv_trackme_health_tracker_state KV Store collection
    to survive process restarts. Key format: {tenant_id}:{task_name}
    """

    # Task tier classification
    TIER_1_TASKS = {
        "check_vtenant_accounts",
        "check_licensing",
        "check_global_trackers_enablement",
        "schema_upgrade",
        "inspect_collection:handle_sync_entities",
        "replica_orchestrator",
        "gen_sla_breaches_and_score_metrics",
        "check_trackers_statuses",
    }

    TIER_2_TASKS = {
        "untracked_entities",
    }

    TIER_3_TASKS = {
        "unclosed_stateful_incidents",
        "check_trackers_definition",
        "check_trackers_collections",
        "check_shadow_auto_enablement",
        "reconcile_threshold_intent",
    }

    TIER_4_TASKS = {
        "apply_licensing_restrictions",
        "check_tenants_indexes_settings",
        "check_alerts_definition",
        "check_tenant_record_knowledge_objects",
        "check_logical_groups",
        "inspect_collection:corrupted_records_inspection",
        "inspect_collection:missing_tenant_id_records_inspection",
        "inspect_collection:entities_auto_disablement",
        "inspect_collection:permanently_deleted_records_inspection",
        "optimize_tenant_scheduled_reports",
        "duplicated_entities",
        "check_guardian:tenant_owner_capabilities",
        "check_guardian:ai_feed_lifecycle_delay_conflict",
    }

    def __init__(self, service, tenant_id, reqinfo):
        self.service = service
        self.tenant_id = tenant_id
        self.collection_name = "kv_trackme_health_tracker_state"
        self._state = {}
        self._cycle_start = time.time()

        # Load frequency settings from trackme_settings.conf
        health_tracker_conf = reqinfo.get("trackme_conf", {}).get("health_tracker", {})
        self.periodic_frequency = int(health_tracker_conf.get("periodic_task_frequency", 6))
        self.offpeak_frequency = int(health_tracker_conf.get("offpeak_task_frequency", 72))
        self.daily_frequency = int(health_tracker_conf.get("daily_task_frequency", 288))
        self.max_cycle_duration = int(health_tracker_conf.get("max_cycle_duration", 240))

        # Performance tracking
        self.tasks_executed = 0
        self.tasks_skipped = 0
        self.tier1_run_time = 0
        self.tier2_run_time = 0
        self.tier3_run_time = 0
        self.tier4_run_time = 0
        self.circuit_breaker_triggered = False

        # Batch-load all state records for this tenant
        self._load_state()

    def _load_state(self):
        """Batch-load all state records for this tenant from KV Store."""
        try:
            collection = self.service.kvstore[self.collection_name]
            query = json.dumps({"tenant_id": self.tenant_id})
            records = collection.data.query(query=query)
            for record in records:
                task_name = record.get("task_name")
                if task_name:
                    self._state[task_name] = {
                        "execution_count": int(record.get("execution_count", 0)),
                        "last_execution_time": float(record.get("last_execution_time", 0)),
                        "last_execution_duration": float(record.get("last_execution_duration", 0)),
                        "last_execution_status": record.get("last_execution_status", "unknown"),
                        "_key": record.get("_key"),
                    }
            logging.debug(
                f'tenant_id="{self.tenant_id}", TaskFrequencyManager loaded {len(self._state)} state records'
            )
        except Exception as e:
            logging.warning(
                f'tenant_id="{self.tenant_id}", TaskFrequencyManager failed to load state, '
                f'all tasks will run this cycle, exception="{str(e)}"'
            )
            self._state = {}

    def _get_tier(self, task_name):
        """Return the tier for a task name."""
        if task_name in self.TIER_1_TASKS:
            return "every_cycle"
        elif task_name in self.TIER_2_TASKS:
            return "periodic"
        elif task_name in self.TIER_3_TASKS:
            return "offpeak"
        elif task_name in self.TIER_4_TASKS:
            return "daily"
        # Unknown tasks default to every_cycle for safety
        return "every_cycle"

    def _get_frequency(self, tier):
        """Return the frequency in cycles for a tier."""
        if tier == "every_cycle":
            return 1
        elif tier == "periodic":
            return self.periodic_frequency
        elif tier == "offpeak":
            return self.offpeak_frequency
        elif tier == "daily":
            return self.daily_frequency
        return 1

    def should_run(self, task_name):
        """
        Determine if a task should run this cycle.

        Tier 1 tasks always run. Tier 2/3/4 tasks run based on their execution count
        modulo their frequency. If the circuit breaker budget is exceeded, Tier 2/3/4
        tasks are skipped.
        """
        tier = self._get_tier(task_name)

        # Tier 1 tasks always run
        if tier == "every_cycle":
            return True

        # Circuit breaker: if elapsed cycle time exceeds budget, skip non-critical tasks
        elapsed = time.time() - self._cycle_start
        if elapsed > self.max_cycle_duration:
            self.circuit_breaker_triggered = True
            logging.warning(
                f'tenant_id="{self.tenant_id}", task="{task_name}", status="skipped_budget", '
                f'elapsed={round(elapsed, 1)}s, budget={self.max_cycle_duration}s, tier="{tier}"'
            )
            self.tasks_skipped += 1
            return False

        # Check execution count against frequency
        state = self._state.get(task_name, {})
        execution_count = state.get("execution_count", 0)
        frequency = self._get_frequency(tier)

        # Run if count is divisible by frequency (i.e., every N-th cycle)
        should_execute = (execution_count % frequency) == 0

        if not should_execute:
            cycles_until_next = frequency - (execution_count % frequency)
            logging.info(
                f'tenant_id="{self.tenant_id}", task="{task_name}", status="skipped", '
                f'tier="{tier}", frequency={frequency}, cycle={execution_count}, next_run_in={cycles_until_next}_cycles'
            )
            self.tasks_skipped += 1

        return should_execute

    def record_execution(self, task_name, duration, status="success"):
        """Record that a task was executed and persist state to KV Store."""
        tier = self._get_tier(task_name)
        state = self._state.get(task_name, {"execution_count": 0})
        state["execution_count"] = state.get("execution_count", 0) + 1
        state["last_execution_time"] = time.time()
        state["last_execution_duration"] = duration
        state["last_execution_status"] = status
        self._state[task_name] = state

        # Track performance by tier
        self.tasks_executed += 1
        if tier == "every_cycle":
            self.tier1_run_time += duration
        elif tier == "periodic":
            self.tier2_run_time += duration
        elif tier == "offpeak":
            self.tier3_run_time += duration
        elif tier == "daily":
            self.tier4_run_time += duration

        # Persist to KV Store
        self._persist_state(task_name, state)

    def increment_skipped(self, task_name):
        """Increment the execution counter for a skipped task without recording execution time."""
        state = self._state.get(task_name, {"execution_count": 0})
        state["execution_count"] = state.get("execution_count", 0) + 1
        self._state[task_name] = state

        # Persist to KV Store
        self._persist_state(task_name, state)

    def _persist_state(self, task_name, state):
        """Persist a single task's state to KV Store."""
        try:
            collection = self.service.kvstore[self.collection_name]
            key = f"{self.tenant_id}:{task_name}"
            record = {
                "_key": key,
                "tenant_id": self.tenant_id,
                "task_name": task_name,
                "execution_count": state.get("execution_count", 0),
                "last_execution_time": state.get("last_execution_time", 0),
                "last_execution_duration": state.get("last_execution_duration", 0),
                "last_execution_status": state.get("last_execution_status", "unknown"),
                "mtime": time.time(),
            }
            # Use batch_save (upsert) with _key
            collection.data.update(key, json.dumps(record))
        except Exception:
            # If update fails (key doesn't exist), try insert
            try:
                collection.data.insert(json.dumps(record))
            except Exception as e:
                logging.warning(
                    f'tenant_id="{self.tenant_id}", task="{task_name}", '
                    f'failed to persist frequency state, exception="{str(e)}"'
                )

    def get_performance_summary(self, total_run_time):
        """Return a performance summary dict for logging."""
        return {
            "tenant_id": self.tenant_id,
            "total_run_time": round(total_run_time, 3),
            "tasks_executed": self.tasks_executed,
            "tasks_skipped": self.tasks_skipped,
            "tier1_run_time": round(self.tier1_run_time, 3),
            "tier2_run_time": round(self.tier2_run_time, 3),
            "tier3_run_time": round(self.tier3_run_time, 3),
            "tier4_run_time": round(self.tier4_run_time, 3),
            "circuit_breaker_triggered": self.circuit_breaker_triggered,
            "max_cycle_duration": self.max_cycle_duration,
            "periodic_frequency": self.periodic_frequency,
            "offpeak_frequency": self.offpeak_frequency,
            "daily_frequency": self.daily_frequency,
        }


@Configuration(distributed=False)
class HealthTracker(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    get_acl = Option(
        doc="""
        **Syntax:** **get_acl=****
        **Description:** Retrieve ACLs information for the tenant knowledge objects, disabled by default as this can generate more rest traffic and load.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    """
    Function to return a unique uuid which is used to trace performance run_time of each subtask.
    """

    def get_uuid(self):
        return str(uuid.uuid4())

    def register_component_summary_async(
        self, session_key, splunkd_uri, tenant_id, component
    ):
        try:
            summary_register_response = trackme_register_tenant_component_summary(
                session_key,
                splunkd_uri,
                tenant_id,
                component,
            )
            logging.debug(
                f'function="trackme_register_tenant_component_summary", response="{json.dumps(summary_register_response, indent=2)}"'
            )
        except Exception as e:
            logging.error(
                f'failed to register the component summary with exception="{str(e)}"'
            )

    def refresh_shadow_async(self, session_key, splunkd_uri, tenant_id, component):
        """
        Fire-and-forget call to the refresh_shadow admin endpoint.
        Runs in a daemon thread — the caller never waits for the result.
        The REST endpoint does the heavy lifting; we just need to dispatch the request.
        """
        try:
            url = f"{splunkd_uri}/services/trackme/v2/component/admin/refresh_shadow"
            header = {
                "Authorization": f"Splunk {session_key}",
                "Content-Type": "application/json",
            }
            body = {
                "tenant_id": tenant_id,
                "component": component,
                "requester": "health_tracker",
            }

            # Fire-and-forget: short connect timeout, generous read timeout
            # for the endpoint to complete its work
            response = requests.post(
                url,
                headers=header,
                json=body,
                verify=False,
                timeout=(5, 120),
            )

            if response.status_code in (200, 201, 204):
                logging.info(
                    f'tenant_id="{tenant_id}", component="{component}", '
                    f'refresh_shadow completed successfully'
                )
            else:
                logging.warning(
                    f'tenant_id="{tenant_id}", component="{component}", '
                    f'refresh_shadow returned status={response.status_code}, '
                    f'response="{response.text[:500]}"'
                )

        except Exception as e:
            logging.warning(
                f'tenant_id="{tenant_id}", component="{component}", '
                f'refresh_shadow failed: {e}'
            )

    def generate(self, **kwargs):

        # performance counter
        start = time.time()

        # set instance_id
        instance_id = self.get_uuid()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
        )
        log.setLevel(reqinfo["logging_level"])

        ###########################################################################
        # Circuit breaker: abort immediately if the tenant is disabled
        ###########################################################################

        try:
            tenant_record = self.service.kvstore["kv_trackme_virtual_tenants"].data.query(
                query=json.dumps({"tenant_id": self.tenant_id})
            )
            tenant_status = tenant_record[0].get("tenant_status", "unknown") if tenant_record else "unknown"
        except Exception as e:
            logging.warning(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                f"circuit breaker check failed to query tenant status: {e}, "
                f"proceeding with Health Tracker execution."
            )
            tenant_status = "enabled"  # fail-open: proceed if we cannot determine status

        if tenant_status != "enabled":
            logging.warning(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                f'tenant_status="{tenant_status}", '
                f"circuit breaker activated: tenant is not enabled, "
                f"the Health Tracker will not proceed. Exiting gracefully."
            )
            yield {
                "tenant_id": self.tenant_id,
                "instance_id": instance_id,
                "status": "aborted",
                "message": f"Circuit breaker: tenant is disabled (tenant_status={tenant_status}), Health Tracker skipped.",
            }
            return

        # Get configurable splunkd timeout
        splunkd_timeout = get_splunkd_timeout(reqinfo=reqinfo)

        # Build header and target URL
        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Splunk {self._metadata.searchinfo.session_key}"
        headers["Content-Type"] = "application/json"

        # Create a requests session for better performance
        session = requests.Session()
        session.headers.update(headers)

        # Initialize the task frequency manager for execution tiering
        task_freq_manager = TaskFrequencyManager(self.service, self.tenant_id, reqinfo)

        ###########################################################################
        # Verify the Virtual Tenant account with privileges escalation
        ###########################################################################
        
        task_start = time.time()
        task_instance_id = self.get_uuid()
        task_name = "check_vtenant_accounts"

        # start task
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
        )

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, verifying the vtenant account'
        )

        try:
            vtenant_account = trackme_vtenant_account(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
            )

        except Exception as e:

            # target
            url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/configuration/admin/maintain_vtenant_account"

            # proceed
            try:
                response = session.post(
                    url,
                    data=json.dumps(
                        {"tenant_id": self.tenant_id, "force_create_missing": True}
                    ),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 204):
                    logging.error(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, verify vtenant account has failed, was this account deleted by mistake? response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                    raise Exception(f'verify vtenant account has failed, was this account deleted by mistake? response.status_code="{response.status_code}", response.text="{response.text}"')
                else:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, account was verified successfully'
                    )
                    response_json = response.json()
                    
                    # fetch the vtenant account again
                    vtenant_account = trackme_vtenant_account(
                        self._metadata.searchinfo.session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id
                    )

            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, verify vtenant account has failed, exception="{str(e)}"'
                )
                raise Exception(f'verify vtenant account has failed, exception="{str(e)}"')

        # end task
        task_duration = round(time.time()-task_start, 3)
        task_freq_manager.record_execution(task_name, task_duration)
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
        )

        #
        #
        #

        # get the target index
        tenant_indexes = trackme_idx_for_tenant(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )

        # get global indexes
        global_indexes = {
            "trackme_summary_idx": reqinfo["trackme_conf"]["index_settings"][
                "trackme_summary_idx"
            ],
            "trackme_audit_idx": reqinfo["trackme_conf"]["index_settings"][
                "trackme_audit_idx"
            ],
            "trackme_metric_idx": reqinfo["trackme_conf"]["index_settings"][
                "trackme_metric_idx"
            ],
            "trackme_notable_idx": reqinfo["trackme_conf"]["index_settings"][
                "trackme_notable_idx"
            ],
        }
        logging.debug(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, global_indexes="{json.dumps(global_indexes, indent=2)}"'
        )

        # get trackme release
        trackme_version = trackme_get_version(
            self.service,
            log_context={
                "context_prefix": f'tenant_id="{self.tenant_id}", instance_id={instance_id}'
            }
        )

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, running trackme version="{trackme_version}"'
        )

        # set the schema_version_required
        schema_version_required = trackme_schema_format_version(trackme_version)

        # Get the session key
        session_key = self._metadata.searchinfo.session_key

        # Add the session_key to the reqinfo
        reqinfo["session_key"] = session_key

        # report name for logging purposes (health_tracker_report_name is a stable
        # alias that won't be shadowed by inner loops reusing `report_name`)
        report_name = f"trackme_health_tracker_tenant_{self.tenant_id}"
        health_tracker_report_name = report_name

        # Data collection
        collection_name = "kv_trackme_virtual_tenants"
        collection = self.service.kvstore[collection_name]

        # Get the tenant KVrecord
        query_string = {
            "tenant_id": self.tenant_id,
        }
        vtenant_record = collection.data.query(query=json.dumps(query_string))[0]

        #
        # check license state (with global cache — 24h TTL, invalidated on license mutation)
        #

        task_start = time.time()
        task_instance_id = self.get_uuid()
        task_name = "check_licensing"

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
        )

        license_cache_ttl = 86400  # 24 hours — admin endpoints invalidate on mutation; natural expiration is a known-date event with no operational urgency
        license_from_cache = False

        # Try to read from global cache first (shared across all tenants)
        cached_license = global_cache_get(self.service, "license_cache", ttl=license_cache_ttl)
        if cached_license and "license_is_valid" in cached_license:
            license_is_valid = cached_license.get("license_is_valid")
            license_subscription_class = cached_license.get("license_subscription_class")
            license_active_tenants = cached_license.get("license_active_tenants")
            license_active_tenants_list = cached_license.get("license_active_tenants_list")
            license_from_cache = True
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                f'license result loaded from global cache, '
                f'license_is_valid="{license_is_valid}", license_subscription_class="{license_subscription_class}"'
            )

        # If not from cache, do the live check and update global cache
        if not license_from_cache:
            try:
                check_license = trackme_check_license(
                    reqinfo["server_rest_uri"], session_key
                )
                license_is_valid = check_license.get("license_is_valid")
                license_subscription_class = check_license.get("license_subscription_class")
                license_active_tenants = check_license.get("license_active_tenants")
                license_active_tenants_list = check_license.get(
                    "license_active_tenants_list"
                )
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, function check_license called (live), license_is_valid="{license_is_valid}", license_subscription_class="{license_subscription_class}", license_active_tenants="{license_active_tenants}", license_active_tenants_list="{license_active_tenants_list}"'
                )

                # Update global cache so other tenants benefit
                global_cache_set(
                    self.service,
                    "license_cache",
                    {
                        "license_is_valid": license_is_valid,
                        "license_subscription_class": license_subscription_class,
                        "license_active_tenants": license_active_tenants,
                        "license_active_tenants_list": license_active_tenants_list,
                    },
                    tenant_id=self.tenant_id,
                )

            except Exception as e:
                license_is_valid = 2
                license_subscription_class = "unlimited"
                logging.error(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, function check_license has failed, exception="{str(e)}"'
                )

        task_duration = round(time.time()-task_start, 3)
        task_freq_manager.record_execution(task_name, task_duration)
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", cached={license_from_cache}, task has terminated.'
        )

        #
        # check tenants indexes settings:
        # - retrieve the configured indexes for the tenant
        # - retrieve via a REST call to splunkd the list of declared indexes on the search head
        # - if any of the tenant defines indexes are not declared on the search head, update the tenant indexes settings to fallback to TrackMe default indexes and log the issue
        #

        task_name = "check_tenants_indexes_settings"
        if task_freq_manager.should_run(task_name):
            task_start = time.time()
            task_instance_id = self.get_uuid()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            def get_indexes_by_datatype(datatype=None):
                """Retrieve indexes from the search head by datatype.

                Args:
                    datatype (str, optional): The datatype to filter by (e.g. 'metric').
                        If None, retrieves all indexes.

                Returns:
                    dict: Dictionary of index names and their datatypes
                """
                url = f"{reqinfo['server_rest_uri']}/services/data/indexes?output_mode=json&count=0"
                if datatype:
                    url += f"&datatype={datatype}"

                try:
                    response = requests.get(url, headers=headers, verify=False, timeout=600)
                    if response.status_code == 200:
                        indexes_raw = response.json().get("entry", [])
                        for index in indexes_raw:
                            if isinstance(index, dict):
                                index_name = index.get("name")
                                if index_name:
                                    declared_indexes_dict[index_name] = {
                                        "datatype": index.get("content", {}).get(
                                            "datatype", ""
                                        )
                                    }
                        logging.debug(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, declared_indexes="{json.dumps(declared_indexes_dict, indent=2)}"'
                        )
                    else:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to retrieve indexes list, status code: {response.status_code}'
                        )
                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, could not retrieve the list of declared indexes on the search head, exception="{str(e)}"'
                    )

            def get_fallback_indexes(index_category=None):
                """Retrieve fallback indexes from the search head.

                Returns:
                    dict: Dictionary of fallback indexes
                """

                fallback_indexes = {
                    "trackme_summary_idx": "trackme_summary",
                    "trackme_audit_idx": "trackme_audit",
                    "trackme_metric_idx": "trackme_metrics",
                    "trackme_notable_idx": "trackme_notable",
                }

                if index_category:
                    return fallback_indexes.get(index_category, None)
                else:
                    return fallback_indexes

            # get the tenant indexes settings
            tenant_indexes_settings = trackme_idx_for_tenant(
                session_key,
                reqinfo["server_rest_uri"],
                self.tenant_id,
            )
            logging.debug(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_indexes_settings="{json.dumps(tenant_indexes_settings, indent=2)}"'
            )

            """ Example of tenant_indexes_settings:
            {
                "trackme_summary_idx": "trackme_summary",
                "trackme_audit_idx": "trackme_audit",
                "trackme_metric_idx": "trackme_metrics",
                "trackme_notable_idx": "trackme_notable"
            }
            """

            # check if tenant_indexes_settings is set to global
            tenant_indexes_uses_global_indexes = False

            if tenant_indexes_settings == "global":
                tenant_indexes_settings = global_indexes
                tenant_indexes_uses_global_indexes = True
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_indexes_settings set to global, will check the search head for declared indexes.'
                )

            # process
            declared_indexes_dict = {}

            # Get all indexes (events)
            get_indexes_by_datatype()

            # Get metrics indexes
            get_indexes_by_datatype(datatype="metric")

            # only proceed if we have declared indexes
            if not declared_indexes_dict:
                logging.warning(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, no declared indexes found, skipping tenant indexes settings check.'
                )
            else:

                # for each index in the tenant indexes settings, check if it is declared on the search head
                # we also want to check for trackme_metrics_idx that the datatype is set to "metric"
                # if not, we will force update the tenant indexes settings to fallback to TrackMe default indexes

                invalid_indexes_settings_detected = False

                # process the tenant indexes settings
                for index_category, index_value in tenant_indexes_settings.items():
                    if not isinstance(index_value, str):
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, index_category="{index_category}" has invalid index value type: {type(index_value)}'
                        )
                        invalid_indexes_settings_detected = True
                        # update the tenant indexes settings for the current index_category
                        tenant_indexes_settings[index_category] = get_fallback_indexes(
                            index_category
                        )
                        continue

                    if index_value not in declared_indexes_dict:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, index_category="{index_category}", index_value="{index_value}" is not declared on the search head, this is an invalid configuration, we will force update the tenant indexes settings to fallback to TrackMe default indexes. Please ensure to define indexes in the search head tier before attempting to configure your tenant indexes settings.'
                        )
                        invalid_indexes_settings_detected = True
                        # update the tenant indexes settings for the current index_category
                        tenant_indexes_settings[index_category] = get_fallback_indexes(
                            index_category
                        )
                        continue

                    elif index_category == "trackme_metrics_idx":
                        index_info = declared_indexes_dict.get(index_value, {})
                        if index_info.get("datatype") != "metric":
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, index_category="{index_category}", index_value="{index_value}" is not configured as a metric index, this is an invalid configuration, we will force update the tenant indexes settings to fallback to TrackMe default indexes.'
                            )
                            invalid_indexes_settings_detected = True
                            # update the tenant indexes settings for the current index_category
                            tenant_indexes_settings[index_category] = get_fallback_indexes(
                                index_category
                            )
                            continue

                if not invalid_indexes_settings_detected:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, no invalid indexes settings detected, nothing to do.'
                    )
                else:
                    # If we were using global indexes and found issues, we need to fallback to default indexes
                    if tenant_indexes_uses_global_indexes:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, issues detected with global indexes, falling back to default indexes.'
                        )
                        tenant_indexes_settings = get_fallback_indexes()

                    # fix the tenant indexes settings
                    vtenant_record["tenant_idx_settings"] = json.dumps(
                        tenant_indexes_settings, indent=2
                    )
                    try:
                        self.service.kvstore["kv_trackme_virtual_tenants"].data.update(
                            str(vtenant_record["_key"]), json.dumps(vtenant_record)
                        )
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, vtenant_record updated successfully, new tenant_idx_settings="{json.dumps(tenant_indexes_settings, indent=2)}"'
                        )
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, Failed to update vtenant_record, exception: {str(e)}'
                        )

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        ############################################################################
        # Configuration Guardian: tenant_owner capabilities check
        # - Runs in TIER_4 (daily cadence) because capability assignments rarely change
        # - Skipped when tenant_owner is missing or "nobody"
        # - Self-healing: clears the alert when capabilities are granted
        ############################################################################

        # Resolve the audit index name once for every Guardian check below so
        # state transitions write a uniform audit trail to `trackme_audit`.
        guardian_audit_idx = (
            reqinfo.get("trackme_conf", {})
            .get("index_settings", {})
            .get("trackme_audit_idx", "trackme_audit")
        )

        task_name = "check_guardian:tenant_owner_capabilities"
        if task_freq_manager.should_run(task_name):
            task_start = time.time()
            task_instance_id = self.get_uuid()

            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                from trackme_libs_guardian import check_tenant_owner_capabilities

                guardian_outcome = check_tenant_owner_capabilities(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.service,
                    vtenant_record,
                    audit_index_name=guardian_audit_idx,
                )
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", '
                    f'task_instance_id={task_instance_id}, outcome="{json.dumps(guardian_outcome)}"'
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", '
                    f'task_instance_id={task_instance_id}, check failed, exception="{str(e)}"'
                )

            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        # Guardian: detect drift between the AI Feed Lifecycle Advisor and
        # the legacy mechanical Adaptive Delay (+ variable_delay_auto_review).
        # The UCC save-time hook
        # ``trackme_rh_vtenants_handler.CustomRestHandlerVtenants`` is the
        # primary control — it auto-disables the legacy flags whenever the
        # AI advisor is turned on for DSM/DHM. This check is the safety net
        # for drift caused by direct KV pokes, downgrade-then-upgrade
        # scenarios, or any API path that bypasses the hook.
        task_name = "check_guardian:ai_feed_lifecycle_delay_conflict"
        if task_freq_manager.should_run(task_name):
            task_start = time.time()
            task_instance_id = self.get_uuid()

            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                from trackme_libs_guardian import (
                    check_ai_feed_lifecycle_delay_conflict,
                )

                guardian_outcome = check_ai_feed_lifecycle_delay_conflict(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.service,
                    vtenant_record,
                    audit_index_name=guardian_audit_idx,
                )
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", '
                    f'task_instance_id={task_instance_id}, outcome="{json.dumps(guardian_outcome)}"'
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", '
                    f'task_instance_id={task_instance_id}, check failed, exception="{str(e)}"'
                )

            task_duration = round(time.time() - task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        ############################################################################
        # Threshold intent-lock reconciliation (DSM + DHM)
        # - TIER_3 (~6h) safety net behind the real-time source gates. Verifies
        #   every operator-pinned entity against the intent ledger and restores
        #   any drift, leaving an audit trace + a Configuration Guardian alert.
        # - Cost scales with the pinned subset (whole small ledger read +
        #   batch_find of only the pinned live entities), never the full entity
        #   collection — safe at 100k+ entities.
        # - Gated on the per-tenant master toggle (vtenant_account, default on).
        ############################################################################
        task_name = "reconcile_threshold_intent"
        _ti_should_run = task_freq_manager.should_run(task_name)
        # The ledger this task reconciles is created by schema migration 2401
        # (Concern D), which runs LATER in this same generate() on a fresh
        # upgrade. Gate on the tenant schema so the first post-upgrade cycle
        # skips WITHOUT advancing the frequency clock (it runs next cycle once
        # schema catches up). No pinned entities can exist pre-2401, so nothing
        # is at risk meanwhile.
        try:
            _ti_schema_ok = int(vtenant_record.get("schema_version") or 0) >= 2401
        except (TypeError, ValueError):
            _ti_schema_ok = False
        if _ti_should_run and _ti_schema_ok:
            task_start = time.time()
            task_instance_id = self.get_uuid()

            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                from trackme_libs_threshold_intent import (
                    reconcile_threshold_intent,
                    threshold_lock_enabled,
                )

                if not threshold_lock_enabled(vtenant_account):
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", '
                        f'task_instance_id={task_instance_id}, threshold intent lock disabled for tenant, skipping.'
                    )
                else:
                    components = []
                    if str(
                        vtenant_record.get("tenant_dsm_enabled")
                    ).strip().lower() in ("1", "true"):
                        components.append("dsm")
                    if str(
                        vtenant_record.get("tenant_dhm_enabled")
                    ).strip().lower() in ("1", "true"):
                        components.append("dhm")

                    for component in components:
                        reconcile_summary = reconcile_threshold_intent(
                            self.service,
                            self.tenant_id,
                            component,
                            logger=logging,
                            session_key=session_key,
                            splunkd_uri=self._metadata.searchinfo.splunkd_uri,
                        )
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", '
                            f'task_instance_id={task_instance_id}, component="{component}", '
                            f'outcome="{json.dumps(reconcile_summary)}"'
                        )

                        # Surface drift in the Configuration Guardian so every
                        # silent overwrite that slipped past the source gates
                        # leaves a visible, audited, AI-explainable trace.
                        try:
                            from trackme_libs_guardian import (
                                check_threshold_intent_drift,
                            )

                            check_threshold_intent_drift(
                                session_key,
                                self._metadata.searchinfo.splunkd_uri,
                                self.service,
                                vtenant_record,
                                component,
                                reconcile_summary,
                                audit_index_name=guardian_audit_idx,
                            )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", '
                                f'task_instance_id={task_instance_id}, component="{component}", guardian drift check failed, exception="{str(e)}"'
                            )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", '
                    f'task_instance_id={task_instance_id}, reconciliation failed, exception="{str(e)}"'
                )

            task_duration = round(time.time() - task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        elif _ti_should_run:
            # Due to run, but the tenant schema predates migration 2401 — the
            # threshold-intent ledger isn't provisioned yet. LOG ONLY: do not
            # touch the frequency counter. increment_skipped() advances
            # execution_count exactly like record_execution() (the modulo cadence
            # increments every cycle), so calling it here would push the next run
            # out by a full Tier-3 window. Leaving the counter untouched keeps
            # should_run() True so this re-evaluates on the very next 5-min cycle
            # — and migration 2401 runs later in THIS same generate(), so it
            # normally self-corrects within one cycle.
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", '
                f'pre-2401 schema (threshold-intent ledger not provisioned yet), log-only skip (frequency counter untouched, will retry next cycle).'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        # NOTE: `check_guardian:assigned_index_exists` used to live here as a
        # per-tenant TIER_4 task. It has been moved to
        # `trackmegeneralhealthmanager.py` so that a single REST call to
        # `/services/data/indexes` (the SH-wide index catalogue is immutable
        # across the run) serves every tenant, rather than N identical calls
        # per day — see `run_checks` + `CHECK_REGISTRY.pre_run` for the
        # fan-out pattern.

        ##################################################################################
        # Global system verifications: verify that the relevant scheduled jobs are enabled
        ##################################################################################

        # These jobs are not tenant specifics, however we use the health tracker to ensure that
        # these are effectively enabled when at least one tenant has been created and is active

        task_start = time.time()
        task_instance_id = self.get_uuid()
        task_name = "check_global_trackers_enablement"

        # start task
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
        )

        savedsearch_names = [
            "trackme_ack_expiration_tracker",
            "trackme_maintenance_mode_tracker",
            "trackme_backup_scheduler",
            "trackme_general_health_manager",
        ]

        for savedsearch_name in savedsearch_names:
            # check ack expiration tracker
            update_properties_required = False

            try:
                mysavedsearch = self.service.saved_searches[savedsearch_name]
                current_disabled = int(mysavedsearch["disabled"])
                logging.debug(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, global config check, verifying savedsearch="{mysavedsearch.name}", disabled="{current_disabled}"'
                )

                if current_disabled == 1:
                    update_properties_required = True

            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, global configuration verification, could not retrieve the status for {savedsearch_name}'
                )

            if update_properties_required:
                try:
                    action = trackme_report_update_enablement(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        savedsearch_name,
                        "enable",
                    )
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, global config check, enabling savedsearch="{savedsearch_name}", result="{action}"'
                    )

                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, global config check, an exception was encountered while trying to enable savedsearch="{savedsearch_name}", exception="{str(e)}"'
                    )

        # end task
        task_duration = round(time.time()-task_start, 3)
        task_freq_manager.record_execution(task_name, task_duration)
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
        )

        ##################################################################################
        # Optimize: enable or disable the schedule for utilities depending on the tenant
        # settings, and conditions
        ##################################################################################

        task_name = "optimize_tenant_scheduled_reports"
        if task_freq_manager.should_run(task_name):
            task_start = time.time()
            task_instance_id = self.get_uuid()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # Define the valid components
            valid_components = {"dsm", "dhm", "mhm", "flx", "wlk", "fqm"}

            def manage_savedsearch_schedule(
                savedsearch_names, feature_enabled, feature_name
            ):
                """
                Helper function to manage saved search scheduling based on feature enablement.

                Args:
                    savedsearch_names: List of saved search names to manage
                    feature_enabled: Boolean indicating if the feature should be enabled
                    feature_name: String name of the feature for logging purposes
                """
                for savedsearch_name in savedsearch_names:
                    # get the status of the savedsearch
                    savedsearch_properties, savedsearch_acl = (
                        trackme_manage_report_schedule(
                            logging,
                            session_key,
                            self._metadata.searchinfo.splunkd_uri,
                            self.tenant_id,
                            savedsearch_name,
                            action="status",
                        )
                    )

                    # log
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", savedsearch_properties="{json.dumps(savedsearch_properties, indent=2)}", savedsearch_acl="{json.dumps(savedsearch_acl, indent=2)}"'
                    )

                    # get the is_scheduled status
                    is_scheduled = int(savedsearch_properties.get("is_scheduled", 0))

                    # avoid failing to schedule the savedsearch if any of the following is missing or equal to None:
                    # dispatch.earliest_time
                    # dispatch.latest_time
                    # cron_schedule
                    # schedule_window

                    # outliers_mltrain:
                    # "cron_schedule": "*/60 * * * *",
                    # "dispatch.earliest_time": "-5m",
                    # "dispatch.latest_time": "now",
                    # "schedule_window": "5",

                    # outliers_mlmonitor:
                    # "cron_schedule": "*/20 * * * *",
                    # "dispatch.earliest_time": "-5m",
                    # "dispatch.latest_time": "now",
                    # "schedule_window": "5",

                    # data_sampling:
                    # "cron_schedule": "*/20 * * * *",
                    # "dispatch.earliest_time": "-24h",
                    # "dispatch.latest_time": "-4h",
                    # "schedule_window": "5",

                    # adaptive_delay:
                    # "cron_schedule": "*/20 * * * *",
                    # "dispatch.earliest_time": "-5m",
                    # "dispatch.latest_time": "now",
                    # "schedule_window": "5",

                    # delayed_inspector:
                    # "cron_schedule": "*/20 * * * *",
                    # "dispatch.earliest_time": "-5m",
                    # "dispatch.latest_time": "now",
                    # "schedule_window": "5",

                    # if any of these parameters is missing in the savedsearch properties, we need to add them
                    if "dispatch.earliest_time" not in savedsearch_properties or savedsearch_properties.get("dispatch.earliest_time") in (None, 'None', ''):
                        if "outliers_mltrain" in savedsearch_name:
                            savedsearch_properties["dispatch.earliest_time"] = "-5m"
                        elif "outliers_mlmonitor" in savedsearch_name:
                            savedsearch_properties["dispatch.earliest_time"] = "-5m"
                        elif "data_sampling" in savedsearch_name:
                            savedsearch_properties["dispatch.earliest_time"] = "-24h"
                        elif "adaptive_delay" in savedsearch_name:
                            savedsearch_properties["dispatch.earliest_time"] = "-5m"
                        elif "delayed_entities_inspector" in savedsearch_name:
                            savedsearch_properties["dispatch.earliest_time"] = "-5m"
                        else:
                            savedsearch_properties["dispatch.earliest_time"] = "-5m"

                    if "dispatch.latest_time" not in savedsearch_properties or savedsearch_properties.get("dispatch.latest_time") in (None, 'None', ''):
                        if "outliers_mltrain" in savedsearch_name:
                            savedsearch_properties["dispatch.latest_time"] = "now"
                        elif "outliers_mlmonitor" in savedsearch_name:
                            savedsearch_properties["dispatch.latest_time"] = "now"
                        elif "data_sampling" in savedsearch_name:
                            savedsearch_properties["dispatch.latest_time"] = "-4h"
                        elif "adaptive_delay" in savedsearch_name:
                            savedsearch_properties["dispatch.latest_time"] = "now"
                        elif "delayed_entities_inspector" in savedsearch_name:
                            savedsearch_properties["dispatch.latest_time"] = "now"
                        else:
                            savedsearch_properties["dispatch.latest_time"] = "now"

                    if "cron_schedule" not in savedsearch_properties or savedsearch_properties.get("cron_schedule") in (None, 'None', ''):
                        if "outliers_mltrain" in savedsearch_name:
                            savedsearch_properties["cron_schedule"] = "0 22-23,0-6 * * *"
                        elif "outliers_mlmonitor" in savedsearch_name:
                            savedsearch_properties["cron_schedule"] = "*/20 * * * *"
                        elif "outliers_mladvisor" in savedsearch_name:
                            savedsearch_properties["cron_schedule"] = "0 2-5 * * *"
                        elif "data_sampling" in savedsearch_name:
                            savedsearch_properties["cron_schedule"] = "*/20 22-23,0-6 * * *"
                        elif "adaptive_delay" in savedsearch_name:
                            savedsearch_properties["cron_schedule"] = "*/20 * * * *"
                        elif "delayed_entities_inspector" in savedsearch_name:
                            savedsearch_properties["cron_schedule"] = "*/20 * * * *"
                        elif "feed_lifecycle_advisor" in savedsearch_name:
                            savedsearch_properties["cron_schedule"] = "0 5-8 * * *"
                        elif "flx_threshold_advisor" in savedsearch_name:
                            savedsearch_properties["cron_schedule"] = "0 9-12 * * *"
                        elif "component_health_advisor" in savedsearch_name:
                            savedsearch_properties["cron_schedule"] = "0 9-12 * * *"
                        elif "fqm_advisor" in savedsearch_name:
                            savedsearch_properties["cron_schedule"] = "0 13-16 * * *"
                        else:
                            savedsearch_properties["cron_schedule"] = "*/5 * * * *"

                    if "schedule_window" not in savedsearch_properties or savedsearch_properties.get("schedule_window") in (None, 'None', ''):
                        savedsearch_properties["schedule_window"] = "5"

                    # act
                    if is_scheduled == 1 and feature_enabled == False:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", savedsearch="{savedsearch_name}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", disabling savedsearch.'
                        )
                        try:
                            savedsearch_properties, savedsearch_acl = (
                                trackme_manage_report_schedule(
                                    logging,
                                    session_key,
                                    self._metadata.searchinfo.splunkd_uri,
                                    self.tenant_id,
                                    savedsearch_name,
                                    input_report_properties=savedsearch_properties,
                                    action="disable",
                                )
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", savedsearch="{savedsearch_name}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", savedsearch updated successfully, properties="{json.dumps(savedsearch_properties, indent=2)}"'
                            )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", savedsearch="{savedsearch_name}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", an exception was encountered while trying to update savedsearch, exception="{str(e)}"'
                            )

                    elif is_scheduled == 0 and feature_enabled == True:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", savedsearch="{savedsearch_name}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", enabling savedsearch.'
                        )
                        try:
                            savedsearch_properties, savedsearch_acl = (
                                trackme_manage_report_schedule(
                                    logging,
                                    session_key,
                                    self._metadata.searchinfo.splunkd_uri,
                                    self.tenant_id,
                                    savedsearch_name,
                                    input_report_properties=savedsearch_properties,
                                    action="enable",
                                )
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", savedsearch="{savedsearch_name}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", savedsearch updated successfully, properties="{json.dumps(savedsearch_properties, indent=2)}"'
                            )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", savedsearch="{savedsearch_name}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", an exception was encountered while trying to update savedsearch, exception="{str(e)}"'
                            )

                    else:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", savedsearch="{savedsearch_name}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", nothing to do.'
                        )

            # Process except for replica tenants
            try:
                tenant_replica = int(vtenant_record.get("tenant_replica", 0))
            except Exception as e:
                tenant_replica = 0

            if tenant_replica == 1:
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, detected replica tenant by name pattern, setting tenant_replica=1'
                )

            # Log replica tenant status for debugging
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_replica="{tenant_replica}", will_process="{tenant_replica == 0}"'
            )

            if tenant_replica == 0: # only process non-replica tenants (value: 0)

                #
                # AI features global kill switch
                #
                # ``trackme_settings.conf [trackme_general] enable_ai_assistant``
                # is the deployment-wide admin kill switch for every AI
                # surface. When set to 0:
                #   - the AI Assistant button is hidden in the UI,
                #   - every AI Advisor POST endpoint returns 403, and
                #   - every automated advisor batch helper short-circuits
                #     with an "AI features are disabled by the administrator"
                #     event.
                # The tracker must mirror that contract by un-scheduling
                # the advisor saved-searches so they stop firing no-op
                # ticks against the disabled provider stack.
                # Defaults to ``"1"`` (enabled) for forward-compat with
                # pre-2.3.x installs where the setting did not exist.
                #
                try:
                    ai_enabled_globally = True
                    trackme_settings_conf = self.service.confs["trackme_settings"]
                    for stanza in trackme_settings_conf:
                        if stanza.name == "trackme_general":
                            if stanza.content.get("enable_ai_assistant", "1") == "0":
                                ai_enabled_globally = False
                            break
                except Exception as ai_global_exc:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                        f'task="{task_name}", task_instance_id={task_instance_id}, '
                        f'failed to read enable_ai_assistant from trackme_settings, '
                        f'falling back to ai_enabled_globally=True, '
                        f'exception="{str(ai_global_exc)}"'
                    )
                    ai_enabled_globally = True  # conservative: keep working

                #
                # Deployment-wide AI provider presence
                #
                # Every AI Advisor (ML Advisor + the four Components Advisors)
                # is gated on THREE signals:
                #   1. The global ``enable_ai_assistant`` admin toggle is on
                #      (see the kill-switch block above).
                #   2. The deployment has at least one usable LLM provider
                #      (any enabled stanza in trackme_ai_provider.conf that
                #      passes list_ai_providers' validity check).
                #   3. The tenant has opted into the specific advisor via
                #      its vtenant_account flag.
                #
                # Without (1) or (2) every advisor invocation fails
                # immediately at the LLM call — there's no point scheduling
                # the report. Mirrors the same pattern as priority/ML-outliers
                # gating: un-schedule when the upstream dependency is absent,
                # and re-schedule automatically once the admin satisfies it.
                #
                # Computed once per tenant — both signals are deployment-wide
                # so their values are identical for every component iteration
                # below.
                #
                try:
                    ai_providers_count = len(list_ai_providers(self.service))
                except Exception as ai_providers_exc:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                        f'task="{task_name}", task_instance_id={task_instance_id}, '
                        f'failed to list AI providers, falling back to '
                        f'providers_configured=False, '
                        f'exception="{str(ai_providers_exc)}"'
                    )
                    ai_providers_count = 0
                providers_configured = ai_providers_count >= 1
                # Compose the deployment-wide signal once. Both the ML Advisor
                # and Components Advisor gates below AND-in this value with
                # their per-tenant flag, so flipping ``enable_ai_assistant=0``
                # or removing the last provider drives every advisor
                # saved-search to ``is_scheduled=0`` on the next cycle, and
                # restoring either flips them back on automatically.
                ai_infra_ready = ai_enabled_globally and providers_configured
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                    f'task="{task_name}", task_instance_id={task_instance_id}, '
                    f'ai_enabled_globally="{ai_enabled_globally}", '
                    f'ai_providers_count="{ai_providers_count}", '
                    f'providers_configured="{providers_configured}", '
                    f'ai_infra_ready="{ai_infra_ready}"'
                )

                for valid_component in valid_components:
                    valid_component_is_enabled = int(
                        vtenant_record.get(f"tenant_{valid_component}_enabled", 0)
                    )

                    if valid_component_is_enabled == 1:

                        # only for dsm/dhm/flx/wlk
                        if valid_component in ("dsm", "dhm", "flx", "wlk", "fqm"):

                            #
                            # ML Outliers
                            #

                            try:

                                savedsearch_names = [
                                    f"trackme_{valid_component}_outliers_mltrain_tracker_tenant_{self.tenant_id}",
                                    f"trackme_{valid_component}_outliers_mlmonitor_tracker_tenant_{self.tenant_id}",
                                ]

                                # Default to True
                                feature_enabled = True

                                # Construct the key dynamically
                                key = f"mloutliers_{valid_component}"

                                # Check if the component is valid and handle exceptions
                                if valid_component in valid_components:
                                    try:
                                        feature_enablement = int(vtenant_account.get(key, 1))
                                        if feature_enablement == 0:
                                            feature_enabled = False
                                    except (ValueError, TypeError):
                                        feature_enabled = True
                                else:
                                    logging.error(
                                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}" is not valid, valid components are {valid_components}'
                                    )

                                manage_savedsearch_schedule(
                                    savedsearch_names, feature_enabled, "outliers"
                                )

                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                                )

                        #
                        # Sampling (dsm only)
                        #

                        try:

                            if valid_component == "dsm":

                                savedsearch_names = [
                                    f"trackme_dsm_data_sampling_tracker_tenant_{self.tenant_id}",
                                ]

                                # Default to True
                                feature_enabled = True

                                # Construct the key dynamically
                                key = f"sampling"

                                # Check if the component is valid and handle exceptions
                                if valid_component in valid_components:
                                    try:
                                        feature_enablement = int(vtenant_account.get(key, 1))
                                        if feature_enablement == 0:
                                            feature_enabled = False
                                    except (ValueError, TypeError):
                                        feature_enabled = True
                                else:
                                    logging.error(
                                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}" is not valid, valid components are {valid_components}'
                                    )

                                manage_savedsearch_schedule(
                                    savedsearch_names, feature_enabled, "sampling"
                                )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        #
                        # Adaptive delay (dsm only)
                        #

                        try:

                            if valid_component == "dsm":

                                savedsearch_names = [
                                    f"trackme_dsm_adaptive_delay_tracker_tenant_{self.tenant_id}",
                                ]

                                # Default to True
                                feature_enabled = True

                                # Construct the key dynamically
                                key = f"adaptive_delay"

                                # Check if the component is valid and handle exceptions
                                if valid_component in valid_components:
                                    try:
                                        feature_enablement = int(vtenant_account.get(key, 1))
                                        if feature_enablement == 0:
                                            feature_enabled = False
                                    except (ValueError, TypeError):
                                        feature_enabled = True
                                else:
                                    logging.error(
                                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}" is not valid, valid components are {valid_components}'
                                    )

                                manage_savedsearch_schedule(
                                    savedsearch_names, feature_enabled, "adaptive_delay"
                                )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        #
                        # Delayed inspector (dsm/dhm only)
                        #

                        try:

                            if valid_component in ("dsm", "dhm"):

                                savedsearch_names = [
                                    f"trackme_{valid_component}_delayed_entities_inspector_tracker_tenant_{self.tenant_id}",
                                ]

                                # Default to True
                                feature_enabled = True

                                # Construct the key dynamically
                                keys = [
                                    "splk_feeds_delayed_inspector_24hours_range_min_sec",
                                    "splk_feeds_delayed_inspector_7days_range_min_sec",
                                    "splk_feeds_delayed_inspector_until_disabled_range_min_sec",
                                ]

                                # Check if the component is valid and handle exceptions (all keys must be set to 0 for the feature to be disabled)
                                if valid_component in valid_components:
                                    try:
                                        feature_enabled = True  # Default to enabled
                                        for key in keys:
                                            feature_enablement = int(
                                                vtenant_account.get(key, 1)
                                            )
                                            if feature_enablement != 0:
                                                # If any key is not 0, the feature should be enabled
                                                feature_enabled = True
                                                break
                                        else:
                                            # If we get here, all keys were 0, so disable the feature
                                            feature_enabled = False
                                    except (ValueError, TypeError):
                                        feature_enabled = True
                                else:
                                    logging.error(
                                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}" is not valid, valid components are {valid_components}'
                                    )

                                manage_savedsearch_schedule(
                                    savedsearch_names, feature_enabled, "delayed_inspector"
                                )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        #
                        # ML Advisor — automated model inspection (dsm/dhm/flx only)
                        #
                        # The trackme_<c>_outliers_mladvisor_tracker runs nightly
                        # (`0 2-5 * * *`) and invokes the LLM-backed mladvisor
                        # helper.  It must be un-scheduled when ANY of:
                        #   - the global ``enable_ai_assistant`` toggle is 0
                        #     (admin kill switch), OR
                        #   - the deployment has no AI provider configured
                        #     (providers_configured=False) — no LLM means
                        #     the helper would fail on every tick, OR
                        #   - the tenant has ai_mladvisor_enabled=0 (the
                        #     collections_data default).
                        # All three conditions must be true to keep the
                        # tracker scheduled — same triple-gate pattern as
                        # the Components Advisor block below. Mirrors how
                        # the priority tracker reacts to the absence of
                        # policies.
                        #

                        try:

                            if valid_component in ("dsm", "dhm", "flx"):

                                savedsearch_names = [
                                    f"trackme_{valid_component}_outliers_mladvisor_tracker_tenant_{self.tenant_id}",
                                ]

                                # Default to False — ai_mladvisor_enabled defaults to 0 in collections_data.py
                                # AND ai_infra_ready defaults to False when AI is globally disabled
                                # or no LLM is configured.
                                feature_enabled = False

                                try:
                                    if (
                                        int(vtenant_account.get("ai_mladvisor_enabled", 0)) == 1
                                        and ai_infra_ready
                                    ):
                                        feature_enabled = True
                                except (ValueError, TypeError):
                                    feature_enabled = False

                                for savedsearch_name in savedsearch_names:
                                    try:
                                        manage_savedsearch_schedule(
                                            [savedsearch_name],
                                            feature_enabled,
                                            "ml_advisor",
                                        )
                                    except Exception as schedule_exc:
                                        logging.error(
                                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                                            f'task="{task_name}", task_instance_id={task_instance_id}, '
                                            f'component="{valid_component}", savedsearch="{savedsearch_name}", '
                                            f'schedule update failed, skipping this savedsearch, '
                                            f'exception="{str(schedule_exc)}"'
                                        )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        #
                        # Components AI Advisor scheduling gate (unified)
                        #
                        # All four component advisors (Feed Lifecycle, FLX
                        # Threshold, FQM, Component Health for WLK/MHM) share
                        # the same enablement contract:
                        #
                        #   feature_enabled = (
                        #       ai_infra_ready
                        #       AND ai_components_advisor_enabled == 1
                        #       AND <component> in ai_components_advisor_list
                        #   )
                        #
                        # The pattern below computes this once per outer
                        # iteration and reuses it across the four advisor
                        # blocks — replacing the previous five separate flags
                        # (ai_feedlifecycle_enabled / ai_flxthreshold_enabled /
                        #  ai_wlkadvisor_enabled / ai_fqmadvisor_enabled /
                        #  ai_mhmadvisor_enabled).
                        #
                        # ``ai_infra_ready`` is the deployment-wide kill
                        # switch composed of (enable_ai_assistant AND
                        # providers_configured). When either is False the
                        # four advisor saved-searches stay un-scheduled
                        # regardless of the per-tenant flags, and re-schedule
                        # themselves automatically once the admin restores
                        # both.
                        #

                        try:
                            ai_components_advisor_enabled_val = int(
                                vtenant_account.get("ai_components_advisor_enabled", 0)
                            )
                        except (ValueError, TypeError):
                            ai_components_advisor_enabled_val = 0
                        components_list_raw = str(
                            vtenant_account.get("ai_components_advisor_list", "dsm,dhm,mhm,flx,fqm,wlk")
                        )
                        components_list_set = {
                            c.strip().lower() for c in components_list_raw.split(",") if c.strip()
                        }
                        components_advisor_active = (
                            ai_infra_ready
                            and ai_components_advisor_enabled_val == 1
                            and valid_component.lower() in components_list_set
                        )

                        # Feed Lifecycle Advisor (DSM/DHM)
                        try:
                            if valid_component in ("dsm", "dhm"):
                                savedsearch_names = [
                                    f"trackme_{valid_component}_feed_lifecycle_advisor_tracker_tenant_{self.tenant_id}",
                                ]
                                manage_savedsearch_schedule(
                                    savedsearch_names, components_advisor_active, "feed_lifecycle_advisor"
                                )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        # FLX Threshold Advisor (FLX)
                        try:
                            if valid_component == "flx":
                                savedsearch_names = [
                                    f"trackme_flx_threshold_advisor_tracker_tenant_{self.tenant_id}",
                                ]
                                manage_savedsearch_schedule(
                                    savedsearch_names, components_advisor_active, "flx_threshold_advisor"
                                )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        # Component Health Advisor (WLK, MHM)
                        try:
                            if valid_component in ("wlk", "mhm"):
                                savedsearch_names = [
                                    f"trackme_{valid_component}_component_health_advisor_tracker_tenant_{self.tenant_id}",
                                ]
                                manage_savedsearch_schedule(
                                    savedsearch_names, components_advisor_active, "component_health_advisor"
                                )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        # FQM Advisor (FQM only — dedicated, dictionary + regex aware)
                        try:
                            if valid_component == "fqm":
                                savedsearch_names = [
                                    f"trackme_fqm_advisor_tracker_tenant_{self.tenant_id}",
                                ]
                                manage_savedsearch_schedule(
                                    savedsearch_names, components_advisor_active, "fqm_advisor"
                                )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        #
                        # Priority policies: depends on if we have content in the KVstore collection
                        #

                        try:

                            savedsearch_names = [
                                f"trackme_{valid_component}_priority_tracker_tenant_{self.tenant_id}",
                            ]

                            priority_collection_name = f"kv_trackme_{valid_component}_priority_policies_tenant_{self.tenant_id}"
                            priority_collection = self.service.kvstore[priority_collection_name]
                            (
                                priority_records,
                                priority_collection_keys,
                                priority_collection_dict,
                            ) = get_full_kv_collection(
                                priority_collection, priority_collection_name
                            )

                            # check if we have content in the collection
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", priority_collection_name="{priority_collection_name}", priority_records_count="{len(priority_records)}"'
                            )
                            feature_enabled = bool(priority_records)

                            manage_savedsearch_schedule(
                                savedsearch_names, feature_enabled, "priority_policies"
                            )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        #
                        # Tags policies: depends on if we have content in the KVstore collection
                        #

                        try:

                            savedsearch_names = [
                                f"trackme_{valid_component}_tags_tracker_tenant_{self.tenant_id}",
                            ]

                            tags_collection_name = f"kv_trackme_{valid_component}_tags_policies_tenant_{self.tenant_id}"
                            tags_collection = self.service.kvstore[tags_collection_name]
                            tags_records, tags_collection_keys, tags_collection_dict = (
                                get_full_kv_collection(tags_collection, tags_collection_name)
                            )

                            # check if we have content in the collection
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", tags_collection_name="{tags_collection_name}", tags_records_count="{len(tags_records)}"'
                            )
                            feature_enabled = bool(tags_records)

                            manage_savedsearch_schedule(
                                savedsearch_names, feature_enabled, "tags_policies"
                            )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        #
                        # SLA policies: depends on if we have content in the KVstore collection
                        #

                        try:

                            savedsearch_names = [
                                f"trackme_{valid_component}_sla_tracker_tenant_{self.tenant_id}",
                            ]

                            sla_collection_name = f"kv_trackme_{valid_component}_sla_policies_tenant_{self.tenant_id}"
                            sla_collection = self.service.kvstore[sla_collection_name]
                            sla_records, sla_collection_keys, sla_collection_dict = (
                                get_full_kv_collection(sla_collection, sla_collection_name)
                            )

                            # check if we have content in the collection
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", sla_collection_name="{sla_collection_name}", sla_records_count="{len(sla_records)}"'
                            )
                            feature_enabled = bool(sla_records)

                            manage_savedsearch_schedule(
                                savedsearch_names, feature_enabled, "sla_policies"
                            )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )

                        #
                        # Shared Elastic Tracker: depends on if we have content in the KVstore collection (dsm only)
                        #

                        try:

                            if valid_component == "dsm":

                                savedsearch_names = [
                                    f"trackme_dsm_shared_elastic_tracker_tenant_{self.tenant_id}",
                                ]

                                shared_elastic_collection_name = (
                                    f"kv_trackme_dsm_elastic_shared_tenant_{self.tenant_id}"
                                )
                                shared_elastic_collection = self.service.kvstore[
                                    shared_elastic_collection_name
                                ]
                                (
                                    shared_elastic_records,
                                    shared_elastic_collection_keys,
                                    shared_elastic_collection_dict,
                                ) = get_full_kv_collection(
                                    shared_elastic_collection, shared_elastic_collection_name
                                )

                                # check if we have content in the collection
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", shared_elastic_collection_name="{shared_elastic_collection_name}", shared_elastic_records_count="{len(shared_elastic_records)}"'
                                )
                                feature_enabled = bool(shared_elastic_records)

                                manage_savedsearch_schedule(
                                    savedsearch_names, feature_enabled, "shared_elastic"
                                )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{valid_component}", an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                            )
            else:
                # Skip processing for replica tenants
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, skipping replica tenant processing, tenant_replica="{tenant_replica}"'
                )

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        ##################################################################################
        # Replica orchestrator
        ##################################################################################

        # This job scheduled will automatically be enabled if we detect that at least one
        # replica tracker has been created

        task_name = "replica_orchestrator"
        if task_freq_manager.should_run(task_name):
            task_start = time.time()
            task_instance_id = self.get_uuid()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # Try to get the current definition
            try:
                tenant_replica_objects = vtenant_record.get("tenant_replica_objects")

                # logging debug
                logging.debug(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_replica_objects="{tenant_replica_objects}"'
                )
            except Exception as e:
                tenant_replica_objects = None

            # only run if we have a proper replica object
            if tenant_replica_objects:
                savedsearch_names = [
                    "trackme_replica_executor",
                ]

                for savedsearch_name in savedsearch_names:
                    # check
                    update_properties_required = False

                    try:
                        mysavedsearch = self.service.saved_searches[savedsearch_name]
                        current_disabled = int(mysavedsearch["disabled"])
                        logging.debug(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, replica config check, verifying savedsearch="{mysavedsearch.name}", disabled="{current_disabled}"'
                        )

                        if current_disabled == 1:
                            update_properties_required = True

                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, replica configuration verification, could not retrieve the status for {savedsearch_name}'
                        )

                    if update_properties_required:
                        try:
                            action = trackme_report_update_enablement(
                                session_key,
                                self._metadata.searchinfo.splunkd_uri,
                                self.tenant_id,
                                savedsearch_name,
                                "enable",
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, replica config check, enabling savedsearch="{savedsearch_name}", result="{action}"'
                            )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, replica config check, an exception was encountered while trying to enable savedsearch="{savedsearch_name}", exception="{str(e)}"'
                            )

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        ###########################################################################
        # schema update and migration: detect and migrate Virtual Tenants if needed
        ###########################################################################

        task_start = time.time()
        task_instance_id = self.get_uuid()
        task_name = "schema_upgrade"

        # Fast path: read schema_version directly from the already-loaded vtenant_record
        # to avoid an expensive splunkd connection and KV Store query on every cycle.
        # Only proceed with the full upgrade logic if versions don't match.
        current_schema_version = vtenant_record.get("schema_version")
        if (
            schema_version_required != 0
            and current_schema_version is not None
            and int(current_schema_version) == int(schema_version_required)
        ):
            task_duration = round(time.time() - task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                f'schema_version={current_schema_version} matches required={schema_version_required}, no upgrade needed, '
                f'run_time="{task_duration}", task has terminated.'
            )
        else:

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task, '
                f'schema_version={current_schema_version}, schema_version_required={schema_version_required}, upgrade check required.'
            )

            from trackme_libs_schema import (
                trackme_schema_get_version,
                trackme_schema_update_version,
                trackme_schema_upgrade_2009,
                trackme_schema_upgrade_2015,
                trackme_schema_upgrade_2016,
                trackme_schema_upgrade_2020,
                trackme_schema_upgrade_2026,
                trackme_schema_upgrade_2034,
                trackme_schema_upgrade_2034_least_privileges,
                trackme_schema_upgrade_2036,
                trackme_schema_upgrade_2038,
                trackme_schema_upgrade_2043,
                trackme_schema_upgrade_2044,
                trackme_schema_upgrade_2045,
                trackme_schema_upgrade_2054,
                trackme_schema_upgrade_2064,
                trackme_schema_upgrade_2067,
                trackme_schema_upgrade_2070,
                trackme_schema_upgrade_2071,
                trackme_schema_upgrade_2072,
                trackme_schema_upgrade_2075,
                trackme_schema_upgrade_2078,
                trackme_schema_upgrade_2083,
                trackme_schema_upgrade_2084,
                trackme_schema_upgrade_2087,
                trackme_schema_upgrade_2089,
                trackme_schema_upgrade_2090,
                trackme_schema_upgrade_2091,
                trackme_schema_upgrade_2094,
                trackme_schema_upgrade_2095,
                trackme_schema_upgrade_2096,
                trackme_schema_upgrade_2097,
                trackme_schema_upgrade_2098,
                trackme_schema_upgrade_2099,
                trackme_schema_upgrade_2100,
                trackme_schema_upgrade_2101,
                trackme_schema_upgrade_2102,
                trackme_schema_upgrade_2104,
                trackme_schema_upgrade_2105,
                trackme_schema_upgrade_2107,
                trackme_schema_upgrade_2108,
                trackme_schema_upgrade_2109,
                trackme_schema_upgrade_2110,
                trackme_schema_upgrade_2111,
                trackme_schema_upgrade_2116,
                trackme_schema_upgrade_2118,
                trackme_schema_upgrade_2119,
                trackme_schema_upgrade_2121,
                trackme_schema_upgrade_2122,
                trackme_schema_upgrade_2123,
                trackme_schema_upgrade_2126,
                trackme_schema_upgrade_2128,
                trackme_schema_upgrade_2130,
                trackme_schema_upgrade_2131,
                trackme_schema_upgrade_2132,
                trackme_schema_upgrade_2300,
                trackme_schema_upgrade_2304,
                trackme_schema_upgrade_2305,
                trackme_schema_upgrade_2306,
                trackme_schema_upgrade_2308,
                trackme_schema_upgrade_2312,
                trackme_schema_upgrade_2313,
                trackme_schema_upgrade_2314,
                trackme_schema_upgrade_2315,
                trackme_schema_upgrade_2316,
                trackme_schema_upgrade_2317,
                trackme_schema_upgrade_2319,
                trackme_schema_upgrade_2322,
                trackme_schema_upgrade_2400,
                trackme_schema_upgrade_2401,
            )

            # Define a mapping between schema versions and their upgrade functions
            schema_upgrades = [
                (2009, trackme_schema_upgrade_2009),
                (2015, trackme_schema_upgrade_2015),
                (2016, trackme_schema_upgrade_2016),
                (2020, trackme_schema_upgrade_2020),
                (2026, trackme_schema_upgrade_2026),
                (2034, trackme_schema_upgrade_2034),
                (2034, trackme_schema_upgrade_2034_least_privileges),
                (2036, trackme_schema_upgrade_2036),
                (2038, trackme_schema_upgrade_2038),
                (2043, trackme_schema_upgrade_2043),
                (2043, trackme_schema_upgrade_2044),
                (2045, trackme_schema_upgrade_2045),
                (2054, trackme_schema_upgrade_2054),
                (2064, trackme_schema_upgrade_2064),
                (2067, trackme_schema_upgrade_2067),
                (2070, trackme_schema_upgrade_2070),
                (2071, trackme_schema_upgrade_2071),
                (2072, trackme_schema_upgrade_2072),
                (2075, trackme_schema_upgrade_2075),
                (2078, trackme_schema_upgrade_2078),
                (2083, trackme_schema_upgrade_2083),
                (2084, trackme_schema_upgrade_2084),
                (2087, trackme_schema_upgrade_2087),
                (2089, trackme_schema_upgrade_2089),
                (2090, trackme_schema_upgrade_2090),
                (2091, trackme_schema_upgrade_2091),
                (2094, trackme_schema_upgrade_2094),
                (2095, trackme_schema_upgrade_2095),
                (2096, trackme_schema_upgrade_2096),
                (2097, trackme_schema_upgrade_2097),
                (2098, trackme_schema_upgrade_2098),
                (2099, trackme_schema_upgrade_2099),
                (2100, trackme_schema_upgrade_2100),
                (2101, trackme_schema_upgrade_2101),
                (2102, trackme_schema_upgrade_2102),
                (2104, trackme_schema_upgrade_2104),
                (2105, trackme_schema_upgrade_2105),
                (2107, trackme_schema_upgrade_2107),
                (2108, trackme_schema_upgrade_2108),
                (2109, trackme_schema_upgrade_2109),
                (2110, trackme_schema_upgrade_2110),
                (2111, trackme_schema_upgrade_2111),
                (2116, trackme_schema_upgrade_2116),
                (2118, trackme_schema_upgrade_2118),
                (2119, trackme_schema_upgrade_2119),
                (2121, trackme_schema_upgrade_2121),
                (2122, trackme_schema_upgrade_2122),
                (2123, trackme_schema_upgrade_2123),
                (2126, trackme_schema_upgrade_2126),
                (2128, trackme_schema_upgrade_2128),
                (2130, trackme_schema_upgrade_2130),
                (2131, trackme_schema_upgrade_2131),
                (2132, trackme_schema_upgrade_2132),
                (2300, trackme_schema_upgrade_2300),
                (2304, trackme_schema_upgrade_2304),
                (2305, trackme_schema_upgrade_2305),
                (2306, trackme_schema_upgrade_2306),
                (2308, trackme_schema_upgrade_2308),
                (2312, trackme_schema_upgrade_2312),
                (2313, trackme_schema_upgrade_2313),
                (2314, trackme_schema_upgrade_2314),
                (2315, trackme_schema_upgrade_2315),
                (2316, trackme_schema_upgrade_2316),
                (2317, trackme_schema_upgrade_2317),
                (2319, trackme_schema_upgrade_2319),
                (2322, trackme_schema_upgrade_2322),
                (2400, trackme_schema_upgrade_2400),
                (2401, trackme_schema_upgrade_2401),
            ]

            # Get the current schema version
            schema_version = None
            try:
                schema_version = trackme_schema_get_version(
                    reqinfo,
                    self.tenant_id,
                    schema_version_required,
                    task_name,
                    task_instance_id,
                )

            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to call function trackme_schema_get_version, exception="{str(e)}"'
                )

            # If schema_version_required is 0 (version retrieval failed), skip upgrade logic
            # to align with graceful degradation when DB Connect causes permission issues
            if schema_version_required == 0:
                logging.warning(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, schema_version_required is 0 (version retrieval failed), skipping schema upgrade logic to prevent data corruption.'
                )
            # Proceed
            elif not schema_version or int(schema_version) != int(schema_version_required):

                # Normalize None to 0 for pre-2.0.9 installs that have no schema_version yet
                if schema_version is None:
                    schema_version = 0

                #
                # API catalog warmup
                #
                # The first REST API Reference UI / chat / agent caller
                # after an app upgrade would otherwise pay a ~19s
                # catalog rebuild interactively. Pay the rebuild here
                # instead — the schema migration window is the natural
                # moment for it: this branch fires only when a real
                # migration is detected (this tenant's
                # ``schema_version`` differs from the running app's
                # required version), the upgrade is already doing
                # heavyweight work, and the helper is idempotent
                # (filesystem cache keyed by ``(target, app_version)``)
                # so the first tenant of an upgrade pays the rebuild
                # and every subsequent tenant migrating in the same
                # window hits the cache.
                #
                # Warm BOTH targets — ``"endpoints"`` (REST API
                # Reference drill-in modals + future programmatic
                # consumers) AND ``"groups"`` (REST API Reference
                # landing-page descriptions). The cache is keyed per
                # target, so a cold ``"groups"`` cache makes the first
                # UI user pay the rebuild for that specific projection
                # even if ``"endpoints"`` is warm.
                #
                # Fail-open: a warmup failure must NOT break the
                # migration. The helper returns a list of
                # ``(target, success, message)`` tuples — failure of
                # one target doesn't short-circuit the loop, so a
                # transient failure on one target doesn't prevent the
                # other from being warmed.
                try:
                    from trackme_libs_autodocs_catalog_builder import (
                        warmup_api_catalog_cache_all_targets,
                    )
                    results = warmup_api_catalog_cache_all_targets(
                        splunkd_uri=reqinfo["server_rest_uri"],
                        session_key=reqinfo["session_key"],
                    )
                    for target, ok, msg in results:
                        if ok:
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                                f'task="{task_name}", task_instance_id={task_instance_id}, '
                                f'api_catalog_warmup target={target}: {msg}'
                            )
                        else:
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                                f'task="{task_name}", task_instance_id={task_instance_id}, '
                                f'api_catalog_warmup target={target}: {msg}. '
                                f'The {target} catalog will be built lazily on the '
                                f'first consumer call instead.'
                            )
                except Exception as e:
                    # Defence-in-depth: even the import / log call
                    # path must not break the migration. The helper
                    # itself doesn't raise but a misconfigured
                    # PYTHONPATH or a syntax error in the helper's
                    # module could surface here at import time.
                    logging.warning(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                        f'task="{task_name}", task_instance_id={task_instance_id}, '
                        f'api_catalog_warmup_call_failed, '
                        f'exception="{type(e).__name__}: {e}". '
                        f'The catalog will be built lazily on the first '
                        f'consumer call instead.'
                    )

                #
                # Backup — safety snapshot before destructive schema migration.
                #
                # Coordination contract (Issue #1557):
                #
                # In a multi-tenant deployment, every enabled tenant's
                # health tracker independently hits this block in the
                # same scheduling window when a release bumps
                # ``schema_version_required``. Without coordination, N
                # tenants fire N parallel ``POST /backup`` calls — each
                # of which is a GLOBAL backup of every tenant + the
                # system, not just one tenant's data. The parallel
                # backups then cannibalize each other's working
                # directories via ``cleanup_backup_directories``,
                # producing partial archives and 2000+ mid-tar I/O
                # errors. Hit in pre-prod on a 2.3.22 → 2.3.23 deploy
                # with 18 enabled tenants.
                #
                # The older dedup mechanism — an SPL search against
                # ``index=_internal`` for a log beacon written by the
                # firing tracker — depended on Splunk's indexing
                # pipeline catching the first tracker's "initiating
                # backup now" log before subsequent trackers ran their
                # dedup search. Under burst load (18 trackers in 5
                # min on a SHC) the indexing-pipeline latency (5-30s)
                # is larger than the inter-tracker gap, so the first
                # 6-12 trackers all read ``count=0`` and all fire.
                #
                # This block now uses an atomic KV INSERT against
                # ``kv_trackme_schema_upgrade_backup_lock`` instead.
                # The ``_key`` encodes the target schema version and
                # the UTC date; KV's primary-key uniqueness is the
                # atomic primitive (HTTP 409 on duplicate). The first
                # tracker wins; the rest see 409 and skip. No
                # indexing-pipeline dependency. SHC-replicated
                # synchronously.

                # Check and act accordingly
                trackme_backup_attempted = False

                # Default: skip the backup. Only the tracker that
                # successfully claims the lock flips this to True. KV
                # unreachable / unexpected HTTP status flips it to True
                # defensively (fail-open — better to risk re-storming
                # than to silently lose the safety net).
                trackme_backup_run = False

                # ``pre_check_now`` is the timestamp anchor for the 24h
                # recent-backup pre-check below. A separate ``lock_now``
                # is captured later (after the pre-check's HTTP call to
                # KV) for the actual lock-claim moment — see the
                # second assignment below. The two are conceptually
                # different moments (pre-check vs. claim), so they live
                # under different names; an earlier version reused the
                # same ``lock_now`` for both and was flagged by bugbot
                # as a confusing duplicate assignment.
                pre_check_now = int(round(time.time()))

                # ──────────────────────────────────────────────────────
                # Pre-check: did a backup already run in the past 24h?
                # ──────────────────────────────────────────────────────
                #
                # The original SPL-based dedup that this lock replaces
                # had TWO clauses: (1) "another tracker already started a
                # backup" AND (2) "any backup completed successfully in
                # the past 24h, regardless of trigger". The KV lock
                # implementation that replaced the SPL search covers
                # clause (1) atomically — but clause (2) was lost in
                # translation: the daily scheduled backup at 02:00
                # produces ``kv_trackme_backup_archives_info`` rows that
                # the schema-upgrade tracker should treat as "already
                # covered", but the old SPL search saw those via the
                # ``"Backup archive created successfully"`` event match,
                # and the new lock-keyed-by-version-and-day doesn't.
                #
                # Result without this check: a tenant upgrades to v+1 a
                # few hours after the daily scheduled backup ran cleanly,
                # and the schema-upgrade tracker fires a redundant
                # global backup that the operator never asked for.
                #
                # Restored here as a direct query against the canonical
                # backup-info collection. Any row with ``mtime > now -
                # 86400s`` short-circuits the schema-upgrade safety
                # snapshot. Fail-open: if KV is unreachable here, fall
                # through to the lock-claim path (the lock alone still
                # prevents the storm).
                try:
                    info_url = (
                        f"{self._metadata.searchinfo.splunkd_uri}"
                        f"/servicesNS/nobody/trackme/storage/collections/data/"
                        f"kv_trackme_backup_archives_info"
                    )
                    recent_threshold = pre_check_now - 86400
                    # ``kv_trackme_backup_archives_info`` declares
                    # ``field.mtime = time`` and Splunk's KV layer should
                    # coerce string-numeric input on insert, but a few
                    # write sites (``post_backup``, ``post_import_backup``)
                    # explicitly pass ``str(...)``. Match both forms so a
                    # missed-coercion edge case can't silently bypass the
                    # 24h dedup and let the schema-upgrade tracker fire a
                    # redundant safety backup on top of the daily one.
                    # Lexicographic comparison of fixed-width 10-digit
                    # epoch strings preserves numeric order (valid until
                    # the year-2286 width transition).
                    info_response = session.get(
                        info_url,
                        params={
                            "query": json.dumps(
                                {"$or": [
                                    {"mtime": {"$gt": recent_threshold}},
                                    {"mtime": {"$gt": str(recent_threshold)}},
                                ]},
                            ),
                            "limit": 1,
                        },
                        verify=False,
                        timeout=splunkd_timeout,
                    )
                    if info_response.status_code == 200:
                        rows = info_response.json()
                        if isinstance(rows, list) and len(rows) > 0:
                            logging.info(
                                f'tenant_id="{self.tenant_id}", '
                                f'instance_id={instance_id}, '
                                f'task="{task_name}", '
                                f'task_instance_id={task_instance_id}, '
                                f'recent backup detected in past 24h '
                                f'(kv_trackme_backup_archives_info), '
                                f'skipping schema-upgrade safety '
                                f'backup entirely. This is the '
                                f'original SPL-dedup contract '
                                f'preserved: any backup in the past '
                                f'day counts as "covered".'
                            )
                            # Skip the whole lock-claim block and the
                            # backup call below.
                            trackme_backup_run = False
                            trackme_backup_attempted = True
                            # Fall through to schema migration without
                            # claiming the upgrade-backup lock; we don't
                            # need to coordinate among trackers because
                            # nobody will fire a backup.
                    elif info_response.status_code != 404:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", '
                            f'instance_id={instance_id}, '
                            f'task="{task_name}", '
                            f'task_instance_id={task_instance_id}, '
                            f'recent-backup pre-check returned '
                            f'unexpected http_status='
                            f'{info_response.status_code}; falling '
                            f'through to lock-based dedup.'
                        )
                except Exception as e:
                    logging.warning(
                        f'tenant_id="{self.tenant_id}", '
                        f'instance_id={instance_id}, '
                        f'task="{task_name}", '
                        f'task_instance_id={task_instance_id}, '
                        f'recent-backup pre-check raised '
                        f'exception="{str(e)}"; falling through to '
                        f'lock-based dedup.'
                    )

                # Build the lock key. UTC date granularity means a stuck
                # multi-day migration gets one safety backup per day
                # (operator-visible signal that something is wrong)
                # rather than zero.
                lock_date_token = time.strftime("%Y%m%d", time.gmtime())
                schema_lock_key = (
                    f"schema_upgrade_backup_"
                    f"{int(schema_version_required)}_"
                    f"{lock_date_token}"
                )
                schema_lock_url = (
                    f"{self._metadata.searchinfo.splunkd_uri}"
                    f"/servicesNS/nobody/trackme/storage/collections/data/"
                    f"kv_trackme_schema_upgrade_backup_lock"
                )

                lock_now = int(round(time.time()))
                lock_record = {
                    "_key": schema_lock_key,
                    "mtime": lock_now,
                    "htime": time.strftime("%c", time.localtime(lock_now)),
                    "schema_version_required": int(schema_version_required),
                    "tenant_id_initiator": self.tenant_id,
                    # Forensic only — full splunkd URI is sufficient for
                    # "which peer's tracker claimed this lock?" auditing.
                    # Not load-bearing for the lock semantics (the _key
                    # is what enforces uniqueness across the cluster).
                    "server_name": self._metadata.searchinfo.splunkd_uri,
                    "backup_call_status": "",
                }

                # Guard: skip the whole lock-claim block when the
                # pre-check above already confirmed a recent backup
                # (within the past 24h). Claiming the lock without
                # firing a backup would leave an empty-status row that
                # the staleness rescue below would then try to recover,
                # firing the very backup we just determined was not needed.
                if not trackme_backup_attempted:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                        f'task="{task_name}", task_instance_id={task_instance_id}, '
                        f'attempting to claim schema-upgrade backup lock, '
                        f'key="{schema_lock_key}"'
                    )

                    try:
                        lock_response = session.post(
                            schema_lock_url,
                            data=json.dumps(lock_record),
                            verify=False,
                            timeout=splunkd_timeout,
                        )
                        if lock_response.status_code in (200, 201):
                            # We won the race — fire the safety backup.
                            trackme_backup_run = True
                            logging.info(
                                f'tenant_id="{self.tenant_id}", '
                                f'instance_id={instance_id}, task="{task_name}", '
                                f'task_instance_id={task_instance_id}, '
                                f'claimed schema-upgrade backup lock, '
                                f'key="{schema_lock_key}", '
                                f'initiating backup now.'
                            )
                        elif lock_response.status_code == 409:
                            # Duplicate key — a row with this _key already
                            # exists. Two possibilities:
                            #
                            #   (a) Fresh lock — another tenant tracker
                            #       claimed it minutes ago and is currently
                            #       running or has finished its global
                            #       safety backup. We are correctly
                            #       covered. Skip.
                            #
                            #   (b) Stale lock — the original claimer
                            #       crashed BETWEEN the INSERT and the
                            #       POST /backup call (worker thread died,
                            #       splunkd recycled the persistent REST
                            #       subprocess, network partition lost the
                            #       response, etc.). The row exists but no
                            #       backup ever fired. Without rescue logic,
                            #       every tenant tracker would see the row
                            #       and skip for the rest of the UTC day —
                            #       24h of exposed migration with no safety
                            #       snapshot.
                            #
                            # Disambiguate by inspecting the existing row's
                            # ``mtime``. The post_backup timeout is 900s
                            # (15 min), and even a slow fleet-wide backup
                            # completes well within that. We use a 30-min
                            # staleness threshold: if the lock has been
                            # held longer than that, treat it as stale and
                            # attempt rescue.
                            STALE_LOCK_THRESHOLD_SECONDS = 1800

                            existing_row = None
                            try:
                                existing_response = session.get(
                                    f"{schema_lock_url}/{schema_lock_key}",
                                    verify=False,
                                    timeout=splunkd_timeout,
                                )
                                if existing_response.status_code == 200:
                                    existing_row = existing_response.json()
                            except Exception as e:
                                logging.warning(
                                    f'tenant_id="{self.tenant_id}", '
                                    f'instance_id={instance_id}, '
                                    f'task="{task_name}", '
                                    f'task_instance_id={task_instance_id}, '
                                    f'schema-upgrade backup lock GET '
                                    f'raised, treating as fresh and '
                                    f'skipping: exception="{str(e)}"'
                                )

                            existing_mtime = 0
                            existing_backup_call_status = ""
                            if isinstance(existing_row, dict):
                                try:
                                    existing_mtime = int(
                                        float(existing_row.get("mtime") or 0)
                                    )
                                except (TypeError, ValueError):
                                    existing_mtime = 0
                                existing_backup_call_status = (
                                    existing_row.get("backup_call_status") or ""
                                )

                            # Sentinel -1 when mtime couldn't be read (GET
                            # failed, row missing the field, unparseable
                            # value). Without this, lock_age_seconds becomes
                            # lock_now - 0 ≈ 1.7e9 seconds and the log line
                            # below would print a meaningless ~54-year age.
                            # Mirrors the convention in
                            # ``_acquire_backup_in_flight_lock``. Bugbot
                            # finding (PR #1558).
                            lock_age_seconds = (
                                (lock_now - existing_mtime)
                                if existing_mtime > 0
                                else -1
                            )
                            # Rescue ONLY if both conditions hold:
                            #   * the lock's mtime is past the staleness
                            #     threshold, AND
                            #   * the lock-holder never recorded a
                            #     completion marker.
                            #
                            # The original mtime-only check incorrectly
                            # treated a "claimed and successfully fired"
                            # lock as stale once its age exceeded the
                            # threshold — triggering a runaway loop where
                            # rescue + re-fire happened roughly every 35
                            # min on a stuck migration (~41 backups/day
                            # instead of the documented "one per day").
                            #
                            # With the completion marker, an empty
                            # ``backup_call_status`` means the holder
                            # crashed BETWEEN the lock claim and the
                            # backup call (genuine orphan — rescue
                            # legitimately needed). A non-empty value
                            # means the holder DID fire post_backup
                            # (regardless of HTTP outcome — even a
                            # failed attempt counts under the original
                            # "ONE attempt per day" contract that the
                            # pre-2.3.23 SPL dedup also enforced).
                            # Bugbot finding (PR #1558).
                            is_stale = (
                                existing_mtime > 0
                                and lock_age_seconds > STALE_LOCK_THRESHOLD_SECONDS
                                and existing_backup_call_status == ""
                            )

                            if not is_stale:
                                # Path (a): fresh lock OR already-fired
                                # lock (completion marker present). Either
                                # way, we are correctly covered and skip.
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", '
                                    f'instance_id={instance_id}, '
                                    f'task="{task_name}", '
                                    f'task_instance_id={task_instance_id}, '
                                    f'schema-upgrade backup lock already '
                                    f'held by another tracker (age='
                                    f'{lock_age_seconds}s, '
                                    f'backup_call_status='
                                    f'{existing_backup_call_status!r}), '
                                    f'key="{schema_lock_key}", skipping '
                                    f'safety backup (covered by the '
                                    f'lock-winning tracker\'s global '
                                    f'backup).'
                                )
                            else:
                                # Path (b): stale lock. Rescue — DELETE
                                # the old row, then re-attempt INSERT.
                                # If multiple tenant trackers all detect
                                # staleness in the same window, KV's
                                # primary-key uniqueness still serializes
                                # them: only ONE rescue INSERT can succeed
                                # (the rest see another 409 against the
                                # rescued row and skip without a third
                                # rescue layer). The DELETE+INSERT window
                                # is milliseconds; the worst-case race
                                # outcome is two simultaneous rescuers
                                # both firing post_backup — a one-off
                                # degradation, not a permanent block.
                                logging.warning(
                                    f'tenant_id="{self.tenant_id}", '
                                    f'instance_id={instance_id}, '
                                    f'task="{task_name}", '
                                    f'task_instance_id={task_instance_id}, '
                                    f'schema-upgrade backup lock is STALE '
                                    f'(age={lock_age_seconds}s > threshold='
                                    f'{STALE_LOCK_THRESHOLD_SECONDS}s), '
                                    f'attempting rescue: key="'
                                    f'{schema_lock_key}", '
                                    f'prior_holder_tenant='
                                    f'{(existing_row or {}).get("tenant_id_initiator")!r}'
                                )
                                try:
                                    # DELETE-by-key is idempotent: 200 if it
                                    # was there, 404 if another rescuer
                                    # already deleted it (fine — proceed to
                                    # INSERT, which will arbitrate).
                                    session.delete(
                                        f"{schema_lock_url}/{schema_lock_key}",
                                        verify=False,
                                        timeout=splunkd_timeout,
                                    )
                                    # Re-INSERT with a TRULY refreshed
                                    # mtime so the next staleness check is
                                    # computed against the rescue time,
                                    # not the original claim time. Earlier
                                    # versions reused ``lock_now`` here,
                                    # which is the timestamp captured
                                    # before the initial INSERT — keeping
                                    # the rescued row "born stale" and
                                    # vulnerable to a redundant re-rescue
                                    # by another tracker. Bugbot finding
                                    # (PR #1558).
                                    rescue_now = int(round(time.time()))
                                    lock_record["mtime"] = rescue_now
                                    lock_record["htime"] = time.strftime(
                                        "%c", time.localtime(rescue_now),
                                    )
                                    rescue_response = session.post(
                                        schema_lock_url,
                                        data=json.dumps(lock_record),
                                        verify=False,
                                        timeout=splunkd_timeout,
                                    )
                                    if rescue_response.status_code in (
                                        200, 201,
                                    ):
                                        trackme_backup_run = True
                                        logging.info(
                                            f'tenant_id="{self.tenant_id}", '
                                            f'instance_id={instance_id}, '
                                            f'task="{task_name}", '
                                            f'task_instance_id='
                                            f'{task_instance_id}, '
                                            f'RESCUED stale schema-upgrade '
                                            f'backup lock, key="'
                                            f'{schema_lock_key}", '
                                            f'initiating backup now.'
                                        )
                                    elif rescue_response.status_code == 409:
                                        # Another tracker rescued first.
                                        # Correctly skip — they will fire
                                        # the safety backup.
                                        logging.info(
                                            f'tenant_id="{self.tenant_id}", '
                                            f'instance_id={instance_id}, '
                                            f'task="{task_name}", '
                                            f'task_instance_id='
                                            f'{task_instance_id}, '
                                            f'another tracker rescued the '
                                            f'stale schema-upgrade backup '
                                            f'lock first, key="'
                                            f'{schema_lock_key}", skipping '
                                            f'safety backup.'
                                        )
                                    else:
                                        # Unexpected. Fail-open.
                                        logging.warning(
                                            f'tenant_id="{self.tenant_id}", '
                                            f'instance_id={instance_id}, '
                                            f'task="{task_name}", '
                                            f'task_instance_id='
                                            f'{task_instance_id}, '
                                            f'schema-upgrade backup lock '
                                            f'rescue INSERT returned '
                                            f'unexpected http_status='
                                            f'{rescue_response.status_code}, '
                                            f'body='
                                            f'{rescue_response.text[:300]!r}; '
                                            f'firing safety backup '
                                            f'defensively.'
                                        )
                                        trackme_backup_run = True
                                except Exception as e:
                                    # Rescue itself raised. Same fail-open.
                                    logging.warning(
                                        f'tenant_id="{self.tenant_id}", '
                                        f'instance_id={instance_id}, '
                                        f'task="{task_name}", '
                                        f'task_instance_id='
                                        f'{task_instance_id}, '
                                        f'schema-upgrade backup lock '
                                        f'rescue raised '
                                        f'exception="{str(e)}"; firing '
                                        f'safety backup defensively.'
                                    )
                                    trackme_backup_run = True
                        else:
                            # Unexpected HTTP status. KV could be in a weird
                            # state. Defensive: fire the backup anyway. Worst
                            # case is the pre-fix behaviour, which we are
                            # already trying to escape from.
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", '
                                f'instance_id={instance_id}, task="{task_name}", '
                                f'task_instance_id={task_instance_id}, '
                                f'schema-upgrade backup lock claim returned '
                                f'unexpected http_status='
                                f'{lock_response.status_code}, body='
                                f'{lock_response.text[:300]!r}; firing safety '
                                f'backup defensively.'
                            )
                            trackme_backup_run = True
                    except Exception as e:
                        # Network / SDK failure. Same defensive fallback.
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", '
                            f'instance_id={instance_id}, task="{task_name}", '
                            f'task_instance_id={task_instance_id}, '
                            f'schema-upgrade backup lock claim raised '
                            f'exception="{str(e)}"; firing safety backup '
                            f'defensively.'
                        )
                        trackme_backup_run = True

                # before running the first function, execute TrackMe's builtin backup job
                if trackme_backup_run:
                    if not trackme_backup_attempted:
                        # ``backup_call_status_marker`` captures the
                        # outcome of the post_backup call (HTTP code or
                        # exception class name). It's written back into
                        # the schema-upgrade lock row immediately after
                        # the call returns. This is the discriminator
                        # the staleness rescue uses to distinguish a
                        # "claimed and fired" lock (status non-empty,
                        # never re-rescue) from a "claimed but the
                        # holder died before firing" lock (status empty,
                        # rescue legitimately needed). Without this
                        # marker, a successful backup that simply takes
                        # longer than the staleness threshold to
                        # complete would trigger a runaway loop of
                        # rescue + re-fire every ~35 min — bugbot
                        # finding (PR #1558).
                        backup_call_status_marker = ""
                        try:
                            response = session.post(
                                f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/backup_and_restore/backup",
                                data=json.dumps(
                                    {
                                        "comment": f"Backup initiated for schema migration from version {schema_version} to {schema_version_required}",
                                        # Honour the contract documented
                                        # in collections.conf for the
                                        # ``kv_trackme_backup_in_flight_lock``
                                        # collection's ``caller_context``
                                        # field — schema-upgrade trackers
                                        # are supposed to identify
                                        # themselves as such so an operator
                                        # investigating a stuck migration
                                        # can filter the lock row by
                                        # caller. Without this, every
                                        # schema-upgrade-triggered backup
                                        # recorded an empty context.
                                        # Bugbot finding (PR #1575).
                                        "caller_context": "schema_upgrade",
                                    }
                                ),
                                verify=False,
                                timeout=900,
                            )
                            backup_call_status_marker = f"http_{response.status_code}"
                            if response.status_code not in (200, 201, 204):
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, backup post call has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                                )
                            else:
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, backup post call executed successfully'
                                )
                        except Exception as e:
                            backup_call_status_marker = (
                                f"exception:{type(e).__name__}"
                            )
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, backup post call has failed, exception="{str(e)}"'
                            )
                        trackme_backup_attempted = True

                        # Persist the completion marker on the schema-
                        # upgrade lock row so subsequent tracker cycles'
                        # staleness rescue sees the lock as "completed,
                        # do not re-rescue".
                        #
                        # IMPORTANT — Splunk KV POST to a specific key
                        # is a FULL DOCUMENT REPLACEMENT, not a partial
                        # merge. Sending just ``{"backup_call_status":
                        # ...}`` would wipe mtime, htime,
                        # schema_version_required, tenant_id_initiator,
                        # and server_name — making the row useless for
                        # operator audit AND breaking the staleness
                        # rescue's mtime check on the next cycle.
                        # Re-send the full ``lock_record`` with the
                        # completion marker mutated in place, mirroring
                        # the rescue-path pattern above. Bugbot finding
                        # (PR #1558).
                        #
                        # Best-effort — if this update fails, the
                        # staleness rescue logic correctly falls back
                        # to (mtime stale && status empty) → triggers
                        # rescue on the next cycle past the threshold,
                        # which is the orphan-handling path the rescue
                        # was designed for.
                        try:
                            update_url = (
                                f"{schema_lock_url}/{schema_lock_key}"
                            )
                            # Mutate in place — preserves _key,
                            # mtime, htime, schema_version_required,
                            # tenant_id_initiator, server_name. We
                            # want the completion POST to keep the
                            # current-claim mtime (not the completion
                            # time). That value depends on which
                            # path we took:
                            #
                            #   * Fresh claim: ``lock_record["mtime"]``
                            #     is still the initial ``lock_now``
                            #     captured at the lock-build site.
                            #   * Rescue: the rescue path above already
                            #     overwrote ``lock_record["mtime"]`` to
                            #     ``rescue_now`` (the new claim time)
                            #     before the rescue INSERT. The
                            #     completion POST inherits that value,
                            #     which is correct because the rescue
                            #     INSERT IS the active claim now.
                            #
                            # In both cases the recorded mtime is
                            # "the active claim's start time" — what
                            # the staleness rescue check needs to gate
                            # correctly. (Bugbot finding flagged the
                            # earlier "original mtime" wording for
                            # being ambiguous on the rescue path —
                            # behaviour unchanged, wording clarified.)
                            #
                            # The staleness rescue gates on
                            # (age > 30min AND status empty), so
                            # writing a non-empty
                            # ``backup_call_status`` here is what
                            # signals "do not rescue" to subsequent
                            # tracker cycles — the mtime value is
                            # informational only at that point.
                            lock_record["backup_call_status"] = (
                                backup_call_status_marker
                            )
                            session.post(
                                update_url,
                                data=json.dumps(lock_record),
                                verify=False,
                                timeout=splunkd_timeout,
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", '
                                f'instance_id={instance_id}, '
                                f'task="{task_name}", '
                                f'task_instance_id={task_instance_id}, '
                                f'recorded schema-upgrade backup lock '
                                f'completion marker '
                                f'backup_call_status='
                                f'{backup_call_status_marker!r}, '
                                f'key="{schema_lock_key}"'
                            )
                        except Exception as e:
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", '
                                f'instance_id={instance_id}, '
                                f'task="{task_name}", '
                                f'task_instance_id={task_instance_id}, '
                                f'failed to update schema-upgrade '
                                f'backup lock completion marker '
                                f'(backup_call_status='
                                f'{backup_call_status_marker!r}); '
                                f'on the next cycle the staleness '
                                f'rescue will fire ONCE past the '
                                f'30-min threshold and re-fire the '
                                f'safety backup — worse than ideal '
                                f'but bounded. exception="{str(e)}"'
                            )

                #
                # schema upgrade
                #

                for version, upgrade_func in schema_upgrades:
                    if not schema_version or int(schema_version) < version:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, detected migration required for schema version {version}, schema_version="{schema_version}", schema_version_required="{schema_version_required}", processing now.'
                        )

                        # proceed
                        try:
                            schema_version_update = upgrade_func(
                                reqinfo,
                                self.tenant_id,
                                int(schema_version),
                                int(schema_version_required),
                                task_name,
                                task_instance_id,
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, schema version {version} migrated successfully.'
                            )

                            # Update schema version after each successful upgrade
                            try:
                                schema_version_update = trackme_schema_update_version(
                                    reqinfo,
                                    self.tenant_id,
                                    version,  # Update to current version being processed
                                    task_name,
                                    task_instance_id,
                                )
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, schema version updated to {version} after successful upgrade.'
                                )
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to update schema version to {version}, exception="{str(e)}"'
                                )
                                raise  # Re-raise the exception to stop the upgrade process

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to call function {upgrade_func.__name__}, exception="{str(e)}"'
                            )
                            raise  # Re-raise the exception to stop the upgrade process

                #
                # finally migrate the schema version to the required version if not already there
                #

                try:
                    if int(schema_version) != int(schema_version_required):
                        schema_version_update = trackme_schema_update_version(
                            reqinfo,
                            self.tenant_id,
                            schema_version_required,
                            task_name,
                            task_instance_id,
                        )
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, final schema version updated to {schema_version_required}.'
                        )
                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to call function trackme_schema_update_version, exception="{str(e)}"'
                    )

                #
                # check if the vtenant is the last enabled vtenant to be upgraded, if so we will execute the general health tracker
                #

                vtenants_records = collection.data.query()
                vtenants_remaining_count = 0
                # iterate through vtenant records, count remaining vtenants to be upgraded
                for record in vtenants_records:
                    schema_version_raw = record.get("schema_version")
                    # If schema_version is None (e.g., tenant was created when version retrieval failed),
                    # treat it as needing an upgrade
                    if schema_version_raw is None:
                        schema_version_needs_upgrade = True
                    else:
                        schema_version_needs_upgrade = int(schema_version_raw) != int(schema_version_required)
                    if (
                        schema_version_needs_upgrade
                        and record.get("tenant_status") == "enabled"
                    ):
                        vtenants_remaining_count += 1

                if vtenants_remaining_count == 0:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, all vtenants are up to date, executing the general health tracker'
                    )
                    try:
                        reader = run_splunk_search(
                            self.service,
                            "| savedsearch trackme_general_health_manager",
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

                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, general health tracker executed successfully'
                        )

                    except Exception as e:
                        msg = f'permanently failed to execute the general health tracker search, exception="{str(e)}"'
                        logging.error(msg)
                        raise Exception(msg)

            else:
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, schema is up to date, no action required, schema_version="{schema_version}"'
                )

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )

        #
        #
        #

        #
        # all components - inspect_collection
        #

        # context: this activity verifies that the collection record object statuses are consistent according to the Decision Maker
        # It works by loading the component data, then looping through objects to verify and update their collection status if needed

        for component in ("dsm", "dhm", "mhm", "wlk", "flx", "fqm"):

            if vtenant_record.get(f"tenant_{component}_enabled") == True:
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, inspecting collection records object statuses now.'
                )

                # set collection target
                inspect_collection_name = (
                    f"kv_trackme_{component}_tenant_{self.tenant_id}"
                )
                inspect_collection = self.service.kvstore[inspect_collection_name]

                #
                # subtask: permanently_deleted_records_inspection
                #

                task_name = "inspect_collection:permanently_deleted_records_inspection"
                if task_freq_manager.should_run(task_name):
                    task_instance_id = self.get_uuid()
                    task_start = time.time()

                    # start task
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
                    )

                    #
                    # Check permanently deleted records:
                    # A permanently deleted record should not exist in the main KVstore collection, if it does, it should be purged
                    #

                    # Lists to store permanently deleted records found in anomaly
                    collection_permanently_deleted_records_anomaly = []

                    # search
                    search = remove_leading_spaces(
                        f"""\
                        | inputlookup trackme_{component}_tenant_{self.tenant_id} | eval keyid=_key
                        | lookup trackme_common_permanently_deleted_objects_tenant_{self.tenant_id} object, object_category OUTPUT _key as permanently_deleted_keys
                        | where isnotnull(permanently_deleted_keys)
                        | table keyid, *
                    """
                    )

                    # kwargs
                    kwargs_search = {
                        "earliest_time": "-5m",
                        "latest_time": "now",
                        "preview": "false",
                        "output_mode": "json",
                        "count": 0,
                    }

                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, inspecting the main data collection for permanently deleted records now.'
                    )

                    try:
                        reader = run_splunk_search(
                            self.service,
                            search,
                            kwargs_search,
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                collection_permanently_deleted_records_anomaly.append(item)

                    except Exception as e:
                        msg = f'permanently deleted records inspection search failed with exception="{str(e)}"'
                        logging.error(msg)
                        raise Exception(msg)

                    if len(collection_permanently_deleted_records_anomaly) > 0:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, permanently deleted records found, no_records="{len(collection_permanently_deleted_records_anomaly)}"'
                        )

                        for record in collection_permanently_deleted_records_anomaly:
                            try:
                                inspect_collection.data.delete(
                                    json.dumps({"_key": record.get("keyid")})
                                )
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, entities in the main collection which are also in their permanently deleted records were purged successfully, keyid="{record.get("keyid")}", record="{json.dumps(record, indent=1)}"'
                                )
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, failed to delete permanently deleted records in anmaly, keyid="{record.get("keyid")}", , record="{json.dumps(record, indent=1)}", exception="{str(e)}"'
                                )

                    else:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, no permanenlty deleted records in anomaly found'
                        )

                    #
                    # Check for any duplicated records in the permanently deleted records collection, based on the object field
                    #

                    permanently_deleted_records_collection_name = f"kv_trackme_common_permanently_deleted_objects_tenant_{self.tenant_id}"
                    permanently_deleted_records_collection = self.service.kvstore[permanently_deleted_records_collection_name]
                    (
                        permanently_deleted_records,
                        permanently_deleted_collection_keys,
                        permanently_deleted_collection_dict,
                    ) = get_full_kv_collection(
                        permanently_deleted_records_collection, permanently_deleted_records_collection_name
                    )

                    # Detect duplicated records (same "(object, object_category)") and collect keys to delete (keep first seen)
                    duplicated_pd_keys = []
                    seen_pairs = set()
                    for pd_key, pd_record in permanently_deleted_collection_dict.items():
                        object_value = pd_record.get("object")
                        object_category = pd_record.get("object_category")
                        if not object_value or not object_category:
                            continue
                        pair = (object_value, object_category)
                        if pair in seen_pairs:
                            duplicated_pd_keys.append(pd_key)
                        else:
                            seen_pairs.add(pair)

                    if len(duplicated_pd_keys) > 0:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, permanently deleted records collection has duplicates, duplicates_count="{len(duplicated_pd_keys)}"'
                        )
                        for pd_key in duplicated_pd_keys:
                            try:
                                permanently_deleted_records_collection.data.delete(json.dumps({"_key": pd_key}))
                                # best-effort to fetch object for logging
                                pd_record = permanently_deleted_collection_dict.get(pd_key, {})
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, duplicate in permanently deleted records purged successfully, keyid="{pd_key}", object="{pd_record.get("object")}", object_category="{pd_record.get("object_category")}"'
                                )
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to purge duplicate in permanently deleted records, keyid="{pd_key}", exception="{str(e)}"'
                                )
                    else:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, no duplicates found in permanently deleted records collection'
                        )

                    # end subtask
                    task_duration = round(time.time()-task_start, 3)
                    task_freq_manager.record_execution(task_name, task_duration)
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
                    )
                else:
                    task_freq_manager.increment_skipped(task_name)

                #
                # subtask: corrupted_records_inspection
                #

                task_name = "inspect_collection:corrupted_records_inspection"
                if task_freq_manager.should_run(task_name):
                    task_start = time.time()
                    task_instance_id = self.get_uuid()

                    # start task
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
                    )

                    #
                    # Check for unexpected corrupted record, a foreign record which has been stored in the KVstore by mistake
                    # would not have an object value, and would be purged if any.
                    #

                    # Lists to store corrupted records
                    collection_corrupted_records = []

                    # search
                    search = remove_leading_spaces(
                        f"""\
                        | inputlookup trackme_{component}_tenant_{self.tenant_id} | eval keyid=_key
                        | where isnull(object) OR object=""
                        | table keyid, *
                    """
                    )

                    # kwargs
                    kwargs_search = {
                        "earliest_time": "-5m",
                        "latest_time": "now",
                        "preview": "false",
                        "output_mode": "json",
                        "count": 0,
                    }

                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, inspecting the main data collection for corrupted records now.'
                    )

                    try:
                        reader = run_splunk_search(
                            self.service,
                            search,
                            kwargs_search,
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                collection_corrupted_records.append(item)

                    except Exception as e:
                        msg = f'corrupted record inspection search failed with exception="{str(e)}"'
                        logging.error(msg)
                        raise Exception(msg)

                    if len(collection_corrupted_records) > 0:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, corrupted records found, no_records="{len(collection_corrupted_records)}"'
                        )

                        for corrupted_record in collection_corrupted_records:
                            try:
                                inspect_collection.data.delete(
                                    json.dumps({"_key": corrupted_record.get("keyid")})
                                )
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, corrupted record deleted successfully, keyid="{corrupted_record.get("keyid")}", record="{json.dumps(corrupted_record, indent=1)}"'
                                )
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, failed to delete corrupted record, keyid="{corrupted_record.get("keyid")}", , record="{json.dumps(corrupted_record, indent=1)}", exception="{str(e)}"'
                                )

                    else:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, no corrupted records found'
                        )

                    # end subtask
                    task_duration = round(time.time()-task_start, 3)
                    task_freq_manager.record_execution(task_name, task_duration)
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
                    )
                else:
                    task_freq_manager.increment_skipped(task_name)

                #
                # subtask: missing_tenant_id_records_inspection
                #

                task_name = "inspect_collection:missing_tenant_id_records_inspection"
                if task_freq_manager.should_run(task_name):
                    task_start = time.time()
                    task_instance_id = self.get_uuid()

                    # start task
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
                    )

                    #
                    # Check for records which would miss the tenant_id field, and add it if needed
                    #

                    # collection_misggin_tenant_id_records records
                    collection_missing_tenant_id_records = []

                    # search
                    search = remove_leading_spaces(
                        f"""\
                        | inputlookup trackme_{component}_tenant_{self.tenant_id} | eval keyid=_key
                        | where isnull(tenant_id) OR tenant_id=""
                        | table keyid, *
                    """
                    )

                    # kwargs
                    kwargs_search = {
                        "earliest_time": "-5m",
                        "latest_time": "now",
                        "preview": "false",
                        "output_mode": "json",
                        "count": 0,
                    }

                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, inspecting the main data collection for missing tenant_id records now.'
                    )

                    try:
                        reader = run_splunk_search(
                            self.service,
                            search,
                            kwargs_search,
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                collection_missing_tenant_id_records.append(item)

                    except Exception as e:
                        msg = f'missing tenant_id record inspection search failed with exception="{str(e)}"'
                        logging.error(msg)
                        raise Exception(msg)

                    if len(collection_missing_tenant_id_records) > 0:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, records found, no_records="{len(collection_missing_tenant_id_records)}"'
                        )

                        for missing_record in collection_missing_tenant_id_records:
                            try:
                                missing_record["tenant_id"] = self.tenant_id
                                inspect_collection.data.update(
                                    missing_record.get("_key"),
                                    json.dumps(missing_record),
                                )
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, record updated successfully, keyid="{missing_record.get("keyid")}", record="{json.dumps(missing_record, indent=1)}"'
                                )
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, failed to update record, keyid="{missing_record.get("keyid")}", , record="{json.dumps(missing_record, indent=1)}", exception="{str(e)}"'
                                )

                    else:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, no records found'
                        )

                    # end subtask
                    task_duration = round(time.time()-task_start, 3)
                    task_freq_manager.record_execution(task_name, task_duration)
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
                    )
                else:
                    task_freq_manager.increment_skipped(task_name)

                #
                # subtask: entities_auto_disablement
                #

                task_name = "inspect_collection:entities_auto_disablement"
                if task_freq_manager.should_run(task_name):
                    task_start = time.time()
                    task_instance_id = self.get_uuid()

                    # start task
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
                    )

                    #
                    # Check for feeds entities to be disabled according to the system wide setting: splk_general_feeds_auto_disablement_period
                    # This setting allows to disable feeds entities if they have not been updated for a certain period of time
                    #

                    # system wide setting
                    try:
                        splk_general_feeds_auto_disablement_period = reqinfo["trackme_conf"][
                            "splk_general"
                        ]["splk_general_feeds_auto_disablement_period"]
                    except Exception as e:
                        logging.warning(f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to get system wide setting, splk_general_feeds_auto_disablement_period, using default value, exception="{str(e)}"')
                        splk_general_feeds_auto_disablement_period = "90d"

                    # tenant setting (override system wide setting, if set)
                    try:
                        splk_feeds_auto_disablement_period = vtenant_account.get(
                            "splk_feeds_auto_disablement_period"
                        )
                    except Exception as e:
                        logging.warning(f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to get tenant setting, splk_feeds_auto_disablement_period, using system wide setting, exception="{str(e)}"')
                        splk_feeds_auto_disablement_period = splk_general_feeds_auto_disablement_period

                    # handle
                    auto_disablement_period = (
                        splk_feeds_auto_disablement_period
                        if splk_feeds_auto_disablement_period
                        else splk_general_feeds_auto_disablement_period
                    )

                    if auto_disablement_period != "0d" and component in (
                        "dsm",
                        "dhm",
                        "mhm",
                    ):

                        # Lists to store entities to be disabled
                        entities_to_be_disabled = []

                        # search
                        search = remove_leading_spaces(
                            f"""\
                            | inputlookup trackme_{component}_tenant_{self.tenant_id} | eval keyid=_key
                            | eval last_time_seen=coalesce(data_last_time_seen, metric_last_time_seen)
                            | where last_time_seen<=relative_time(now(), "-{auto_disablement_period}")
                            | table keyid, object, last_time_seen
                            | eval last_time_seen_human=strftime(last_time_seen, "%c")
                        """
                        )

                        # kwargs
                        kwargs_search = {
                            "earliest_time": "-5m",
                            "latest_time": "now",
                            "preview": "false",
                            "output_mode": "json",
                            "count": 0,
                        }

                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, inspecting the main data collection for entities to be disabled according to auto-disablement setting. (auto_disablement_period="{auto_disablement_period}")'
                        )

                        try:
                            reader = run_splunk_search(
                                self.service,
                                search,
                                kwargs_search,
                                24,
                                5,
                            )

                            for item in reader:
                                if isinstance(item, dict):
                                    entities_to_be_disabled.append(item.get("keyid"))

                        except Exception as e:
                            msg = f'auto-disablement record inspection search failed with exception="{str(e)}"'
                            logging.error(msg)
                            raise Exception(msg)

                        if len(entities_to_be_disabled) > 0:
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, entities to be disabled were found, list="{entities_to_be_disabled}"'
                            )

                            # turn entities_to_be_disabled list into CSV
                            entities_to_be_disabled_csv = ",".join(entities_to_be_disabled)

                            # call mass disablement endpoint
                            if component == "dsm":
                                target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_dsm/write/ds_monitoring"
                            elif component == "dhm":
                                target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_dhm/write/dh_monitoring"
                            elif component == "mhm":
                                target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_mhm/write/mh_monitoring"

                            try:
                                response = session.post(
                                    target_url,
                                    data=json.dumps(
                                        {
                                            "tenant_id": self.tenant_id,
                                            "keys_list": entities_to_be_disabled_csv,
                                            "action": "disable",
                                            "update_comment": f"auto-disabled by the system, last seen data is beyond the system wide auto-disablement period of {splk_general_feeds_auto_disablement_period}",
                                        }
                                    ),
                                    verify=False,
                                    timeout=600,
                                )

                                if response.status_code not in (200, 201, 204):
                                    msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, query has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                                    logging.error(msg)
                                else:
                                    try:
                                        success_count = response.json().get("success_count")
                                    except Exception as e:
                                        success_count = 0
                                    msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, request was successful, success_count="{success_count}"'
                                    logging.info(msg)

                            except Exception as e:
                                msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, ctask="{task_name}", task_instance_id={task_instance_id}, request failed with exception="{str(e)}"'
                                logging.info(msg)

                        else:
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, no entities to be disabled were found'
                            )

                    # end subtask
                    task_duration = round(time.time()-task_start, 3)
                    task_freq_manager.record_execution(task_name, task_duration)
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
                    )
                else:
                    task_freq_manager.increment_skipped(task_name)

                #
                # subtask: handle_sync_entities
                #

                task_start = time.time()
                task_instance_id = self.get_uuid()
                task_name = "inspect_collection:handle_sync_entities"

                # start task
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
                )

                #
                # Inspecting statuses
                #

                #
                # START raw collections records: Get enriched records and find state deltas
                #
                # Shadow fast-path: if shadow is available, read pre-computed enriched
                # records from shadow (~7s) instead of running full decision maker
                # enrichment via trackmegetcoll (~100s+ at 100k scale).
                #

                shadow_threshold = int(vtenant_account.get("shadow_entity_threshold", 1000))
                shadow_enabled = int(vtenant_account.get("shadow_enabled", 0))
                use_shadow_for_sync = (
                    shadow_threshold > 0
                    and should_use_shadow(self.service, self.tenant_id, component, shadow_threshold, False, shadow_enabled=shadow_enabled)
                )

                delta_records = []
                delta_records_keys = set()
                delta_records_objects = set()
                delta_records_dict = {}

                if use_shadow_for_sync:
                    # Shadow fast-path: read enriched records from shadow, compare with KV store in Python
                    try:
                        shadow_start = time.time()
                        shadow_transform = f"trackme_{component}_shadow_tenant_{self.tenant_id}"
                        shadow_records = read_shadow_records(self.service, shadow_transform, instance_id)

                        # Build a dict of enriched records keyed by _key/keyid
                        shadow_dict = {}
                        for rec in shadow_records:
                            key = rec.get("keyid") or rec.get("_key")
                            if key:
                                shadow_dict[key] = rec

                        # Batch-read raw KV records to compare object_state
                        kv_records_for_compare = {}
                        if shadow_dict:
                            try:
                                kv_records_for_compare, _ = batch_find_records_by_key(
                                    inspect_collection, list(shadow_dict.keys())
                                )
                            except Exception as e:
                                logging.warning(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", '
                                    f'shadow sync: batch KV read failed, falling back to trackmegetcoll, exception="{e}"'
                                )
                                use_shadow_for_sync = False

                        if use_shadow_for_sync:
                            # Compare enriched object_state with raw KV store object_state
                            for key, enriched_rec in shadow_dict.items():
                                kv_rec = kv_records_for_compare.get(key)
                                if not kv_rec:
                                    continue

                                enriched_state = enriched_rec.get("object_state", "")
                                kv_state = kv_rec.get("object_state", "")

                                if enriched_state != kv_state:
                                    # Build a delta record matching the SPL output format
                                    enriched_rec["kvcoll_object_state"] = kv_state
                                    enriched_rec["kvcoll_anomaly_reason"] = kv_rec.get("anomaly_reason", "unknown")
                                    enriched_rec["kvcoll_latest_flip_time"] = kv_rec.get("latest_flip_time", "0")

                                    delta_records.append(enriched_rec)
                                    delta_records_keys.add(key)
                                    delta_records_objects.add(enriched_rec.get("object"))
                                    delta_records_dict[key] = enriched_rec

                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, '
                                f'shadow sync completed, shadow_records={len(shadow_records)}, delta_records={len(delta_records)}, run_time={round(time.time()-shadow_start, 3)}s'
                            )

                    except Exception as e:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", '
                            f'shadow sync failed, falling back to trackmegetcoll, exception="{e}"'
                        )
                        use_shadow_for_sync = False
                        delta_records = []
                        delta_records_keys = set()
                        delta_records_objects = set()
                        delta_records_dict = {}

                if not use_shadow_for_sync:
                    # Standard path: full enrichment via trackmegetcoll
                    search = remove_leading_spaces(
                        f"""\
                        | trackmegetcoll tenant_id="{self.tenant_id}" component="{component}" | fields - _raw | table *
                        | lookup trackme_{component}_tenant_{self.tenant_id} _key as keyid OUTPUT object_state as kvcoll_object_state, anomaly_reason as kvcoll_anomaly_reason, latest_flip_time as kvcoll_latest_flip_time
                        | where object_state!=kvcoll_object_state
                    """
                    )

                    kwargs_search = {
                        "earliest_time": "-5m",
                        "latest_time": "now",
                        "preview": "false",
                        "output_mode": "json",
                        "count": 0,
                    }

                    try:
                        reader = run_splunk_search(
                            self.service,
                            search,
                            kwargs_search,
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                delta_records.append(item)
                                delta_records_keys.add(item.get("keyid"))
                                delta_records_objects.add(item.get("object"))
                                delta_records_dict[item.get("keyid")] = item

                    except Exception as e:
                        msg = f'main search failed with exception="{str(e)}"'
                        logging.error(msg)
                        raise Exception(msg)

                #
                # END raw collections records: Get raw collection records using a Splunk search
                #

                #
                # Handle delta records (batch KV Store fetch to avoid N+1 query pattern)
                #

                inspectcollection_compare_records_start_time = time.time()

                # Batch-fetch all delta records from KV Store in a single call
                batch_kvrecords_dict = {}
                if delta_records_keys:
                    try:
                        batch_kvrecords_dict, _ = batch_find_records_by_key(
                            inspect_collection, list(delta_records_keys)
                        )
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, '
                            f'batch fetched {len(batch_kvrecords_dict)} KV records for {len(delta_records_keys)} delta keys'
                        )
                    except Exception as e:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, '
                            f'batch fetch failed, falling back to individual queries, exception="{str(e)}"'
                        )

                for item in delta_records:

                    item_key = item.get("keyid")
                    item_object = decode_unicode(item.get("object"))
                    item_alias = item.get("alias")
                    item_object_state = item.get("object_state")
                    item_object_category = item.get("object_category")
                    item_anomaly_reason = item.get("anomaly_reason")
                    item_monitored_state = item.get("monitored_state")
                    item_priority = item.get("priority")

                    # our delta state
                    collection_object_state = item.get("kvcoll_object_state")

                    # previous_anomaly_reason
                    collection_anomaly_reason = item.get(
                        "kvcoll_anomaly_reason", "unknown"
                    )

                    # previous flip time
                    try:
                        collection_latest_flip_time = float(
                            item.get("kvcoll_latest_flip_time", 0)
                        )
                    except Exception as e:
                        collection_latest_flip_time = 0

                    # disruption time
                    disruption_time = 0

                    # compare the object state with item_object_state using decisionmaker_collection_records_dict using the key
                    # if the object_state value is different, log the issue

                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, collection record object state is not consistent, object="{item_object}", object_id="{item_key}", in_collection_object_state="{collection_object_state}", in_result_object_state="{item_object_state}", in_collection_anomaly_reason="{collection_anomaly_reason}"'
                    )

                    # get the current kvrecord (from batch-fetched dict, fall back to individual query)
                    kvrecord_updated = False

                    try:
                        kvrecord = batch_kvrecords_dict.get(item_key)
                        if not kvrecord:
                            # Fallback: individual query if batch missed this key
                            kvrecord = inspect_collection.data.query(
                                query=json.dumps({"_key": item_key})
                            )[0]

                        # update the kvrecord object_state, status_message and anomaly_reason
                        kvrecord["object_state"] = item_object_state
                        kvrecord["status_message"] = item.get("status_message")
                        kvrecord["anomaly_reason"] = item_anomaly_reason
                        kvrecord["mtime"] = time.time()
                        kvrecord["latest_flip_time"] = time.time()
                        kvrecord["latest_flip_state"] = item_object_state

                        # process the KVstore record update
                        inspect_collection.data.update(item_key, json.dumps(kvrecord))

                        kvrecord_updated = True

                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, collection record object update successfully, object="{item_object}", object_id="{item_key}"'
                        )

                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, failed to update the KVstore record, object="{item_object}", collection_name="{inspect_collection_name}", exception="{str(e)}"'
                        )

                    # proceed with next steps
                    if kvrecord_updated:
                        try:

                            # calculate disruption time if current_state is green and previous_state was red
                            if (
                                item_object_state == "green"
                                and collection_object_state == "red"
                            ):
                                try:
                                    disruption_time = round(
                                        (time.time() - collection_latest_flip_time),
                                        2,
                                    )
                                except Exception as e:
                                    disruption_time = 0

                            flip_timestamp = time.strftime(
                                "%d/%m/%Y %H:%M:%S",
                                time.localtime(time.time()),
                            )
                            disruption_time_str = f', disruption_time="{disruption_time}"' if disruption_time and disruption_time > 0 else ""
                            flip_result = f'{flip_timestamp}, object="{item_object}" has flipped from previous_state="{collection_object_state}" to state="{item_object_state}" with anomaly_reason="{item_anomaly_reason}", previous_anomaly_reason="{collection_anomaly_reason}"{disruption_time_str}'

                            flip_record = {
                                "timeStr": flip_timestamp,
                                "tenant_id": self.tenant_id,
                                "alias": item_alias,
                                "keyid": item_key,
                                "object": item_object,
                                "object_category": item_object_category,
                                "object_state": item_object_state,
                                "object_previous_state": collection_object_state,
                                "priority": item_priority,
                                "latest_flip_time": time.time(),
                                "latest_flip_state": item_object_state,
                                "anomaly_reason": item_anomaly_reason,
                                "result": flip_result,
                            }

                            # add event_id
                            flip_record["event_id"] = hashlib.sha256(
                                json.dumps(flip_record).encode()
                            ).hexdigest()

                            trackme_gen_state(
                                index=tenant_indexes["trackme_summary_idx"],
                                sourcetype="trackme:flip",
                                source="flip_state_change_tracking",
                                event=flip_record,
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, TrackMe flipping event created successfully, record="{json.dumps(flip_record, indent=1)}"'
                            )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, object="{item_object}", task="{task_name}", task_instance_id={task_instance_id}, record="{json.dumps(flip_record, indent=1)}", failed to generate a flipping state event with exception="{e}"'
                            )

                        #
                        # SLA metrics
                        #

                        # create a list for SLA metrics generation
                        sla_metrics_records = []

                        if item_object_state == "green":
                            object_num_state = 1
                        elif item_object_state == "red":
                            object_num_state = 2
                        elif item_object_state == "orange":
                            object_num_state = 3
                        elif item_object_state == "blue":
                            object_num_state = 4
                        else:
                            object_num_state = 5

                        # add to our list
                        sla_metrics_records.append(
                            {
                                "tenant_id": self.tenant_id,
                                "object_id": item_key,
                                "object": item_object,
                                "alias": item_alias,
                                "object_category": item_object_category,
                                "monitored_state": item_monitored_state,
                                "priority": item_priority,
                                "metrics_event": {"object_state": object_num_state},
                            }
                        )

                        # call the SLA gen metrics function
                        sla_metrics_gen_start = time.time()
                        try:
                            sla_metrics = trackme_sla_gen_metrics(
                                self.tenant_id,
                                tenant_indexes.get("trackme_metric_idx"),
                                sla_metrics_records,
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, function trackme_sla_gen_metrics success {sla_metrics}, run_time={round(time.time()-sla_metrics_gen_start, 3)}, no_entities={len(sla_metrics_records)}'
                            )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, function trackme_sla_gen_metrics failed with exception {str(e)}'
                            )

                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, no_delta_records="{len(delta_records_keys)}", run_time="{round((time.time() - inspectcollection_compare_records_start_time), 3)}", collection="{inspect_collection_name}"'
                )

                #
                # END comparison
                #

                # end subtask
                task_duration = round(time.time()-task_start, 3)
                task_freq_manager.record_execution(task_name, task_duration)
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
                )

                #
                #
                #

                #
                # Call the trackme_register_tenant_component_summary
                #

                # Use threading to do an async call to the register summary without waiting for it to complete
                thread = threading.Thread(
                    target=self.register_component_summary_async,
                    args=(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        component,
                    ),
                )
                thread.start()
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, trackme_register_tenant_component_summary was requested.'
                )

                #
                # Refresh shadow copy async after component processing
                #

                shadow_thread = threading.Thread(
                    target=self.refresh_shadow_async,
                    args=(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        component,
                    ),
                    daemon=True,
                )
                shadow_thread.start()
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, refresh_shadow was requested.'
                )

        #
        # task: untracked_entities
        #

        #
        # splk-dsm - untracked entities
        #

        # context: this activity tracks and maintain state for untracked entities
        # untracked entities are entities which are entirely out of the scope of any trackers, and therefore not maintained otherwise

        task_name = "untracked_entities"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            task_start = time.time()

            # Short-circuit: check if any enabled component has stale entities before running expensive SPL
            # An entity is considered untracked if tracker_runtime is older than 15 minutes (900s)
            # Note: tracker_runtime is stored as a string in KV Store (written via SPL outputlookup),
            # so we read a lightweight projection and compare in Python to avoid type mismatch issues.
            # Uses paginated reads (limit+skip) to handle large collections safely.
            has_untracked = False
            stale_threshold = time.time() - 900
            chunk_size = 5000

            for comp_setting, comp_suffix in [
                ("tenant_dsm_enabled", "dsm"),
                ("tenant_dhm_enabled", "dhm"),
            ]:
                if vtenant_record.get(comp_setting) == True:
                    try:
                        comp_collection = self.service.kvstore[f"kv_trackme_{comp_suffix}_tenant_{self.tenant_id}"]
                        skip = 0
                        while True:
                            # Fetch only _key and tracker_runtime fields for a lightweight check
                            records = comp_collection.data.query(
                                fields="_key,tracker_runtime", limit=chunk_size, skip=skip
                            )
                            if not records:
                                break
                            for rec in records:
                                runtime_val = rec.get("tracker_runtime")
                                if runtime_val is None or runtime_val == "":
                                    has_untracked = True
                                    break
                                try:
                                    if float(runtime_val) < stale_threshold:
                                        has_untracked = True
                                        break
                                except (ValueError, TypeError):
                                    has_untracked = True
                                    break
                            if has_untracked:
                                break
                            # Advance by actual count; stop only on an empty page.
                            skip += len(records)
                        if has_untracked:
                            break
                    except Exception as e:
                        # If the pre-check fails, assume there may be untracked entities and proceed
                        logging.debug(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", '
                            f'short-circuit pre-check failed for {comp_suffix}, proceeding with full check, exception="{str(e)}"'
                        )
                        has_untracked = True
                        break

            if not has_untracked:
                task_duration = round(time.time() - task_start, 3)
                task_freq_manager.record_execution(task_name, task_duration)
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                    f'no untracked entities found (all tracker_runtime within 15m), skipping expensive SPL, '
                    f'run_time="{task_duration}", task has terminated.'
                )
            else:

                # start task
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task, untracked entities detected.'
                )

                # Run DSM and DHM untracked entities in parallel using a shared function
                def _process_untracked_component(comp):
                    """Process untracked entities for a single component (DSM or DHM)."""
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{comp}", task="{task_name}", task_instance_id={task_instance_id}, inspecting untracked entities now.'
                    )

                    kwargs_oneshot = {
                        "earliest_time": "-5m",
                        "latest_time": "now",
                        "output_mode": "json",
                        "count": 0,
                    }

                    untracked_count = 0
                    processed_objects = []

                    search_str = f"""\
                        | inputlookup trackme_{comp}_tenant_{self.tenant_id} | eval key=_key

                        ``` target any entity that has not been updated since more than 15m ```
                        | eval time_sec_since_inspection=now()-tracker_runtime
                        | where ( time_sec_since_inspection>900 OR isnull(tracker_runtime) )

                        ``` called the offline abstract macro version ```
                        `trackme_{comp}_tracker_abstract({self.tenant_id})`

                        ``` collects latest collection state into the summary index ```
                        | `trackme_collect_state("current_state_tracking:splk-{comp}:{self.tenant_id}", "object", "{self.tenant_id}")`

                        ``` output flipping change status if changes ```
                        | trackmesplkgetflipping tenant_id="{self.tenant_id}" object_category="splk-{comp}"

                        ``` update the KVstore collection ```
                        | `trackme_outputlookup_tracker_health(trackme_{comp}_tenant_{self.tenant_id}, key)`

                        ``` update the delay metric only ```
                        | `trackme_mcollect(object, splk-{comp}, "metric_name:trackme.splk.feeds.lag_event_sec=data_last_lag_seen", "tenant_id, object_category, object", "{self.tenant_id}")`

                        ``` summarize job ```
                        | stats count as report_entities_count, values(object) as objects by tenant_id
                    """

                    try:
                        reader = run_splunk_search(
                            self.service,
                            search_str,
                            kwargs_oneshot,
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                untracked_count += 1
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{comp}", task="{task_name}", task_instance_id={task_instance_id}, entities_count="{len(item)}"'
                                )
                                processed_objects = item.get("objects", [])

                        if untracked_count == 0:
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{comp}", task="{task_name}", task_instance_id={task_instance_id}, there are no untracked entities currently.'
                            )

                    except Exception as e:
                        trackme_register_tenant_object_summary(
                            session_key,
                            self._metadata.searchinfo.splunkd_uri,
                            self.tenant_id,
                            "all",
                            report_name,
                            "failure",
                            time.time(),
                            str(time.time() - start),
                            str(e),
                            "-5m",
                            "now",
                        )
                        msg = f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{self.tenant_id}", component="{comp}", main search failed with exception="{str(e)}"'
                        logging.error(msg)
                        raise Exception(msg)

                    if processed_objects:
                        # ensure list type
                        if isinstance(processed_objects, str):
                            processed_objects = [processed_objects]

                        handler_events_records = []
                        for object_name in processed_objects:
                            handler_events_records.append(
                                {
                                    "object": object_name,
                                    "object_category": f"splk-{comp}",
                                    "object_id": hashlib.sha256(
                                        object_name.encode("utf-8")
                                    ).hexdigest(),
                                    "handler": "health_tracker:untracked_entities",
                                    "handler_message": "Entity was inspected by the heath tracker, it is out of the scope of any hybrid tracker due to high delay and/or latency.",
                                    "handler_troubleshoot_search": f"index=_internal sourcetype=trackme:custom_commands:trackmetrackerhealth tenant_id={self.tenant_id} component={comp} task=untracked_entities",
                                    "handler_time": time.time(),
                                }
                            )

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
                                f'tenant_id="{self.tenant_id}", component="{comp}", could not send notification event, exception="{e}"'
                            )

                # Determine enabled components and run in parallel
                untracked_components = []
                if vtenant_record.get("tenant_dsm_enabled") == True:
                    untracked_components.append("dsm")
                if vtenant_record.get("tenant_dhm_enabled") == True:
                    untracked_components.append("dhm")

                if len(untracked_components) > 1:
                    # Run DSM and DHM in parallel
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        futures = {
                            executor.submit(_process_untracked_component, comp): comp
                            for comp in untracked_components
                        }
                        for future in as_completed(futures):
                            comp = futures[future]
                            try:
                                future.result()
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{comp}", '
                                    f'task="{task_name}", task_instance_id={task_instance_id}, '
                                    f'parallel untracked_entities failed with exception="{str(e)}"'
                                )
                elif len(untracked_components) == 1:
                    # Only one component enabled, run directly
                    _process_untracked_component(untracked_components[0])

                # end task
                task_duration = round(time.time()-task_start, 3)
                task_freq_manager.record_execution(task_name, task_duration)
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
                )
        else:
            task_freq_manager.increment_skipped(task_name)

        #
        # task: duplicated_entities
        #

        task_name = "duplicated_entities"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            task_start = time.time()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # all components except splk-wlk
            #
            # context: this situation is not expected, but if we have duplicated entities, we need to verify and purge them

            # splk-wlk - duplicated entities
            #
            # context: this activity tracks for duplicated entities in the Workload component
            # under some rare circumstances, the Splunk scheduler logs may lack the user context, althrough we implement several safeties
            # if this happens, we need to verify and purge any duplicated entity with the system user context instead of the proper user context

            for component in ("dsm", "dhm", "mhm", "wlk", "flx", "fqm"):

                if (
                    vtenant_record.get(f"tenant_{component}_enabled") == True
                    and vtenant_record.get("tenant_replica") == False
                ):
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, inspecting entities now.'
                    )

                    # kwargs
                    kwargs_oneshot = {
                        "earliest_time": "-5m",
                        "latest_time": "now",
                        "output_mode": "json",
                        "count": 0,
                    }

                    duplicated_entities_count = 0
                    duplicated_entities_list = []

                    # specific search for wlk
                    if component == "wlk":
                        duplicated_entities_search = remove_leading_spaces(
                            f"""\
                            | inputlookup trackme_wlk_tenant_{self.tenant_id} | eval keyid=_key
                            | fields keyid, account, app, user, savedsearch_name, object, last_seen
                            | eventstats count as dcount by account, app, savedsearch_name
                            | where dcount>1
                            | sort - 0 savedsearch_name, last_seen
                        """
                        )

                    else:  # other components
                        duplicated_entities_search = remove_leading_spaces(
                            f"""\
                            | inputlookup trackme_{component}_tenant_{self.tenant_id} | eval keyid=_key
                            | sort 0 object
                            | eventstats count as dcount by object
                            | streamstats count as rank by object
                            | where dcount>1
                            ``` handle rank if the duplicated is due to FIPS migration ```
                            | eval rank=if(len(keyid) == 64, 2, 1)
                            | where rank=1
                        """
                        )

                    # run the main report, every result is a Splunk search to be executed on its own thread
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, executing search="{duplicated_entities_search}"'
                    )
                    try:
                        reader = run_splunk_search(
                            self.service,
                            duplicated_entities_search,
                            kwargs_oneshot,
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                duplicated_entities_count += 1
                                duplicated_entities_list.append(item.get("keyid"))
                                logging.warning(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, detected duplicated entity, keyid="{item.get("keyid")}", object="{item.get("object")}"'
                                )

                        if duplicated_entities_count == 0:
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, there are no duplicated entities currently.'
                            )

                    except Exception as e:
                        # Call the component register
                        trackme_register_tenant_object_summary(
                            session_key,
                            self._metadata.searchinfo.splunkd_uri,
                            self.tenant_id,
                            "all",
                            report_name,
                            "failure",
                            time.time(),
                            str(time.time() - start),
                            str(e),
                            "-5m",
                            "now",
                        )
                        msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, main search failed with exception="{str(e)}"'
                        logging.error(msg)
                        raise Exception(msg)

                    # process if needed
                    if duplicated_entities_count > 0:

                        # target
                        if component == "dsm":
                            target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_dsm/write/ds_delete"

                        elif component == "dhm":
                            target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_dhm/write/dh_delete"

                        if component == "mhm":
                            target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_mhm/write/mh_delete"

                        if component == "flx":
                            target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_flx/write/flx_delete"

                        if component == "fqm":
                            target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_fqm/write/fqm_delete"

                        if component == "wlk":
                            target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_wlk/write/wlk_delete"

                        # data
                        # turn duplicated_entities_list into a comma separated string

                        # update comment
                        if component == "wlk":
                            update_comment = "One or more duplicated entities were detected by the health tracker, this condition can happen when Splunk scheduler logs lack the user context, automated purge of these entities."
                        else:
                            update_comment = "One or more duplicated entities were detected by the health tracker, this condition is not expected and TrackMe needs to purge duplicates to avoid further issues."

                        duplicated_entities_list = ",".join(duplicated_entities_list)
                        post_data = {
                            "tenant_id": self.tenant_id,
                            "keys_list": duplicated_entities_list,
                            "deletion_type": "temporary",
                            "update_comment": update_comment,
                        }

                        try:
                            response = session.post(
                                target_url,
                                data=json.dumps(post_data),
                                verify=False,
                                timeout=600,
                            )
                            msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, duplicated entities purge successful, results="{json.dumps(response.json(), indent=2)}"'
                            logging.info(msg)

                        except Exception as e:
                            msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, duplicated entities purge failed with exception="{str(e)}"'
                            logging.info(msg)

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        #
        # task: check_trackers_collections
        #

        # this task is designed to verify that trackers referenced in the dedicated collections are still present in the system
        # if not, it will remove the tracker from the collection

        task_name = "check_trackers_collections"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            task_start = time.time()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            def check_trackers_existence(vtenant_record, component):
                logging.info(f"Checking tracker definitions for component: {component}")

                # Load the tracker collection associated with the component (source of truth)
                tracker_collection_name = (
                    f"kv_trackme_{component}_hybrid_trackers_tenant_{self.tenant_id}"
                )
                tracker_collection = self.service.kvstore[tracker_collection_name]

                # Get all the tracker records
                tracker_records = tracker_collection.data.query()

                for tracker_record in tracker_records:
                    record_knowledge_objects = json.loads(
                        tracker_record.get("knowledge_objects", "{}")
                    )

                    # get the reports list
                    reports_list = record_knowledge_objects.get("reports", [])

                    # identify the main tracker (tracker_main_name) which contains _tracker_tenant_ in the name
                    tracker_main_name = None
                    for report_name in reports_list:
                        if "_tracker_tenant_" in report_name:
                            tracker_main_name = report_name
                            break

                    # Verify the existence of the main tracker, if it cannot be found in the system, the entire record will be removed from the collection
                    purge_tracker_record = False

                    # the main tracker was found in the record
                    if tracker_main_name:

                        # process
                        savedsearch_definition = None
                        try:
                            savedsearch = self.service.saved_searches[tracker_main_name]
                            savedsearch_definition = savedsearch.content["search"]
                            savedsearch_content = savedsearch.content
                        except Exception as e:
                            savedsearch_definition = None
                            savedsearch_content = {}

                        # purge if necessary
                        if not savedsearch_definition:
                            purge_tracker_record = True
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, the main tracker="{tracker_main_name}" does not exist anymore, the tracker record will be removed from the collection.'
                            )

                    else:  # the main tracker was not found in the record, the record is considered as invalid and will be removed from the collection
                        purge_tracker_record = True
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, the tracker record="{tracker_record}" is invalid, the tracker record will be removed from the collection.'
                        )

                    # purge if necessary
                    if purge_tracker_record:

                        try:
                            tracker_collection.data.delete(
                                json.dumps({"_key": tracker_record.get("_key")})
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, the tracker record was successfully removed from the collection.'
                            )

                            # Also clean the orphaned report/macro references from tenant_{component}_hybrid_objects
                            # to prevent recreate_missing_tracker_records() from re-creating this record
                            try:
                                hybrid_objects_json = vtenant_record.get(f"tenant_{component}_hybrid_objects")
                                if hybrid_objects_json:
                                    hybrid_objects = json.loads(hybrid_objects_json)
                                    vtenant_reports = hybrid_objects.get("reports", [])
                                    vtenant_macros = hybrid_objects.get("macros", [])

                                    # Remove all reports and macros that belong to this tracker
                                    orphan_reports = set(record_knowledge_objects.get("reports", []))
                                    orphan_macros = set(record_knowledge_objects.get("macros", []))

                                    cleaned_reports = [r for r in vtenant_reports if r not in orphan_reports]
                                    cleaned_macros = [m for m in vtenant_macros if m not in orphan_macros]

                                    if len(cleaned_reports) != len(vtenant_reports) or len(cleaned_macros) != len(vtenant_macros):
                                        hybrid_objects["reports"] = cleaned_reports
                                        hybrid_objects["macros"] = cleaned_macros
                                        vtenant_record[f"tenant_{component}_hybrid_objects"] = json.dumps(hybrid_objects, indent=2)

                                        self.service.kvstore["kv_trackme_virtual_tenants"].data.update(
                                            str(vtenant_record["_key"]), json.dumps(vtenant_record)
                                        )
                                        logging.info(
                                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, cleaned orphaned references from tenant_{component}_hybrid_objects.'
                                        )
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, failed to clean orphaned references from tenant_{component}_hybrid_objects, exception="{str(e)}"'
                                )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, the tracker record failed to be removed from the collection, exception="{str(e)}"'
                            )

            def recreate_missing_tracker_records(vtenant_record, component):
                """
                Recreate hybrid tracker records in dedicated KVstore if they exist in 
                tenant_<component>_hybrid_objects but are missing from the dedicated collection.
                """
                logging.info(f"Checking for missing tracker records to recreate for component: {component}")

                # Load the tenant hybrid objects from vtenant_record (central source)
                hybrid_objects_json = vtenant_record.get(f"tenant_{component}_hybrid_objects")

                if not hybrid_objects_json:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, No hybrid objects found in vtenant_record for component "{component}", skipping recreation check.'
                    )
                    return

                try:
                    hybrid_objects = json.loads(hybrid_objects_json)
                except Exception as e:
                    logging.warning(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Failed to parse hybrid_objects JSON, exception="{str(e)}"'
                    )
                    return

                reports_list = hybrid_objects.get("reports", [])
                macros_list = hybrid_objects.get("macros", [])

                if not reports_list:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, No reports found in hybrid_objects for component "{component}", skipping recreation check.'
                    )
                    return

                # Load the dedicated tracker collection
                tracker_collection_name = (
                    f"kv_trackme_{component}_hybrid_trackers_tenant_{self.tenant_id}"
                )
                tracker_collection = self.service.kvstore[tracker_collection_name]

                # Get existing tracker records from dedicated collection
                existing_tracker_records = tracker_collection.data.query()
                existing_tracker_names = set()

                for record in existing_tracker_records:
                    tracker_name = record.get("tracker_name")
                    if tracker_name:
                        existing_tracker_names.add(tracker_name)

                # Process wrapper reports to extract tracker names
                # Pattern: trackme_<component>_hybrid_<tracker_name>_wrapper_tenant_<tenant_id>
                wrapper_prefix = f"trackme_{component}_hybrid_"
                wrapper_suffix = f"_wrapper_tenant_{self.tenant_id}"

                # Track trackers we've already processed to avoid duplicates
                processed_trackers = {}

                for report_name in reports_list:
                    # Only process wrapper reports to identify trackers
                    if "_wrapper_" not in report_name:
                        continue

                    # Extract tracker_name from wrapper report name
                    # Pattern: trackme_<component>_hybrid_<tracker_name>_wrapper_tenant_<tenant_id>
                    if report_name.startswith(wrapper_prefix) and report_name.endswith(wrapper_suffix):
                        # Remove prefix and suffix to get tracker_name
                        tracker_name = report_name[len(wrapper_prefix):-len(wrapper_suffix)]

                        # Check if this tracker exists in the dedicated collection
                        if tracker_name not in existing_tracker_names and tracker_name not in processed_trackers:
                            # Collect all reports and macros for this tracker
                            tracker_reports = []
                            tracker_macros = []

                            # Find all reports that belong to this tracker
                            # Use explicit expected report name construction for precise matching
                            # This avoids issues with reserved words (abstract, wrapper, tracker) and substring matches
                            # Reports patterns vary by component:
                            # - Components with abstract (dsm, dhm, mhm): 
                            #   * trackme_<component>_hybrid_abstract_<tracker_name>_tenant_<tenant_id>
                            #   * trackme_<component>_hybrid_<tracker_name>_wrapper_tenant_<tenant_id>
                            #   * trackme_<component>_hybrid_<tracker_name>_tracker_tenant_<tenant_id>
                            # - Components without abstract (flx, wlk, fqm):
                            #   * trackme_<component>_hybrid_<tracker_name>_wrapper_tenant_<tenant_id>
                            #   * trackme_<component>_hybrid_<tracker_name>_tracker_tenant_<tenant_id>

                            # Construct expected report names explicitly for exact matching
                            expected_reports = []
                            # Components with abstract reports: dsm, dhm, mhm
                            if component in ["dsm", "dhm", "mhm"]:
                                expected_reports.append(f"trackme_{component}_hybrid_abstract_{tracker_name}_tenant_{self.tenant_id}")
                            # All components have wrapper and tracker reports
                            expected_reports.append(f"trackme_{component}_hybrid_{tracker_name}_wrapper_tenant_{self.tenant_id}")
                            expected_reports.append(f"trackme_{component}_hybrid_{tracker_name}_tracker_tenant_{self.tenant_id}")

                            # Match reports using exact names
                            for report in reports_list:
                                if report in expected_reports:
                                    tracker_reports.append(report)

                            # Find all macros that belong to this tracker
                            # Note: Macros are only applicable to dsm, dhm, mhm components
                            # Macro pattern: trackme_<component>_hybrid_root_constraint_<tracker_name>_tenant_<tenant_id>
                            # Use exact expected macro name for matching (similar to reports above)
                            if component in ["dsm", "dhm", "mhm"]:
                                expected_macro = f"trackme_{component}_hybrid_root_constraint_{tracker_name}_tenant_{self.tenant_id}"
                                if expected_macro in macros_list:
                                    tracker_macros.append(expected_macro)

                            # Only proceed if we have at least one report
                            if tracker_reports:
                                processed_trackers[tracker_name] = {
                                    "reports": tracker_reports,
                                    "macros": tracker_macros
                                }

                # Recreate missing tracker records
                # Track reports to clean from vtenant hybrid_objects if saved searches don't exist
                orphan_reports_to_clean = []
                orphan_macros_to_clean = []

                for tracker_name, knowledge_data in processed_trackers.items():

                    # Before re-creating, verify that the main saved search (tracker report) actually exists
                    # This prevents the loop where we keep re-creating records for deleted trackers
                    tracker_report_name = None
                    for report_name in knowledge_data["reports"]:
                        if "_tracker_tenant_" in report_name:
                            tracker_report_name = report_name
                            break

                    # Fallback: build expected tracker report name if not found in reports list
                    if not tracker_report_name:
                        tracker_report_name = f"trackme_{component}_hybrid_{tracker_name}_tracker_tenant_{self.tenant_id}"

                    try:
                        savedsearch = self.service.saved_searches[tracker_report_name]
                        savedsearch_definition = savedsearch.content.get("search")
                    except Exception:
                        savedsearch_definition = None

                    if not savedsearch_definition:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, '
                            f'Skipping recreation of tracker record for "{tracker_name}" because main saved search "{tracker_report_name}" does not exist. '
                            f'Cleaning orphaned references from tenant_{component}_hybrid_objects.'
                        )
                        orphan_reports_to_clean.extend(knowledge_data["reports"])
                        orphan_macros_to_clean.extend(knowledge_data.get("macros", []))
                        continue

                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Recreating missing tracker record for "{tracker_name}" in dedicated collection.'
                    )

                    # Build knowledge_objects structure (without properties as per requirement)
                    knowledge_objects = {
                        "reports": knowledge_data["reports"]
                    }

                    # Add macros if present (only for components that use them)
                    if knowledge_data["macros"]:
                        knowledge_objects["macros"] = knowledge_data["macros"]

                    # Create the tracker record
                    new_tracker_record = {
                        "_key": hashlib.sha256(tracker_name.encode("utf-8")).hexdigest(),
                        "tracker_name": tracker_name,
                        "knowledge_objects": json.dumps(knowledge_objects, indent=2),
                        "created_time": time.time(),
                        "created_by": "health_tracker"
                    }

                    # Add component-specific fields
                    if component == "wlk":
                        # wlk tracker records require tracker_type field
                        # tracker_name format is: {tracker_type}_{uuid}
                        # Extract tracker_type from tracker_name
                        # Note: Some tracker types contain underscores (e.g., inactive_entities, splunkcloud_svc)
                        # so we need to check for multi-word types first before falling back to simple split
                        valid_wlk_tracker_types = [
                            "main", "introspection", "scheduler", "metadata", 
                            "orphan", "inactive_entities", "splunkcloud_svc", "notable"
                        ]
                        extracted_tracker_type = None
                        # First, try to match known multi-word tracker types
                        for valid_type in valid_wlk_tracker_types:
                            if tracker_name.startswith(valid_type + "_") or tracker_name == valid_type:
                                extracted_tracker_type = valid_type
                                break
                        # If no match found, fall back to simple split for single-word types
                        if not extracted_tracker_type and "_" in tracker_name:
                            first_segment = tracker_name.split("_", 1)[0]
                            if first_segment in valid_wlk_tracker_types:
                                extracted_tracker_type = first_segment

                        if extracted_tracker_type:
                            new_tracker_record["tracker_type"] = extracted_tracker_type
                        else:
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Could not extract valid tracker_type from tracker_name="{tracker_name}" (expected format: tracker_type_uuid)'
                            )
                    elif component in ["flx", "fqm"]:
                        # flx and fqm use tracker_id field
                        new_tracker_record["tracker_id"] = tracker_name

                    try:
                        # Final safety check: verify the tracker doesn't exist before insertion
                        final_check = tracker_collection.data.query(
                            query=json.dumps({"tracker_name": tracker_name})
                        )
                        if not final_check:
                            tracker_collection.data.insert(json.dumps(new_tracker_record))
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Successfully recreated tracker record for "{tracker_name}" in dedicated collection.'
                            )
                        else:
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Tracker "{tracker_name}" already exists in dedicated collection, skipping recreation.'
                            )
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Failed to recreate tracker record for "{tracker_name}", exception: {str(e)}'
                        )

                # Clean orphaned references from tenant_{component}_hybrid_objects
                if orphan_reports_to_clean or orphan_macros_to_clean:
                    try:
                        hybrid_objects_json = vtenant_record.get(f"tenant_{component}_hybrid_objects")
                        if hybrid_objects_json:
                            hybrid_objects = json.loads(hybrid_objects_json)
                            vtenant_reports = hybrid_objects.get("reports", [])
                            vtenant_macros = hybrid_objects.get("macros", [])

                            orphan_reports_set = set(orphan_reports_to_clean)
                            orphan_macros_set = set(orphan_macros_to_clean)

                            cleaned_reports = [r for r in vtenant_reports if r not in orphan_reports_set]
                            cleaned_macros = [m for m in vtenant_macros if m not in orphan_macros_set]

                            if len(cleaned_reports) != len(vtenant_reports) or len(cleaned_macros) != len(vtenant_macros):
                                hybrid_objects["reports"] = cleaned_reports
                                hybrid_objects["macros"] = cleaned_macros
                                vtenant_record[f"tenant_{component}_hybrid_objects"] = json.dumps(hybrid_objects, indent=2)

                                self.service.kvstore["kv_trackme_virtual_tenants"].data.update(
                                    str(vtenant_record["_key"]), json.dumps(vtenant_record)
                                )
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, '
                                    f'cleaned {len(vtenant_reports) - len(cleaned_reports)} orphaned report(s) and {len(vtenant_macros) - len(cleaned_macros)} orphaned macro(s) from tenant_{component}_hybrid_objects.'
                                )
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, '
                            f'failed to clean orphaned references from tenant_{component}_hybrid_objects, exception="{str(e)}"'
                        )

            # Main logic
            components = ["dsm", "dhm", "mhm", "flx", "wlk", "fqm"]
            for component in components:
                if vtenant_record.get(f"tenant_{component}_enabled"):
                    check_trackers_existence(vtenant_record, component)
                    recreate_missing_tracker_records(vtenant_record, component)

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        #
        # task: check_trackers
        #

        task_name = "check_trackers_definition"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            task_start = time.time()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            def check_trackers_definition(vtenant_record, component):
                logging.info(f"Checking tracker definitions for component: {component}")

                # Load the tracker collection associated with the component (source of truth)
                tracker_collection_name = (
                    f"kv_trackme_{component}_hybrid_trackers_tenant_{self.tenant_id}"
                )
                tracker_collection = self.service.kvstore[tracker_collection_name]

                # Get all the tracker records
                tracker_records = tracker_collection.data.query()

                # Initialize empty sets for the reports and macros that should be in the vtenant_record
                truth_reports = set()
                truth_macros = set()

                for tracker_record in tracker_records:
                    record_knowledge_objects = json.loads(
                        tracker_record.get("knowledge_objects", "{}")
                    )

                    # Collect the reports and macros from the tracker record's knowledge_objects
                    truth_reports.update(record_knowledge_objects.get("reports", []))
                    truth_macros.update(record_knowledge_objects.get("macros", []))

                # Load the current tenant hybrid objects from vtenant_record (destination)
                hybrid_objects_json = vtenant_record.get(
                    f"tenant_{component}_hybrid_objects"
                )

                if hybrid_objects_json:
                    # Load the JSON object from the hybrid_objects field
                    hybrid_objects = json.loads(hybrid_objects_json)
                else:
                    # If no existing hybrid_objects, initialize an empty structure
                    hybrid_objects = {"reports": [], "macros": []}

                vtenant_reports = set(hybrid_objects.get("reports", []))
                vtenant_macros = set(hybrid_objects.get("macros", []))

                # Compare and find missing reports/macros in the vtenant_record
                missing_reports = truth_reports - vtenant_reports
                missing_macros = truth_macros - vtenant_macros

                # If there are any missing reports or macros, add them to the vtenant_record
                if missing_reports or missing_macros:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Missing reports: {missing_reports} or macros: {missing_macros} in vtenant_record.'
                    )

                    # Update the vtenant_record with missing reports and macros
                    hybrid_objects["reports"] = list(vtenant_reports.union(truth_reports))
                    hybrid_objects["macros"] = list(vtenant_macros.union(truth_macros))

                    # Save the updated hybrid objects back to the vtenant_record
                    vtenant_record[f"tenant_{component}_hybrid_objects"] = json.dumps(
                        hybrid_objects, indent=2
                    )

                    try:
                        self.service.kvstore["kv_trackme_virtual_tenants"].data.update(
                            str(vtenant_record["_key"]), json.dumps(vtenant_record)
                        )
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, vtenant_record updated successfully.'
                        )
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Failed to update vtenant_record, exception: {str(e)}'
                        )

            def check_trackers_existence_in_dedicated_kvstore(vtenant_record, component):
                logging.info(f"Checking tracker existence in dedicated KVstore for component: {component}")

                # Load the central KVstore collection to get all tracker records
                central_collection_name = f"kv_trackme_{component}_tenant_{self.tenant_id}"
                try:
                    central_collection = self.service.kvstore[central_collection_name]
                    central_records = central_collection.data.query()
                except Exception as e:
                    logging.warning(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Central collection "{central_collection_name}" not found or accessible, exception: {str(e)}'
                    )
                    return

                # Load the dedicated tracker collection
                tracker_collection_name = (
                    f"kv_trackme_{component}_hybrid_trackers_tenant_{self.tenant_id}"
                )
                tracker_collection = self.service.kvstore[tracker_collection_name]

                # Get existing tracker records from dedicated collection
                existing_tracker_records = tracker_collection.data.query()
                existing_tracker_names = set()

                for record in existing_tracker_records:
                    tracker_name = record.get("tracker_name")
                    if tracker_name:
                        existing_tracker_names.add(tracker_name)

                # Track tracker names being processed in this batch to prevent duplicates
                processing_tracker_names = set()

                # Process each central record to find tracker names
                for central_record in central_records:
                    tracker_name = central_record.get("tracker_name")
                    if not tracker_name:
                        continue

                    # Check if tracker_name is a JSON array (concurrent tracker format)
                    # If it's a JSON array, skip it - these are normalized tracker names, not full report names
                    # We only process full report names that match the hybrid pattern
                    try:
                        if isinstance(tracker_name, str):
                            parsed_tracker_name = json.loads(tracker_name)
                            if isinstance(parsed_tracker_name, list):
                                # This is a JSON array of normalized tracker names, skip it
                                # These are from concurrent trackers and don't need hybrid tracker records
                                continue
                    except (json.JSONDecodeError, TypeError):
                        # Not a JSON array, continue processing as a string
                        pass

                    # Extract the base tracker name by removing _wrapper_tenant_ or _tracker_tenant_ suffix
                    base_tracker_name = None
                    if "_wrapper_tenant_" in tracker_name:
                        base_tracker_name = tracker_name.split("_wrapper_tenant_")[0]
                    elif "_tracker_tenant_" in tracker_name:
                        base_tracker_name = tracker_name.split("_tracker_tenant_")[0]

                    if not base_tracker_name:
                        continue

                    # Remove the trackme_<component>_hybrid_ prefix to get the actual tracker name
                    # This applies to all components that follow this naming convention
                    expected_prefix = f"trackme_{component}_hybrid_"
                    if base_tracker_name.startswith(expected_prefix):
                        actual_tracker_name = base_tracker_name.replace(expected_prefix, "", 1)
                    else:
                        actual_tracker_name = base_tracker_name

                    # Check if this tracker exists in the dedicated collection (by name or ID)
                    # Also check if we're already processing this tracker name in this batch
                    if (actual_tracker_name not in existing_tracker_names and
                        actual_tracker_name not in processing_tracker_names):

                        # Add to processing set to prevent duplicates in this batch
                        processing_tracker_names.add(actual_tracker_name)

                        # Before creating, verify the main saved search (tracker report) actually exists
                        # This prevents re-creating records for trackers whose saved searches have been deleted
                        tracker_report_name = tracker_name if "_tracker_tenant_" in tracker_name else None
                        if not tracker_report_name:
                            # Build expected tracker report name
                            tracker_report_name = f"trackme_{component}_hybrid_{actual_tracker_name}_tracker_tenant_{self.tenant_id}"

                        try:
                            savedsearch = self.service.saved_searches[tracker_report_name]
                            savedsearch_definition = savedsearch.content.get("search")
                        except Exception:
                            savedsearch_definition = None

                        if not savedsearch_definition:
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, '
                                f'Skipping creation of tracker record for "{actual_tracker_name}" because main saved search "{tracker_report_name}" does not exist.'
                            )
                            continue

                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Tracker "{actual_tracker_name}" not found in dedicated collection, creating record.'
                        )

                        # Create a new tracker record in the dedicated collection
                        # Build knowledge_objects with both wrapper and tracker reports
                        reports_list = []

                        # Add both wrapper and tracker reports
                        wrapper_name = tracker_name.replace("_tracker_tenant_", "_wrapper_tenant_")
                        reports_list = [wrapper_name, tracker_name]

                        # Build knowledge_objects structure
                        knowledge_objects = {
                            "reports": reports_list
                        }

                        # Macros are only applicable to dsm, dhm, mhm components
                        if component in ["dsm", "dhm", "mhm"]:
                            # Extract the tracker identifier from the base tracker name
                            # Example: trackme_dsm_hybrid_tracker-iew8hkxv -> tracker-iew8hkxv
                            if "_hybrid_" in base_tracker_name:
                                tracker_identifier = base_tracker_name.split("_hybrid_")[1]
                                macro_name = f"trackme_{component}_hybrid_root_constraint_{tracker_identifier}_tenant_{self.tenant_id}"
                                knowledge_objects["macros"] = [macro_name]

                        new_tracker_record = {
                            "tracker_name": actual_tracker_name,
                            "tracker_id": actual_tracker_name,  # tracker_id should equal tracker_name
                            "knowledge_objects": json.dumps(knowledge_objects, indent=2),
                            "created_time": time.time(),
                            "created_by": "health_tracker"
                        }

                        try:
                            # Final safety check: verify the tracker doesn't exist before insertion
                            final_check = tracker_collection.data.query(query=json.dumps({"tracker_name": actual_tracker_name}))
                            if not final_check:
                                tracker_collection.data.insert(json.dumps(new_tracker_record))
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Successfully created tracker record for "{actual_tracker_name}" in dedicated collection.'
                                )
                            else:
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Tracker "{actual_tracker_name}" already exists in dedicated collection, skipping creation.'
                                )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, Failed to create tracker record for "{actual_tracker_name}", exception: {str(e)}'
                            )

            # Main logic
            components = ["dsm", "dhm", "mhm", "flx", "wlk", "fqm"]
            for component in components:
                if vtenant_record.get(f"tenant_{component}_enabled"):
                    check_trackers_definition(vtenant_record, component)
                    check_trackers_existence_in_dedicated_kvstore(vtenant_record, component)

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        #
        # task: check_alerts_definition
        #

        task_name = "check_alerts_definition"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            task_start = time.time()

            #
            # Verify for each tenant record the content of tenant_alert_objects
            # - load the tenant_alert_objects object
            # - For each alert, verify that the alert exists in the system
            # - if not, remove the alert from the tenant_alert_objects object and update the record
            #

            def check_alerts_definition(alert_name):

                # get the current search definition
                try:
                    alert_current = self.service.saved_searches[alert_name]
                    alert_current_search = alert_current.content.get("search")
                    return True

                except Exception as e:
                    return False

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # Load the tenant_alert_objects object
            tenant_alert_objects = vtenant_record.get("tenant_alert_objects", {})
            if tenant_alert_objects:
                try:
                    tenant_alert_objects = json.loads(tenant_alert_objects)
                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, Failed to load tenant_alert_objects, exception: {str(e)}'
                    )
                    tenant_alert_objects = {}

            # alerts is a list stored in "alerts" key
            alerts = tenant_alert_objects.get("alerts", [])

            # verify each alert
            alerts_were_removed = False
            for alert_name in alerts:
                alert_exists = check_alerts_definition(alert_name)

                if not alert_exists:
                    logging.warning(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, alert="{alert_name}" not found in saved searches, will be removed from tenant_alert_objects'
                    )
                    alerts.remove(alert_name)
                    if not alerts_were_removed:
                        alerts_were_removed = True

            # save the updated tenant_alert_objects
            if alerts_were_removed:
                tenant_alert_objects["alerts"] = alerts

                # save the updated tenant_alert_objects
                vtenant_record["tenant_alert_objects"] = json.dumps(
                    tenant_alert_objects, indent=2
                )

                try:
                    self.service.kvstore["kv_trackme_virtual_tenants"].data.update(
                        str(vtenant_record["_key"]), json.dumps(vtenant_record)
                    )
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, vtenant_record updated successfully.'
                    )
                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, Failed to update vtenant_record, exception: {str(e)}'
                    )

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        #
        # task: logical_groups
        #

        task_name = "check_logical_groups"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            task_start = time.time()

            #
            # Verify Logical Groups:
            # - load the logical groups KVstore collection
            # - verify that for each member of the groups, the member can be found in in any of the dsm/dhm/mhm/flx/fqm KVstore collection as an actively monitoreed entity
            # - if not, purge the member from the group
            #

            if (
                vtenant_record.get("tenant_dsm_enabled") == True
                or vtenant_record.get("tenant_dhm_enabled") == True
                or vtenant_record.get("tenant_mhm_enabled") == True
                or vtenant_record.get("tenant_flx_enabled") == True
                or vtenant_record.get("tenant_fqm_enabled") == True
            ):
                # log start
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting to verify logical groups, any orphan logical group member will be purged automatically.'
                )

                # time counter
                logical_group_check_start = time.time()

                #
                # Logical groups collection records
                #

                logical_group_coll = self.service.kvstore[
                    f"kv_trackme_common_logical_group_tenant_{self.tenant_id}"
                ]

                (
                    logical_groups_coll_records,
                    logical_groups_by_group_key_dict,
                    logical_groups_by_group_name_list,
                    logical_groups_by_member_dict,
                    logical_groups_by_member_list,
                ) = get_logical_groups_collection_records(logical_group_coll)

                # log all returned from the function
                logging.debug(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, logical_groups_coll_records={json.dumps(logical_groups_coll_records, indent=2)}, logical_groups_by_group_key_dict={json.dumps(logical_groups_by_group_key_dict, indent=2)}, logical_groups_by_group_name_list={json.dumps(logical_groups_by_group_name_list, indent=2)}, logical_groups_by_member_dict={json.dumps(logical_groups_by_member_dict, indent=2)}, logical_groups_by_member_list={json.dumps(logical_groups_by_member_list, indent=2)}'
                )

                # Pre-load all enabled entity names from each component collection into in-memory sets
                # This replaces the N+1 per-member per-component KV Store query pattern with C batch loads + O(M) set lookups
                enabled_entity_names = set()
                for tenant_setting, collection_suffix in [
                    ("tenant_dsm_enabled", "dsm"),
                    ("tenant_dhm_enabled", "dhm"),
                    ("tenant_mhm_enabled", "mhm"),
                    ("tenant_flx_enabled", "flx"),
                    ("tenant_fqm_enabled", "fqm"),
                ]:
                    if vtenant_record.get(tenant_setting) == True:
                        try:
                            target_collection_name = f"kv_trackme_{collection_suffix}_tenant_{self.tenant_id}"
                            target_collection = self.service.kvstore[target_collection_name]
                            all_records, _, _ = get_full_kv_collection(target_collection, target_collection_name)
                            for record in all_records:
                                if record.get("monitored_state") == "enabled":
                                    obj_name = record.get("object")
                                    if obj_name:
                                        enabled_entity_names.add(obj_name)
                            logging.debug(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                f'pre-loaded {len(all_records)} records from {target_collection_name} for logical group member check'
                            )
                        except Exception as e:
                            logging.warning(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                f'failed to pre-load {collection_suffix} entities for logical group check, exception="{str(e)}"'
                            )

                # loops through logical_groups_by_member_list if not empty, then check using pre-loaded sets
                logical_members_orphans = []

                # ensure logical_groups_by_member_list is a list
                if isinstance(logical_groups_by_member_list, str):
                    logical_groups_by_member_list = [logical_groups_by_member_list]

                if len(logical_groups_by_member_list) > 0:

                    #
                    # Orphans — O(1) set lookups instead of per-member KV Store queries
                    #

                    for member in logical_groups_by_member_list:
                        if member not in enabled_entity_names:
                            logical_members_orphans.append(member)

                    # log orphans
                    logging.debug(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, logical_members_orphans={json.dumps(logical_members_orphans, indent=2)}'
                    )

                    # purge orphans
                    if len(logical_members_orphans) > 0:
                        # turn the list into a comma separated string
                        logical_members_orphans = ",".join(logical_members_orphans)

                        try:
                            logical_group_purge_remove_response = (
                                logical_group_remove_object_from_groups(
                                    self._metadata.searchinfo.splunkd_uri,
                                    self._metadata.searchinfo.session_key,
                                    self.tenant_id,
                                    logical_members_orphans,
                                )
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, orphan_members="{logical_members_orphans}", successfully purged the logical groups collection, response="{json.dumps(logical_group_purge_remove_response, indent=2)}"'
                            )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, orphan_members="{logical_members_orphans}", failed to purge from the logical groups collection, exception={str(e)}'
                            )

                    #
                    # empty groups
                    #

                    for logical_group_record in logical_groups_coll_records:

                        # get the group name
                        object_group_name = logical_group_record.get("object_group_name")

                        # get the members
                        members = logical_group_record.get("object_group_members", None)
                        if members:
                            if not len(members) > 0:
                                members = None

                        if not members:

                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, group="{object_group_name}", group has no members, will be purged.'
                            )

                            try:
                                logical_group_delete_response = (
                                    logical_group_delete_group_by_name(
                                        self._metadata.searchinfo.splunkd_uri,
                                        self._metadata.searchinfo.session_key,
                                        self.tenant_id,
                                        object_group_name,
                                    )
                                )
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, group="{object_group_name}", group has been purged successfully, response="{json.dumps(logical_group_delete_response, indent=2)}"'
                                )
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, group="{object_group_name}", failed to purge the group, exception={str(e)}'
                                )

                # log time
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, logical_groups_check_duration="{round(time.time() - logical_group_check_start, 3)}"'
                )

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        #
        # task: check_trackers
        #

        task_name = "check_trackers_statuses"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            check_trackers_report_name = report_name
            task_start = time.time()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # Call the get_tenant_ops_status REST endpoint directly and expand the job_component_register JSON
            ops_status_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/configuration/get_tenant_ops_status"
            ops_status_body = json.dumps({"mode": "raw", "tenant_id": self.tenant_id})

            # logging
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{self.tenant_id}", calling get_tenant_ops_status REST endpoint directly'
            )

            # run the REST call and expand the job_component_register JSON
            try:
                ops_status_response = session.post(
                    ops_status_url,
                    data=ops_status_body,
                    verify=False,
                    timeout=splunkd_timeout,
                )
                ops_status_response.raise_for_status()
                ops_status_results = ops_status_response.json()

                # Expand job_component_register from each result
                expanded_items = []
                if isinstance(ops_status_results, list):
                    for raw_record in ops_status_results:
                        job_component_register_str = raw_record.get("job_component_register")
                        if job_component_register_str:
                            job_component_records = json.loads(job_component_register_str) if isinstance(job_component_register_str, str) else job_component_register_str
                            if isinstance(job_component_records, list):
                                for record in job_component_records:
                                    expanded_items.append(record)

                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, get_tenant_ops_status returned {len(expanded_items)} expanded component records'
                )

                yielded_count = 0

                # Load all saved searches once to avoid per-report REST calls.
                # If this fails, raise to abort — an empty dict would silently skip all trackers.
                saved_searches_dict = {}
                try:
                    for ss in self.service.saved_searches:
                        saved_searches_dict[ss.name] = ss
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, loaded {len(saved_searches_dict)} saved searches in single batch'
                    )
                except Exception as e:
                    raise Exception(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to load saved searches batch, aborting task, exception="{str(e)}"'
                    )

                for item in expanded_items:
                    # verify the knowledge object - if for some reason it is not existing anymore, we should remove it
                    # and not take it into account any longer

                    # process
                    item_report_name = item.get("report")

                    # Skip placeholder records (e.g. report="none" when exec summary is empty)
                    if not item_report_name or item_report_name == "none":
                        continue

                    # Look up from pre-loaded dict — O(1) instead of individual REST call
                    savedsearch = saved_searches_dict.get(item_report_name)
                    if not savedsearch:
                        savedsearch_definition = None
                        savedsearch_content = {}
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, the report="{item_report_name}" does not exist anymore, somehow it was removed without TrackMe being aware of it, will get rid of this now.'
                        )
                    else:
                        savedsearch_definition = savedsearch.content.get("search")
                        savedsearch_content = savedsearch.content

                    if not savedsearch_definition:
                        # extract component
                        component = item_report_name.split("_")[1]

                        # purge
                        try:
                            delete_register_summary = (
                                trackme_delete_tenant_object_summary(
                                    self._metadata.searchinfo.session_key,
                                    self._metadata.searchinfo.splunkd_uri,
                                    self.tenant_id,
                                    f"splk-{component}",
                                    item_report_name,
                                )
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, knowledge for the report="{item_report_name}" was purged successfully, response="{delete_register_summary}"'
                            )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, exception encountered while calling function trackme_delete_tenant_object_summary, exception="{str(e)}"'
                            )

                    else:

                        search_component = item.get("component")
                        search_cron_schedule = savedsearch_content.get("cron_schedule")
                        search_description = savedsearch_content.get("description")
                        search_earliest = savedsearch_content.get(
                            "dispatch.earliest_time"
                        )
                        search_last_duration = item.get("last_duration")
                        search_last_exec = item.get("last_exec")
                        search_last_result = item.get("last_result")
                        search_last_status = item.get("last_status")
                        search_latest = savedsearch_content.get("dispatch.latest_time")
                        search_report_name = item_report_name
                        search_schedule_window = savedsearch_content.get(
                            "schedule_window"
                        )
                        search_tenant_id = item.get("tenant_id")
                        search_workload_pool = savedsearch_content.get(
                            "workload_pool", None
                        )

                        # ACLs
                        acl_report_info = None
                        if self.get_acl:
                            # try to get acl
                            acl_link = savedsearch.links["alternate"]
                            acl_report_info = {}
                            acl_url = f"{self._metadata.searchinfo.splunkd_uri}{acl_link}/acl/list?output_mode=json"

                            try:
                                response = session.get(
                                    acl_url,
                                    verify=False,
                                    timeout=600,
                                )
                                response_json = response.json()
                                response.raise_for_status()
                                acl_properties = response_json["entry"][0].get(
                                    "acl", {}
                                )
                                acl_report_info = {
                                    "eai:acl.owner": acl_properties.get("owner"),
                                    "eai:acl.perms.read": acl_properties["perms"][
                                        "read"
                                    ],
                                    "eai:acl.perms.write": acl_properties["perms"][
                                        "write"
                                    ],
                                    "eai:acl.sharing": acl_properties.get("sharing"),
                                }

                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, exception encountered while trying to get the ACL for the report="{item_report_name}", exception="{str(e)}"'
                                )

                        # set info record
                        search_info_record = {
                            "component": search_component,
                            "cron_schedule": search_cron_schedule,
                            "description": search_description,
                            "earliest": search_earliest,
                            "last_duration": search_last_duration,
                            "last_exec": search_last_exec,
                            "last_result": search_last_result,
                            "last_status": search_last_status,
                            "latest": search_latest,
                            "report": search_report_name,
                            "schedule_window": search_schedule_window,
                            "tenant_id": search_tenant_id,
                        }

                        # most often the workload pool is not set, only add if explicitly set
                        if search_workload_pool:
                            search_info_record["workload_pool"] = search_workload_pool

                        # add acl info
                        if acl_report_info:
                            search_info_record.update(acl_report_info)

                        yielded_count += 1
                        yield {
                            "_time": time.time(),
                            "_raw": search_info_record,
                            "component": search_component,
                            "cron_schedule": search_cron_schedule,
                            "description": search_description,
                            "earliest": search_earliest,
                            "last_duration": search_last_duration,
                            "last_exec": search_last_exec,
                            "last_result": search_last_result,
                            "last_status": search_last_status,
                            "latest": search_latest,
                            "report": search_report_name,
                            "schedule_window": search_schedule_window,
                            "tenant_id": search_tenant_id,
                            "workload_pool": search_workload_pool,
                        }

                        # index the audit record
                        try:
                            trackme_state_event(
                                session_key=self._metadata.searchinfo.session_key,
                                splunkd_uri=self._metadata.searchinfo.splunkd_uri,
                                tenant_id=self.tenant_id,
                                index=tenant_indexes["trackme_audit_idx"],
                                sourcetype="trackme:health",
                                source=f"trackme:health:{self.tenant_id}",
                                record=search_info_record,
                                splunkd_timeout=splunkd_timeout,
                            )
                        except Exception as e:
                            error_msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, exception encountered while calling function trackme_state_event, exception="{str(e)}"'
                            logging.error(error_msg)
                            raise Exception(error_msg)

                # If no tracker records were yielded, produce a single informational record
                if yielded_count == 0:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, no tracker status data available yet, yielding informational record'
                    )
                    yield {
                        "_time": time.time(),
                        "_raw": json.dumps({
                            "tenant_id": self.tenant_id,
                            "message": "No tracker status data available yet, this is expected on first run or after a status cleanup, tracker data will be populated on the next scheduled execution.",
                        }),
                        "tenant_id": self.tenant_id,
                        "component": "all",
                        "report": "pending",
                        "last_status": "info",
                        "last_result": "No tracker status data available yet",
                    }

            except Exception as e:
                # Register failure metric before re-raising (end-of-generate is unreachable after raise)
                try:
                    trackme_register_tenant_object_summary(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        "all",
                        health_tracker_report_name,
                        "failure",
                        time.time(),
                        str(time.time() - start),
                        str(e),
                        "-5m",
                        "now",
                    )
                except Exception:
                    pass
                msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, main search failed with exception="{str(e)}"'
                logging.error(msg)
                raise Exception(msg)

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        #
        # task: check_tenant_record_knowledge_objects
        #

        task_name = "check_tenant_record_knowledge_objects"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            task_start = time.time()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # logic:
            # For each component, check the field  tenant_<component>_hybrid_objects from the vtenant record
            # load the object as json, get the list reports and the list macros
            # for each object, check that it actually exists in Splunk
            # if not, delete the object from the vtenant record

            for component in ["dsm", "dhm", "mhm", "flx", "wlk", "fqm"]:

                # if the component is disabled, skip
                try:
                    component_enablement = int(vtenant_record.get(f"tenant_{component}_enabled", 0))
                except Exception as e:
                    component_enablement = 0

                if component_enablement == 0:
                    continue

                # get the hybrid_objects field
                hybrid_objects = vtenant_record.get(
                    f"tenant_{component}_hybrid_objects"
                )

                try:
                    hybrid_objects = json.loads(hybrid_objects)
                except Exception as e:
                    hybrid_objects = {}

                # if the field does not exist, skip
                if not hybrid_objects:
                    continue

                # if "reports" is in the list, get the list of reports
                if "reports" in hybrid_objects:
                    reports = hybrid_objects.get("reports")
                else:
                    reports = []

                # if "macros" is in the list, get the list of macros
                if "macros" in hybrid_objects:
                    macros = hybrid_objects.get("macros")
                else:
                    macros = []

                # check reports
                if reports:
                    for report_name in reports:

                        # process
                        savedsearch_definition = None
                        try:
                            savedsearch = self.service.saved_searches[report_name]
                            savedsearch_definition = savedsearch.content["search"]
                            savedsearch_content = savedsearch.content
                        except Exception as e:
                            savedsearch_definition = None
                            savedsearch_content = {}

                        # purge if necessary
                        if not savedsearch_definition:

                            logging.warning(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, the report="{report_name}" does not exist anymore, somehow it was removed without TrackMe being aware of it, will get rid of this now.'
                            )

                            # remove from list in hybrid_objects, update the vtenant record and update the KVstore collection
                            try:
                                reports.remove(report_name)
                            except ValueError:
                                logging.warning(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, report="{report_name}" not found in tenant_{component}_hybrid_objects, skipping removal'
                                )
                            hybrid_objects["reports"] = reports
                            vtenant_record[f"tenant_{component}_hybrid_objects"] = (
                                json.dumps(hybrid_objects, indent=2)
                            )

                            try:
                                self.service.kvstore[
                                    "kv_trackme_virtual_tenants"
                                ].data.update(
                                    str(vtenant_record["_key"]), json.dumps(vtenant_record)
                                )
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, vtenant_record updated successfully.'
                                )
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, Failed to update vtenant_record, exception: {str(e)}'
                                )

                # check macros
                if macros:
                    for macro_name in macros:
                        # process
                        macro_definition = None
                        try:
                            macro = self.service.confs["macros"][macro_name]
                            macro_definition = macro.content["definition"]
                        except Exception as e:
                            macro = None
                            macro_definition = None

                        # purge if necessary
                        if not macro_definition:

                            logging.warning(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, the macro="{macro_name}" does not exist anymore, somehow it was removed without TrackMe being aware of it, will get rid of this now.'
                            )

                            # remove from list in hybrid_objects, update the vtenant record and update the KVstore collection
                            try:
                                macros.remove(macro_name)
                            except ValueError:
                                logging.warning(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, macro="{macro_name}" not found in tenant_{component}_hybrid_objects, skipping removal'
                                )
                            hybrid_objects["macros"] = macros
                            vtenant_record[f"tenant_{component}_hybrid_objects"] = (
                                json.dumps(hybrid_objects, indent=2)
                            )

                            try:
                                self.service.kvstore[
                                    "kv_trackme_virtual_tenants"
                                ].data.update(
                                    str(vtenant_record["_key"]), json.dumps(vtenant_record)
                                )
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, vtenant_record updated successfully.'
                                )

                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, Failed to update vtenant_record, exception: {str(e)}'
                                )

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        #
        # task: gen_sla_breaches_and_score_metrics
        #

        task_instance_id = self.get_uuid()
        task_name = "gen_sla_breaches_and_score_metrics"
        task_start = time.time()

        # start task
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
        )

        # get sla gen events frequency
        try:
            sla_breaches_events_frequency = int(
                reqinfo["trackme_conf"]["sla"]["sla_breaches_events_frequency"]
            )
        except Exception as e:
            sla_breaches_events_frequency = 86400

        def process_component(component, sla_breaches_events_frequency):
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, processing component.'
            )

            # Shadow fast-path: read enriched records from shadow instead of
            # running full decision maker enrichment via trackmegetcoll
            shadow_threshold = int(vtenant_account.get("shadow_entity_threshold", 1000))
            shadow_enabled = int(vtenant_account.get("shadow_enabled", 0))
            use_shadow = (
                shadow_threshold > 0
                and should_use_shadow(self.service, self.tenant_id, component, shadow_threshold, False, shadow_enabled=shadow_enabled)
            )

            results_list = []

            if use_shadow:
                try:
                    shadow_start = time.time()
                    shadow_transform = f"trackme_{component}_shadow_tenant_{self.tenant_id}"
                    shadow_records = read_shadow_records(self.service, shadow_transform, instance_id)

                    # Filter to enabled entities only (matching the SPL "where monitored_state=enabled")
                    results_list = [
                        rec for rec in shadow_records
                        if rec.get("monitored_state") == "enabled"
                    ]

                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, '
                        f'shadow read for SLA/scoring, total_shadow={len(shadow_records)}, enabled={len(results_list)}, run_time={round(time.time()-shadow_start, 3)}s'
                    )
                except Exception as e:
                    logging.warning(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", '
                        f'shadow read failed for SLA/scoring, falling back to trackmegetcoll, exception="{e}"'
                    )
                    use_shadow = False

            if not use_shadow:
                # Standard path: full enrichment via trackmegetcoll
                search_string = f'| trackmegetcoll tenant_id="{self.tenant_id}" component="{component}" | where monitored_state="enabled" | table _key alias object object_category object_state priority keyid score sla_* anomaly_reason status_message'

                kwargs_search = {
                    "earliest_time": "-5m",
                    "latest_time": "now",
                    "preview": "false",
                    "output_mode": "json",
                    "count": 0,
                }

                try:
                    search_results = run_splunk_search(
                        self.service,
                        search_string,
                        kwargs_search,
                        24,
                        5,
                    )

                    results_list = [
                        item for item in search_results if isinstance(item, dict)
                    ]

                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", component="{component}", task="{task_name}", task_instance_id={task_instance_id}, failed to run search with exception="{e}"'
                    )

            #
            # Part 1: Generate impact score metrics for ALL enabled entities (always runs)
            #

            if results_list:
                impact_score_records = []
                for item in results_list:
                    try:
                        score_value = item.get("score", 0)
                        try:
                            score_value = float(score_value)
                        except (ValueError, TypeError):
                            score_value = 0

                        impact_score_records.append({
                            "tenant_id": self.tenant_id,
                            "object_id": item.get("keyid") or item.get("_key"),
                            "object": item.get("object", ""),
                            "component": item.get("object_category", f"splk-{component}"),
                            "metrics_event": {"score": score_value},
                        })
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", component="{component}", task="{task_name}", task_instance_id={task_instance_id}, failed to process impact score record with exception="{e}"'
                        )

                if impact_score_records:
                    scoring_gen_start = time.time()
                    try:
                        scoring_result = trackme_impact_score_gen_metrics(
                            self.tenant_id,
                            tenant_indexes.get("trackme_metric_idx"),
                            impact_score_records,
                        )
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, function trackme_impact_score_gen_metrics success {scoring_result}, run_time={round(time.time()-scoring_gen_start, 3)}, no_entities={len(impact_score_records)}'
                        )
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", task="{task_name}", task_instance_id={task_instance_id}, function trackme_impact_score_gen_metrics failed with exception {str(e)}'
                        )

            #
            # Part 2: Generate SLA breach events (only if enabled, only breached entities)
            #

            if sla_breaches_events_frequency > 0 and results_list:

                # Get the KVstore collection for SLA notifications
                collection_name = (
                    f"kv_trackme_{component}_sla_notifications_tenant_{self.tenant_id}"
                )
                collection = self.service.kvstore[collection_name]

                # Filter for breached entities only
                breached_results = [item for item in results_list if str(item.get("sla_is_breached")) == "1"]

                keyids = [item.get("keyid") for item in breached_results if item.get("keyid")]
                notification_mtimes = {}
                if keyids:
                    try:
                        kvrecords_dict, _ = batch_find_records_by_key(
                            collection, keyids
                        )
                        notification_mtimes = {
                            key: float(record.get("mtime", 0))
                            for key, record in kvrecords_dict.items()
                        }
                    except Exception as e:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", component="{component}", task="{task_name}", task_instance_id={task_instance_id}, failed batch find SLA notifications with exception="{e}"'
                        )
                current_time = time.time()

                for item in breached_results:
                    try:
                        # Extract required fields
                        alias = item.get("alias")
                        object_value = item.get("object")
                        object_category = item.get("object_category")
                        object_state = item.get("object_state")
                        priority = item.get("priority")
                        keyid = item.get("keyid")
                        anomaly_reason = item.get("anomaly_reason")
                        status_message = item.get("status_message")
                        sla_class = item.get("sla_class")
                        sla_is_breached = item.get("sla_is_breached")
                        sla_message = item.get("sla_message")
                        sla_threshold = item.get("sla_threshold")
                        sla_threshold_duration = item.get("sla_threshold_duration")
                        sla_timer = item.get("sla_timer")
                        sla_timer_duration = item.get("sla_timer_duration")

                        # Check if we have a notification record for this object
                        last_notification_time = notification_mtimes.get(keyid, 0)
                        # Only generate event if last notification was > frequency ago
                        should_generate_event = (
                            current_time - last_notification_time
                            > sla_breaches_events_frequency
                        )

                        if should_generate_event:
                            # Create the SLA breach event record
                            breach_record = {
                                "timeStr": time.strftime(
                                    "%d/%m/%Y %H:%M:%S", time.localtime(time.time())
                                ),
                                "tenant_id": self.tenant_id,
                                "alias": alias,
                                "object": decode_unicode(object_value),
                                "keyid": keyid,
                                "object_category": object_category,
                                "object_state": object_state,
                                "priority": priority,
                                "anomaly_reason": anomaly_reason,
                                "status_message": status_message,
                                "sla_class": sla_class,
                                "sla_is_breached": sla_is_breached,
                                "sla_message": sla_message,
                                "sla_threshold": sla_threshold,
                                "sla_threshold_duration": sla_threshold_duration,
                                "sla_timer": sla_timer,
                                "sla_timer_duration": sla_timer_duration,
                            }

                            # Add event_id
                            breach_record["event_id"] = hashlib.sha256(
                                json.dumps(breach_record).encode()
                            ).hexdigest()

                            # Generate the event
                            try:
                                trackme_gen_state(
                                    index=tenant_indexes["trackme_summary_idx"],
                                    sourcetype="trackme:sla_breaches",
                                    source=f"health_tracker:{task_name}",
                                    event=breach_record,
                                )
                                logging.info(
                                    f'TrackMe SLA breach event created successfully, tenant_id="{self.tenant_id}", keyid="{keyid}", object="{object_value}", sla_class="{sla_class}", sla_timer="{sla_timer}", sla_gen_events_frequency="{sla_breaches_events_frequency}"'
                                )

                                # Update or create the notification record
                                notification_record = {
                                    "_key": keyid,
                                    "mtime": time.time(),
                                    "last_notification": breach_record,
                                }

                                try:
                                    collection.data.update(
                                        keyid, json.dumps(notification_record)
                                    )
                                except Exception:
                                    collection.data.insert(
                                        json.dumps(notification_record)
                                    )

                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", object="{object_value}", failed to generate a SLA breach event with exception="{e}"'
                                )

                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", failed to process record with exception="{e}"'
                        )

        # Main logic
        # Process components in parallel (max 4 workers to avoid overloading splunkd)
        components = ["dsm", "dhm", "mhm", "flx", "wlk", "fqm"]
        enabled_components = [
            c for c in components if vtenant_record.get(f"tenant_{c}_enabled")
        ]

        if enabled_components:
            with ThreadPoolExecutor(max_workers=min(4, len(enabled_components))) as executor:
                futures = {
                    executor.submit(process_component, component, sla_breaches_events_frequency): component
                    for component in enabled_components
                }
                for future in as_completed(futures):
                    component = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="{component}", '
                            f'task="{task_name}", task_instance_id={task_instance_id}, '
                            f'parallel process_component failed with exception="{str(e)}"'
                        )

        # end task
        task_duration = round(time.time()-task_start, 3)
        task_freq_manager.record_execution(task_name, task_duration)
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
        )

        #
        # task: unclosed_stateful_incidents
        #

        task_name = "unclosed_stateful_incidents"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            task_start = time.time()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # objective: get any opened or updated incidents in the KVstore, verify that:
            # - the entity associated with the incident is still existing and with monitored_state="enabled", if not the incident will be updated and closed.
            # - if the entity exists, but is in a non alerting state (green, blue), and the incident is older than 24 hours, the incident will be updated and closed.

            # get the KVstore collection for stateful incidents
            stateful_incidents_collection_name = (
                f"kv_trackme_stateful_alerting_tenant_{self.tenant_id}"
            )
            stateful_incidents_collection = self.service.kvstore[
                stateful_incidents_collection_name
            ]

            def get_stateful_incidents(collection_name, collection):

                collection_records = []
                collection_records_keys = set()
                collection_dict = {}

                try:
                    end = False
                    skip_tracker = 0
                    while end == False:
                        process_collection_records = collection.data.query(
                            skip=skip_tracker
                        )
                        if len(process_collection_records) != 0:
                            for item in process_collection_records:
                                # Dedup on "_key" (NOT "object"): a single object
                                # can legitimately have several non-closed stateful
                                # records, and the consumer loop iterates this list
                                # to close EVERY duplicate by its own _key. Deduping
                                # by object would drop those duplicates from the list
                                # and leave them open. The set/dict are unused here;
                                # keying them on _key keeps the guard consistent
                                # without altering the consumed list (see issue #1800).
                                item_key = item.get("_key")
                                if item_key not in collection_records_keys:
                                    if item.get("alert_status") in ["opened", "updated"]:
                                        collection_records.append(item)
                                        collection_records_keys.add(item_key)
                                        collection_dict[item_key] = item
                            skip_tracker += len(process_collection_records)
                        else:
                            end = True

                    return collection_records, collection_records_keys, collection_dict

                except Exception as e:
                    raise Exception(str(e))

            # get the stateful incidents
            try:
                (
                    stateful_incidents_records,
                    stateful_incidents_keys,
                    stateful_incidents_dict,
                ) = get_stateful_incidents(
                    stateful_incidents_collection_name, stateful_incidents_collection
                )

            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to call get_kv_collection, args={stateful_incidents_collection_name}, cannot process this task, exception="{str(e)}"'
                )
                stateful_incidents_records = []
                stateful_incidents_keys = set()
                stateful_incidents_dict = {}

            # batch-fetch data objects by component for performance optimization
            def batch_fetch_data_objects_by_component(incidents_records):
                """
                Batch fetch all data objects grouped by component to avoid N+1 query problem.
                Uses get_full_kv_collection() from trackme_libs_get_data for efficient batch retrieval.
                Returns a tuple: (data_objects_by_component_dict, failed_components_set)
                """
                data_objects_by_component = {}
                failed_components = set()
                components_processed = set()
            
                # First, identify all unique components from incidents
                for incident in incidents_records:
                    object_category = incident.get("object_category")
                    if object_category:
                        try:
                            component_suffix = object_category.split("-")[1]
                            components_processed.add(component_suffix)
                        except (IndexError, AttributeError):
                            continue
            
                # Batch fetch data for each component using get_full_kv_collection
                batch_fetch_start = time.time()
                for component_suffix in components_processed:
                    data_collection_name = (
                        f"kv_trackme_{component_suffix}_tenant_{self.tenant_id}"
                    )
                    try:
                        data_collection = self.service.kvstore[data_collection_name]
                    
                        # Use get_full_kv_collection for efficient batch retrieval
                        (
                            collection_records,
                            collection_records_keys,
                            component_data_dict,
                        ) = get_full_kv_collection(data_collection, data_collection_name)
                    
                        data_objects_by_component[component_suffix] = component_data_dict
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, batch_fetched component="{component_suffix}", records_count="{len(component_data_dict)}", collection="{data_collection_name}"'
                        )
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to batch_fetch component="{component_suffix}", collection="{data_collection_name}", exception="{str(e)}"'
                        )
                        # Track failed components so fallback can be triggered
                        failed_components.add(component_suffix)
                        # Don't set empty dict - let it be missing so fallback triggers
            
                batch_fetch_time = round(time.time() - batch_fetch_start, 2)
                total_components = len(components_processed)
                total_incidents = len(incidents_records)
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, batch_fetch_completed, components="{total_components}", incidents="{total_incidents}", queries_eliminated="{total_incidents}", batch_fetch_time="{batch_fetch_time}", failed_components="{len(failed_components)}"'
                )
            
                return data_objects_by_component, failed_components

            # Pre-fetch all data objects by component
            data_objects_by_component = {}
            failed_batch_fetch_components = set()
            if len(stateful_incidents_records) > 0:
                data_objects_by_component, failed_batch_fetch_components = batch_fetch_data_objects_by_component(
                    stateful_incidents_records
                )

            # iterate through opened or updated incidents
            for stateful_incident in stateful_incidents_records:

                # Log essential incident fields only (exclude verbose fields like messages, reference_chain)
                incident_summary = {
                    "_key": stateful_incident.get("_key"),
                    "object": stateful_incident.get("object"),
                    "object_category": stateful_incident.get("object_category"),
                    "object_id": stateful_incident.get("object_id"),
                    "object_state": stateful_incident.get("object_state"),
                    "incident_id": stateful_incident.get("incident_id"),
                    "alert_status": stateful_incident.get("alert_status")
                }
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, inspecting stateful with _key="{stateful_incident.get("_key")}", incident={incident_summary}'
                )

                # get the object
                stateful_object = stateful_incident.get("object")

                # get the object_id
                stateful_object_id = stateful_incident.get("object_id")

                # get the object_category (ex: splk-dsm)
                stateful_object_category = stateful_incident.get("object_category")

                # get the object_state
                stateful_object_state = stateful_incident.get("object_state")

                # get the object status
                stateful_object_status = stateful_incident.get("object_status")

                # get the mtime
                stateful_incident_mtime = float(stateful_incident.get("mtime"))

                # calculate the incident duration
                stateful_incident_duration = time.time() - stateful_incident_mtime

                # get the object from the pre-fetched data dictionary (optimized batch fetch)
                data_object = None
                try:
                    object_category_suffix = stateful_object_category.split("-")[1]
                
                    # Check if batch fetch failed for this component - if so, use fallback immediately
                    if object_category_suffix in failed_batch_fetch_components:
                        raise KeyError(f"Batch fetch failed for component {object_category_suffix}")
                
                    component_data_dict = data_objects_by_component.get(
                        object_category_suffix
                    )
                
                    # If component dict doesn't exist or is None, trigger fallback
                    if component_data_dict is None:
                        raise KeyError(f"Component {object_category_suffix} not found in batch fetch results")
                
                    data_object = component_data_dict.get(stateful_object_id)
                
                    # If data_object is None but component was batch-fetched successfully,
                    # it means the object doesn't exist (not a batch fetch failure)
                    # So we don't trigger fallback here - None is a valid result
                
                except (IndexError, AttributeError, KeyError) as e:
                    # Fallback: if batch fetch failed or component not found, try individual query
                    # First, safely extract object_category_suffix to avoid NameError in logging
                    object_category_suffix = "unknown"
                    try:
                        if stateful_object_category:
                            object_category_suffix = stateful_object_category.split("-")[1]
                    except (IndexError, AttributeError):
                        # Invalid category format - cannot proceed with fallback query
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, invalid_object_category, object_category="{stateful_object_category}", object_id="{stateful_object_id}", cannot_proceed_with_fallback'
                        )
                        data_object = None
                    else:
                        # Only attempt fallback query if we successfully extracted the component suffix
                        try:
                            data_collection_name = (
                                f"kv_trackme_{object_category_suffix}_tenant_{self.tenant_id}"
                            )
                            data_collection = self.service.kvstore[data_collection_name]
                            data_object = data_collection.data.query(
                                query=json.dumps({"_key": stateful_object_id})
                            )[0]
                            logging.debug(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, fallback_query_succeeded, component="{object_category_suffix}", object_id="{stateful_object_id}"'
                            )
                        except Exception as fallback_e:
                            data_object = None
                            logging.debug(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, fallback_query_failed, component="{object_category_suffix}", object_id="{stateful_object_id}", exception="{str(fallback_e)}"'
                            )

                # use-case 1: the object does not exist anymore
                stateful_object_exists = True

                if not data_object:
                    stateful_object_exists = False

                # use-case 2: the object exists, but is in a non alerting state while the incident has not been closed 24 hours later
                stateful_incident_outdated = False

                if stateful_object_exists:
                    if data_object.get("object_state", "green") in ["green", "blue"]:
                        if stateful_incident_duration > 86400:
                            stateful_incident_outdated = True
                    elif data_object.get("monitored_state") != "enabled":
                        stateful_incident_outdated = True

                # Update the incident if necessary
                if not stateful_object_exists or stateful_incident_outdated:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, update of outdated stateful incident is required, stateful_object_exists="{stateful_object_exists}", stateful_incident_outdated="{stateful_incident_outdated}", incident="{stateful_incident}"'
                    )

                    # update the incident
                    stateful_incident["alert_status"] = "closed"
                    stateful_incident["mtime"] = time.time()

                    if stateful_object_exists:
                        stateful_incident["object_state"] = stateful_object_status

                    # update the incident in the KVstore
                    try:
                        stateful_incidents_collection.data.update(
                            stateful_incident.get("_key"), json.dumps(stateful_incident)
                        )
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to update stateful incident with exception="{e}"'
                        )

                else:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, no action required against incident with _key="{stateful_incident.get("_key")}", stateful_object_exists="{stateful_object_exists}", stateful_incident_outdated="{stateful_incident_outdated}"'
                    )

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        #
        # task: check_shadow_auto_enablement
        # Automatically enables shadow copies when any enabled component's central
        # collection has entity count >= shadow_entity_threshold. This ensures shadow
        # is active on tenants that need it for UI scaling, even if an admin disabled it.
        # Runs at Tier 3 (every 6h) — entity counts don't change fast.
        #

        task_name = "check_shadow_auto_enablement"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            task_start = time.time()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                # Get current shadow settings from the vtenant_account conf.
                # IMPORTANT: shadow_enabled / shadow_entity_threshold are persisted
                # in trackme_vtenants.conf (the vtenant_account, exposed here as the
                # `vtenant_account` dict loaded earlier in generate()), NOT in the
                # kv_trackme_virtual_tenants record. Reading them off `vtenant_record`
                # always fell back to the defaults (0 / 1000) because those keys are
                # absent from the KV record, so the "already enabled" guard below never
                # fired and this task re-POSTed update_tenant_shadow_config every cycle,
                # generating a spurious no-op audit event ({"old":"1","new":"1"}).
                shadow_enabled = 0
                shadow_entity_threshold = 1000
                try:
                    shadow_enabled = int(vtenant_account.get("shadow_enabled", 0))
                except (ValueError, TypeError):
                    shadow_enabled = 0
                try:
                    shadow_entity_threshold = int(vtenant_account.get("shadow_entity_threshold", 1000))
                except (ValueError, TypeError):
                    shadow_entity_threshold = 1000

                # If already enabled, nothing to do
                if shadow_enabled == 1:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                        f'shadow already enabled, skipping auto-enablement check'
                    )
                elif shadow_entity_threshold <= 0:
                    # Threshold is 0 or negative — admin explicitly wants no shadow
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                        f'shadow_entity_threshold={shadow_entity_threshold}, shadow auto-enablement not applicable'
                    )
                else:
                    # Check entity counts in each enabled component's central collection
                    needs_shadow = False
                    trigger_component = None
                    trigger_count = 0
                    components = ["dsm", "dhm", "mhm", "flx", "fqm", "wlk"]

                    for comp in components:
                        try:
                            comp_enabled = int(vtenant_record.get(f"tenant_{comp}_enabled", 0))
                        except (ValueError, TypeError):
                            comp_enabled = 0

                        if comp_enabled == 0:
                            continue

                        # Count records using paginated _key-only queries
                        collection_name = f"kv_trackme_{comp}_tenant_{self.tenant_id}"
                        try:
                            comp_collection = self.service.kvstore[collection_name]
                            entity_count = 0
                            chunk_size = 5000
                            skip = 0

                            while True:
                                rows = comp_collection.data.query(
                                    fields="_key", limit=chunk_size, skip=skip
                                )
                                if not rows:
                                    break
                                entity_count += len(rows)

                                # Early exit: we only need to know if >= threshold
                                if entity_count >= shadow_entity_threshold:
                                    needs_shadow = True
                                    trigger_component = comp
                                    trigger_count = entity_count
                                    break

                                # Advance by actual count; stop only on an empty page
                                # (the >= threshold early-exit above still applies).
                                skip += len(rows)

                            if needs_shadow:
                                break

                        except Exception as e:
                            logging.debug(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                f'failed to count entities in {collection_name}, exception="{str(e)}"'
                            )

                    if needs_shadow:
                        # Auto-enable shadow via REST endpoint
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                            f'component="{trigger_component}" has {trigger_count}+ entities (>= shadow_entity_threshold={shadow_entity_threshold}), '
                            f'auto-enabling shadow for scaling'
                        )

                        try:
                            shadow_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/vtenants/admin/update_tenant_shadow_config"
                            shadow_body = {
                                "tenant_id": self.tenant_id,
                                "shadow_enabled": 1,
                                "update_comment": f"Auto-enabled by health tracker: component {trigger_component} has {trigger_count}+ entities (>= threshold {shadow_entity_threshold})",
                            }

                            shadow_response = session.post(
                                shadow_url,
                                data=json.dumps(shadow_body),
                                verify=False,
                                timeout=splunkd_timeout,
                            )

                            if shadow_response.status_code in (200, 201, 204):
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                    f'shadow auto-enabled successfully'
                                )
                            else:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                    f'failed to auto-enable shadow, status_code={shadow_response.status_code}'
                                )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                f'failed to auto-enable shadow, exception="{str(e)}"'
                            )
                    else:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                            f'no component exceeds shadow_entity_threshold={shadow_entity_threshold}, shadow auto-enablement not needed'
                        )

            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                    f'exception="{str(e)}"'
                )

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        #
        # task: apply_licensing_restrictions
        #

        task_name = "apply_licensing_restrictions"
        if task_freq_manager.should_run(task_name):
            task_instance_id = self.get_uuid()
            task_start = time.time()

            # start task
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            #
            # licensing restriction
            #

            max_free_tenants = 3 if license_subscription_class == "foundation" else 2

            # Helper: determines if this tenant uses restricted components (FLX, FQM, WLK)
            tenant_has_restricted_components = (
                vtenant_record.get("tenant_flx_enabled") == 1
                or vtenant_record.get("tenant_fqm_enabled") == 1
                or vtenant_record.get("tenant_wlk_enabled") == 1
            )

            # Helper: disable a tenant for licensing reasons via the admin endpoint
            def _disable_tenant_for_licensing(reason_log, update_comment):
                logging.info(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, due to licensing restrictions, this tenant will be automatically disabled, {reason_log}'
                )
                target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/vtenants/admin/disable_tenant"
                post_data = {
                    "tenant_id": self.tenant_id,
                    "update_comment": update_comment,
                    "force": "true",
                }
                try:
                    response = session.post(
                        target_url,
                        data=json.dumps(post_data),
                        verify=False,
                        timeout=600,
                    )
                    return json.loads(response.text)
                except Exception as e:
                    raise Exception(
                        f'An exception was encountered while attempting to disable the tenant due to licensing restrictions, exception="{str(e)}"'
                    )

            # if the component is a restricted component and the product is not registered, it should be disabled now
            if license_is_valid == 0 and tenant_has_restricted_components:
                return _disable_tenant_for_licensing(
                    "the tenant is running a restricted component while this instance is not registered",
                    "Auto disabling this tenant due to licensing limitation, the tenant is running a restricted component while the product is not currently registered",
                )

            # Foundation Edition does not support restricted components (FLX, FQM, WLK)
            # Disable tenants using these components even when the trial is valid
            elif (
                license_is_valid == 1
                and license_subscription_class == "foundation"
                and tenant_has_restricted_components
            ):
                return _disable_tenant_for_licensing(
                    "the tenant is running a restricted component which is not available in Foundation Edition",
                    "Auto disabling this tenant due to licensing limitation, restricted components (FLX, FQM, WLK) require an Enterprise or Unlimited license",
                )

            elif (
                license_is_valid == 0
                and license_active_tenants > max_free_tenants
                and self.tenant_id not in license_active_tenants_list[0:max_free_tenants]
            ):
                return _disable_tenant_for_licensing(
                    "this deployment has reached the maximum number of tenants allowed",
                    f"Auto disabling this tenant due to licensing limitation, this deployment has reached the maximum number of tenants allowed ({license_active_tenants}), only the following tenants can be used: {license_active_tenants_list[0:max_free_tenants]}",
                )

            # Foundation Edition: enforce 3-tenant limit even when trial is valid
            elif (
                license_is_valid == 1
                and license_subscription_class == "foundation"
                and license_active_tenants > max_free_tenants
                and self.tenant_id not in license_active_tenants_list[0:max_free_tenants]
            ):
                return _disable_tenant_for_licensing(
                    "the tenant is over the maximum number of allowed tenants in Foundation Edition",
                    f"Auto disabling this tenant due to licensing limitation, Foundation Edition allows a maximum of {max_free_tenants} tenants ({license_active_tenants} active), only the following tenants can be used: {license_active_tenants_list[0:max_free_tenants]}",
                )

            elif (
                license_is_valid == 1
                and license_subscription_class == "enterprise"
                and license_active_tenants > 6
                and self.tenant_id not in license_active_tenants_list[0:6]
            ):
                return _disable_tenant_for_licensing(
                    "the tenant is over the maximum number of allowed tenants in Enterprise Edition",
                    f"Auto disabling this tenant due to licensing limitation, this deployment has reached the maximum number of tenants allowed ({license_active_tenants}), only the following tenants can be used: {license_active_tenants_list[0:6]}",
                )

            # An exception was raised while attempting to validate the license
            # Log the error but do nothing
            elif license_is_valid == 2:
                logging.error(
                    f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, an exception was raised while attempting to validate the license, no actions will be taken for now.'
                )

            # end task
            task_duration = round(time.time()-task_start, 3)
            task_freq_manager.record_execution(task_name, task_duration)
            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{task_duration}", task has terminated.'
            )
        else:
            task_freq_manager.increment_skipped(task_name)

        # end general task — emit structured performance summary
        total_run_time = round(time.time() - start, 3)

        # Register runtime metric unconditionally every cycle (used by Trackers Performance DeepDive dashboard)
        try:
            trackme_register_tenant_object_summary(
                session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
                "all",
                health_tracker_report_name,
                "success",
                time.time(),
                str(total_run_time),
                "The report was executed successfully",
                "-5m",
                "now",
            )
        except Exception as e:
            logging.warning(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                f'failed to register health tracker runtime metric, exception="{str(e)}"'
            )

        perf_summary = task_freq_manager.get_performance_summary(total_run_time)
        perf_summary["instance_id"] = instance_id

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
            f'trackmetrackerhealth has terminated, total_run_time={total_run_time}, '
            f'tasks_executed={perf_summary["tasks_executed"]}, tasks_skipped={perf_summary["tasks_skipped"]}, '
            f'tier1_run_time={perf_summary["tier1_run_time"]}, tier2_run_time={perf_summary["tier2_run_time"]}, '
            f'tier3_run_time={perf_summary["tier3_run_time"]}, tier4_run_time={perf_summary["tier4_run_time"]}, '
            f'circuit_breaker_triggered={perf_summary["circuit_breaker_triggered"]}'
        )

        # Emit a structured performance summary event for operational monitoring
        try:
            trackme_gen_state(
                index=tenant_indexes.get("trackme_summary_idx", "trackme_summary"),
                sourcetype="trackme:health_tracker:performance_summary",
                source="health_tracker:performance_summary",
                event=perf_summary,
            )
        except Exception as e:
            logging.warning(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, '
                f'failed to emit performance summary event, exception="{str(e)}"'
            )


dispatch(HealthTracker, sys.argv, sys.stdin, sys.stdout, __name__)

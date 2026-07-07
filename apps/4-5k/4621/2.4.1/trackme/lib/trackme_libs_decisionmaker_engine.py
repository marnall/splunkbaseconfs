#!/usr/bin/env python
# coding=utf-8

"""
TrackMe Decision Maker Engine — on-demand Python callable.

Importable, in-process equivalent of the per-entity processing loop performed
by ``GET /trackme/v2/component/load_component_data`` and the
``trackmedecisionmaker`` streaming command. Lets backend Python code (alert
actions, health trackers, AI agent tools, batch evaluators) re-evaluate one
or many entity records without an HTTP round-trip and without re-implementing
the orchestration around the ``set_*_status`` helpers.

Two construction modes:

1. Standard — the engine loads every collection + configuration itself::

       engine = DecisionMakerEngine(session_key, splunkd_uri, tenant_id, "dsm")
       engine.load()
       evaluated = engine.evaluate(record)

2. Pre-loaded — the caller already has the collections in memory (e.g. a
   future internal refactor of the REST handler) and skips ``load()``::

       engine = DecisionMakerEngine.from_preloaded(
           session_key, splunkd_uri, tenant_id, "dsm",
           preloaded={...},
       )
       evaluated = engine.evaluate(record)

Why a class:

- Loading is heavy (10+ KV reads, scoring via ``mstats``, conf reads).
  Amortizing it across many records is the main performance win.
- The disruption queue collection handle is mutated inside the
  ``set_*_status`` functions for grace-period writes — naturally lives as
  instance state.
- Two construction modes map cleanly onto a constructor + factory.

A module-level ``evaluate_records()`` helper is provided for one-shot callers
that don't care about lifecycle.

NOTE on safety: this module is **purely additive**. It does not modify the
existing REST handler (``trackme_rest_handler_component_user.py``), the
streaming command (``trackmedecisionmaker.py``), or any function in
``trackme_libs_decisionmaker.py``. The per-entity orchestration here is a
faithful port of the REST handler's loop body — same library calls, same
ordering, same shared-state defaults (notably ``thresholds_collection_dict``
must be initialized before component-specific blocks; see PR #716).
"""

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import json
import logging
import os
import sys
import time

# splunk home + lib path (so we can import sibling helper modules)
splunkhome = os.environ.get("SPLUNK_HOME", "/opt/splunk")
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "bin"))

import splunklib.client as client

from trackme_libs import (
    trackme_idx_for_tenant,
    trackme_reqinfo_from_service,
    trackme_vtenant_account_from_service,
)
from trackme_libs_get_data import (
    get_target_from_kv_collection,
    get_sampling_kv_collection,
    get_wlk_apps_enablement_kv_collection,
    get_feeds_datagen_kv_collection,
    search_kv_collection,
    search_kv_collection_sdkmode,
)
from trackme_libs_decisionmaker import (
    ack_check,
    apply_blocklist,
    calculate_score,
    convert_epoch_to_datetime,
    define_state_icon_code,
    docs_ref_lookup,
    dsm_check_default_thresholds,
    dhm_check_default_thresholds,
    dsm_sampling_lookup,
    dynamic_labels_lookup,
    dynamic_priority_lookup,
    dynamic_sla_class_lookup,
    dynamic_tags_lookup,
    flx_check_dynamic_thresholds,
    flx_default_metrics_lookup,
    flx_drilldown_searches_lookup,
    flx_thresholds_lookup,
    fqm_check_dynamic_thresholds,
    fqm_thresholds_lookup,
    get_coll_docs_ref,
    get_data_sampling_status,
    get_dsm_delay_status,
    get_dsm_latency_status,
    get_future_metrics_status,
    get_future_status,
    get_is_under_dcount_host,
    get_logical_groups_collection_records,
    get_monitoring_time_status,
    get_outliers_status,
    get_sla_timer,
    logical_group_lookup,
    outliers_data_lookup,
    outliers_readiness,
    resolve_lagging_class_threshold,
    resolve_variable_delay_threshold,
    sampling_anomaly_status,
    set_dsm_status,
    set_dhm_status,
    set_flx_status,
    set_fqm_status,
    set_mhm_status,
    set_wlk_status,
    set_feeds_lag_summary,
    set_feeds_thresholds_duration,
    wlk_disabled_apps_lookup,
    wlk_orphan_lookup,
    wlk_thresholds_lookup,
    wlk_versioning_lookup,
)
from trackme_libs_disruption_queue import disruption_queue_lookup
from trackme_libs_entity_maintenance import (
    entity_maintenance_lookup,
    apply_entity_maintenance_override,
    clear_entity_maintenance_fields,
)
from trackme_libs_utils import replace_encoded_backslashes


# Module-level logger used as a fallback when no logger is injected.
_module_logger = logging.getLogger("trackme.decisionmaker.engine")


class DecisionMakerEngine:
    """In-process decision maker for one tenant + one component.

    Re-implements the per-entity loop of ``GET /trackme/v2/component/load_component_data``
    so backend code can evaluate one or many records without an HTTP round-trip.

    Lifecycle:
        engine = DecisionMakerEngine(session_key, splunkd_uri, tenant_id, "dsm")
        engine.load()                  # one-shot: KV reads + scoring + conf reads
        result = engine.evaluate(rec)  # per-record: pure orchestration over loaded state

    The engine is single-tenant, single-component by construction. Re-instantiate
    for a different tenant or component.
    """

    SUPPORTED_COMPONENTS = ("dsm", "dhm", "mhm", "flx", "fqm", "wlk")

    def __init__(
        self,
        session_key,
        splunkd_uri,
        tenant_id,
        component,
        *,
        system_authtoken=None,
        splunkd_port=None,
        service=None,
        service_system=None,
        logger=None,
    ):
        if component not in self.SUPPORTED_COMPONENTS:
            raise ValueError(
                f"unsupported component={component!r}; expected one of {self.SUPPORTED_COMPONENTS}"
            )
        if not tenant_id:
            raise ValueError("tenant_id is required")
        if not session_key:
            raise ValueError("session_key is required")

        if not splunkd_uri:
            raise ValueError("splunkd_uri is required")

        self.session_key = session_key
        # System token is needed for set_*_status (which writes back to the
        # disruption queue via REST) and for conf reads. Caller may pass an
        # elevated token; otherwise we reuse the session token.
        self.system_authtoken = system_authtoken or session_key
        # splunkd_uri and splunkd_port come from the caller's request_info /
        # searchinfo context (request_info.server_rest_uri /
        # request_info.server_rest_port for REST handlers,
        # self._metadata.searchinfo.splunkd_uri for custom commands).
        # Stored as-is — downstream libs (e.g. trackme_idx_for_tenant) handle
        # scheme normalisation; no fallback host or port is invented here.
        # splunkd_port may be None at construction time and is only required
        # at load() time when service / service_system need to be created.
        self.splunkd_uri = splunkd_uri
        self.splunkd_port = splunkd_port
        self.tenant_id = tenant_id
        self.component = component
        self.logger = logger or _module_logger

        # Optional pre-built service handles (lets callers reuse their own
        # connections instead of opening fresh ones).
        self._service = service
        self._service_system = service_system

        # Mirror the REST handler's instance_id so log lines can be correlated
        # with existing tooling.
        self.instance_id = None

        self._loaded = False
        self._init_state_defaults()

    # ------------------------------------------------------------------ state

    def _init_state_defaults(self):
        """Initialize every shared-state slot to a safe default.

        Mirrors the REST handler's pattern (PR #716): shared dicts are
        initialised BEFORE any component-specific block populates them, so a
        bug in component dispatch can never leak stale data from a previous
        component's scope.
        """
        # System / tenant settings
        self.trackme_conf = None
        self.vtenant_conf = None
        self.tenant_indexes = {}
        self.tenant_trackme_metric_idx = "trackme_metrics"
        self.system_future_tolerance = 0.0
        self.default_disruption_min_time_sec = 0
        self.default_monitoring_time_policy = "all_time"
        self.sla_classes = {}
        self.sla_default_class = "silver"
        self.tenant_outliers_set_state = 1
        self.tenant_data_sampling_set_state = 1

        # Global docs references (DSM/DHM/etc.)
        self.docs_is_global = "False"
        self.docs_note_global = "N/A"
        self.docs_link_global = "N/A"

        # DHM macro
        self.default_splk_dhm_alerting_policy = None

        # Scores (per-entity dict)
        self.scores_dict = {}

        # KVStore handles
        self.disruption_queue_collection = None  # mutated by set_*_status

        # Common collections
        self.ack_collection_keys = []
        self.ack_collection_dict = {}
        self.priority_collection_keys = []
        self.priority_collection_dict = {}
        self.tags_collection_keys = []
        self.tags_collection_dict = {}
        self.sla_collection_keys = []
        self.sla_collection_dict = {}
        self.disruption_queue_collection_keys = []
        self.disruption_queue_collection_dict = {}
        # Per-entity maintenance mode (forces BLUE while the window is active)
        self.entity_maintenance_collection_keys = []
        self.entity_maintenance_collection_dict = {}
        self.labels_def_collection_dict = {}
        self.labels_assign_collection_dict = {}
        self.notes_count_by_object = {}
        self.outliers_data_collection_keys = []
        self.outliers_data_collection_dict = {}
        self.outliers_rules_collection_keys = []
        self.outliers_rules_collection_dict = {}

        # Logical groups
        self.logical_coll_dict = {}
        self.logical_coll_members_list = []
        self.logical_coll_members_dict = {}

        # Blocklist / allowlist
        self.datagen_collection_dict = {}
        self.datagen_collection_blocklist_not_regex_dict = {}
        self.datagen_collection_blocklist_regex_dict = {}

        # Component-specific shared dicts — default-initialized BEFORE
        # component-specific blocks populate them (PR #716 guard).
        self.thresholds_collection_dict = {}
        self.variable_delay_collection_dict = {}
        self.lagging_classes_records = []

        # DSM-specific
        self.sampling_collection_keys = []
        self.sampling_collection_dict = {}
        self.docs_collection_members_list = []
        self.docs_collection_members_dict = {}

        # FLX-specific
        self.drilldown_searches_collection_dict = {}
        self.default_metrics_collection_dict = {}

        # WLK-specific
        self.apps_enablement_collection_keys = []
        self.apps_enablement_collection_dict = {}
        self.versioning_collection_keys = []
        self.versioning_collection_dict = {}
        self.orphan_collection_keys = []
        self.orphan_collection_dict = {}

    # ----------------------------------------------------------------- loading

    @property
    def service(self):
        if self._service is None:
            if not self.splunkd_port:
                raise ValueError(
                    "splunkd_port is required to construct a splunklib service "
                    "(pass splunkd_port=request_info.server_rest_port for REST handlers, "
                    "or pass an existing service= to the engine constructor)"
                )
            self._service = client.connect(
                owner="nobody",
                app="trackme",
                port=self.splunkd_port,
                token=self.session_key,
                timeout=600,
            )
        return self._service

    @property
    def service_system(self):
        if self._service_system is None:
            if not self.splunkd_port:
                raise ValueError(
                    "splunkd_port is required to construct a system-level splunklib service "
                    "(pass splunkd_port=request_info.server_rest_port for REST handlers, "
                    "or pass an existing service_system= to the engine constructor)"
                )
            self._service_system = client.connect(
                owner="nobody",
                app="trackme",
                port=self.splunkd_port,
                token=self.system_authtoken,
                timeout=600,
            )
        return self._service_system

    def load(self):
        """Load every collection + configuration the component needs.

        Idempotent — safe to call once per engine lifetime. Mirrors the setup
        phase of ``trackme_rest_handler_component_user.get_load_component_data``
        (lines ~348–1109 in the v2320 source).
        """
        if self._loaded:
            return

        # Generate a request-style instance_id so log lines look like the REST
        # handler's. Imported here to avoid a hard dep at module import time.
        try:
            from trackme_libs_utils import get_uuid
            self.instance_id = get_uuid()
        except Exception:
            self.instance_id = "engine"

        load_start = time.time()
        self._load_configurations()
        self._load_scores()
        self._load_component_specific_collections_phase1()
        self._load_common_collections()
        self._load_component_specific_collections_phase2()
        self._loaded = True

        # Greppable confirmation that the engine has been instantiated and
        # loaded. Operators searching for `task=decisionmaker_engine` can
        # confirm the in-process path is being used (vs. a load_component_data
        # HTTP loopback). One line per engine, regardless of how many
        # records it later evaluates.
        self.logger.info(
            f"task=decisionmaker_engine, action=load_completed, "
            f"instance_id={self.instance_id}, tenant_id={self.tenant_id}, "
            f"component={self.component}, "
            f"run_time={round(time.time() - load_start, 3)}, "
            f"score_cache_size={len(self.scores_dict)}"
        )

    def _load_configurations(self):
        # Conf reads via system-level service
        self.trackme_conf = trackme_reqinfo_from_service(self.service_system)["trackme_conf"]
        self.vtenant_conf = trackme_vtenant_account_from_service(
            self.service_system, self.tenant_id
        )

        self.system_future_tolerance = float(
            self.trackme_conf["splk_general"]["splk_general_feeds_future_tolerance"]
        )
        self.default_disruption_min_time_sec = int(
            self.vtenant_conf["default_disruption_min_time_sec"]
        )
        try:
            self.default_monitoring_time_policy = self.vtenant_conf["monitoring_time_policy"]
        except Exception:
            self.default_monitoring_time_policy = "all_time"

        # SLA classes — fall back to the shipped defaults on parse error.
        sla_classes_raw = self.trackme_conf["sla"]["sla_classes"]
        try:
            self.sla_classes = json.loads(sla_classes_raw)
            self.sla_default_class = self.trackme_conf["sla"]["sla_default_class"]
            if (
                not self.sla_default_class
                or self.sla_default_class not in self.sla_classes
            ):
                self.sla_default_class = "silver"
        except Exception:
            self.sla_classes = json.loads(
                '{"platinum": {"sla_threshold": 14400, "rank": 3}, '
                '"gold": {"sla_threshold": 86400, "rank": 2}, '
                '"silver": {"sla_threshold": 172800, "rank": 1}}'
            )
            self.sla_default_class = "silver"

        # Tenant index settings (for scoring)
        try:
            self.tenant_indexes = trackme_idx_for_tenant(
                self.system_authtoken, self.splunkd_uri, self.tenant_id
            )
            self.tenant_trackme_metric_idx = self.tenant_indexes.get(
                "trackme_metric_idx", "trackme_metrics"
            )
        except Exception as exc:
            self.logger.warning(
                f'instance_id={self.instance_id}, failed to retrieve tenant index '
                f'settings: {exc}, using default "trackme_metrics"'
            )
            self.tenant_trackme_metric_idx = "trackme_metrics"

        # Tenant-level outlier / sampling state (deprecated in scoring path
        # but still consumed by get_outliers_status / get_data_sampling_status)
        self.tenant_outliers_set_state = int(
            self.vtenant_conf.get("outliers_set_state", 1)
        )
        self.tenant_data_sampling_set_state = int(
            self.vtenant_conf.get("data_sampling_set_state", 1)
        )

        # Global docs reference (tenant override > system-wide)
        tenant_docs_note = self.vtenant_conf.get("docs_note_global", "")
        tenant_docs_link = self.vtenant_conf.get("docs_link_global", "")
        if tenant_docs_note and tenant_docs_link:
            self.docs_note_global = tenant_docs_note
            self.docs_link_global = tenant_docs_link
            self.docs_is_global = "True"
        else:
            try:
                self.docs_note_global = self.trackme_conf["splk_general"][
                    "splk_general_dsm_docs_note_global"
                ] or "N/A"
            except Exception:
                self.docs_note_global = "N/A"
            try:
                self.docs_link_global = self.trackme_conf["splk_general"][
                    "splk_general_dsm_docs_link_global"
                ] or "N/A"
            except Exception:
                self.docs_link_global = "N/A"
            if self.docs_note_global == "N/A" or self.docs_link_global == "N/A":
                self.docs_note_global = "N/A"
                self.docs_link_global = "N/A"
            else:
                self.docs_is_global = "True"

    def _load_scores(self):
        self.scores_dict = calculate_score(
            self.service,
            self.tenant_id,
            self.component,
            tenant_trackme_metric_idx=self.tenant_trackme_metric_idx,
        )

    def _load_component_specific_collections_phase1(self):
        """Load DSM-specific / DHM-macro / FLX / FQM collections that the REST
        handler loads BEFORE the common collections."""

        # DSM: data sampling + docs knowledge
        if self.component == "dsm":
            sampling_collection_name = (
                f"kv_trackme_dsm_data_sampling_tenant_{self.tenant_id}"
            )
            sampling_collection = self.service.kvstore[sampling_collection_name]
            (
                _sampling_records,
                self.sampling_collection_keys,
                self.sampling_collection_dict,
            ) = get_sampling_kv_collection(sampling_collection, sampling_collection_name)

            docs_collection_name = f"kv_trackme_dsm_knowledge_tenant_{self.tenant_id}"
            docs_collection = self.service.kvstore[docs_collection_name]
            (
                _docs_records,
                _docs_records_dict,
                self.docs_collection_members_list,
                self.docs_collection_members_dict,
            ) = get_coll_docs_ref(docs_collection, docs_collection_name)

        # DHM: default alerting policy macro
        if self.component == "dhm":
            macro_name = (
                f"trackme_dhm_default_splk_dhm_alert_policy_tenant_{self.tenant_id}"
            )
            macro_current = self.service.confs["macros"][macro_name]
            policy = macro_current.content.get("definition") or ""
            self.default_splk_dhm_alerting_policy = policy.replace('"', "")

        # FLX: thresholds, drilldowns, default metrics
        if self.component == "flx":
            thresholds_collection_name = (
                f"kv_trackme_flx_thresholds_tenant_{self.tenant_id}"
            )
            (
                _records,
                _keys,
                self.thresholds_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                self.logger, self.service, thresholds_collection_name,
                page=1, page_count=0, orderby="keyid",
            )

            drilldown_searches_collection_name = (
                f"kv_trackme_flx_drilldown_searches_tenant_{self.tenant_id}"
            )
            try:
                (
                    _records,
                    _keys,
                    self.drilldown_searches_collection_dict,
                    _last_page,
                ) = search_kv_collection_sdkmode(
                    self.logger, self.service, drilldown_searches_collection_name,
                    page=1, page_count=0, orderby="keyid",
                )
            except Exception:
                self.drilldown_searches_collection_dict = {}

            default_metrics_collection_name = (
                f"kv_trackme_flx_default_metric_tenant_{self.tenant_id}"
            )
            try:
                (
                    _records,
                    _keys,
                    self.default_metrics_collection_dict,
                    _last_page,
                ) = search_kv_collection_sdkmode(
                    self.logger, self.service, default_metrics_collection_name,
                    page=1, page_count=0, orderby="keyid",
                )
            except Exception:
                self.default_metrics_collection_dict = {}

        # FQM: thresholds
        if self.component == "fqm":
            thresholds_collection_name = (
                f"kv_trackme_fqm_thresholds_tenant_{self.tenant_id}"
            )
            (
                _records,
                _keys,
                self.thresholds_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                self.logger, self.service, thresholds_collection_name,
                page=1, page_count=0, orderby="keyid",
            )

    def _load_common_collections(self):
        """Load every collection consumed by every component."""

        # Logical groups
        logical_group_coll = self.service.kvstore[
            f"kv_trackme_common_logical_group_tenant_{self.tenant_id}"
        ]
        (
            _logical_records,
            self.logical_coll_dict,
            self.logical_coll_members_list,
            self.logical_coll_members_dict,
            _logical_count,
        ) = get_logical_groups_collection_records(logical_group_coll)

        # Ack collection
        ack_collection_name = f"kv_trackme_common_alerts_ack_tenant_{self.tenant_id}"
        (
            _ack_records,
            self.ack_collection_keys,
            self.ack_collection_dict,
            _last_page,
        ) = search_kv_collection_sdkmode(
            self.logger, self.service, ack_collection_name,
            page=1, page_count=0, orderby="object",
        )

        # Priority / Tags / SLA
        priority_collection_name = (
            f"kv_trackme_{self.component}_priority_tenant_{self.tenant_id}"
        )
        (
            _records,
            self.priority_collection_keys,
            self.priority_collection_dict,
            _last_page,
        ) = search_kv_collection_sdkmode(
            self.logger, self.service, priority_collection_name,
            page=1, page_count=0, orderby="keyid",
        )

        tags_collection_name = (
            f"kv_trackme_{self.component}_tags_tenant_{self.tenant_id}"
        )
        (
            _records,
            self.tags_collection_keys,
            self.tags_collection_dict,
            _last_page,
        ) = search_kv_collection_sdkmode(
            self.logger, self.service, tags_collection_name,
            page=1, page_count=0, orderby="keyid",
        )

        sla_collection_name = (
            f"kv_trackme_{self.component}_sla_tenant_{self.tenant_id}"
        )
        (
            _records,
            self.sla_collection_keys,
            self.sla_collection_dict,
            _last_page,
        ) = search_kv_collection_sdkmode(
            self.logger, self.service, sla_collection_name,
            page=1, page_count=0, orderby="keyid",
        )

        # Disruption queue — keep the collection HANDLE because set_*_status
        # writes back to it for grace-period accounting.
        disruption_queue_collection_name = (
            f"kv_trackme_common_disruption_queue_tenant_{self.tenant_id}"
        )
        self.disruption_queue_collection = self.service.kvstore[
            disruption_queue_collection_name
        ]
        (
            _records,
            self.disruption_queue_collection_keys,
            self.disruption_queue_collection_dict,
            _last_page,
        ) = search_kv_collection_sdkmode(
            self.logger, self.service, disruption_queue_collection_name,
            page=1, page_count=0, orderby="keyid",
        )

        # Per-entity maintenance mode. Older tenants may not have the collection
        # until the general health manager backfills it — that case is expected
        # and degrades to empty. But a genuine read failure (auth/session) must
        # NOT silently disable maintenance (which would re-enable alerting on
        # entities that should be protected), so we only treat a MISSING
        # collection as empty and let real read errors propagate. Keyed by the
        # entity's SHA256 object_id (_key), looked up per record below.
        entity_maintenance_collection_name = (
            f"kv_trackme_common_entity_maintenance_tenant_{self.tenant_id}"
        )
        if entity_maintenance_collection_name in self.service.kvstore:
            (
                _records,
                self.entity_maintenance_collection_keys,
                self.entity_maintenance_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                self.logger, self.service, entity_maintenance_collection_name,
                page=1, page_count=0, orderby="keyid",
            )
        else:
            self.logger.info(
                f'maintenance collection="{entity_maintenance_collection_name}" not present yet; '
                f'skipping maintenance override for this run'
            )
            self.entity_maintenance_collection_keys = []
            self.entity_maintenance_collection_dict = {}

        # Labels (definitions + assignments) — best-effort; older tenants may
        # not have these collections.
        labels_def_collection_name = f"kv_trackme_labels_tenant_{self.tenant_id}"
        try:
            (
                _records,
                _keys,
                self.labels_def_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                self.logger, self.service, labels_def_collection_name,
                page=1, page_count=0, orderby="keyid",
            )
        except Exception:
            self.labels_def_collection_dict = {}

        labels_assign_collection_name = (
            f"kv_trackme_label_assignments_tenant_{self.tenant_id}"
        )
        try:
            (
                _records,
                _keys,
                self.labels_assign_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                self.logger, self.service, labels_assign_collection_name,
                page=1, page_count=0, orderby="keyid",
            )
        except Exception:
            self.labels_assign_collection_dict = {}

        # Notes counts (per object_id)
        notes_collection_name = f"kv_trackme_notes_tenant_{self.tenant_id}"
        try:
            (
                notes_records,
                _keys,
                _notes_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                self.logger, self.service, notes_collection_name,
                page=1, page_count=0, orderby="keyid",
            )
            counts = {}
            for note_rec in notes_records or []:
                note_object_id = note_rec.get("object_id")
                if note_object_id:
                    counts[note_object_id] = counts.get(note_object_id, 0) + 1
            self.notes_count_by_object = counts
        except Exception:
            self.notes_count_by_object = {}

        # Outliers (data + rules) — for every component except MHM
        if self.component != "mhm":
            outliers_data_collection_name = (
                f"kv_trackme_{self.component}_outliers_entity_data_tenant_{self.tenant_id}"
            )
            (
                _records,
                self.outliers_data_collection_keys,
                self.outliers_data_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                self.logger, self.service, outliers_data_collection_name,
                page=1, page_count=0, orderby="keyid",
            )

            outliers_rules_collection_name = (
                f"kv_trackme_{self.component}_outliers_entity_rules_tenant_{self.tenant_id}"
            )
            (
                _records,
                self.outliers_rules_collection_keys,
                self.outliers_rules_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                self.logger, self.service, outliers_rules_collection_name,
                page=1, page_count=0, orderby="keyid",
            )

        # Allowlist / blocklist (datagen)
        if self.component in self.SUPPORTED_COMPONENTS:
            datagen_collection_name = (
                f"kv_trackme_{self.component}_allowlist_tenant_{self.tenant_id}"
            )
            datagen_collection = self.service.kvstore[datagen_collection_name]
            (
                _records,
                _keys,
                self.datagen_collection_dict,
                self.datagen_collection_blocklist_not_regex_dict,
                self.datagen_collection_blocklist_regex_dict,
            ) = get_feeds_datagen_kv_collection(
                datagen_collection, datagen_collection_name, self.component
            )

    def _load_component_specific_collections_phase2(self):
        """WLK-specific + variable-delay/lagging-classes collections that the
        REST handler loads AFTER the common collections."""

        if self.component == "wlk":
            apps_enablement_collection_name = (
                f"kv_trackme_wlk_apps_enablement_tenant_{self.tenant_id}"
            )
            apps_enablement_collection = self.service.kvstore[
                apps_enablement_collection_name
            ]
            (
                _records,
                self.apps_enablement_collection_keys,
                self.apps_enablement_collection_dict,
            ) = get_wlk_apps_enablement_kv_collection(
                apps_enablement_collection, apps_enablement_collection_name
            )

            versioning_collection_name = (
                f"kv_trackme_wlk_versioning_tenant_{self.tenant_id}"
            )
            (
                _records,
                self.versioning_collection_keys,
                self.versioning_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                self.logger, self.service, versioning_collection_name,
                page=1, page_count=0, orderby="keyid",
            )

            orphan_collection_name = (
                f"kv_trackme_wlk_orphan_status_tenant_{self.tenant_id}"
            )
            (
                _records,
                self.orphan_collection_keys,
                self.orphan_collection_dict,
                _last_page,
            ) = search_kv_collection_sdkmode(
                self.logger, self.service, orphan_collection_name,
                page=1, page_count=0, orderby="keyid",
            )

            wlk_thresholds_collection_name = (
                f"kv_trackme_wlk_thresholds_tenant_{self.tenant_id}"
            )
            try:
                (
                    _records,
                    _keys,
                    self.thresholds_collection_dict,
                    _last_page,
                ) = search_kv_collection_sdkmode(
                    self.logger, self.service, wlk_thresholds_collection_name,
                    page=1, page_count=0, orderby="keyid",
                )
            except Exception:
                self.thresholds_collection_dict = {}

        # Variable delay (DSM/DHM)
        if self.component in ("dsm", "dhm"):
            variable_delay_collection_name = (
                f"kv_trackme_{self.component}_variable_delay_tenant_{self.tenant_id}"
            )
            try:
                (
                    _records,
                    _keys,
                    self.variable_delay_collection_dict,
                    _last_page,
                ) = search_kv_collection_sdkmode(
                    self.logger, self.service, variable_delay_collection_name,
                    page=1, page_count=0, orderby="keyid",
                )
            except Exception as exc:
                self.logger.warning(
                    f'instance_id={self.instance_id}, failed to load variable delay '
                    f'collection={variable_delay_collection_name}, exception="{exc}", '
                    f'variable delay will not be applied'
                )
                self.variable_delay_collection_dict = {}

            lagging_classes_collection_name = (
                f"kv_trackme_{self.component}_lagging_classes_tenant_{self.tenant_id}"
            )
            try:
                (
                    self.lagging_classes_records,
                    _keys,
                    _dict,
                    _last_page,
                ) = search_kv_collection_sdkmode(
                    self.logger, self.service, lagging_classes_collection_name,
                    page=1, page_count=0, orderby="keyid",
                )
            except Exception as exc:
                self.logger.warning(
                    f'instance_id={self.instance_id}, failed to load lagging classes '
                    f'collection={lagging_classes_collection_name}, exception="{exc}"'
                )
                self.lagging_classes_records = []

    # ---------------------------------------------------- alternate construction

    @classmethod
    def from_preloaded(
        cls,
        session_key,
        splunkd_uri,
        tenant_id,
        component,
        *,
        preloaded,
        system_authtoken=None,
        splunkd_port=None,
        service=None,
        service_system=None,
        logger=None,
    ):
        """Construct an engine with collections already loaded by the caller.

        ``preloaded`` is a dict whose keys map directly onto engine attributes
        (``scores_dict``, ``priority_collection_dict``, ...). Missing keys keep
        their safe defaults — useful for unit tests that only need a subset.

        The disruption queue collection HANDLE (``disruption_queue_collection``)
        must be supplied if the caller expects ``set_*_status`` to mutate it
        (live evaluation); for read-only equivalence checks pass a stub object
        that no-ops on writes.
        """
        engine = cls(
            session_key,
            splunkd_uri,
            tenant_id,
            component,
            system_authtoken=system_authtoken,
            splunkd_port=splunkd_port,
            service=service,
            service_system=service_system,
            logger=logger,
        )
        for key, value in (preloaded or {}).items():
            if hasattr(engine, key):
                setattr(engine, key, value)
            else:
                raise AttributeError(
                    f"DecisionMakerEngine has no attribute {key!r}; "
                    f"check the preloaded dict"
                )
        engine._loaded = True
        return engine

    # ----------------------------------------------------------- evaluation API

    def evaluate(self, record):
        """Evaluate one entity record. Mutates and returns the record.

        Pre-condition: ``load()`` has been called (or the engine was built via
        ``from_preloaded()``). Raises ``RuntimeError`` otherwise.

        Returns the same dict instance, augmented with ``object_state``,
        ``status_message``, ``status_message_json``, ``anomaly_reason``,
        ``score``, ``score_outliers``, ``state_icon_code``, etc. — exactly
        the fields ``GET /trackme/v2/component/load_component_data`` would
        attach.
        """
        if not self._loaded:
            raise RuntimeError(
                "DecisionMakerEngine: call .load() or use .from_preloaded() before .evaluate()"
            )

        try:
            evaluated = self._evaluate_unsafe(record)
        except Exception as exc:
            # Mirror the REST handler's behaviour: log and do not propagate
            # so a single bad record can't poison a batch.
            #
            # The REST handler's per-entity loop body wraps the same
            # orchestration in `try: ... except Exception: continue` (around
            # line 3310 of trackme_rest_handler_component_user.py), so
            # records that fail evaluation are skipped — they never make it
            # into `processed_records` / the response array.
            #
            # Match that here by setting `_dme_append = False` on the
            # returned record. Both downstream filters in this module
            # (evaluate_all, evaluate_object_full) treat _dme_append=False
            # as "exclude / surface as None", which is exactly the behaviour
            # the REST handler had.
            self.logger.error(
                f'instance_id={self.instance_id}, tenant_id="{self.tenant_id}", '
                f'component="{self.component}", Error processing record, '
                f'exception="{exc}"'
            )
            record["_dme_append"] = False
            return record

        # Per-record greppable confirmation. DEBUG-level so it does not flood
        # logs at INFO; flip the engine logger to DEBUG to verify the engine
        # is being called per record. Same `task=decisionmaker_engine` token
        # as load() — operators searching for that string see both the
        # one-shot load lines and the per-record evaluations together.
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"task=decisionmaker_engine, action=evaluate, "
                f"instance_id={self.instance_id}, tenant_id={self.tenant_id}, "
                f"component={self.component}, "
                f"object_id={evaluated.get('keyid', '')}, "
                f"object={evaluated.get('object', '')}, "
                f"object_state={evaluated.get('object_state', '')}"
            )
        return evaluated

    def evaluate_records(self, records):
        """Evaluate a list of records. Returns the (mutated) list."""
        out = []
        for record in records:
            out.append(self.evaluate(record))
        return out

    def evaluate_all(self):
        """Fetch every KV record for this (tenant, component) and evaluate them.

        Equivalent to ``GET /trackme/v2/component/load_component_data`` with
        ``pagination_mode=local`` and no filters: returns every record the
        REST handler would have returned, in the same order, with the same
        per-entity enrichment (``object_state``, ``anomaly_reason``,
        ``status_message``, ``score``, scoring fields, ``tags``,
        ``labels``, ``state_icon_code``, etc.).

        Records filtered out by the per-component blocklist
        (``_dme_append`` is ``False``) are excluded from the returned list,
        matching the REST handler's
        ``if append_record: processed_records.append(record)`` gate.

        Designed for batch callers (REST handlers and scheduled jobs that
        need the full tenant view in one shot — e.g. shadow refresh, summary
        stats, the tenant-wide describe path).
        """
        if not self._loaded:
            raise RuntimeError(
                "DecisionMakerEngine: call .load() or use .from_preloaded() before .evaluate_all()"
            )

        data_collection_name = f"kv_trackme_{self.component}_tenant_{self.tenant_id}"

        # Honour the system-wide kvcollection_mode setting from
        # trackme_settings.conf [trackme_general] central_kvcollection_mode
        # (default "search_mode" — runs `| inputlookup <coll>` as a Splunk
        # search, usually faster at scale than the SDK direct read).
        # The dispatcher search_kv_collection() routes to the right
        # implementation; this matches what get_load_component_data does
        # for its bulk read so the engine path is performance-equivalent
        # at scale, not just functionally equivalent.
        try:
            kvcollection_mode = self.trackme_conf["trackme_general"].get(
                "central_kvcollection_mode", "search_mode"
            )
        except Exception:
            kvcollection_mode = "search_mode"

        raw_records, _keys, _dict, _last_page = search_kv_collection(
            self.service,
            data_collection_name,
            page=1,
            page_count=0,
            kvcollection_mode=kvcollection_mode,
            provenance=f"DecisionMakerEngine.evaluate_all:{self.component}:tenant_{self.tenant_id}",
            logger=self.logger,
            instance_id=self.instance_id,
        )
        evaluated_records = self.evaluate_records(raw_records)
        # Filter on _dme_append (default False — defence in depth: the
        # contract is that evaluate() always sets the flag, so a missing
        # flag would only happen via a future regression; treat missing as
        # "exclude" to match the REST handler's
        # `if append_record: processed_records.append(record)` gate).
        # Then strip the internal flag from the kept records — high-level
        # callers (REST handlers returning the records directly as JSON
        # responses) must not see this internal field, which the legacy
        # load_component_data response never had.
        kept = []
        for record in evaluated_records:
            if record.get("_dme_append", False):
                record.pop("_dme_append", None)
                kept.append(record)
        return kept

    def evaluate_object_full(self, value, *, lookup_field="_key"):
        """Fetch the single KV record matching ``value`` on ``lookup_field``
        (default ``_key``) and evaluate it.

        Returns the full mutated record dict (every field the REST handler's
        per-entity loop body produces — ``object_state``, ``anomaly_reason``,
        ``status_message``, ``score``, ``score_outliers``, ``tags``,
        ``labels``, etc.), or ``None`` if:
          - the record does not exist, or
          - the record was filtered out by the blocklist (``_dme_append`` is
            False — the entity is excluded from monitoring, so the engine has
            not recomputed its state).

        Designed for hot-loop callers (custom commands, alert actions) that
        want to amortize ``load()`` across many lookups and only need to do
        a per-object KV lookup on each iteration.

        ``lookup_field`` matches the load_component_data REST endpoint's
        filter semantics: ``_key`` corresponds to ``filter_key=`` and
        ``object`` corresponds to ``filter_object=``.
        """
        if not self._loaded:
            raise RuntimeError(
                "DecisionMakerEngine: call .load() or use .from_preloaded() before .evaluate_object_full()"
            )

        data_collection_name = f"kv_trackme_{self.component}_tenant_{self.tenant_id}"
        data_collection = self.service.kvstore[data_collection_name]
        data_records, _keys, _dict = get_target_from_kv_collection(
            lookup_field, value, data_collection, data_collection_name
        )
        if not data_records:
            return None

        evaluated = self.evaluate(data_records[0])
        # Default False (defence in depth): see the equivalent comment in
        # evaluate_all(). Treats both "blocklisted" and "evaluation raised"
        # as no-decision so callers can fail open uniformly.
        if not evaluated.get("_dme_append", False):
            return None
        # Strip the internal flag from the returned record — high-level
        # callers must not see this internal field, which the legacy
        # load_component_data response never had.
        evaluated.pop("_dme_append", None)
        return evaluated

    # ----------------------------------------------------------- per-record body

    def _evaluate_unsafe(self, record):
        """Per-record orchestration. Faithful port of the REST handler's loop body."""

        # Tenant ID safeguard
        if not record.get("tenant_id"):
            record["tenant_id"] = self.tenant_id

        # Track whether the record should be kept (blocklist may flip this)
        append_record = True

        object_value = record.get("object", None)

        # Preserve the KV-current state (some downstream logic needs the
        # original value, e.g. SLA timer)
        record["kvcurrent_object_state"] = record.get("object_state", "N/A")

        key_value = record.get("_key", None)
        record["keyid"] = key_value

        # Score lookup
        try:
            score = int(self.scores_dict.get(key_value, {}).get("score", 0))
        except Exception:
            score = 0
        try:
            score_outliers = int(
                self.scores_dict.get(key_value, {}).get("score_outliers", 0)
            )
        except Exception:
            score_outliers = 0
        try:
            score_source = self.scores_dict.get(key_value, {}).get("score_source", [])
        except Exception:
            score_source = []
        record["score"] = score
        record["score_outliers"] = score_outliers
        record["score_source"] = score_source

        # Alias hygiene
        record["alias"] = replace_encoded_backslashes(record.get("alias", ""))

        # Logical group lookup (skipped for WLK)
        if self.component != "wlk":
            logical_group_lookup(
                object_value,
                self.logical_coll_members_list,
                self.logical_coll_members_dict,
                record,
            )

        # Default-threshold safety checks for feeds
        if self.component == "dsm":
            dsm_check_default_thresholds(record, self.trackme_conf)
        elif self.component == "dhm":
            dhm_check_default_thresholds(record, self.trackme_conf)

        # Acknowledgement check
        ack_check(
            object_value,
            self.ack_collection_keys,
            self.ack_collection_dict,
            record,
        )

        # Dynamic priority / tags / labels / SLA
        dynamic_priority_lookup(
            key_value,
            self.priority_collection_keys,
            self.priority_collection_dict,
            record,
        )
        dynamic_tags_lookup(
            key_value,
            self.tags_collection_keys,
            self.tags_collection_dict,
            record,
        )
        dynamic_labels_lookup(
            key_value,
            self.component,
            self.labels_def_collection_dict,
            self.labels_assign_collection_dict,
            record,
        )

        record["notes_count"] = self.notes_count_by_object.get(key_value, 0)

        dynamic_sla_class_lookup(
            key_value,
            self.sla_collection_keys,
            self.sla_collection_dict,
            record,
        )

        # Disruption queue: aggregate per-tracker disruption_min_time_sec
        aggregated_disruption_min_time_sec = self._aggregate_disruption_min_time(
            record, object_value
        )

        disruption_queue_record = disruption_queue_lookup(
            key_value,
            self.disruption_queue_collection_keys,
            self.disruption_queue_collection_dict,
            aggregated_disruption_min_time_sec,
        )

        # Outliers data lookup (all components except MHM)
        if self.component != "mhm":
            outliers_data_lookup(
                key_value,
                self.outliers_data_collection_keys,
                self.outliers_data_collection_dict,
                self.outliers_rules_collection_keys,
                self.outliers_rules_collection_dict,
                record,
            )

        # Outliers readiness flag
        outliers_readiness(record)

        # Human time fields
        record["latest_flip_time (translated)"] = convert_epoch_to_datetime(
            record.get("latest_flip_time", "0")
        )
        record["tracker_runtime (translated)"] = convert_epoch_to_datetime(
            record.get("tracker_runtime", "0")
        )

        # Tags normalisation
        self._normalize_tags(record)

        # Component dispatch
        component_state = {
            "score": score,
            "score_outliers": score_outliers,
            "disruption_queue_record": disruption_queue_record,
            "object_value": object_value,
            "key_value": key_value,
        }

        if self.component == "dsm":
            append_record = self._evaluate_dsm(record, component_state, append_record)
        elif self.component == "dhm":
            append_record = self._evaluate_dhm(record, component_state, append_record)
        elif self.component == "mhm":
            append_record = self._evaluate_mhm(record, component_state, append_record)
        elif self.component == "flx":
            append_record = self._evaluate_flx(record, component_state, append_record)
        elif self.component == "fqm":
            append_record = self._evaluate_fqm(record, component_state, append_record)
        elif self.component == "wlk":
            append_record = self._evaluate_wlk(record, component_state, append_record)

        # Final defaults applied across components
        if append_record:
            if not record.get("object_state", None):
                record["object_state"] = "red"

            # Per-entity maintenance override (TOP precedence). Applied as the
            # FINAL state mutation so it wins over the computed state AND every
            # other blue/protection layer (ACK, disruption grace, logical
            # group). Inert the moment the window expires. Done before
            # define_state_icon_code so the icon reflects the blue state.
            maintenance_record = entity_maintenance_lookup(
                key_value,
                self.entity_maintenance_collection_keys,
                self.entity_maintenance_collection_dict,
            )
            if maintenance_record:
                apply_entity_maintenance_override(record, maintenance_record)
            else:
                # No active window — strip any stale maintenance metadata a
                # prior (now-expired) window may have persisted on the record.
                clear_entity_maintenance_fields(record)

            record["state_icon_code"] = define_state_icon_code(record)

        # Replica swap (preserve the parent tenant in the same way the REST
        # handler does post-loop). We do it here because callers passing a
        # single record would otherwise miss it.
        tenant_parent = record.get("tenant_parent")
        if tenant_parent and str(tenant_parent) not in ("", "None"):
            record["tenant_replica_id"] = record.get("tenant_id", "")
            record["tenant_id"] = tenant_parent

        # Internal flag consumed by evaluate_all() / evaluate_object_full()
        # to filter out records the per-component dispatch dropped (blocklist
        # or evaluation exception). Both high-level methods strip it before
        # returning so it never reaches API callers.
        record["_dme_append"] = append_record
        return record

    # ----------------------------------------------------------- helpers (utility)

    def _aggregate_disruption_min_time(self, record, object_value):
        aggregated = self.default_disruption_min_time_sec
        if "disruption_min_time_sec" not in record:
            return aggregated

        try:
            value = record.get("disruption_min_time_sec")
            if not value:
                return aggregated

            disruption_times_by_tracker = None
            if isinstance(value, str):
                try:
                    disruption_times_by_tracker = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        return max(
                            self.default_disruption_min_time_sec,
                            int(float(value)),
                        )
                    except (ValueError, TypeError):
                        return aggregated
            elif isinstance(value, dict):
                disruption_times_by_tracker = value
            else:
                try:
                    return max(
                        self.default_disruption_min_time_sec,
                        int(float(value)),
                    )
                except (ValueError, TypeError):
                    return aggregated

            if disruption_times_by_tracker and isinstance(
                disruption_times_by_tracker, dict
            ):
                max_disruption_time = max(
                    int(float(v)) for v in disruption_times_by_tracker.values()
                )
                return max(self.default_disruption_min_time_sec, max_disruption_time)
        except Exception as exc:
            self.logger.error(
                f'instance_id={self.instance_id}, failed to aggregate '
                f'disruption_min_time_sec for object="{object_value}", exception="{exc}"'
            )
        return aggregated

    def _normalize_tags(self, record):
        tags_auto = record.get("tags_auto", []) or []
        tags_manual = record.get("tags_manual", []) or []

        if isinstance(tags_auto, str):
            tags_auto = tags_auto.split(",")
        if isinstance(tags_manual, str):
            tags_manual = tags_manual.split(",")

        record["tags_auto"] = tags_auto
        record["tags_manual"] = tags_manual

        tags = sorted(
            list(set([x.lower() for x in (tags_auto + tags_manual) if x]))
        )
        record["tags"] = tags if tags else "N/A"

    # ----------------------------------------------------------- per-component

    def _evaluate_dsm(self, record, state, append_record):
        if (
            self.datagen_collection_blocklist_not_regex_dict
            or self.datagen_collection_blocklist_regex_dict
        ):
            append_record = apply_blocklist(
                record,
                self.datagen_collection_blocklist_not_regex_dict,
                self.datagen_collection_blocklist_regex_dict,
            )
        if not append_record:
            return False

        score = state["score"]
        score_outliers = state["score_outliers"]
        disruption_queue_record = state["disruption_queue_record"]
        object_value = state["object_value"]
        key_value = state["key_value"]

        # Refresh delay vs now
        try:
            record["data_last_lag_seen"] = time.time() - float(
                record.get("data_last_time_seen", 0)
            )
        except Exception:
            record["data_last_lag_seen"] = 0

        # Outlier / anomaly raw flags
        try:
            isOutlier = int(record.get("isOutlier", 0))
        except Exception:
            isOutlier = 0
        try:
            OutliersDisabled = int(record.get("OutliersDisabled", 0))
        except Exception:
            OutliersDisabled = 0
        try:
            isAnomaly = int(record.get("isAnomaly", 0))
        except Exception:
            isAnomaly = 0

        # Future tolerance
        future_tolerance = record.get("future_tolerance", 0)
        try:
            future_tolerance = float(future_tolerance)
        except Exception:
            future_tolerance = 0

        # Primary KPIs
        data_last_ingestion_lag_seen = record.get("data_last_ingestion_lag_seen", 0)
        if data_last_ingestion_lag_seen == "":
            data_last_ingestion_lag_seen = 0
        try:
            data_last_ingestion_lag_seen = float(data_last_ingestion_lag_seen)
        except Exception:
            data_last_ingestion_lag_seen = 0
        data_last_lag_seen = record.get("data_last_lag_seen", 0)

        data_max_lag_allowed = float(record.get("data_max_lag_allowed", 0))
        data_max_delay_allowed = float(record.get("data_max_delay_allowed", 0))

        # Threshold intent lock — when the operator has pinned the delay / lag
        # threshold, the decision maker must NOT override it with a lagging-class
        # or variable-delay resolved value. The flag is a persistent field on the
        # entity record (default "false" / absent = not locked). The locked value
        # stays in data_max_{delay,lag}_allowed so the status evaluation below
        # uses the pinned threshold.
        delay_locked = (
            str(record.get("data_max_delay_allowed_locked", "false")).strip().lower()
            == "true"
        )
        lag_locked = (
            str(record.get("data_max_lag_allowed_locked", "false")).strip().lower()
            == "true"
        )

        # Lagging class resolution
        lc_matched = False
        lc_delay_mode = None
        lc_resolved_delay = None
        lc_active_slot = None
        if self.lagging_classes_records:
            (
                lc_matched,
                lc_override_lag,
                lc_override_delay,
                lc_delay_mode,
                lc_resolved_delay,
                lc_active_slot,
                lc_match_info,
            ) = resolve_lagging_class_threshold(record, self.lagging_classes_records)
            if lc_matched:
                if lc_override_lag is not None and not lag_locked:
                    data_max_lag_allowed = lc_override_lag
                    record["data_max_lag_allowed"] = lc_override_lag
                if (
                    lc_delay_mode == "static"
                    and lc_override_delay is not None
                    and not delay_locked
                ):
                    data_max_delay_allowed = lc_override_delay
                    record["data_max_delay_allowed"] = lc_override_delay
                record["lagging_class_matched"] = "true"
                record["lagging_class_name"] = str(lc_match_info.get("name", ""))
                record["lagging_class_level"] = str(lc_match_info.get("level", ""))
                record["lagging_class_match_mode"] = str(lc_match_info.get("match_mode", ""))
                record["lagging_class_delay_mode"] = str(lc_delay_mode) if lc_delay_mode else ""
                record["lagging_class_key"] = str(lc_match_info.get("_key", ""))
        if not lc_matched:
            record["lagging_class_matched"] = "false"
            record["lagging_class_name"] = ""
            record["lagging_class_level"] = ""
            record["lagging_class_match_mode"] = ""
            record["lagging_class_delay_mode"] = ""
            record["lagging_class_key"] = ""

        min_dcount_threshold = record.get("min_dcount_threshold", 0)
        try:
            min_dcount_threshold = float(min_dcount_threshold)
        except Exception:
            min_dcount_threshold = 0

        min_dcount_host = record.get("min_dcount_host", "any")
        try:
            min_dcount_host = float(min_dcount_host)
        except Exception:
            pass
        min_dcount_field = record.get("min_dcount_field", None)

        # Monitoring time policy
        monitoring_time_policy = record.get("monitoring_time_policy", None)
        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
            monitoring_time_policy = self.default_monitoring_time_policy
            record["monitoring_time_policy"] = self.default_monitoring_time_policy
        monitoring_time_rules = record.get("monitoring_time_rules", None)

        # Logical group dict for set_*_status
        object_group_key = record.get("object_group_key", "")
        object_logical_group_dict = self.logical_coll_dict.get(object_group_key, {})

        # Time fields (epoch)
        data_last_ingest = record.get("data_last_ingest", 0)
        try:
            data_last_ingest = float(data_last_ingest)
        except Exception:
            pass
        data_last_time_seen = record.get("data_last_time_seen", 0)
        if data_last_time_seen == "":
            data_last_time_seen = 0
        try:
            data_last_time_seen = float(data_last_time_seen)
        except Exception:
            data_last_time_seen = 0

        # Status helpers
        (
            isUnderMonitoring,
            monitoring_anomaly_reason,
            isUnderMonitoringMsg,
        ) = get_monitoring_time_status(monitoring_time_policy, monitoring_time_rules)

        isOutlier = get_outliers_status(
            isOutlier,
            OutliersDisabled,
            self.tenant_outliers_set_state,
            score_outliers=score_outliers,
        )

        # DSM sampling lookup + status
        dsm_sampling_lookup(
            object_value,
            self.sampling_collection_keys,
            self.sampling_collection_dict,
            record,
        )
        isAnomaly = get_data_sampling_status(
            record.get("data_sample_status_colour"),
            record.get("data_sample_feature"),
            self.tenant_data_sampling_set_state,
        )

        (
            isFuture,
            isFutureMsg,
            merged_future_tolerance,
        ) = get_future_status(
            future_tolerance,
            self.system_future_tolerance,
            data_last_lag_seen,
            data_last_ingestion_lag_seen,
            data_last_time_seen,
            data_last_ingest,
        )

        (
            isUnderDcountHost,
            isUnderDcountHostMsg,
        ) = get_is_under_dcount_host(min_dcount_host, min_dcount_threshold, min_dcount_field)

        (
            isUnderLatencyAlert,
            isUnderLatencyMessage,
        ) = get_dsm_latency_status(
            data_last_ingestion_lag_seen,
            data_max_lag_allowed,
            data_last_ingest,
            data_last_time_seen,
        )

        # Variable delay resolution
        if lc_matched and lc_delay_mode == "variable":
            resolved_threshold = lc_resolved_delay
            active_slot_name = lc_active_slot
            is_variable = True
        elif lc_matched and lc_delay_mode == "static":
            resolved_threshold = None
            active_slot_name = None
            is_variable = False
        else:
            variable_delay_record = self.variable_delay_collection_dict.get(key_value, None)
            (
                resolved_threshold,
                active_slot_name,
                is_variable,
            ) = resolve_variable_delay_threshold(record, variable_delay_record)

        # Threshold intent lock — a pinned delay threshold must GOVERN the
        # decision/alert path and IGNORE lagging classes. But a locked
        # VARIABLE-policy entity must keep evaluating against its OWN slots
        # (time-aware) — it must NOT collapse to a flat static value. So re-resolve
        # from the entity's own variable-delay record: a variable-policy entity
        # keeps its slots, a static-policy entity resolves to is_variable=False and
        # uses the pinned data_max_delay_allowed. (This deliberately bypasses any
        # matched lagging class above — the lock means the operator's own config
        # wins.) For variable entities reconcile restores slot drift; it does NOT
        # touch data_max_delay_allowed, which legitimately tracks the active slot.
        if delay_locked:
            variable_delay_record = self.variable_delay_collection_dict.get(key_value, None)
            (
                resolved_threshold,
                active_slot_name,
                is_variable,
            ) = resolve_variable_delay_threshold(record, variable_delay_record)

        if is_variable:
            record["variable_delay_active_slot"] = (
                str(active_slot_name) if active_slot_name else ""
            )
            record["variable_delay_active_threshold"] = str(int(round(resolved_threshold, 0)))
            record["data_max_delay_allowed"] = resolved_threshold
        else:
            record["variable_delay_active_slot"] = ""
            record["variable_delay_active_threshold"] = ""

        (
            isUnderDelayAlert,
            isUnderDelayMessage,
        ) = get_dsm_delay_status(
            data_last_lag_seen,
            data_max_delay_allowed,
            data_last_ingest,
            data_last_time_seen,
            resolved_max_delay_allowed=resolved_threshold if is_variable else None,
            variable_delay_slot_name=active_slot_name if is_variable else None,
        )

        # Compose state via set_dsm_status — same call shape as REST handler.
        # Note: source_handler="rest_handler" matches the REST handler value
        # so the function's internal branching produces identical output.
        (
            object_state,
            status_message,
            status_message_json,
            anomaly_reason,
        ) = set_dsm_status(
            self.logger,
            self.splunkd_uri,
            self.system_authtoken,
            self.tenant_id,
            record,
            isOutlier,
            isAnomaly,
            isFuture,
            isFutureMsg,
            isUnderMonitoring,
            isUnderMonitoringMsg,
            isUnderDcountHost,
            isUnderDcountHostMsg,
            object_logical_group_dict,
            isUnderLatencyAlert,
            isUnderLatencyMessage,
            isUnderDelayAlert,
            isUnderDelayMessage,
            self.disruption_queue_collection,
            disruption_queue_record,
            source_handler="rest_handler",
            monitoring_anomaly_reason=monitoring_anomaly_reason,
            score=score,
            score_outliers=score_outliers,
            vtenant_account=self.vtenant_conf,
            delay_is_variable=is_variable,
        )

        record["object_state"] = object_state
        record["status_message"] = " | ".join(status_message)
        record["status_message_json"] = status_message_json
        record["anomaly_reason"] = "|".join(anomaly_reason)

        # DSM-specific post-processing
        sampling_anomaly_status(record)
        try:
            record["future_tolerance"] = int(round(merged_future_tolerance, 0))
        except Exception:
            record["future_tolerance"] = -600

        record["last_time"] = convert_epoch_to_datetime(data_last_time_seen)
        record["last_ingest"] = convert_epoch_to_datetime(data_last_ingest)
        record["last_time_idx"] = convert_epoch_to_datetime(data_last_time_seen)

        latest_flip_time_human = record.get("latest_flip_time", 0)
        try:
            latest_flip_time_human = float(latest_flip_time_human)
        except Exception:
            latest_flip_time_human = 0
        record["latest_flip_time_human"] = convert_epoch_to_datetime(latest_flip_time_human)

        record["lag_summary"] = set_feeds_lag_summary(record, self.component)

        (
            data_max_delay_allowed_duration,
            data_max_lag_allowed_duration,
        ) = set_feeds_thresholds_duration(record)
        record["data_max_delay_allowed_duration"] = data_max_delay_allowed_duration
        record["data_max_lag_allowed_duration"] = data_max_lag_allowed_duration

        docs_ref_lookup(
            self.docs_is_global,
            self.docs_note_global,
            self.docs_link_global,
            object_value,
            self.docs_collection_members_list,
            self.docs_collection_members_dict,
            record,
        )

        get_sla_timer(record, self.sla_classes, self.sla_default_class)
        return True

    def _evaluate_dhm(self, record, state, append_record):
        if (
            self.datagen_collection_blocklist_not_regex_dict
            or self.datagen_collection_blocklist_regex_dict
        ):
            append_record = apply_blocklist(
                record,
                self.datagen_collection_blocklist_not_regex_dict,
                self.datagen_collection_blocklist_regex_dict,
            )
        if not append_record:
            return False

        score = state["score"]
        score_outliers = state["score_outliers"]
        disruption_queue_record = state["disruption_queue_record"]
        object_value = state["object_value"]
        key_value = state["key_value"]

        try:
            record["data_last_lag_seen"] = time.time() - float(
                record.get("data_last_time_seen", 0)
            )
        except Exception:
            record["data_last_lag_seen"] = 0

        try:
            isOutlier = int(record.get("isOutlier", 0))
        except Exception:
            isOutlier = 0
        try:
            OutliersDisabled = int(record.get("OutliersDisabled", 0))
        except Exception:
            OutliersDisabled = 0

        future_tolerance = record.get("future_tolerance", 0)
        try:
            future_tolerance = float(future_tolerance)
        except Exception:
            future_tolerance = 0

        data_last_ingestion_lag_seen = record.get("data_last_ingestion_lag_seen", 0)
        if data_last_ingestion_lag_seen == "":
            data_last_ingestion_lag_seen = 0
        try:
            data_last_ingestion_lag_seen = float(data_last_ingestion_lag_seen)
        except Exception:
            data_last_ingestion_lag_seen = 0
        data_last_lag_seen = record.get("data_last_lag_seen", 0)

        data_max_lag_allowed = float(record.get("data_max_lag_allowed", 0))
        data_max_delay_allowed = float(record.get("data_max_delay_allowed", 0))

        # Threshold intent lock — when the operator has pinned the delay / lag
        # threshold, the decision maker must NOT override it with a lagging-class
        # or variable-delay resolved value (same as DSM). The locked value stays
        # in data_max_{delay,lag}_allowed so the status evaluation uses the pin.
        delay_locked = (
            str(record.get("data_max_delay_allowed_locked", "false")).strip().lower()
            == "true"
        )
        lag_locked = (
            str(record.get("data_max_lag_allowed_locked", "false")).strip().lower()
            == "true"
        )

        # Lagging class resolution (same as DSM)
        lc_matched = False
        lc_delay_mode = None
        lc_resolved_delay = None
        lc_active_slot = None
        if self.lagging_classes_records:
            (
                lc_matched,
                lc_override_lag,
                lc_override_delay,
                lc_delay_mode,
                lc_resolved_delay,
                lc_active_slot,
                lc_match_info,
            ) = resolve_lagging_class_threshold(record, self.lagging_classes_records)
            if lc_matched:
                if lc_override_lag is not None and not lag_locked:
                    data_max_lag_allowed = lc_override_lag
                    record["data_max_lag_allowed"] = lc_override_lag
                if (
                    lc_delay_mode == "static"
                    and lc_override_delay is not None
                    and not delay_locked
                ):
                    data_max_delay_allowed = lc_override_delay
                    record["data_max_delay_allowed"] = lc_override_delay
                record["lagging_class_matched"] = "true"
                record["lagging_class_name"] = str(lc_match_info.get("name", ""))
                record["lagging_class_level"] = str(lc_match_info.get("level", ""))
                record["lagging_class_match_mode"] = str(lc_match_info.get("match_mode", ""))
                record["lagging_class_delay_mode"] = str(lc_delay_mode) if lc_delay_mode else ""
                record["lagging_class_key"] = str(lc_match_info.get("_key", ""))
        if not lc_matched:
            record["lagging_class_matched"] = "false"
            record["lagging_class_name"] = ""
            record["lagging_class_level"] = ""
            record["lagging_class_match_mode"] = ""
            record["lagging_class_delay_mode"] = ""
            record["lagging_class_key"] = ""

        monitoring_time_policy = record.get("monitoring_time_policy", None)
        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
            monitoring_time_policy = self.default_monitoring_time_policy
            record["monitoring_time_policy"] = self.default_monitoring_time_policy
        monitoring_time_rules = record.get("monitoring_time_rules", None)

        object_group_key = record.get("object_group_key", "")
        object_logical_group_dict = self.logical_coll_dict.get(object_group_key, {})

        data_last_ingest = record.get("data_last_ingest", 0)
        try:
            data_last_ingest = float(data_last_ingest)
        except Exception:
            pass
        data_last_time_seen = record.get("data_last_time_seen", 0)
        if data_last_time_seen == "":
            data_last_time_seen = 0
        try:
            data_last_time_seen = float(data_last_time_seen)
        except Exception:
            data_last_time_seen = 0

        (
            isUnderMonitoring,
            monitoring_anomaly_reason,
            isUnderMonitoringMsg,
        ) = get_monitoring_time_status(monitoring_time_policy, monitoring_time_rules)

        isOutlier = get_outliers_status(
            isOutlier,
            OutliersDisabled,
            self.tenant_outliers_set_state,
            score_outliers=score_outliers,
        )

        (
            isFuture,
            isFutureMsg,
            merged_future_tolerance,
        ) = get_future_status(
            future_tolerance,
            self.system_future_tolerance,
            data_last_lag_seen,
            data_last_ingestion_lag_seen,
            data_last_time_seen,
            data_last_ingest,
        )

        (
            isUnderLatencyAlert,
            isUnderLatencyMessage,
        ) = get_dsm_latency_status(
            data_last_ingestion_lag_seen,
            data_max_lag_allowed,
            data_last_ingest,
            data_last_time_seen,
        )

        if lc_matched and lc_delay_mode == "variable":
            resolved_threshold = lc_resolved_delay
            active_slot_name = lc_active_slot
            is_variable = True
        elif lc_matched and lc_delay_mode == "static":
            resolved_threshold = None
            active_slot_name = None
            is_variable = False
        else:
            variable_delay_record = self.variable_delay_collection_dict.get(key_value, None)
            (
                resolved_threshold,
                active_slot_name,
                is_variable,
            ) = resolve_variable_delay_threshold(record, variable_delay_record)

        # Threshold intent lock — a pinned delay threshold must GOVERN the
        # decision/alert path and IGNORE lagging classes. But a locked
        # VARIABLE-policy entity must keep evaluating against its OWN slots
        # (time-aware) — it must NOT collapse to a flat static value. So re-resolve
        # from the entity's own variable-delay record: a variable-policy entity
        # keeps its slots, a static-policy entity resolves to is_variable=False and
        # uses the pinned data_max_delay_allowed. (This deliberately bypasses any
        # matched lagging class above — the lock means the operator's own config
        # wins.) For variable entities reconcile restores slot drift; it does NOT
        # touch data_max_delay_allowed, which legitimately tracks the active slot.
        if delay_locked:
            variable_delay_record = self.variable_delay_collection_dict.get(key_value, None)
            (
                resolved_threshold,
                active_slot_name,
                is_variable,
            ) = resolve_variable_delay_threshold(record, variable_delay_record)

        if is_variable:
            record["variable_delay_active_slot"] = (
                str(active_slot_name) if active_slot_name else ""
            )
            record["variable_delay_active_threshold"] = str(int(round(resolved_threshold, 0)))
            record["data_max_delay_allowed"] = resolved_threshold
        else:
            record["variable_delay_active_slot"] = ""
            record["variable_delay_active_threshold"] = ""

        (
            isUnderDelayAlert,
            isUnderDelayMessage,
        ) = get_dsm_delay_status(
            data_last_lag_seen,
            data_max_delay_allowed,
            data_last_ingest,
            data_last_time_seen,
            resolved_max_delay_allowed=resolved_threshold if is_variable else None,
            variable_delay_slot_name=active_slot_name if is_variable else None,
        )

        (
            object_state,
            status_message,
            status_message_json,
            anomaly_reason,
            splk_dhm_alerting_policy,
        ) = set_dhm_status(
            self.logger,
            self.splunkd_uri,
            self.system_authtoken,
            self.tenant_id,
            record,
            isOutlier,
            isFuture,
            isFutureMsg,
            isUnderMonitoring,
            isUnderMonitoringMsg,
            object_logical_group_dict,
            isUnderLatencyAlert,
            isUnderLatencyMessage,
            isUnderDelayAlert,
            isUnderDelayMessage,
            self.default_splk_dhm_alerting_policy,
            self.disruption_queue_collection,
            disruption_queue_record,
            source_handler="rest_handler",
            monitoring_anomaly_reason=monitoring_anomaly_reason,
            score=score,
            score_outliers=score_outliers,
            vtenant_account=self.vtenant_conf,
            delay_is_variable=is_variable,
        )

        record["object_state"] = object_state
        record["status_message"] = " | ".join(status_message)
        record["status_message_json"] = status_message_json
        record["anomaly_reason"] = "|".join(anomaly_reason)

        try:
            record["future_tolerance"] = int(round(merged_future_tolerance, 0))
        except Exception:
            record["future_tolerance"] = -600

        record["splk_dhm_alerting_policy"] = splk_dhm_alerting_policy

        record["last_time"] = convert_epoch_to_datetime(data_last_time_seen)
        record["last_ingest"] = convert_epoch_to_datetime(data_last_ingest)
        record["last_time_idx"] = convert_epoch_to_datetime(data_last_time_seen)

        latest_flip_time_human = record.get("latest_flip_time", 0)
        try:
            latest_flip_time_human = float(latest_flip_time_human)
        except Exception:
            latest_flip_time_human = 0
        record["latest_flip_time_human"] = convert_epoch_to_datetime(latest_flip_time_human)

        record["lag_summary"] = set_feeds_lag_summary(record, self.component)

        (
            data_max_delay_allowed_duration,
            data_max_lag_allowed_duration,
        ) = set_feeds_thresholds_duration(record)
        record["data_max_delay_allowed_duration"] = data_max_delay_allowed_duration
        record["data_max_lag_allowed_duration"] = data_max_lag_allowed_duration

        # Note: the REST handler also computes sourcetype_summary views from
        # splk_dhm_st_summary here. That helper lives in the REST handler module
        # and is UI-presentation-only; it does not influence object_state and is
        # intentionally omitted from the engine to keep this module independent.

        docs_ref_lookup(
            self.docs_is_global,
            self.docs_note_global,
            self.docs_link_global,
            object_value,
            self.docs_collection_members_list,
            self.docs_collection_members_dict,
            record,
        )

        get_sla_timer(record, self.sla_classes, self.sla_default_class)
        return True

    def _evaluate_mhm(self, record, state, append_record):
        if (
            self.datagen_collection_blocklist_not_regex_dict
            or self.datagen_collection_blocklist_regex_dict
        ):
            append_record = apply_blocklist(
                record,
                self.datagen_collection_blocklist_not_regex_dict,
                self.datagen_collection_blocklist_regex_dict,
            )
        if not append_record:
            return False

        score = state["score"]
        score_outliers = state["score_outliers"]
        disruption_queue_record = state["disruption_queue_record"]
        object_value = state["object_value"]

        try:
            record["last_lag_seen"] = time.time() - float(
                record.get("metric_last_time_seen", 0)
            )
        except Exception:
            record["last_lag_seen"] = 0

        metric_details = record.get("metric_details", None)

        # MHM has metric_details_minimal/compact/full views; the engine returns
        # the minimal view to match the REST handler default and keeps `metric_details_full`
        # available for UI expansion paths.
        record["metric_details"] = record.get("metric_details_minimal", "{}")
        record.pop("metric_details_minimal", None)
        record.pop("metric_details_compact", None)

        object_group_key = record.get("object_group_key", "")
        object_logical_group_dict = self.logical_coll_dict.get(object_group_key, {})

        metric_last_time_seen = record.get("metric_last_time_seen", 0)
        try:
            metric_last_time_seen = float(metric_last_time_seen)
        except Exception:
            pass

        isFuture, isFutureMsg = get_future_metrics_status(
            self.system_future_tolerance, metric_last_time_seen
        )

        monitoring_time_policy = record.get("monitoring_time_policy", None)
        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
            monitoring_time_policy = self.default_monitoring_time_policy
            record["monitoring_time_policy"] = self.default_monitoring_time_policy
        monitoring_time_rules = record.get("monitoring_time_rules", None)

        (
            isUnderMonitoring,
            monitoring_anomaly_reason,
            isUnderMonitoringMsg,
        ) = get_monitoring_time_status(monitoring_time_policy, monitoring_time_rules)

        (
            object_state,
            status_message,
            status_message_json,
            anomaly_reason,
        ) = set_mhm_status(
            self.logger,
            self.splunkd_uri,
            self.system_authtoken,
            self.tenant_id,
            record,
            metric_details,
            isFuture,
            isFutureMsg,
            isUnderMonitoring,
            isUnderMonitoringMsg,
            object_logical_group_dict,
            self.disruption_queue_collection,
            disruption_queue_record,
            source_handler="rest_handler",
            monitoring_anomaly_reason=monitoring_anomaly_reason,
            score=score,
            score_outliers=score_outliers,
            vtenant_account=self.vtenant_conf,
        )

        record["object_state"] = object_state
        record["status_message"] = " | ".join(status_message)
        record["status_message_json"] = status_message_json
        record["anomaly_reason"] = "|".join(anomaly_reason)

        record["last_time"] = convert_epoch_to_datetime(metric_last_time_seen)

        latest_flip_time_human = record.get("latest_flip_time", 0)
        try:
            latest_flip_time_human = float(latest_flip_time_human)
        except Exception:
            latest_flip_time_human = 0
        record["latest_flip_time_human"] = convert_epoch_to_datetime(latest_flip_time_human)

        record["lag_summary"] = set_feeds_lag_summary(record, self.component)

        docs_ref_lookup(
            self.docs_is_global,
            self.docs_note_global,
            self.docs_link_global,
            object_value,
            self.docs_collection_members_list,
            self.docs_collection_members_dict,
            record,
        )

        get_sla_timer(record, self.sla_classes, self.sla_default_class)
        return True

    def _evaluate_flx(self, record, state, append_record):
        if (
            self.datagen_collection_blocklist_not_regex_dict
            or self.datagen_collection_blocklist_regex_dict
        ):
            append_record = apply_blocklist(
                record,
                self.datagen_collection_blocklist_not_regex_dict,
                self.datagen_collection_blocklist_regex_dict,
            )
        if not append_record:
            return False

        score = state["score"]
        score_outliers = state["score_outliers"]
        disruption_queue_record = state["disruption_queue_record"]
        object_value = state["object_value"]
        key_value = state["key_value"]

        try:
            isOutlier = int(record.get("isOutlier", 0))
        except Exception:
            isOutlier = 0
        try:
            OutliersDisabled = int(record.get("OutliersDisabled", 0))
        except Exception:
            OutliersDisabled = 0

        monitoring_time_policy = record.get("monitoring_time_policy", None)
        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
            monitoring_time_policy = self.default_monitoring_time_policy
            record["monitoring_time_policy"] = self.default_monitoring_time_policy
        monitoring_time_rules = record.get("monitoring_time_rules", None)

        object_group_key = record.get("object_group_key", "")
        object_logical_group_dict = self.logical_coll_dict.get(object_group_key, {})

        (
            isUnderMonitoring,
            monitoring_anomaly_reason,
            isUnderMonitoringMsg,
        ) = get_monitoring_time_status(monitoring_time_policy, monitoring_time_rules)

        isOutlier = get_outliers_status(
            isOutlier,
            OutliersDisabled,
            self.tenant_outliers_set_state,
            score_outliers=score_outliers,
        )

        # Tracker-keyed metrics aggregation (same logic as REST handler)
        self._aggregate_flx_metrics(record, object_value)

        flx_thresholds_lookup(
            object_value,
            key_value,
            record,
            self.thresholds_collection_dict,
        )

        (
            threshold_alert,
            threshold_messages,
            threshold_scores,
        ) = flx_check_dynamic_thresholds(
            self.logger,
            record.get("dynamic_thresholds", {}),
            record.get("metrics", {}),
        )

        try:
            flx_drilldown_searches_lookup(
                self.tenant_id,
                record.get("tracker_name", ""),
                record.get("account", "local"),
                record,
                self.drilldown_searches_collection_dict,
            )
        except Exception as exc:
            self.logger.error(
                f'instance_id={self.instance_id}, Error in flx_drilldown_searches_lookup: {exc}'
            )

        try:
            flx_default_metrics_lookup(
                self.tenant_id,
                record.get("tracker_name", ""),
                record,
                self.default_metrics_collection_dict,
            )
        except Exception as exc:
            self.logger.error(
                f'instance_id={self.instance_id}, Error in flx_default_metrics_lookup: {exc}'
            )

        # Tracker-keyed string aggregations (status_description, status_description_short,
        # tracker_name, object_description) — kept for fidelity with the REST handler.
        self._aggregate_flx_tracker_keyed_strings(record, object_value)

        (
            object_state,
            status_message,
            status_message_json,
            anomaly_reason,
        ) = set_flx_status(
            self.logger,
            self.splunkd_uri,
            self.system_authtoken,
            self.tenant_id,
            record,
            isOutlier,
            isUnderMonitoring,
            isUnderMonitoringMsg,
            object_logical_group_dict,
            threshold_alert,
            threshold_messages,
            self.disruption_queue_collection,
            disruption_queue_record,
            source_handler="rest_handler",
            monitoring_anomaly_reason=monitoring_anomaly_reason,
            score=score,
            score_outliers=score_outliers,
            threshold_scores=threshold_scores,
            vtenant_account=self.vtenant_conf,
        )

        record["object_state"] = object_state
        record["status_message"] = " | ".join(status_message)
        record["status_message_json"] = status_message_json
        record["anomaly_reason"] = "|".join(anomaly_reason)

        latest_flip_time_human = record.get("latest_flip_time", 0)
        try:
            latest_flip_time_human = float(latest_flip_time_human)
        except Exception:
            latest_flip_time_human = 0
        record["latest_flip_time_human"] = convert_epoch_to_datetime(latest_flip_time_human)

        docs_ref_lookup(
            self.docs_is_global,
            self.docs_note_global,
            self.docs_link_global,
            object_value,
            self.docs_collection_members_list,
            self.docs_collection_members_dict,
            record,
        )

        get_sla_timer(record, self.sla_classes, self.sla_default_class)
        return True

    def _aggregate_flx_metrics(self, record, object_value):
        if "metrics" not in record:
            return
        try:
            metrics_value = record.get("metrics")
            if not metrics_value:
                return

            metrics_by_tracker = None
            if isinstance(metrics_value, str):
                try:
                    metrics_by_tracker = json.loads(metrics_value)
                except (json.JSONDecodeError, TypeError):
                    return
            elif isinstance(metrics_value, dict):
                metrics_by_tracker = metrics_value

            if not (metrics_by_tracker and isinstance(metrics_by_tracker, dict)):
                return

            aggregated_metrics = {}
            is_tracker_keyed = False
            for _key, value in metrics_by_tracker.items():
                if isinstance(value, dict):
                    # Tracker-keyed format: each value is a per-tracker
                    # metrics dict. Merge them all.
                    # (Mirrors trackme_rest_handler_component_user.py — the
                    # original code branched on whether the inner dict was
                    # flat or nested, but both branches produced the same
                    # result, so the conditional is collapsed here.)
                    aggregated_metrics.update(value)
                    is_tracker_keyed = True
                else:
                    break

            if is_tracker_keyed:
                if "status" in aggregated_metrics:
                    del aggregated_metrics["status"]
                record["metrics"] = aggregated_metrics
            else:
                # Old format (already flat); strip internal status field.
                if isinstance(metrics_value, str):
                    try:
                        old_metrics = json.loads(metrics_value)
                        if isinstance(old_metrics, dict):
                            if "status" in old_metrics:
                                old_metrics = old_metrics.copy()
                                del old_metrics["status"]
                            record["metrics"] = old_metrics
                        else:
                            record["metrics"] = {}
                    except Exception:
                        record["metrics"] = {}
                elif isinstance(metrics_by_tracker, dict):
                    if "status" in metrics_by_tracker:
                        metrics_by_tracker = metrics_by_tracker.copy()
                        del metrics_by_tracker["status"]
                    record["metrics"] = metrics_by_tracker
                else:
                    record["metrics"] = {}
        except Exception as exc:
            self.logger.error(
                f'instance_id={self.instance_id}, failed to aggregate metrics for '
                f'object="{object_value}", exception="{exc}"'
            )

    def _aggregate_flx_tracker_keyed_strings(self, record, object_value):
        # Determine number of trackers (controls "tracker: " prefixing)
        num_trackers = 1
        if "tracker_name" in record:
            try:
                tracker_name_value = record.get("tracker_name")
                if tracker_name_value:
                    if isinstance(tracker_name_value, str):
                        try:
                            tracker_names = json.loads(tracker_name_value)
                            if isinstance(tracker_names, list):
                                num_trackers = len(tracker_names)
                        except (json.JSONDecodeError, TypeError):
                            if "," in tracker_name_value:
                                num_trackers = len(
                                    [t.strip() for t in tracker_name_value.split(",")]
                                )
                    elif isinstance(tracker_name_value, list):
                        num_trackers = len(tracker_name_value)
            except Exception:
                pass

        for field_name in ("status_description", "status_description_short", "object_description"):
            if field_name not in record:
                continue
            try:
                value = record.get(field_name)
                if not value:
                    continue
                by_tracker = None
                if isinstance(value, str):
                    try:
                        by_tracker = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        continue
                elif isinstance(value, dict):
                    by_tracker = value

                if by_tracker and isinstance(by_tracker, dict):
                    descs = []
                    is_tracker_keyed = False
                    for tracker_name, desc in by_tracker.items():
                        if isinstance(desc, str):
                            if desc:
                                if num_trackers > 1:
                                    descs.append(f"{tracker_name}: {desc}")
                                else:
                                    descs.append(desc)
                                is_tracker_keyed = True
                        else:
                            break
                    if is_tracker_keyed and descs:
                        record[field_name] = " | ".join(descs)
            except Exception as exc:
                self.logger.error(
                    f'instance_id={self.instance_id}, failed to aggregate {field_name} for '
                    f'object="{object_value}", exception="{exc}"'
                )

        # tracker_name display normalisation
        if "tracker_name" in record:
            try:
                tracker_name_value = record.get("tracker_name")
                if tracker_name_value:
                    if isinstance(tracker_name_value, str):
                        try:
                            tracker_names = json.loads(tracker_name_value)
                            if isinstance(tracker_names, list):
                                record["tracker_name"] = ", ".join(tracker_names)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    elif isinstance(tracker_name_value, list):
                        record["tracker_name"] = ", ".join(tracker_name_value)
            except Exception as exc:
                self.logger.error(
                    f'instance_id={self.instance_id}, failed to aggregate tracker_name for '
                    f'object="{object_value}", exception="{exc}"'
                )

    def _evaluate_fqm(self, record, state, append_record):
        if (
            self.datagen_collection_blocklist_not_regex_dict
            or self.datagen_collection_blocklist_regex_dict
        ):
            append_record = apply_blocklist(
                record,
                self.datagen_collection_blocklist_not_regex_dict,
                self.datagen_collection_blocklist_regex_dict,
            )
        if not append_record:
            return False

        score = state["score"]
        score_outliers = state["score_outliers"]
        disruption_queue_record = state["disruption_queue_record"]
        object_value = state["object_value"]
        key_value = state["key_value"]

        try:
            isOutlier = int(record.get("isOutlier", 0))
        except Exception:
            isOutlier = 0
        try:
            OutliersDisabled = int(record.get("OutliersDisabled", 0))
        except Exception:
            OutliersDisabled = 0

        monitoring_time_policy = record.get("monitoring_time_policy", None)
        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
            monitoring_time_policy = self.default_monitoring_time_policy
            record["monitoring_time_policy"] = self.default_monitoring_time_policy
        monitoring_time_rules = record.get("monitoring_time_rules", None)

        object_group_key = record.get("object_group_key", "")
        object_logical_group_dict = self.logical_coll_dict.get(object_group_key, {})

        (
            isUnderMonitoring,
            monitoring_anomaly_reason,
            isUnderMonitoringMsg,
        ) = get_monitoring_time_status(monitoring_time_policy, monitoring_time_rules)

        isOutlier = get_outliers_status(
            isOutlier,
            OutliersDisabled,
            self.tenant_outliers_set_state,
            score_outliers=score_outliers,
        )

        fqm_thresholds_lookup(
            object_value,
            key_value,
            record,
            self.thresholds_collection_dict,
        )

        (
            threshold_alert,
            threshold_messages,
            threshold_scores,
        ) = fqm_check_dynamic_thresholds(
            self.logger,
            record.get("dynamic_thresholds", {}),
            record.get("metrics", {}),
        )

        (
            object_state,
            status_message,
            status_message_json,
            anomaly_reason,
        ) = set_fqm_status(
            self.logger,
            self.splunkd_uri,
            self.system_authtoken,
            self.tenant_id,
            record,
            isOutlier,
            isUnderMonitoring,
            isUnderMonitoringMsg,
            object_logical_group_dict,
            threshold_alert,
            threshold_messages,
            self.disruption_queue_collection,
            disruption_queue_record,
            source_handler="rest_handler",
            monitoring_anomaly_reason=monitoring_anomaly_reason,
            score=score,
            score_outliers=score_outliers,
            threshold_scores=threshold_scores,
            vtenant_account=self.vtenant_conf,
        )

        record["object_state"] = object_state
        record["status_message"] = " | ".join(status_message)
        record["status_message_json"] = status_message_json
        record["anomaly_reason"] = "|".join(anomaly_reason)

        # Custom breakby fields (metadata.* → metadata_*) — fidelity with REST
        if "fields_quality_summary" in record:
            try:
                fields_quality_summary = json.loads(record["fields_quality_summary"])
                for field in fields_quality_summary:
                    if field.startswith("metadata.") and field not in (
                        "metadata.datamodel",
                        "metadata.nodename",
                        "metadata.index",
                        "metadata.sourcetype",
                    ):
                        newfield_name = field.replace("metadata.", "metadata_")
                        record[newfield_name] = fields_quality_summary[field]
            except Exception:
                pass

        latest_flip_time_human = record.get("latest_flip_time", 0)
        try:
            latest_flip_time_human = float(latest_flip_time_human)
        except Exception:
            latest_flip_time_human = 0
        record["latest_flip_time_human"] = convert_epoch_to_datetime(latest_flip_time_human)

        docs_ref_lookup(
            self.docs_is_global,
            self.docs_note_global,
            self.docs_link_global,
            object_value,
            self.docs_collection_members_list,
            self.docs_collection_members_dict,
            record,
        )

        get_sla_timer(record, self.sla_classes, self.sla_default_class)
        return True

    def _evaluate_wlk(self, record, state, append_record):
        if (
            self.datagen_collection_blocklist_not_regex_dict
            or self.datagen_collection_blocklist_regex_dict
        ):
            append_record = apply_blocklist(
                record,
                self.datagen_collection_blocklist_not_regex_dict,
                self.datagen_collection_blocklist_regex_dict,
            )
        if not append_record:
            return False

        score = state["score"]
        score_outliers = state["score_outliers"]
        disruption_queue_record = state["disruption_queue_record"]
        object_value = state["object_value"]
        key_value = state["key_value"]

        if "overgroup" not in record:
            record["overgroup"] = record.get("group")

        wlk_disabled_apps_lookup(
            record.get("app"),
            self.apps_enablement_collection_keys,
            self.apps_enablement_collection_dict,
            record,
        )
        wlk_versioning_lookup(
            key_value,
            self.versioning_collection_keys,
            self.versioning_collection_dict,
            record,
        )
        wlk_orphan_lookup(
            key_value,
            self.orphan_collection_keys,
            self.orphan_collection_dict,
            record,
        )

        if record.get("app_is_enabled") == "False":
            return False

        # Engine returns the minimal metrics view (matches REST handler default
        # mode_view="minimal"). Strip metrics_extended if present.
        if "metrics_extended" in record:
            del record["metrics_extended"]

        try:
            isOutlier = int(record.get("isOutlier", 0))
        except Exception:
            isOutlier = 0
        try:
            OutliersDisabled = int(record.get("OutliersDisabled", 0))
        except Exception:
            OutliersDisabled = 0

        monitoring_time_policy = record.get("monitoring_time_policy", None)
        if monitoring_time_policy is None or len(monitoring_time_policy) == 0:
            monitoring_time_policy = self.default_monitoring_time_policy
            record["monitoring_time_policy"] = self.default_monitoring_time_policy
        monitoring_time_rules = record.get("monitoring_time_rules", None)

        (
            isUnderMonitoring,
            monitoring_anomaly_reason,
            isUnderMonitoringMsg,
        ) = get_monitoring_time_status(monitoring_time_policy, monitoring_time_rules)

        isOutlier = get_outliers_status(
            isOutlier,
            OutliersDisabled,
            self.tenant_outliers_set_state,
            score_outliers=score_outliers,
        )

        wlk_thresholds_lookup(
            object_value,
            key_value,
            record,
            self.thresholds_collection_dict,
        )

        (
            object_state,
            status_message,
            status_message_json,
            anomaly_reason,
        ) = set_wlk_status(
            self.logger,
            self.splunkd_uri,
            self.system_authtoken,
            self.tenant_id,
            record,
            isOutlier,
            isUnderMonitoring,
            isUnderMonitoringMsg,
            self.disruption_queue_collection,
            disruption_queue_record,
            source_handler="rest_handler",
            monitoring_anomaly_reason=monitoring_anomaly_reason,
            score=score,
            score_outliers=score_outliers,
            vtenant_account=self.vtenant_conf,
            dynamic_thresholds=record.get("dynamic_thresholds", {}),
        )

        record["object_state"] = object_state
        record["status_message"] = " | ".join(status_message)
        record["status_message_json"] = status_message_json
        record["anomaly_reason"] = "|".join(anomaly_reason)

        latest_flip_time_human = record.get("latest_flip_time", 0)
        try:
            latest_flip_time_human = float(latest_flip_time_human)
        except Exception:
            latest_flip_time_human = 0
        record["latest_flip_time_human"] = convert_epoch_to_datetime(latest_flip_time_human)

        record["last_seen_human"] = convert_epoch_to_datetime(record.get("last_seen", 0))

        docs_ref_lookup(
            self.docs_is_global,
            self.docs_note_global,
            self.docs_link_global,
            object_value,
            self.docs_collection_members_list,
            self.docs_collection_members_dict,
            record,
        )

        get_sla_timer(record, self.sla_classes, self.sla_default_class)
        return True


# -------------------------------------------------------------- module-level API


def evaluate_records(
    session_key,
    splunkd_uri,
    tenant_id,
    component,
    records,
    *,
    system_authtoken=None,
    splunkd_port=None,
    logger=None,
):
    """One-shot helper for callers that don't need to amortize the engine's load
    cost across multiple invocations.

    Equivalent to::

        engine = DecisionMakerEngine(session_key, splunkd_uri, tenant_id, component, ...)
        engine.load()
        return engine.evaluate_records(records)
    """
    engine = DecisionMakerEngine(
        session_key,
        splunkd_uri,
        tenant_id,
        component,
        system_authtoken=system_authtoken,
        splunkd_port=splunkd_port,
        logger=logger,
    )
    engine.load()
    return engine.evaluate_records(records)


def evaluate_object_state(
    session_key,
    splunkd_uri,
    tenant_id,
    component,
    object_id,
    *,
    system_authtoken=None,
    splunkd_port=None,
    logger=None,
):
    """Convenience helper used by alert-action validation paths.

    Loads the engine, fetches the single KV record matching ``object_id``
    (``_key``), evaluates it, and returns ``(object_state, anomaly_reason,
    status_message)``.

    Returns ``(None, None, None)`` when:
      - the record cannot be found, or
      - the record was filtered out by the blocklist (``_dme_append`` is
        False — the entity is excluded from monitoring, so the engine has
        not recomputed its state and the stored value is stale).

    Callers should treat both cases identically as "no decision available"
    and apply their own fail-open semantics — matching the behaviour of
    the previous REST-loopback path, which returned an empty data array
    for blocklisted entities.
    """
    engine = DecisionMakerEngine(
        session_key,
        splunkd_uri,
        tenant_id,
        component,
        system_authtoken=system_authtoken,
        splunkd_port=splunkd_port,
        logger=logger,
    )
    engine.load()
    evaluated = engine.evaluate_object_full(object_id)
    if evaluated is None:
        return (None, None, None)
    return (
        evaluated.get("object_state"),
        evaluated.get("anomaly_reason"),
        evaluated.get("status_message"),
    )

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

# default remote account configuration settings
remote_account_default = {
    "app_namespace": "search",
    "rbac_roles": "admin,sc_admin,trackme_user,trackme_power,trackme_admin",
    "timeout_connect_check": "15",
    "timeout_search_check": "600",
    "token_rotation_enablement": "1",
    "token_rotation_frequency": "7",
    "retry_enabled": "1",
    "retry_max_total_time": "30",
    "retry_initial_delay": "2",
    "retry_backoff_multiplier": "2.0",
    "retry_max_attempts": "10",
}

# default vtenant account configuration settings
vtenant_account_default = {
    "alias": "",
    "description": "",
    "ui_default_timerange": "24h",
    "ui_min_object_width": 300,
    "data_sampling_obfuscation": 0,
    "ui_expand_metrics": 0,
    "ui_home_tabs_order": "dsm,flx,dhm,mhm,wlk,fqm,flip,audit,alerts",
    "adaptive_delay": 1,
    "adaptive_delay_notes": 1,
    "mloutliers": 1,
    "mloutliers_allowlist": "dsm,dhm,flx,wlk,fqm",
    # Default matches the migrated value applied by trackme_schema_upgrade_2322
    # so the UCC admin form (which falls back to this default when a key is
    # absent from the .conf) cannot regress migrated tenants by displaying or
    # saving a narrower scope. The wizard sends a narrower "critical,high"
    # value at creation time as a per-tenant override (same pattern as
    # `enableMlOutliers=false` for DHM/WLK/FQM).
    "mloutliers_priority_filter": "critical,high,medium,low",
    "mloutliers_filter_expression": "",
    "mloutliers_volume_kpi": "",
    "sampling": 1,
    "shadow_enabled": 0,
    "shadow_entity_threshold": 1000,
    "variable_delay_auto_review": 1,
    "delay_threshold_lock_enabled": 1,
    "dsm_default_delay_policy": "static",
    "dsm_default_delay_threshold_sec": 3600,
    "dsm_variable_delay_default_slots": "{}",
    "dsm_variable_delay_default": "3600",
    "dhm_default_delay_policy": "static",
    "dhm_default_delay_threshold_sec": 86400,
    "dhm_variable_delay_default_slots": "{}",
    "dhm_variable_delay_default": "86400",
    "indexed_constraint": "",
    "splk_feeds_auto_disablement_period": "90d",
    "splk_feeds_delayed_inspector_24hours_range_min_sec": "14400",
    "splk_feeds_delayed_inspector_7days_range_min_sec": "43200",
    "splk_feeds_delayed_inspector_until_disabled_range_min_sec": "172800",
    "splk_feeds_delayed_inspector_max_backoff_multiplier": "4",
    "cmdb_lookup": 1,
    "cmdb_account": "",
    "splk_dsm_cmdb_search": "",
    "splk_dhm_cmdb_search": "",
    "splk_mhm_cmdb_search": "",
    "splk_flx_cmdb_search": "",
    "splk_fqm_cmdb_search": "",
    "splk_wlk_cmdb_search": "",
    "default_priority": "medium",
    "monitoring_time_policy": "all_time",
    "pagination_mode": "local",
    "pagination_size": 10000,
    "splk_dsm_tabulator_groupby": "data_index",
    "splk_dhm_tabulator_groupby": "tenant_id",
    "splk_mhm_tabulator_groupby": "tenant_id",
    "splk_flx_tabulator_groupby": "group",
    "splk_fqm_tabulator_groupby": "metadata_datamodel,metadata_index,metadata_sourcetype",
    "splk_wlk_tabulator_groupby": "overgroup",
    "default_disruption_min_time_sec": 0,
    # Impact scoring defaults
    "impact_score_outliers_default": 36,
    "impact_score_dsm_data_sampling_anomaly": 36,
    "impact_score_dsm_delay_threshold_breach": 100,
    "impact_score_dsm_latency_threshold_breach": 48,
    "impact_score_dsm_min_hosts_dcount_breach": 100,
    "impact_score_dsm_future_tolerance_breach": 36,
    "impact_score_dhm_delay_threshold_breach": 100,
    "impact_score_dhm_latency_threshold_breach": 48,
    "impact_score_dhm_future_tolerance_breach": 36,
    "impact_score_mhm_metric_alert": 100,
    "impact_score_mhm_future_tolerance_breach": 36,
    "impact_score_flx_inactive": 100,
    "impact_score_flx_status_not_met": 100,
    "impact_score_fqm_status_not_met": 100,
    "impact_score_wlk_skipping_searches": 100,
    "impact_score_wlk_execution_errors": 100,
    "impact_score_wlk_orphan_search": 100,
    "impact_score_wlk_execution_delayed": 100,
    "impact_score_wlk_status_not_met": 100,
    # Tenant-level global note and link (override system-wide defaults)
    "docs_note_global": "",
    "docs_link_global": "",
    # Optional comma-separated allowlist of Splunk usernames permitted to see
    # this tenant. Empty = no username restriction (RBAC roles still apply).
    # Bypasses: splunk-system-user (always) and the tenant_owner (always).
    "tenant_allowed_users": "",
    # AI ML Advisor (kept distinct from the component advisors — its tools
    # operate on ML model internals, not on entity configuration, so its
    # parameters tune a different concern).
    "ai_mladvisor_enabled": 0,
    "ai_mladvisor_mode": "act",
    "ai_mladvisor_provider_name": "",
    "ai_mladvisor_min_days_between_reviews": 30,
    "ai_mladvisor_max_runtime_sec": 14400,
    "ai_mladvisor_allow_model_disable": "0",
    # ──────────────────────────────────────────────────────────────────────
    # AI Components Advisor — unified configuration for the four
    # component-level advisors (Feed Lifecycle / FLX Threshold / FQM /
    # Component Health).  Each scheduled batch reads the same set of
    # parameters; per-component customisation is gated by
    # `ai_components_advisor_list`.
    #
    # Migrated from the previous per-advisor field families
    # (ai_feedlifecycle_*, ai_flxthreshold_*, ai_wlkadvisor_*,
    # ai_fqmadvisor_*, ai_mhmadvisor_*) — see schema migration in
    # trackme_libs_schema.py.
    # ──────────────────────────────────────────────────────────────────────
    # Comma-separated list of components eligible for automated batch
    # advisor runs.  Each helper checks both that its own component is in
    # this list AND that the component is enabled on the tenant before
    # selecting any entities.
    "ai_components_advisor_list": "dsm,dhm,mhm,flx,fqm,wlk",
    "ai_components_advisor_enabled": 0,
    "ai_components_advisor_mode": "act",
    "ai_components_advisor_provider_name": "",
    "ai_components_advisor_min_days_between_reviews": 30,
    "ai_components_advisor_max_runtime_sec": 14400,
    "ai_components_advisor_allow_decommission": "0",
    # ──────────────────────────────────────────────────────────────────────
    # Shared AUTOMATED-action filter — applied to BOTH the ML Advisor's
    # mladvisor batch AND every Components Advisor batch (Feed Lifecycle /
    # FLX Threshold / FQM / Component Health).  Replaces the per-section
    # ``ai_mladvisor_priority_filter`` and ``ai_components_advisor_priority_filter``
    # fields with a single authoritative pair.
    #
    # ``ai_automated_priority_filter`` is a CSV of priority levels eligible
    # for automated review.  Empty == match-all (treated as "no override").
    # Default ``critical,high`` keeps automated LLM spend bounded by
    # reviewing only high-stakes entities; analysts can still launch any
    # advisor interactively on anything regardless of this filter.
    #
    # ``ai_automated_filter_expression`` is a TrackMe filter DSL expression
    # (same syntax as Virtual Groups / ML Outliers scope) — `field=value`,
    # wildcards `*`/`?`, space = implicit AND, `OR` for alternatives,
    # parens for grouping, case-insensitive.  Available fields: `priority`,
    # `tags`, `labels`, `object`, `component`, plus any raw entity field
    # (`data_index` / `data_sourcetype` resolve on DSM/DHM entities only
    # — they are not surfaced in the UI quick-reference since this filter
    # applies across every component).  Empty == no expression.
    #
    # Interactive launches (AI Assistant consent card or direct REST
    # invocation) ignore both fields — this gates only the scheduled
    # batch helpers.
    # ──────────────────────────────────────────────────────────────────────
    "ai_automated_priority_filter": "critical,high",
    "ai_automated_filter_expression": "",
    # ──────────────────────────────────────────────────────────────────────
    # ``auto_labels_rules`` — rule-driven automatic label assignment.
    #
    # A JSON-encoded array of rule objects. Each rule auto-assigns one or
    # more tenant labels (from the ``kv_trackme_labels_tenant_<tid>``
    # catalog) to entities when a lifecycle trigger fires, optionally
    # narrowed by the shared priority + filter-DSL gating (same fields and
    # semantics as ``ai_automated_*`` above; available fields include
    # ``component`` so a tenant-wide rule can target a single component).
    #
    # One rule object:
    #   {
    #     "rule_id": "<stable id, assigned at save>",
    #     "enabled": true,
    #     "trigger": "discovered|enters_alert|recovers|custom_filter",
    #     "removal_mode": "manual|auto",   # manual=keep the label, never
    #                                      #   auto-remove it (additive);
    #                                      # auto=remove when the condition clears
    #     "label_ids": ["<catalog _key>", ...],   # resolved at save time
    #     "priority_filter": "critical,high",     # optional CSV gate, "" = all
    #     "filter_expression": "data_index=siem-*",  # optional DSL gate
    #     "description": ""
    #   }
    #
    # Evaluated only in the scheduled decision-maker batch path
    # (``trackmedecisionmaker``); writes are additive (``manual``) or
    # reconciled (``auto``) and never touch labels a rule did not assign.
    # Empty ``"[]"`` (default) == feature inert, zero added cost.
    # ──────────────────────────────────────────────────────────────────────
    "auto_labels_rules": "[]",
    # ──────────────────────────────────────────────────────────────────────
    # Tenant-level free-text Custom Instructions appended to every
    # automated AI Advisor system prompt (ML Advisor batch + every
    # Components Advisor batch). Concatenated AFTER the AI-provider-level
    # ``ai_custom_prompt`` at agent runtime — tenant-level wins
    # specificity. The Concierge advisor deliberately ignores this field
    # because it runs from the chat-driven path with its own context
    # plumbing, not the scheduled batches.
    #
    # Empty (default) = no extra instructions appended.
    # ──────────────────────────────────────────────────────────────────────
    "ai_automated_custom_instructions": "",
    # ──────────────────────────────────────────────────────────────────────
    # AI Concierge Advisor — generalist (catalog-driven) advisor for the
    # long tail of user requests that don't match a specialist. The agent
    # is read-only at the SDK level; mutation flows through the consent-
    # card click. Authorisation is splunkd RBAC at the REST boundary
    # (the user's effective roles must permit the proposed endpoint's
    # required capability) — there is no per-tenant enablement gate.
    # Destructive actions additionally require per-action typed
    # confirmation in the consent card; that's the UX safeguard, the
    # gate was redundant with RBAC.
    #
    # The previous ``ai_concierge_enabled`` and
    # ``ai_concierge_allow_destructive`` fields were removed in the
    # gate-removal refactor (they added nothing beyond what RBAC + the
    # typed-confirmation already enforce, and the enablement gate broke
    # the Virtual Tenants chat surface — no single ``tenant_id`` in
    # scope to gate against).
    #
    # Plan + outcome: ai-context/integrations/concierge-advisor-implementation-plan.md
    # Runtime:        ai-context/integrations/concierge-advisor.md
    # ──────────────────────────────────────────────────────────────────────
    # Cap on the number of actions the Concierge can propose in one
    # contract. The schema-level cap in
    # ``trackme_libs_ai_concierge_advisor.ConciergeProposalResult`` is
    # 200 (catches runaway proposals); this per-tenant operational
    # limit defaults to 10 — enough for any reasonable bulk action,
    # restrictive enough that an analyst confirms-and-fires 50 changes
    # only when they explicitly opt into the larger batch.
    "ai_concierge_max_actions_per_proposal": 10,
    # Rate-limit on contracts per minute per chat session. Above the
    # limit, the chat surfaces a polite "I've proposed several actions
    # in the last minute — confirm or reject those before I propose
    # more." Defaults to 5 — enough for a normal back-and-forth, low
    # enough that a pathological prompt doesn't fire 100 contracts.
    "ai_concierge_rate_limit_per_minute": 5,
}

# main and shared collections
collections_list_main = [
    "trackme_virtual_tenants",
    "trackme_virtual_tenants_entities_summary",
    "trackme_maintenance_mode",
    "trackme_maintenance_kdb",
    "trackme_backup_archives_info",
    "trackme_native_ml_models",
    "trackme_health_tracker_state",
]

# splk-flx allowed uc_ref listing
splk_flx_allowed_uc_ref = [
    "cribl_logstream_health_inputs",
    "cribl_logstream_health_outputs",
    "cribl_logstream_hosts_cpu_usage",
    "cribl_logstream_output_destination_pressure",
    "cribl_logstream_pack_traffic",
    "cribl_logstream_pipeline",
    "cribl_logstream_route_traffic",
    "cribl_logstream_total_traffic_inputs",
    "cribl_logstream_total_traffic_outputs",
    "cribl_edge_fleet_api",
    "cribl_edge_fleet_metrics",
    "splk_bucket_health_per_index",
    "splk_bundle_size",
    "splk_dbconnect",
    "splk_deployment_server_clients",
    "splk_detect_daily_variations_volume_global",
    "splk_detect_daily_variations_volume_index",
    "splk_detect_drop_events_count_absolute",
    "splk_detect_drop_events_count_rolling",
    "splk_dma",
    "splk_good_practices_alltime_scheduled",
    "splk_good_practices_detect_dynamic_sourcetype",
    "splk_good_practices_run_as_user_scheduled",
    "splk_hosts_tracking",
    "splk_kvstore_size",
    "splk_kvstore_status",
    "splk_large_lookup_files",
    "splk_lastchanceindex",
    "splk_license_pool_usage",
    "splk_license_usage_global_splunkcloud",
    "splk_license_usage_global_splunkenterprise",
    "splk_license_usage_per_index_splunkcloud",
    "splk_license_usage_per_index_splunkenterprise",
    "splk_parsing_issues_per_component",
    "splk_queues_filling",
    "splk_search_head_activity",
    "splk_search_head_healthmon_artifact_count_remote",
    "splk_soar_actions_adhocs_failures",
    "splk_soar_actions_playbooks_failures",
    "splk_soar_assets_health",
    "splk_soar_automation_brokers_manage",
    "splk_soar_automation_brokers_monitor",
    "splk_soar_forwarding_splunk",
    "splk_soar_infra_load",
    "splk_soar_infra_memory",
    "splk_soar_services_health",
    "splk_soar_concurrent_playbooks",
    "splk_splunk_cloud_storage_usage",
    "splk_splunk_cloud_svc_usage",
    "splk_splunk_cloud_svc_usage_by_app",
    "splk_splunk_cloud_svc_usage_by_consumer_service",
    "splk_splunk_enterprise_cluster_peers_status",
    "splk_splunk_enterprise_cluster_status",
    "splk_splunk_infra_cpu_used",
    "splk_splunk_infra_log_level_variations",
    "splk_splunk_infra_mem_used",
    "splk_splunk_shc_global_status",
    "splk_splunk_shc_members_status",
    "splk_volume_ingested_per_day",
    "splk_uf_clients_versions_tracking",
    "splk_splunk_fields_quality",
    "splk_splunk_hec_errors",
    "ta_nix_cpu_usage",
    "ta_nix_mem_usage",
    "ta_windows_cpu_usage",
    "ta_windows_mem_usage",
]

# dict of collections
collections_dict = dict(
    [
        (
            "trackme_dsm",
            "_key, ctime, mtime, search_mode, tenant_id, object_category, alias, data_index, data_last_lag_seen, data_last_ingestion_lag_seen, data_eventcount, data_last_lag_seen_idx, data_first_time_seen, data_last_time_seen, data_last_ingest, data_last_time_seen_idx, data_max_lag_allowed, data_max_delay_allowed, data_max_delay_allowed_locked, data_max_lag_allowed_locked, future_tolerance, monitored_state, object, data_sourcetype, monitoring_time_policy, monitoring_time_rules, data_monitoring_wdays, isUnderMonitoringDays, data_monitoring_hours_ranges, isUnderMonitoringHours, data_override_lagging_class, allow_adaptive_delay, variable_delay_policy, variable_delay_active_slot, variable_delay_active_threshold, impact_score_weights, object_state, tracker_runtime, tracker_health_runtime, object_previous_state, data_previous_tracker_runtime, dcount_host, min_dcount_host, min_dcount_field, min_dcount_threshold, avg_dcount_host_5m, latest_dcount_host_5m, perc95_dcount_host_5m, stdev_dcount_host_5m, global_dcount_host, isAnomaly, data_sample_lastrun, tags, tags_manual, latest_flip_state, latest_flip_time, priority, priority_updated, priority_external, priority_reason, sla_class, sla_notification_mtime, status_message, anomaly_reason, outliers_readiness, tenant_parent",
        ),
        (
            "trackme_dsm_elastic_shared",
            "_key, object, alias, search_constraint, search_mode, elastic_index, elastic_sourcetype, earliest, latest",
        ),
        (
            "trackme_dsm_elastic_dedicated",
            "_key, object, alias, search_constraint, search_mode, elastic_index, elastic_sourcetype, elastic_wrapper, elastic_report",
        ),
        ("trackme_dsm_hybrid_trackers", "_key, tracker_name, knowledge_objects"),
        (
            "trackme_dsm_allowlist",
            "_key, object_category, object, is_rex, action, comment, mtime",
        ),
        (
            "trackme_dsm_data_sampling",
            "_key, object, raw_sample, events_count, min_time_btw_iterations_seconds, pct_min_major_inclusive_model_match, pct_max_exclusive_model_match, pct_max_exclusive_model_match, relative_time_window_seconds, data_sample_mtime, data_sample_last_entity_epoch_processed, data_sample_model_matched_summary, data_sample_feature, data_sample_iteration, data_sample_anomaly_reason, data_sample_status_colour, data_sample_anomaly_detected, data_sample_status_message, multiformat_detected, current_detected_format, current_detected_format_id, current_detected_format_dcount, current_detected_major_format, previous_detected_format, previous_detected_format_id, previous_detected_format_dcount, previous_detected_major_format",
        ),
        (
            "trackme_dsm_data_sampling_custom_models",
            "_key, model_id, model_name, model_regex, model_type, sourcetype_scope, mtime",
        ),
        ("trackme_dsm_knowledge", "_key, object, doc_link, doc_note"),
        (
            "trackme_dsm_outliers_entity_rules",
            "_key, object_category, object, mtime, is_disabled, entities_outliers, last_exec, confidence, confidence_reason, splk_outliers_min_days_history",
        ),
        (
            "trackme_dsm_outliers_entity_data",
            "_key, object_category, object, mtime, isOutlier, isOutlierReason, models_in_anomaly, models_summary, lastIsOutlierReason, lastIsOutlierReason_models, lastIsOutlierReason_mtime",
        ),
        (
            "trackme_dsm_tags",
            "_key, object, tags_auto, tags_auto_policies",
        ),
        (
            "trackme_dsm_tags_policies",
            "_key, tags_policy_id, tags_policy_type, tags_policy_value, tags_policy_regex, tags_policy_lookup_name, tags_policy_lookup_field_mappings, tags_policy_lookup_tags_field, tags_policy_lookup_tags_separator, tags_policy_lookup_match_mode, tags_policy_search_query, tags_policy_search_earliest, tags_policy_search_latest, mtime, account",
        ),
        (
            "trackme_dsm_priority",
            "_key, object, priority, priority_reason, mtime",
        ),
        (
            "trackme_dsm_priority_policies",
            "_key, priority_policy_id, priority_policy_type, priority_policy_value, priority_policy_regex, priority_policy_regex_match_field, priority_policy_lookup_name, priority_policy_lookup_field_mappings, priority_policy_lookup_priority_field, priority_policy_lookup_priority_mappings, priority_policy_lookup_match_mode, priority_policy_search_query, priority_policy_search_earliest, priority_policy_search_latest, mtime, account",
        ),
        (
            "trackme_dsm_sla",
            "_key, object, sla_class, sla_class_reason, mtime",
        ),
        (
            "trackme_dsm_sla_policies",
            "_key, sla_policy_id, sla_policy_type, sla_policy_value, sla_policy_regex, sla_policy_lookup_name, sla_policy_lookup_field_mappings, sla_policy_lookup_sla_field, sla_policy_lookup_sla_mappings, sla_policy_lookup_match_mode, sla_policy_search_query, sla_policy_search_earliest, sla_policy_search_latest, mtime, account",
        ),
        (
            "trackme_dsm_sla_notifications",
            "_key, mtime",
        ),
        (
            "trackme_dsm_delayed_entities_inspector",
            "_key, mtime, object, inspector_exec_counters, inspector_error_counters, inspector_last_error, inspector_last_status, inspector_consecutive_no_data_count, inspector_last_data_found, inspector_backoff_multiplier",
        ),
        (
            "trackme_dsm_variable_delay",
            "_key, object, object_category, tenant_id, variable_delay_enabled, variable_delay_mode, variable_delay_default, variable_delay_slots, variable_delay_last_auto_review, variable_delay_auto_review_enabled, variable_delay_auto_review_period, variable_delay_auto_review_method, variable_delay_ctime, variable_delay_mtime, variable_delay_updated_by",
        ),
        (
            "trackme_dsm_threshold_intent",
            "_key, object, object_category, tenant_id, component, requested_delay_allowed, requested_lag_allowed, locked, requested_by, requested_ctime, last_reconcile_time, last_reconcile_status, mtime",
        ),
        (
            "trackme_flx",
            "_key, ctime, mtime, tenant_id, group, subgroup, object, object_category, object_state, object_description, alias, monitored_state, account, tracker_name, tracker_runtime, status, status_description_short, status_description, upstream_status, upstream_status_description_short, upstream_status_description, metrics, outliers_metrics, extra_attributes, monitoring_time_policy, monitoring_time_rules, monitoring_wdays, isUnderMonitoringDays, monitoring_hours_ranges, isUnderMonitoringHours, tags, tags_manual, latest_flip_state, latest_flip_time, priority, priority_updated, priority_external, priority_reason, sla_class, sla_notification_mtime, status_message, anomaly_reason, outliers_readiness, tenant_parent, max_sec_inactive, flx_type",
        ),
        (
            "trackme_flx_hybrid_trackers",
            "_key, tracker_id, tracker_name, knowledge_objects, enable_zero_kpis_when_inactive",
        ),
        (
            "trackme_flx_outliers_entity_rules",
            "_key, object_category, object, mtime, is_disabled, entities_outliers, last_exec, confidence, confidence_reason, splk_outliers_min_days_history",
        ),
        (
            "trackme_flx_outliers_entity_data",
            "_key, object_category, object, mtime, isOutlier, isOutlierReason, models_in_anomaly, models_summary, lastIsOutlierReason, lastIsOutlierReason_models, lastIsOutlierReason_mtime",
        ),
        (
            "trackme_flx_tags",
            "_key, object, tags_auto, tags_auto_policies",
        ),
        (
            "trackme_flx_tags_policies",
            "_key, tags_policy_id, tags_policy_type, tags_policy_value, tags_policy_regex, tags_policy_lookup_name, tags_policy_lookup_field_mappings, tags_policy_lookup_tags_field, tags_policy_lookup_tags_separator, tags_policy_lookup_match_mode, tags_policy_search_query, tags_policy_search_earliest, tags_policy_search_latest, mtime, account",
        ),
        (
            "trackme_flx_priority",
            "_key, object, priority, priority_reason, mtime",
        ),
        (
            "trackme_flx_priority_policies",
            "_key, priority_policy_id, priority_policy_type, priority_policy_value, priority_policy_regex, priority_policy_regex_match_field, priority_policy_lookup_name, priority_policy_lookup_field_mappings, priority_policy_lookup_priority_field, priority_policy_lookup_priority_mappings, priority_policy_lookup_match_mode, priority_policy_search_query, priority_policy_search_earliest, priority_policy_search_latest, mtime, account",
        ),
        (
            "trackme_flx_sla",
            "_key, object, sla_class, sla_class_reason, mtime",
        ),
        (
            "trackme_flx_sla_policies",
            "_key, sla_policy_id, sla_policy_type, sla_policy_value, sla_policy_regex, sla_policy_lookup_name, sla_policy_lookup_field_mappings, sla_policy_lookup_sla_field, sla_policy_lookup_sla_mappings, sla_policy_lookup_match_mode, sla_policy_search_query, sla_policy_search_earliest, sla_policy_search_latest, mtime, account",
        ),
        (
            "trackme_flx_sla_notifications",
            "_key, mtime",
        ),
        (
            "trackme_flx_allowlist",
            "_key, object_category, object, is_rex, action, comment, mtime",
        ),
        (
            "trackme_flx_last_seen_activity",
            "_key, object, last_seen_metrics",
        ),
        (
            "trackme_flx_thresholds",
            "_key, object_id, metric_name, value, operator, condition_true, score, mtime, comment, variable_threshold_enabled, variable_threshold_default, variable_threshold_slots",
        ),
        (
            "trackme_fqm",
            "_key, ctime, mtime, tenant_id, metadata_datamodel, metadata_nodename, metadata_index, metadata_sourcetype, object, object_category, object_state, object_description, alias, fieldname, fields_quality_summary, monitored_state, account, tracker_name, tracker_runtime, tracker_name, tracker_index, status, status_description_short, status_description, metrics, outliers_metrics, monitoring_time_policy, monitoring_time_rules, monitoring_wdays, isUnderMonitoringDays, monitoring_hours_ranges, isUnderMonitoringHours, tags, tags_manual, latest_flip_state, latest_flip_time, priority, priority_updated, priority_external, priority_reason, sla_class, sla_notification_mtime, status_message, anomaly_reason, outliers_readiness, tenant_parent, max_sec_inactive, fqm_type, percent_success, percent_coverage",
        ),
        (
            "trackme_fqm_hybrid_trackers",
            "_key, tracker_id, tracker_name, knowledge_objects",
        ),
        (
            "trackme_fqm_outliers_entity_rules",
            "_key, object_category, object, mtime, is_disabled, entities_outliers, last_exec, confidence, confidence_reason, splk_outliers_min_days_history",
        ),
        (
            "trackme_fqm_outliers_entity_data",
            "_key, object_category, object, mtime, isOutlier, isOutlierReason, models_in_anomaly, models_summary, lastIsOutlierReason, lastIsOutlierReason_models, lastIsOutlierReason_mtime",
        ),
        (
            "trackme_fqm_tags",
            "_key, object, tags_auto, tags_auto_policies",
        ),
        (
            "trackme_fqm_tags_policies",
            "_key, tags_policy_id, tags_policy_type, tags_policy_value, tags_policy_regex, tags_policy_lookup_name, tags_policy_lookup_field_mappings, tags_policy_lookup_tags_field, tags_policy_lookup_tags_separator, tags_policy_lookup_match_mode, tags_policy_search_query, tags_policy_search_earliest, tags_policy_search_latest, mtime, account",
        ),
        (
            "trackme_fqm_priority",
            "_key, object, priority, priority_reason, mtime",
        ),
        (
            "trackme_fqm_priority_policies",
            "_key, priority_policy_id, priority_policy_type, priority_policy_value, priority_policy_regex, priority_policy_regex_match_field, priority_policy_lookup_name, priority_policy_lookup_field_mappings, priority_policy_lookup_priority_field, priority_policy_lookup_priority_mappings, priority_policy_lookup_match_mode, priority_policy_search_query, priority_policy_search_earliest, priority_policy_search_latest, mtime, account",
        ),
        (
            "trackme_fqm_sla",
            "_key, object, sla_class, sla_class_reason, mtime",
        ),
        (
            "trackme_fqm_sla_policies",
            "_key, sla_policy_id, sla_policy_type, sla_policy_value, sla_policy_regex, sla_policy_lookup_name, sla_policy_lookup_field_mappings, sla_policy_lookup_sla_field, sla_policy_lookup_sla_mappings, sla_policy_lookup_match_mode, sla_policy_search_query, sla_policy_search_earliest, sla_policy_search_latest, mtime, account",
        ),
        (
            "trackme_fqm_sla_notifications",
            "_key, mtime",
        ),
        (
            "trackme_fqm_allowlist",
            "_key, object_category, object, is_rex, action, comment, mtime",
        ),
        (
            "trackme_fqm_last_seen_activity",
            "_key, object, last_seen_metrics",
        ),
        (
            "trackme_fqm_thresholds",
            "_key, object_id, metric_name, value, operator, condition_true, score, mtime, comment",
        ),
        (
            "trackme_fqm_data_dictionary",
            "_key, mtime, name, label, json_dict",
        ),
        (
            "trackme_wlk",
            "_key, ctime, mtime, tenant_id, overgroup, group, app, user, savedsearch_name, object, object_category, object_state, object_description, alias, monitored_state, account, tracker_name, tracker_runtime, status, status_description, metrics, metrics_extended, outliers_metrics, monitoring_time_policy, monitoring_time_rules, monitoring_wdays, isUnderMonitoringDays, monitoring_hours_ranges, isUnderMonitoringHours, first_seen, last_seen, sec_since_lastexec, skipped_pct, skipped_pct_last_60m, skipped_pct_last_4h, skipped_pct_last_24h, count_errors, count_errors_last_60m, count_errors_last_4h, count_errors_last_24h, tags, tags_manual, latest_flip_state, latest_flip_time, priority, priority_updated, priority_external, priority_reason, sla_class, sla_notification_mtime, tags, status_message, anomaly_reason, outliers_readiness, tenant_parent",
        ),
        (
            "trackme_wlk_hybrid_trackers",
            "_key, tracker_id, tracker_name, knowledge_objects",
        ),
        (
            "trackme_wlk_outliers_entity_rules",
            "_key, object_category, object, mtime, is_disabled, entities_outliers, last_exec, confidence, confidence_reason, splk_outliers_min_days_history",
        ),
        (
            "trackme_wlk_outliers_entity_data",
            "_key, object_category, object, mtime, isOutlier, isOutlierReason, models_in_anomaly, models_summary, lastIsOutlierReason, lastIsOutlierReason_models, lastIsOutlierReason_mtime",
        ),
        (
            "trackme_wlk_versioning",
            "_key, mtime, object, version_dict, description, current_version_id, cron_exec_sequence_sec",
        ),
        ("trackme_wlk_orphan_status", "_key, mtime, object, user, app, orphan"),
        ("trackme_wlk_apps_enablement", "_key, mtime, app, enabled"),
        (
            "trackme_wlk_last_seen_activity",
            "_key, account, object, last_seen_scheduler, last_seen_introspection, last_seen_notable, last_seen_splunkcloud_svc",
        ),
        (
            "trackme_wlk_tags",
            "_key, object, tags_auto, tags_auto_policies",
        ),
        (
            "trackme_wlk_tags_policies",
            "_key, tags_policy_id, tags_policy_type, tags_policy_value, tags_policy_regex, tags_policy_lookup_name, tags_policy_lookup_field_mappings, tags_policy_lookup_tags_field, tags_policy_lookup_tags_separator, tags_policy_lookup_match_mode, tags_policy_search_query, tags_policy_search_earliest, tags_policy_search_latest, mtime, account",
        ),
        (
            "trackme_wlk_priority",
            "_key, object, priority, priority_reason, mtime",
        ),
        (
            "trackme_wlk_priority_policies",
            "_key, priority_policy_id, priority_policy_type, priority_policy_value, priority_policy_regex, priority_policy_regex_match_field, priority_policy_lookup_name, priority_policy_lookup_field_mappings, priority_policy_lookup_priority_field, priority_policy_lookup_priority_mappings, priority_policy_lookup_match_mode, priority_policy_search_query, priority_policy_search_earliest, priority_policy_search_latest, mtime, account",
        ),
        (
            "trackme_wlk_sla",
            "_key, object, sla_class, sla_class_reason, mtime",
        ),
        (
            "trackme_wlk_sla_policies",
            "_key, sla_policy_id, sla_policy_type, sla_policy_value, sla_policy_regex, sla_policy_lookup_name, sla_policy_lookup_field_mappings, sla_policy_lookup_sla_field, sla_policy_lookup_sla_mappings, sla_policy_lookup_match_mode, sla_policy_search_query, sla_policy_search_earliest, sla_policy_search_latest, mtime, account",
        ),
        (
            "trackme_wlk_sla_notifications",
            "_key, mtime",
        ),
        (
            "trackme_wlk_allowlist",
            "_key, object_category, object, is_rex, action, comment, mtime",
        ),
        (
            "trackme_wlk_thresholds",
            "_key, object_id, metric_name, value, operator, condition_true, score, mtime, comment",
        ),
        (
            "trackme_dhm",
            "_key, ctime, mtime, search_mode, tenant_id, object_category, object, alias, asset, data_index, data_sourcetype, data_last_lag_seen, data_last_ingestion_lag_seen, data_eventcount, data_first_time_seen, data_last_time_seen, data_last_ingest, data_max_lag_allowed, data_max_delay_allowed, data_max_delay_allowed_locked, data_max_lag_allowed_locked, future_tolerance, monitored_state, monitoring_time_policy, monitoring_time_rules, data_monitoring_wdays, isUnderMonitoringDays, data_monitoring_hours_ranges, isUnderMonitoringHours, data_override_lagging_class, allow_adaptive_delay, variable_delay_policy, variable_delay_active_slot, variable_delay_active_threshold, impact_score_weights, object_state, tracker_runtime, tracker_health_runtime, object_previous_state, data_previous_tracker_runtime, splk_dhm_st_summary, splk_dhm_alerting_policy, host_idx_blocklists, host_st_blocklists, tags, tags_manual, latest_flip_state, latest_flip_time, priority, priority_updated, priority_external, priority_reason, sla_class, sla_notification_mtime, status_message, anomaly_reason, outliers_readiness, tenant_parent",
        ),
        (
            "trackme_dhm_allowlist",
            "_key, object_category, object, is_rex, action, comment, mtime",
        ),
        (
            "trackme_dhm_outliers_entity_rules",
            "_key, object_category, object, mtime, is_disabled, entities_outliers, last_exec, confidence, confidence_reason, splk_outliers_min_days_history",
        ),
        (
            "trackme_dhm_outliers_entity_data",
            "_key, object_category, object, mtime, isOutlier, isOutlierReason, models_in_anomaly, models_summary, lastIsOutlierReason, lastIsOutlierReason_models, lastIsOutlierReason_mtime",
        ),
        (
            "trackme_dhm_tags",
            "_key, object, tags_auto, tags_auto_policies",
        ),
        (
            "trackme_dhm_tags_policies",
            "_key, tags_policy_id, tags_policy_type, tags_policy_value, tags_policy_regex, tags_policy_lookup_name, tags_policy_lookup_field_mappings, tags_policy_lookup_tags_field, tags_policy_lookup_tags_separator, tags_policy_lookup_match_mode, tags_policy_search_query, tags_policy_search_earliest, tags_policy_search_latest, mtime, account",
        ),
        (
            "trackme_dhm_priority",
            "_key, object, priority, priority_reason, mtime",
        ),
        (
            "trackme_dhm_priority_policies",
            "_key, priority_policy_id, priority_policy_type, priority_policy_value, priority_policy_regex, priority_policy_regex_match_field, priority_policy_lookup_name, priority_policy_lookup_field_mappings, priority_policy_lookup_priority_field, priority_policy_lookup_priority_mappings, priority_policy_lookup_match_mode, priority_policy_search_query, priority_policy_search_earliest, priority_policy_search_latest, mtime, account",
        ),
        (
            "trackme_dhm_sla",
            "_key, object, sla_class, sla_class_reason, mtime",
        ),
        (
            "trackme_dhm_sla_policies",
            "_key, sla_policy_id, sla_policy_type, sla_policy_value, sla_policy_regex, sla_policy_lookup_name, sla_policy_lookup_field_mappings, sla_policy_lookup_sla_field, sla_policy_lookup_sla_mappings, sla_policy_lookup_match_mode, sla_policy_search_query, sla_policy_search_earliest, sla_policy_search_latest, mtime, account",
        ),
        (
            "trackme_dhm_sla_notifications",
            "_key, mtime",
        ),
        ("trackme_dhm_hybrid_trackers", "_key, tracker_name, knowledge_objects"),
        (
            "trackme_dhm_delayed_entities_inspector",
            "_key, mtime, object, inspector_exec_counters, inspector_error_counters, inspector_last_error, inspector_last_status, inspector_consecutive_no_data_count, inspector_last_data_found, inspector_backoff_multiplier",
        ),
        (
            "trackme_dhm_variable_delay",
            "_key, object, object_category, tenant_id, variable_delay_enabled, variable_delay_mode, variable_delay_default, variable_delay_slots, variable_delay_last_auto_review, variable_delay_auto_review_enabled, variable_delay_auto_review_period, variable_delay_auto_review_method, variable_delay_ctime, variable_delay_mtime, variable_delay_updated_by",
        ),
        (
            "trackme_dhm_threshold_intent",
            "_key, object, object_category, tenant_id, component, requested_delay_allowed, requested_lag_allowed, locked, requested_by, requested_ctime, last_reconcile_time, last_reconcile_status, mtime",
        ),
        (
            "trackme_mhm",
            "_key, ctime, mtime, tenant_id, object_category, object, alias, metric_index, metric_category, metric_details, metric_details_full, metric_details_compact, metric_details_minimal, metric_last_lag_seen, metric_first_time_seen, metric_last_time_seen, metric_max_lag_allowed, monitored_state, metric_override_lagging_class, monitoring_time_policy, monitoring_time_rules, object_state, tracker_runtime, object_previous_state, metric_previous_tracker_runtime, tags, tags_manual, latest_flip_state, latest_flip_time, priority, priority_updated, priority_external, priority_reason, sla_class, sla_notification_mtime, status_message, anomaly_reason, outliers_readiness, tenant_parent",
        ),
        (
            "trackme_mhm_allowlist",
            "_key, object_category, object, is_rex, action, comment, mtime",
        ),
        (
            "trackme_common_lagging_classes",
            "_key, level, name, object, value_lag, value_delay, comment, mtime",
        ),
        (
            "trackme_dsm_lagging_classes",
            "_key, level, name, match_mode, value_delay, delay_mode, variable_delay_default, variable_delay_slots, value_lag, comment, ctime, mtime",
        ),
        (
            "trackme_dhm_lagging_classes",
            "_key, level, name, match_mode, value_delay, delay_mode, variable_delay_default, variable_delay_slots, value_lag, comment, ctime, mtime",
        ),
        (
            "trackme_stateful_alerting",
            "_key, object_id, object, object_category, object_state, incident_id, message_id, messages, reference_chain, delivery_type, alert_status, ctime, mtime, opened_anomaly_reason, updated_anomaly_reason",
        ),
        (
            "trackme_stateful_alerting_charts",
            "_key, object_id, object, object_category, incident_id, message_id, ctime, chart_id, chart_description, chart_svg_base64",
        ),
        (
            "trackme_mhm_lagging_classes",
            "_key, metric_category, metric_max_lag_allowed, comment, mtime",
        ),
        ("trackme_mhm_hybrid_trackers", "_key, tracker_name, knowledge_objects"),
        (
            "trackme_common_audit_changes",
            "_key, time, action, change_type, object, object_category, object_attrs, user, result, comment",
        ),
        (
            "trackme_mhm_tags",
            "_key, object, tags_auto, tags_auto_policies",
        ),
        (
            "trackme_mhm_tags_policies",
            "_key, tags_policy_id, tags_policy_type, tags_policy_value, tags_policy_regex, tags_policy_lookup_name, tags_policy_lookup_field_mappings, tags_policy_lookup_tags_field, tags_policy_lookup_tags_separator, tags_policy_lookup_match_mode, tags_policy_search_query, tags_policy_search_earliest, tags_policy_search_latest, mtime, account",
        ),
        (
            "trackme_mhm_priority",
            "_key, object, priority, priority_reason, mtime",
        ),
        (
            "trackme_mhm_priority_policies",
            "_key, priority_policy_id, priority_policy_type, priority_policy_value, priority_policy_regex, priority_policy_regex_match_field, priority_policy_lookup_name, priority_policy_lookup_field_mappings, priority_policy_lookup_priority_field, priority_policy_lookup_priority_mappings, priority_policy_lookup_match_mode, priority_policy_search_query, priority_policy_search_earliest, priority_policy_search_latest, mtime, account",
        ),
        (
            "trackme_mhm_sla",
            "_key, object, sla_class, sla_class_reason, mtime",
        ),
        (
            "trackme_mhm_sla_policies",
            "_key, sla_policy_id, sla_policy_type, sla_policy_value, sla_policy_regex, sla_policy_lookup_name, sla_policy_lookup_field_mappings, sla_policy_lookup_sla_field, sla_policy_lookup_sla_mappings, sla_policy_lookup_match_mode, sla_policy_search_query, sla_policy_search_earliest, sla_policy_search_latest, mtime, account",
        ),
        (
            "trackme_mhm_sla_notifications",
            "_key, mtime",
        ),
        (
            "trackme_common_alerts_ack",
            "_key, object, object_category, anomaly_reason, ack_source, ack_mtime, ack_expiration, ack_state, ack_type, ack_comment",
        ),
        (
            "trackme_common_logical_group",
            "_key, object_group_name, object_group_min_green_percent, object_group_members, object_group_members_green, object_group_members_red, object_group_mtime",
        ),
        (
            "trackme_common_permanently_deleted_objects",
            "_key, object, object_category, ctime",
        ),
        ("trackme_common_replica_trackers", "_key, tracker_name, knowledge_objects"),
        (
            "trackme_common_disruption_queue",
            "_key, is_system_default, disruption_min_time_sec, disruption_start_epoch, object_state, mtime",
        ),
        # Per-entity maintenance mode. One record per entity (``_key`` is the
        # entity's SHA256 object_id, same convention as the disruption queue).
        # While ``maintenance_start_epoch <= now < maintenance_end_epoch`` the
        # decision maker forces the entity to BLUE (protected). ``is_active`` is
        # always computed from ``now`` vs the epochs — never stored.
        (
            "trackme_common_entity_maintenance",
            "_key, object, object_category, component, maintenance_start_epoch, maintenance_end_epoch, maintenance_comment, src_user, ctime, mtime",
        ),
        # Per-tenant variable delay slot templates (quick templates presets)
        # shown in the DSM/DHM variable delay editors. If a tenant has no
        # records in this collection, the UI falls back to the hardcoded
        # factory defaults in splunkui/.../slotTemplates.ts — zero regression.
        # Admins manage these via /trackme/v2/splk_variable_delay/admin/templates/*.
        (
            "trackme_common_variable_delay_templates",
            "_key, template_id, label, description, component, slots, default_threshold, sort_order, ctime, mtime, author",
        ),
        (
            "trackme_notes",
            "_key, object_id, note, created_by, mtime",
        ),
        (
            "trackme_labels",
            "_key, label_name, label_color, label_description, label_order, is_default, created_by, ctime, mtime",
        ),
        (
            "trackme_label_assignments",
            "_key, object_id, component, label_ids, auto_applied, updated_by, ctime, mtime",
        ),
        (
            "trackme_flx_drilldown_searches",
            "_key, tracker_name, drilldown_search, drilldown_search_earliest, drilldown_search_latest",
        ),
        (
            "trackme_flx_default_metric",
            "_key, tracker_name, metric_name",
        ),
        (
            "trackme_native_ml_models",
            "_key, model_data, model_type, feature_name, dist_type, fitted_at, group_count, mtime",
        ),
        # Shadow copy collections — pre-computed enriched entity records for instant UI loading
        ("trackme_dsm_shadow", "_key, record, shadow_mtime"),
        ("trackme_dhm_shadow", "_key, record, shadow_mtime"),
        ("trackme_mhm_shadow", "_key, record, shadow_mtime"),
        ("trackme_flx_shadow", "_key, record, shadow_mtime"),
        ("trackme_fqm_shadow", "_key, record, shadow_mtime"),
        ("trackme_wlk_shadow", "_key, record, shadow_mtime"),
        # Score cache — immediate visibility for false positive and manual score changes
        (
            "trackme_common_score_cache",
            "_key, score_id, tenant_id, object_id, object, object_category, score_source, score, ctime",
        ),
    ]
)

# DSM
collections_list_dsm = [
    "trackme_dsm",
    "trackme_dsm_elastic_shared",
    "trackme_dsm_elastic_dedicated",
    "trackme_dsm_hybrid_trackers",
    "trackme_dsm_allowlist",
    "trackme_dsm_data_sampling",
    "trackme_dsm_data_sampling_custom_models",
    "trackme_dsm_knowledge",
    "trackme_dsm_outliers_entity_rules",
    "trackme_dsm_outliers_entity_data",
    "trackme_dsm_tags",
    "trackme_dsm_tags_policies",
    "trackme_dsm_priority",
    "trackme_dsm_priority_policies",
    "trackme_dsm_sla",
    "trackme_dsm_sla_policies",
    "trackme_dsm_sla_notifications",
    "trackme_dsm_delayed_entities_inspector",
    "trackme_dsm_variable_delay",
    "trackme_dsm_threshold_intent",
    "trackme_dsm_lagging_classes",
    "trackme_dsm_shadow",
]

persistent_fields_dsm = [
    "alias",
    "allow_adaptive_delay",
    "data_max_delay_allowed",
    # Trace fields stamped by post_ds_update_lag_policy when the update
    # originates from trackmesplkadaptivedelay. Listed here so the
    # trackmepersistentfields cycle preserves them across decision-maker
    # rewrites — without these entries the trace would be wiped within
    # one cycle and the UI banner would never appear.
    "data_max_delay_allowed_updated_by",
    "data_max_delay_allowed_mtime",
    "data_max_lag_allowed",
    # Threshold intent-lock flags. When "true" the operator has pinned the
    # delay / lag threshold; the background auto-writers (adaptive delay,
    # variable-delay review, static lagging-class override) skip the entity
    # and the reconcile task restores the requested value on drift. Listed
    # here so the trackmepersistentfields cycle preserves the lock across
    # decision-maker rewrites — same rationale as the trace fields above.
    "data_max_delay_allowed_locked",
    "data_max_lag_allowed_locked",
    "monitoring_time_policy",
    "monitoring_time_rules",
    "data_monitoring_hours_ranges",
    "data_monitoring_wdays",
    "data_override_lagging_class",
    "future_tolerance",
    "impact_score_weights",
    "min_dcount_field",
    "min_dcount_host",
    "monitored_state",
    "priority",
    "priority_updated",
    "priority_external",
    "priority_reason",
    "sla_class",
    "sla_class_reason",
    "sla_updated",
    "tags_manual",
    "variable_delay_policy",
]

# FLX
collections_list_flx = [
    "trackme_flx",
    "trackme_flx_hybrid_trackers",
    "trackme_flx_outliers_entity_rules",
    "trackme_flx_outliers_entity_data",
    "trackme_flx_tags",
    "trackme_flx_tags_policies",
    "trackme_flx_priority",
    "trackme_flx_priority_policies",
    "trackme_flx_sla",
    "trackme_flx_sla_policies",
    "trackme_flx_sla_notifications",
    "trackme_flx_allowlist",
    "trackme_flx_last_seen_activity",
    "trackme_flx_thresholds",
    "trackme_flx_drilldown_searches",
    "trackme_flx_default_metric",
    "trackme_flx_shadow",
]

persistent_fields_flx = [
    "alias",
    "monitoring_hours_ranges",
    "monitoring_time_policy",
    "monitoring_time_rules",
    "monitoring_wdays",
    "monitored_state",
    "priority",
    "priority_updated",
    "priority_external",
    "priority_reason",
    "sla_class",
    "sla_class_reason",
    "sla_updated",
    "tags_manual",
]

# FQM
collections_list_fqm = [
    "trackme_fqm",
    "trackme_fqm_hybrid_trackers",
    "trackme_fqm_outliers_entity_rules",
    "trackme_fqm_outliers_entity_data",
    "trackme_fqm_tags",
    "trackme_fqm_tags_policies",
    "trackme_fqm_priority",
    "trackme_fqm_priority_policies",
    "trackme_fqm_sla",
    "trackme_fqm_sla_policies",
    "trackme_fqm_sla_notifications",
    "trackme_fqm_allowlist",
    "trackme_fqm_last_seen_activity",
    "trackme_fqm_thresholds",
    "trackme_fqm_data_dictionary",
    "trackme_fqm_shadow",
]

persistent_fields_fqm = [
    "alias",
    "monitoring_hours_ranges",
    "monitoring_time_policy",
    "monitoring_time_rules",
    "monitoring_wdays",
    "monitored_state",
    "priority",
    "priority_updated",
    "priority_external",
    "priority_reason",
    "sla_class",
    "sla_class_reason",
    "sla_updated",
    "tags_manual",
]

# DHM
collections_list_dhm = [
    "trackme_dhm",
    "trackme_dhm_allowlist",
    "trackme_dhm_outliers_entity_rules",
    "trackme_dhm_outliers_entity_data",
    "trackme_dhm_hybrid_trackers",
    "trackme_dhm_tags",
    "trackme_dhm_tags_policies",
    "trackme_dhm_priority",
    "trackme_dhm_priority_policies",
    "trackme_dhm_sla",
    "trackme_dhm_sla_policies",
    "trackme_dhm_sla_notifications",
    "trackme_dhm_delayed_entities_inspector",
    "trackme_dhm_variable_delay",
    "trackme_dhm_threshold_intent",
    "trackme_dhm_lagging_classes",
    "trackme_dhm_shadow",
]

persistent_fields_dhm = [
    "alias",
    "allow_adaptive_delay",
    "data_max_delay_allowed",
    # Trace fields stamped by post_dh_update_lag_policy when the update
    # originates from trackmesplkadaptivedelay. Listed here so the
    # trackmepersistentfields cycle preserves them across decision-maker
    # rewrites — without these entries the trace would be wiped within
    # one cycle and the UI banner would never appear.
    "data_max_delay_allowed_updated_by",
    "data_max_delay_allowed_mtime",
    "data_max_lag_allowed",
    # Threshold intent-lock flags. When "true" the operator has pinned the
    # delay / lag threshold; the background auto-writers (adaptive delay,
    # variable-delay review, static lagging-class override) skip the entity
    # and the reconcile task restores the requested value on drift. Listed
    # here so the trackmepersistentfields cycle preserves the lock across
    # decision-maker rewrites — same rationale as the trace fields above.
    "data_max_delay_allowed_locked",
    "data_max_lag_allowed_locked",
    "monitoring_time_policy",
    "monitoring_time_rules",
    "data_monitoring_hours_ranges",
    "data_monitoring_wdays",
    "data_override_lagging_class",
    "future_tolerance",
    "impact_score_weights",
    "host_idx_blocklists",
    "host_st_blocklists",
    "monitored_state",
    "priority",
    "priority_updated",
    "priority_external",
    "priority_reason",
    "sla_class",
    "sla_class_reason",
    "sla_updated",
    "splk_dhm_alerting_policy",
    "tags_manual",
    "variable_delay_policy",
]

# MHM
collections_list_mhm = [
    "trackme_mhm",
    "trackme_mhm_allowlist",
    "trackme_mhm_lagging_classes",
    "trackme_mhm_hybrid_trackers",
    "trackme_mhm_tags",
    "trackme_mhm_tags_policies",
    "trackme_mhm_priority",
    "trackme_mhm_priority_policies",
    "trackme_mhm_sla",
    "trackme_mhm_sla_policies",
    "trackme_mhm_sla_notifications",
    "trackme_mhm_shadow",
]

persistent_fields_mhm = [
    "alias",
    "metric_details_compact",
    "metric_details_full",
    "metric_max_lag_allowed",
    "metric_override_lagging_class",
    "monitoring_time_policy",
    "monitoring_time_rules",
    "monitored_state",
    "priority",
    "priority_updated",
    "priority_external",
    "priority_reason",
    "sla_class",
    "sla_class_reason",
    "sla_updated",
    "tags_manual",
]

# WLK
collections_list_wlk = [
    "trackme_wlk",
    "trackme_wlk_hybrid_trackers",
    "trackme_wlk_outliers_entity_rules",
    "trackme_wlk_outliers_entity_data",
    "trackme_wlk_versioning",
    "trackme_wlk_orphan_status",
    "trackme_wlk_apps_enablement",
    "trackme_wlk_last_seen_activity",
    "trackme_wlk_tags",
    "trackme_wlk_tags_policies",
    "trackme_wlk_priority",
    "trackme_wlk_priority_policies",
    "trackme_wlk_sla",
    "trackme_wlk_sla_policies",
    "trackme_wlk_sla_notifications",
    "trackme_wlk_allowlist",
    "trackme_wlk_thresholds",
    "trackme_wlk_shadow",
]

persistent_fields_wlk = [
    "alias",
    "monitoring_hours_ranges",
    "monitoring_time_policy",
    "monitoring_time_rules",
    "monitoring_wdays",
    "monitored_state",
    "priority",
    "priority_updated",
    "priority_external",
    "priority_reason",
    "sla_class",
    "sla_class_reason",
    "sla_updated",
    "tags_manual",
]

# WLK default thresholds seeded for new tenants
# condition_true=False means "the condition being true is abnormal — alert when it IS met"
# e.g. count_errors > 0, condition_true=False → alert when errors exist (condition is met)
wlk_default_thresholds = [
    {
        "metric_name": "skipped_pct_last_4h",
        "value": 5,
        "operator": ">",
        "condition_true": False,
        "score": 50,
        "comment": "default threshold",
    },
    {
        "metric_name": "skipped_pct_last_24h",
        "value": 20,
        "operator": ">",
        "condition_true": False,
        "score": 100,
        "comment": "default threshold",
    },
    {
        "metric_name": "count_errors_last_24h",
        "value": 0,
        "operator": ">",
        "condition_true": False,
        "score": 25,
        "comment": "default threshold",
    },
    {
        "metric_name": "count_errors_last_4h",
        "value": 0,
        "operator": ">",
        "condition_true": False,
        "score": 50,
        "comment": "default threshold",
    },
    {
        "metric_name": "count_errors_last_60m",
        "value": 0,
        "operator": ">",
        "condition_true": False,
        "score": 100,
        "comment": "default threshold",
    },
]

# COMMON
collections_list_common = [
    "trackme_common_lagging_classes",
    "trackme_common_audit_changes",
    "trackme_common_alerts_ack",
    "trackme_common_logical_group",
    "trackme_common_permanently_deleted_objects",
    "trackme_common_replica_trackers",
    "trackme_common_disruption_queue",
    "trackme_common_entity_maintenance",
    "trackme_common_variable_delay_templates",
    "trackme_notes",
    "trackme_labels",
    "trackme_label_assignments",
    "trackme_stateful_alerting",
    "trackme_stateful_alerting_charts",
    "trackme_native_ml_models",
    "trackme_common_score_cache",
]

# Default labels seeded on tenant creation and schema migration
default_labels = [
    {"label_name": "blocked", "label_color": "#dc4e41", "label_description": "Entity is blocked, requires immediate attention", "label_order": "1"},
    {"label_name": "under-review", "label_color": "#ffb347", "label_description": "Entity is currently being investigated", "label_order": "2"},
    {"label_name": "in-progress", "label_color": "#5b9bd5", "label_description": "Remediation work is in progress", "label_order": "3"},
    {"label_name": "resolved", "label_color": "#45d4ba", "label_description": "Issue has been resolved", "label_order": "4"},
    {"label_name": "maintenance", "label_color": "#9e9e9e", "label_description": "Entity under planned maintenance", "label_order": "5"},
    {"label_name": "acknowledged", "label_color": "#9b59b6", "label_description": "Issue acknowledged, no immediate action needed", "label_order": "6"},
    {"label_name": "noise", "label_color": "#8d6e63", "label_description": "Known noisy source, low signal value", "label_order": "7"},
    {"label_name": "decommissioned", "label_color": "#607d8b", "label_description": "Entity is being decommissioned", "label_order": "8"},
]

def get_vtenant_mladvisor_field(vtenant_account, field_name, default=None):
    """Read an ML Advisor tenant setting (``ai_mladvisor_<field_name>``)."""
    return vtenant_account.get("ai_mladvisor_%s" % field_name, default)


def get_ml_model_mladvisor_disabled(model_record):
    """Return 1/0 for per-model automated-batch opt-out."""
    if not isinstance(model_record, dict):
        return 0
    try:
        return 1 if int(model_record.get("ai_mladvisor_disabled", 0)) == 1 else 0
    except (TypeError, ValueError):
        return 0

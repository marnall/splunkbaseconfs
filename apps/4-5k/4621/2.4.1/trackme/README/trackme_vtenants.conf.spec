[<name>]
alias = 
description = 
default_priority = 
pagination_mode = 
pagination_size = 
ui_default_timerange = 
ui_min_object_width = 
ui_expand_metrics = 
ui_home_tabs_order =
data_sampling_obfuscation = 
adaptive_delay =
adaptive_delay_notes =
mloutliers =
mloutliers_allowlist =
mloutliers_priority_filter =
mloutliers_filter_expression =
mloutliers_volume_kpi =
auto_labels_rules = <json string>
    * JSON-encoded array of automatic label assignment rules. Each rule
    * auto-assigns one or more tenant labels to entities when a lifecycle
    * trigger fires (discovered, enters_alert, recovers, custom_filter),
    * optionally gated by a priority CSV and a TrackMe filter DSL expression.
    * Evaluated only in the scheduled decision-maker batch path.
    * Default: []
sampling =
shadow_enabled =
shadow_entity_threshold =
splk_feeds_auto_disablement_period = 
splk_feeds_delayed_inspector_24hours_range_min_sec = 
splk_feeds_delayed_inspector_7days_range_min_sec = 
splk_feeds_delayed_inspector_until_disabled_range_min_sec = 
splk_feeds_delayed_inspector_max_backoff_multiplier =
indexed_constraint = 
cmdb_lookup = 
cmdb_account =
splk_dsm_cmdb_search =
splk_dhm_cmdb_search =
splk_mhm_cmdb_search =
splk_flx_cmdb_search =
splk_fqm_cmdb_search =
splk_wlk_cmdb_search =
docs_link_global =
docs_note_global =
tenant_allowed_users =
splk_dsm_tabulator_groupby = 
splk_dhm_tabulator_groupby = 
splk_mhm_tabulator_groupby = 
splk_flx_tabulator_groupby =
splk_fqm_tabulator_groupby =
splk_wlk_tabulator_groupby = 
default_disruption_min_time_sec =
monitoring_time_policy =
variable_delay_auto_review =
delay_threshold_lock_enabled =
data_sampling_set_state =
outliers_set_state =
dhm_default_delay_policy =
dhm_default_delay_threshold_sec =
dhm_variable_delay_default =
dhm_variable_delay_default_slots =
dsm_default_delay_policy =
dsm_default_delay_threshold_sec =
dsm_variable_delay_default =
dsm_variable_delay_default_slots =
impact_score_dhm_delay_threshold_breach =
impact_score_dhm_future_tolerance_breach =
impact_score_dhm_latency_threshold_breach =
impact_score_dsm_data_sampling_anomaly =
impact_score_dsm_delay_threshold_breach =
impact_score_dsm_future_tolerance_breach =
impact_score_dsm_latency_threshold_breach =
impact_score_dsm_min_hosts_dcount_breach =
impact_score_flx_inactive =
impact_score_flx_status_not_met =
impact_score_fqm_status_not_met =
impact_score_mhm_future_tolerance_breach =
impact_score_mhm_metric_alert =
impact_score_outliers_default =
impact_score_wlk_execution_delayed =
impact_score_wlk_execution_errors =
impact_score_wlk_orphan_search =
impact_score_wlk_out_of_monitoring_times =
impact_score_wlk_skipping_searches =
impact_score_wlk_status_not_met =
ai_mladvisor_enabled = <0|1>
    * Enable (1) or disable (0) the automated AI ML Advisor. Default: 0.

ai_mladvisor_mode = <act|inspect>
    * Mode for the automated AI ML Advisor. act applies changes; inspect is read-only. Default: act.

ai_mladvisor_provider_name = <string>
    * AI provider name. Empty = first configured provider. Default: "".

ai_mladvisor_min_days_between_reviews = <integer>
    * Minimum days between automated reviews per ML model. Use 0 for unlimited. Default: 30.

ai_mladvisor_max_runtime_sec = <integer>
    * Maximum total runtime (seconds) for a single scheduled run. Default: 14400.

ai_mladvisor_allow_model_disable = <0|1>
    * Allow automated act mode to fully disable an ML model. Default: 0.

ai_automated_priority_filter = <comma-separated list>
    * Shared priority filter applied to BOTH the ML Advisor batch and
    * every Components Advisor batch (Feed Lifecycle / FLX Threshold / FQM /
    * Component Health). Comma-separated list of priority values eligible for
    * automated review; empty = match-all. Entities whose `priority` is not in
    * this list are skipped at entity-selection time, keeping the nightly batch
    * cost bounded. Analysts can still launch any advisor interactively on any
    * entity regardless of this filter. Default: critical,high.

ai_automated_filter_expression = <string>
    * Optional TrackMe filter DSL expression scoping which entities are eligible
    * for any automated AI Advisor action. Same syntax as Virtual Groups / ML
    * Outliers scope: `field=value` with wildcards (`*`, `?`), `OR` for
    * alternatives, space for implicit AND, parens for grouping, case-insensitive.
    * Available fields: priority, tags, labels, object, component, plus any raw
    * entity field (data_index / data_sourcetype resolve on DSM/DHM entities
    * only — not surfaced in the UI quick-reference since this filter applies
    * across every component). Empty = no expression (only the Priority Filter
    * applies). Default: "".

ai_automated_custom_instructions = <string>
    * Optional free-text instructions appended to every automated AI Advisor
    * system prompt on this tenant (both the ML Advisor batch and every
    * Components Advisor batch). Concatenated AFTER any AI-provider-level
    * `ai_custom_prompt` at agent runtime — tenant-level wins specificity.
    * Interactive launches via the AI Assistant ignore this field. Default: "".

ai_components_advisor_list = <comma-separated list>
    * Comma-separated list of monitoring components eligible for the automated AI
    * components advisor (Feed Lifecycle for DSM/DHM, FLX Threshold for FLX, FQM
    * Advisor for FQM, Component Health for WLK/MHM). Each helper checks both that
    * its component appears here AND that the component is enabled on the tenant
    * before selecting any entities. Default: dsm,dhm,mhm,flx,fqm,wlk.

ai_components_advisor_enabled = <0|1>
    * Enable (1) or disable (0) the automated AI components advisor. Single switch
    * across the four component-level advisors. Default: 0.

ai_components_advisor_mode = <act|inspect>
    * Mode for automated component advisor reviews. act applies changes; inspect is
    * read-only. Default: act.

ai_components_advisor_provider_name = <string>
    * AI provider name for component advisor reviews. Empty = first configured
    * provider. Default: "".

ai_components_advisor_min_days_between_reviews = <integer>
    * Minimum days between automated component advisor reviews per entity. Use 0
    * for unlimited. Default: 30.

ai_components_advisor_max_runtime_sec = <integer>
    * Maximum total runtime (seconds) for a single scheduled component advisor run.
    * Default: 14400.

ai_components_advisor_allow_decommission = <0|1>
    * Allow automated component advisor act mode to disable entity monitoring
    * across all four component advisors. Default: 0.

ai_concierge_max_actions_per_proposal = <positive integer>
    * Cap on the number of actions the Concierge can propose in a single contract.
    * Larger batches require splitting into multiple proposals. Default: 10.

ai_concierge_rate_limit_per_minute = <positive integer>
    * Maximum Concierge contract proposals per minute per chat session. Above the
    * limit, the chat surfaces a polite "confirm or reject pending proposals
    * before I propose more". Default: 5.
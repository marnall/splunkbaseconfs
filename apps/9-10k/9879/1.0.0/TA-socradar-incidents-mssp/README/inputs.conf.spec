[socradar_incidents_mssp_collector://<name>]
socradar_api_key =
multi_tenant_id = Your SOCRadar Multi-Tenant ID. All entitled companies are collected through this single ID; every alarm carries its own company_id/company_name.
ioc_api_key = LEGACY (still honored as fallback). Prefer the global "IOC Enrichment API Key" under Configuration > Add-on Settings, set once for the whole add-on. When both exist, the global key wins.
severity_filter = Comma-separated severities to collect (CRITICAL,HIGH,MEDIUM,LOW,INFO). Empty = collect all severities.
status_filter = Comma-separated statuses to collect (OPEN,ON_HOLD,CLOSED). Empty = collect all statuses. Applies to NEW alarms only; status changes on already-collected alarms are always re-indexed.
tags = Comma-separated tags to INCLUDE (free-form, case-insensitive). Empty = no tag filter. Applies to NEW alarms only (client-side).
excluded_tags = Comma-separated tags to EXCLUDE (free-form, case-insensitive). Empty = no exclusion. Applies to NEW alarms only (client-side).
alarm_type_ids = Comma-separated numeric alarm type IDs to collect (server-side API filter). Empty = collect all alarm types.
alarm_main_types = Comma-separated alarm MAIN type names to collect, e.g. "Surface Web Monitoring,Brand Protection" (server-side API filter, case-insensitive). Empty = collect all main types.
alarm_sub_types = Comma-separated alarm SUB type names to collect, e.g. "Malware Analysis Service Monitoring" (server-side API filter). Empty = collect all sub types.
include_content = Whether to keep the alarm "content" section (leak records, dump data) in indexed events. 1 = include (new inputs created in the UI start checked = 1). 0 = drop the section from every alarm before indexing so events stay small. When the key is absent (inputs created before this option existed), content is still included so upgrades do not change existing behavior. Applies to newly collected alarms only.
# NOTE on combining filters: values WITHIN one field are OR (union); DIFFERENT fields combine as AND (intersection).
# Use only ONE type axis (alarm_type_ids OR alarm_main_types OR alarm_sub_types) per input; severity/status/tags are orthogonal and combine safely with any single type axis.
# NOTE on multiple inputs: ONE input collects every company of a Multi-Tenant ID into one index, which is the intended MSSP topology - the bundled MSSP Overview dashboard reads a single index. Checkpoints are PER-INPUT, so two ENABLED inputs with the SAME multi_tenant_id in that index will collect every alarm once PER INPUT (duplicates in raw searches; the bundled dashboards collapse them via the latest_alarm_version_mssp macro). The collector logs a WARNING when it detects that case. Dedup ad-hoc searches with: | `latest_alarm_version_mssp`
include_alarm_details = Optional. 1/true = ask the API for flat title + numeric alarm_type_id per alarm (include_alarm_details=true). 0/false/absent (default) = request identical to previous versions.

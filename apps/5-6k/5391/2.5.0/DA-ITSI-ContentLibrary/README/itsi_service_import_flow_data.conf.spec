# itsi_service_import_flow_data.conf.spec
#
# This file documents the specification for creating content pack entries
# in itsi_service_import_flow_data.conf for the service import workflow.
# This configuration supports both existing legacy workflow components and
# new enhanced workflow features with dynamic filters and service discovery.
#
# File Location: 
#   - /DA-ITSI-CP-<content-pack>/default/itsi_service_import_flow_data.conf
#
# Each stanza represents a service import module for a specific content pack.

[<module_id>]
# Required: Unique identifier for this module (e.g., catalyst_center, meraki, nexus)
# This becomes the stanza name and is used in API calls

name = <string>
# Required: Display name for the content pack
# Example: name = Cisco Catalyst Center

appname = <string>
# Required: The app name where this content pack is located
# Example: appname = DA-ITSI-CP-enterprise-networking

itsiappname = <string>
# Required: The ITSI app name
# Example: itsiappname = SA-ITOA

description = <string>
# Required: Brief description of what this module does
# Example: description = Import Services

icon = <path>
# Required: Path to the icon image
# Example: icon = app/DA-ITSI-CP-enterprise-networking/images/catalyst_center_logo.svg

dashboard_welcome_text = <string>
# Required: Welcome text shown in the workflow dashboard
# Use \n for newlines (will be converted to actual newlines in the UI)
# Example: dashboard_welcome_text = The Content Pack for Cisco Enterprise Networks provides visibility...\n\nUse the content pack to import services.

dashboard_configuration_text = <string>
# Required: Configuration instructions text shown in the workflow
# Use \n for newlines
# Example: dashboard_configuration_text = Import Cisco Catalyst Center applications to build, test, and publish them using ITSI service sandboxes.

dashboard_configuration_button_text = <string>
# Required: Text for the main action button
# Use [CPName] placeholder which will be replaced with the content pack name
# Example: dashboard_configuration_button_text = Import [CPName] services

dependencies_for_service_import = <JSON>
# Required: JSON object listing service templates and entity types needed for import
# Format:
# {
#   "service_templates": ["template_id_1", "template_id_2"],
#   "entity_types": ["entity_type_id_1", "entity_type_id_2"]
# }
#
# Example:
# dependencies_for_service_import = { \
#   "service_templates": ["da-itsi-cp-enterprise-networking-catalyst-center-site"], \
#   "entity_types": ["da-itsi-cp-cisco-enterprise-networking-sites"] \
# }

conf_file_name = <string>
# Required: Configuration file name for workflow
# Example: conf_file_name = service_import_workflow_catalyst_center

retrieve_record_url = <string>
# Required: URL path for retrieving records
# Example: retrieve_record_url = cl_discovery/itsi_cp_catalyst_center_records

retrieve_sandbox_url = <string>
# Required: URL path for sandbox operations
# Example: retrieve_sandbox_url = itoa_interface/sandbox

filters = <JSON>
# JSON object defining dynamic filters for enhanced workflow
# Each filter defines a dropdown/input field that users configure before service discovery
# Used by the GET /content_library/service-import/filters/{module_id} API endpoint
#
# Format:
# {
#   "<filter_key>": {
#     "name": "<filter_name>",
#     "label": "<display_label>",
#     "placeholder": "<placeholder_text>",
#     "SPL": "<splunk_search_query>"
#   }
# }
#
# SPL Requirements for Filter Options:
# -------------------------------
# The SPL query MUST return results in one of these formats:
#
# Format 1: Single Column (value only)
#   - Returns one column which is used as both the value AND label
#   - Column name doesn't matter, first column is used
#   - Example: | table cisco_catalyst_host
#   - Result: [{value: "host1", label: "host1"}, {value: "host2", label: "host2"}]
#
# Format 2: Two Columns (value and label)
#   - Returns two columns: first is value, second is label
#   - Column names don't matter, position matters
#   - Example: | table id, name
#   - Result: [{value: "123", label: "Production Org"}, {value: "456", label: "Dev Org"}]

fetch_services_spl = <SPL_query>
# SPL query to discover and fetch services for import
# Used by the POST /content_library/service-import/services API endpoint
#
# Filter Placeholder Substitution:
# --------------------------------
# Placeholders in the query (e.g., {cisco_catalyst_host}) will be substituted with 
# actual values selected by the user from the filters defined above.
# Syntax: {filter_name} where filter_name matches a key from the filters object.
#
# Standard Fields (Service Structure):
# ------------------------------------
# The SPL query MUST return these standard fields to define the service structure:
#
# 1. service_title (REQUIRED)
#    - The display name/title for the service
#    - Type: String
#    - Must be unique per service
#    - Rows without service_title are automatically skipped
#
# 2. service_dependency (OPTIONAL)
#    - The parent service or dependency for this service
#    - Type: String (use empty string "" if no dependency)
#    - Multiple rows with the same service_title but different dependencies
#      will be aggregated into a dependencies array
#    - Example: "Core Network", "Parent Site", ""
#
# 3. service_template (OPTIONAL)
#    - The service template ID to use when creating this service
#    - Type: String (use empty string "" if no template)
#    - Must match a service template ID defined in dependencies_for_service_import
#    - If empty, the service type will be set to "N/A"
#    - Example: "Catalyst Center Site", "Meraki Network", ""
#
# Additional Fields (Tags):
# -------------------------
# ALL other fields returned by the SPL are automatically converted to tags
# and stored in the service's tags object.
#
# Output Format:
# --------------
# The backend transforms SPL results into service objects with this structure:
# {
#   "id": "<service_title>",
#   "title": "<service_title>",
#   "dependencies": ["<service_dependency_1>", "<service_dependency_2>"],
#   "type": "<service_template or 'N/A'>",
#   "tags": {
#     "<custom_field_1>": "<value_1>",
#     "<custom_field_2>": "<value_2>"
#   }
# }

fetch_services_lookback = <time_modifier>
# Optional: Time range lookback for the fetch_services_spl query
# Specifies how far back in time to search when discovering services
# Used as the earliest_time parameter for the SPL search
#
# Format: Relative time modifier (e.g., -7d, -30d, -1h, -24h@h)
# Default: -7d (if not specified)

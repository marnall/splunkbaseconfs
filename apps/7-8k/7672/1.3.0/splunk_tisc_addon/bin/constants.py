# constants.py

additional_attributes_label_to_api_field_mapping = {
    "Additional Context": "additional_context",
    "Attack Phases": "attack_phases",
    "Author": "author",
    "Comments": "comments",
    "Created": "sys_created_on",
    "Description": "description",
    "Expiration Time": "expiration_time",
    "Extensions": "extensions",
    "First Observed": "first_observed",
    "First Seen": "first_seen",
    "Historically Significant": "historically_significant",
    "ID": "id",
    "Is Defanged": "is_defanged",
    "Is False Positive": "is_false_positive",
    "Language": "language",
    "Last Observed": "last_observed",
    "Last Seen": "last_seen",
    "No of Sources": "source_count",
    "Notes": "notes",
    "Number": "number",
    "Security Type": "security_type",
    "Sources": "sources",
    "Status": "status",
    "TISC Tags": "tags",
    "TLP": "tlp",
    "Taxonomies": "taxonomies",
    "Updated": "sys_updated_on",
    "Usage Categories": "usage_categories",
    "Watch List": "watch_list"
}

api_field_to_kv_store_field_mapping = {
    "additional_context": "additional_context",
    "attack_phases": "attack_phases",
    "author": "author",
    "comments": "comments",
    "sys_created_on": "created",
    "description": "description",
    "expiration_time": "expiration_time",
    "extensions": "extensions",
    "first_observed": "first_observed",
    "first_seen": "first_seen",
    "historically_significant": "historically_significant",
    "id": "id",
    "is_defanged": "is_defanged",
    "is_false_positive": "is_false_positive",
    "language": "language",
    "last_observed": "last_observed",
    "last_seen": "last_seen",
    "source_count": "no_of_sources",
    "notes": "notes",
    "number": "number",
    "security_type": "security_type",
    "sources": "sources",
    "status": "status",
    "tags": "tisc_tags",
    "tlp": "tlp",
    "taxonomies": "taxonomies",
    "sys_updated_on": "updated",
    "usage_categories": "usage_categories",
    "watch_list": "watch_list"
}

INPUTS_METADATA_KV_STORE = "inputs_metadata_kv_store"


# KV Store Field Names
LAST_EXECUTION_TIME = "last_execution_time"
INPUT_NAME = "input_name"
CONFIGURATION_NAME = "configuration_name"
ADDON_NAME = "splunk_tisc_addon"
APP_NAME = "splunk_tisc_addon"


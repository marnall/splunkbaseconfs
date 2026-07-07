# File: threatstream_consts.py
#
# Copyright (c) 2016-2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
# Default values
DEFAULT_MAX_RESULTS = 1000
DEFAULT_TIMEOUT = 120

# JSON keys
THREATSTREAM_JSON_USERNAME = "username"
THREATSTREAM_JSON_API_KEY = "api_key"  # pragma: allowlist secret
THREATSTREAM_JSON_HASH = "hash"
THREATSTREAM_JSON_DOMAIN = "domain"
THREATSTREAM_JSON_IP = "ip"
THREATSTREAM_JSON_URL = "url"
THREATSTREAM_JSON_EMAIL = "email"
THREATSTREAM_JSON_TAGS = "tags"
THREATSTREAM_JSON_SOURCE_USER_ID = "source_user_id"

# Endpoints
ENDPOINT_INTELLIGENCE = "/v2/intelligence"
ENDPOINT_PDNS = "/v1/pdns/{ioc_type}/{ioc_value}/"
ENDPOINT_INSIGHT = "/v1/inteldetails/insights/"
ENDPOINT_REFERENCE = "/v1/inteldetails/references/{ioc_value}/"
ENDPOINT_CONFIDENCE = "/v1/inteldetails/confidence_trend/"
ENDPOINT_WHOIS = "/v1/inteldetails/whois/{ioc_value}/"
ENDPOINT_INCIDENT = "/v1/incident/"
ENDPOINT_VULNERABILITY = "/v1/vulnerability/"
ENDPOINT_SINGLE_VULNERABILITY = "/v1/vulnerability/{vul_id}/"
ENDPOINT_INCIDENT_WITH_VALUE = "/v1/incident/associated_with_intelligence/"
ENDPOINT_SINGLE_INCIDENT = "/v1/incident/{inc_id}/"
ENDPOINT_IMPORT_IOC = "/v1/intelligence/"
ENDPOINT_IMPORT_APPROVAL_IOC = "/v1/intelligence/import/"
ENDPOINT_TAG_IOC = "/v1/intelligence/{indicator_id}/tag/"
ENDPOINT_DETONATION = "/v1/submit/new/"
ENDPOINT_GET_REPORT = "/v1/submit/{report_id}/report/"
ENDPOINT_ASSOCIATE_INTELLIGENCE = "/v1/incident/{incident}/intelligence/bulk_add/"
ENDPOINT_IMPORT_SESSION = "/v1/importsession/"
ENDPOINT_THREAT_MODEL_SEARCH = "/v1/threat_model_search/"
ENDPOINT_TAG_IMPORT_SESSION = "/v1/importsession/{session_id}/intelligence/tag/"
ENDPOINT_COMMENT_IMPORT_SESSION = "/v1/importsession/{session_id}/comment/"
ENDPOINT_THREAT_BULLETIN = "/v1/tipreport/"
ENDPOINT_ATTACHMENT_THREAT_BULLETIN = "/v1/tipreport/{id}/attachment/"
ENDPOINT_UPDATE_THREAT_BULLETIN = "/v1/tipreport/{id}/"
ENDPOINT_UPDATE_OBSERVABLE = "/v2/intelligence/{id}/"
ENDPOINT_IMPORT_SESSIONS_THREAT_BULLETIN = "/v1/tipreport/{id}/update_import_sessions/"
ENDPOINT_FETCH_ENTITIES = "/v1/{entity_type}/{id}/{associated_entity_type}/"
ENDPOINT_THREAT_BULLETIN_ASSOCIATE_INTELLIGENCE = "/v1/tipreport/{id}/intelligence/bulk_add/"
ENDPOINT_RULE = "/v1/rule/"
ENDPOINT_SINGLE_RULE = "/v1/rule/{rule_id}/"
ENDPOINT_ADD_ASSOCIATION = "/v1/{entity_type}/{entity_id}/{associated_entity_type}/bulk_add/"
ENDPOINT_REMOVE_ASSOCIATION = "/v1/{entity_type}/{entity_id}/{associated_entity_type}/bulk_remove/"
ENDPOINT_ACTOR = "/v1/actor/"
ENDPOINT_LIST_ACTORS = "/v1/threat_model_search/?model_type=actor"
ENDPOINT_ADD_ATTACHMENT = "/v1/{entity_type}/{entity_id}/external_reference/attachment/"
ENDPOINT_ADD_COMMENT = "/v1/{entity_type}/{entity_id}/comment/"
ENDPOINT_GET_SINGLE_THREAT_MODEL = "/v1/{entity_type}/{entity_id}/"
ENDPOINT_SINGLE_ACTOR = "/v1/actor/{actor_id}/"
ENDPOINT_IMPORT = "/v1/import"
ENDPOINT_INVESTIGATION = "/v1/investigation/"
ENDPOINT_SINGLE_INVESTIGATION = "/v1/investigation/{}/"

# Value lists
THREATSTREAM_PUBLICATION_STATUS = ["new", "published", "reviewed", "pending_review", "review_requested"]
THREATSTREAM_CLASSIFICATION = ["public", "private"]
THREATSTREAM_SEVERITY = ["low", "medium", "high", "very-high"]
THREATSTREAM_TLP = ["white", "green", "amber", "red"]
THREATSTREAM_BODY_CONTENT_TYPE = ["markdown", "richtext"]
THREATSTREAM_STATUS = ["Approved", "Ready To Review", "Errors", "Rejected", "Processing"]
THREATSTREAM_PRIORITY = ["very low", "low", "medium", "high", "very high"]

# Error and status messages
THREATSTREAM_INVALID_SELECTION = "Invalid '{0}' entered. Must be one of: {1}"
THREATSTREAM_ERR_INVALID_TYPE = "Invalid IOC Type"
THREATSTREAM_ERR_INVALID_VALUE = "Invalid IOC Value. Don't include the http:// or any paths"
THREATSTREAM_ERR_FETCH_REPLY = "Unable to fetch the whois response. Error from the server: {error}"
THREATSTREAM_ERR_PARSE_REPLY = "Unable to parse whois response. Error from the server: {error}"
THREATSTREAM_SUCCESS_WHOIS_MESSAGE = "Successfully retrieved whois info"
THREATSTREAM_ERR_INVALID_PARAM = "Please provide a non-zero positive integer in the {param}"
THREATSTREAM_ERR_NEGATIVE_INT_PARAM = "Please provide a valid non-negative integer value in the {param}"
THREATSTREAM_ERR_API_INVALID_VALUE = "Please provide valid values in entity_type and associated_entity_type parameters"
THREATSTREAM_ERR_INVALID_INTELLIGENCE = "None of the intelligence got associated, please provide valid intelligence"
THREATSTREAM_ERR_INVALID_LOCAL_INTELLIGENCE = (
    "Error occurred while associating local IDs: {}. Please provide valid local IDs in 'local intelligence' parameter"
)
THREATSTREAM_ERR_INVALID_REMOTE_INTELLIGENCE = (
    "Error occurred while associating remote IDs: {}. Please provide valid remote IDs in 'cloud intelligence' parameter"
)
THREATSTREAM_SUCCESS_THREATBULLETIN_MESSAGE = "Successfully created threat bulletin with id: {}"
THREATSTREAM_SUCCESS_INCIDENT_MESSAGE = "Successfully created incident with id: {}"
THREATSTREAM_SUCCESS_THREATMODEL_MESSAGE = "Successfully created {} with id: {}"

THREATSTREAM_ERR_INVALID_JSON_WITH_PARAM = "Error building fields dictionary: {0}. Please ensure that provided input is in valid JSON format"
THREATSTREAM_ERR_INVALID_JSON = "Error building fields dictionary. Please ensure that provided input is in valid JSON dictionary format"
THREATSTREAM_ERR_INVALID_FIELD_PARAM_VALUE = "Please enter the value of the key, {0}, in 'fields' parameter in form of a list"
THREATSTREAM_ERR_INVALID_KEYWORDS_PARAM = "Please enter the value of keywords parameter in form of list"
THREATSTREAM_ERR_RULE_ID_NOT_FOUND = "Error while fetching the rule ID of the created rule"
THREATSTREAM_ERR_MISSING_LOCAL_REMOTE_ID = "Please provide either local_ids or remote_ids param"
THREATSTREAM_ERR_MISSING_PARAMS_UPDATE_THREAT_MODEL = (
    "Please provide at least one parameter, either 'intelligence', 'attachment', 'comment' or 'fields' to update the provided {}"
)
THREATSTREAM_ERR_MISSING_PARAMS_UPDATE_OBSERVABLE = (
    "Please provide at least one parameter, either 'indicator_type', "
    "'confidence', 'tlp', 'severity', 'status', 'expiration_date' or 'fields' to update the provided observable"
)

WHOIS_NO_DATA = "No Whois Data Available"
THREATSTREAM_INVALID_TIMEOUT = "Please provide non-zero positive integer in timeout_minutes"
THREATSTREAM_INVALID_CONFIDENCE = "Please provide positive integer in range of 0-100 in confidence parameter"
THREATSTREAM_ERR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
THREATSTREAM_EMPTY_RESPONSE = "Status code: {}. Empty response and no information in the header"

# Numeric parameters key
THREATSTREAM_LIMIT = "'limit' action parameter"
THREATSTREAM_ITEM_ID = "'item_id' action parameter"
THREATSTREAM_VMRAY_MAX_JOBS = "'vmray_max_jobs' action parameter"
THREATSTREAM_REPORT_ID = "'report_id' action parameter"
THREATSTREAM_THREAT_BULLETIN_ID = "'threat_bulletin_id' action parameter"
THREATSTREAM_VULNERABILITY_ID = "'vulnerability_id' action parameter"
THREATSTREAM_INVESTIGATION_ID = "'investigation_id' action parameter"
THREATSTREAM_OFFSET = "'offset' action parameter"
THREATSTREAM_CONFIDENCE = "'confidence' action parameter"
THREATSTREAM_FIRST_RUN_CONTAINER = "'first_run_container' configuration parameter"
THREATSTREAM_INVALID_INT = "Please provide a valid integer value in the {param}"
THREATSTREAM_RULE_ID = "'rule_id' action parameter"
THREATSTREAM_ACTOR_ID = "'actor_id' action parameter"
THREATSTREAM_ID = "'id' action parameter"
THREATSTREAM_INTELLIGENCE_ID = "'intelligence id' parameter"
THREATSTREAM_INCIDENT_ID = "'incident id' parameter"

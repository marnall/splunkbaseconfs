# File: cofensevision_consts.py
#
# Copyright (c) 2023-2026 Cofense
#
# This unpublished material is proprietary to Cofense.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Cofense.
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


# Endpoints
BASE_ENDPOINT = "/api/v4"
VISION_ENDPOINT_TOKEN = "/uaa/oauth/token"
VISION_ENDPOINT_TEST_CONNECTIVITY = "/actuator/health"
VISION_ENDPOINT_MESSAGE_SEARCH = f"{BASE_ENDPOINT}/searches"
VISION_ENDPOINT_QUARANTINE_JOBS = f"{BASE_ENDPOINT}/quarantineJobs"
VISION_ENDPOINT_FILTER_JOBS = f"{BASE_ENDPOINT}/quarantineJobs/filter"
VISION_ENDPOINT_QUARANTINE_JOB = f"{BASE_ENDPOINT}/quarantineJobs/{{job_id}}"
VISION_ENDPOINT_APPROVE_QUARANTINE_JOBS = f"{BASE_ENDPOINT}/quarantineJobs/{{job_id}}/approve"
VISION_ENDPOINT_RESTORE_QUARANTINE_JOBS = f"{BASE_ENDPOINT}/quarantineJobs/{{job_id}}/restore"
VISION_ENDPOINT_STOP_QUARANTINE_JOBS = f"{BASE_ENDPOINT}/quarantineJobs/{{job_id}}/stop"
VISION_ENDPOINT_MESSAGE = f"{BASE_ENDPOINT}/messages"
VISION_ENDPOINT_ATTACHMENT = f"{BASE_ENDPOINT}/attachment"
VISION_ENDPOINT_IOC = "/iocrepository/v1/iocs"
VISION_ENDPOINT_MESSAGE_METADATA = f"{BASE_ENDPOINT}/messages/metadata"
VISION_ENDPOINT_SEARCHABLE_HEADER = f"{BASE_ENDPOINT}/config/searchableHeaders"
VISION_ENDPOINT_IOC_LAST = f"{VISION_ENDPOINT_IOC}/last"
VISION_ENDPOINT_DOWNLOAD_LOGS = f"{BASE_ENDPOINT}/download/logs"

# JSON keys
VISION_STATE_TOKEN = "token"
VISION_STATE_ACCESS_TOKEN = "access_token"

VISION_MESSAGE_EXPIRED_TOKEN = "invalid_token"
VISION_IOC_SOURCE_HEADER = "X-Cofense-IOC-Source"

# Status and Error messages
VISION_ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
VISION_ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
VISION_ERROR_NEGATIVE_INT_PARAM = "Please provide a valid non-negative integer value in the '{key}' parameter"
VISION_ERROR_ZERO_INT_PARAM = "Please provide a non-zero positive integer value in the '{key}' parameter"
VISION_ERROR_MAX_ALLOWED_INT_PARAM = "Please provide a non-zero positive integer value upto {max} in the '{key}' parameter"
VISION_ERROR_EMPTY_RESPONSE = "Status code: {}. Empty response and no information in the header"
VISION_ERROR_HTML_RESPONSE = "Error parsing html response"
VISION_ERROR_JSON_RESPONSE = "Unable to parse JSON response. Error: {0}"
VISION_ERROR_GENERAL_MESSAGE = "Status code: {0}, Data from server: {1}"
VISION_ERROR_REST_CALL = "Error connecting to server. Details: {0}"
VISION_ERROR_STATE_FILE_CORRUPT = "Error occurred while loading the state file. Resetting the state file with the default format."
VISION_SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
VISION_ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
VISION_ERROR_SYSTEM_HEALTH = "Failed to get the system health status"
VISION_SUCCESS_SYSTEM_HEALTH = "Cofense Vision is up and running"
VISION_ERROR_ACTION_EMPTY_RESPONSE = "The server returned an unexpected empty response"
VISION_ERROR_TEST_CONNECTIVITY_INVALID_STATUS = "Error message: Server status is {}"
VISION_ERROR_EXTRA_VALUES = "The {0} parameter has more than {1} values. Please enter max {1} values to create a search."
VISION_ERROR_INVALID_MD5_VALUE = "Please provide a valid value for MD5 Hash in the attachment_hashes parameter"
VISION_ERROR_INVALID_SHA256_VALUE = "Please provide a valid value for SHA256 Hash in the attachment_hashes parameter"
VISION_ERROR_INVALID_HASH_TYPE_VALUE = "Please provide a valid hashType in attachment_hashes parameter. Allowed values are : SHA256, MD5 "
VISION_ERROR_INVALID_HASH_VALUE = "Please provide a valid value for attachment_hashes parameter. "
VISION_ERROR_INVALID_DATE_FORMAT = "Please provide a value of {} parameter in valid date format"
VISION_ERROR_INVALID_HEADER = "Please provide a valid value of headers parameter"
VISION_ERROR_VALUE_LIST = "Please provide a valid value for '{}' parameter. Valid values are: {}"
VISION_ERROR_INVALID_FILENAME = "Please provide a valid file name including the extension in the 'filename' parameter"
VISION_SUCCESS_GET_MESSAGE_SEARCH_ACTION = "Fetched message search successfully"
VISION_SUCCESS_SEARCHABLE_HEADERS_ACTION = "Fetched searchable headers successfully"
VISION_SUCCESS_GET_IOC_ACTION = "Fetched IOC successfully"
VISION_SUCCESS_DELETE_IOC_ACTION = "Delete IOC action ran successfully and IOC with MD5 ID {} is deleted"
VISION_SUCCESS_CREATE_QUARANTINE_JOB = "Created a quarantine job successfully"
VISION_SUCCESS_DELETE_QUARANTINE_JOB = "Deleted the quarantine job successfully"
VISION_ERROR_INVALID_PARAMETER_VALUE = "Please provide valid value in the '{}' parameter"
VISION_GET_METADATA_SUCCESS = "Retrieved message metadata successfully"
VISION_UPDATE_IOC_SUCCESS = "Updated the IOC successfully"
VISION_SUCCESS_GET_LAST_IOC_ACTION = "Get Last IOC Action succeeded, MD5 ID of fetched IOC : {}"
VISION_NO_HASH_PARAMETER = "Please provide a value for at least one of the hash parameters"
VISION_SUCCESS_APPROVE_JOB_ACTION = "The quarantine job has been approved successfully"
VISION_SUCCESS_RESTORE_JOB_ACTION = "Successfully initiated the restore process"
VISION_SUCCESS_GET_JOB_ACTION = "Successfully retrieved the quarantine job information"
VISION_SUCCESS_STOP_JOB_ACTION = "Successfully stopped the quarantine job"

# Consts
VISION_REQUEST_TIMEOUT = 120
VISION_DEFAULT_PAGE_SIZE = 50
VISION_DEFAULT_PAGE_NUMBER = 0
VISION_MAX_PAGE_SIZE = 2000
VISION_DATE_FORMAT = "%4Y-%m-%dT%H:%M:%S.%fZ"
VISION_DEFAULT_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
VISION_HASH_TYPE_MD5 = "MD5"
VISION_HASH_TYPE_SHA256 = "SHA256"
VISION_MAX_ALLOWED_VALUES = 3
VISION_VALID_SORT_PROPERTY = ["id", "createdBy", "createdDate", "modifiedBy", "modifiedDate", "receivedAfterDate", "receivedBeforeDate"]
VISION_VALID_SORT_ORDER = ["asc", "desc"]
VISION_THREAT_TYPES = ["domain", "md5", "sender", "sha256", "subject", "url"]
VISION_SUPPORTED_SORT_FIELDS = {
    "list_quarantine_jobs": ["id", "createdBy", "createdDate", "modifiedBy", "modifiedDate", "stopRequested"],
    "list_message_searches": ["id", "createdBy", "createdDate", "modifiedBy", "modifiedDate", "receivedAfterDate", "receivedBeforeDate"],
    "get_message_search_results": ["id", "subject", "createdOn", "sentOn", "processedOn", "htmlBody", "md5", "sha1", "sha256"],
    "list_iocs": ["updatedAt"],
}
VISION_JOB_STATUS = ["NEW", "PENDING_APPROVAL", "QUEUED", "RUNNING", "COMPLETED", "FAILED"]
VISION_SUPPORTED_CRITERIA = ["ANY", "ALL"]

# Action Parameters
VISION_UPDATE_IOCS_REQUIRED_PARAMS = ["threat_type", "threat_value", "threat_level", "created_at", "source_id"]
VISION_PARAM_SENDERS = "senders"
VISION_PARAM_SUBJECTS = "subjects"
VISION_PARAM_ATTACHMENT_NAMES = "attachment_names"
VISION_PARAM_ATTACHMENT_HASH_MATCH_CRITERIA = "attachment_hash_match_criteria"
VISION_PARAM_ATTACHMENT_HASHES = "attachment_hashes"
VISION_PARAM_ATTACHMENT_MIME_TYPES = "attachment_mime_types"
VISION_PARAM_ATTACHMENT_EXCLUDE_MIME_TYPES = "attachment_exclude_mime_types"
VISION_PARAM_DOMAIN_MATCH_CRITERIA = "domain_match_criteria"
VISION_PARAM_DOMAINS = "domains"
VISION_PARAM_HEADERS = "headers"
VISION_PARAM_INTERNET_MESSAGE_ID = "internet_message_id"
VISION_PARAM_PARTIAL_INGEST = "partial_ingest"
VISION_PARAM_RECEIVED_AFTER_DATE = "received_after_date"
VISION_PARAM_RECEIVED_BEFORE_DATE = "received_before_date"
VISION_PARAM_RECIPIENT = "recipient"
VISION_PARAM_URL = "url"
VISION_PARAM_IOC_MD5_ID = "id"
VISION_PARAM_IOC_SOURCE = "source"
VISION_PARAM_JOB_ID = "id"

# File: zendesk_consts.py
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
ZENDESK_JSON_DEVICE_URL = "url"
ZENDESK_JSON_MAX_RESULTS = "max_results"
ZENDESK_JSON_TOTAL_TICKETS = "total_tickets"
ZENDESK_JSON_SHORT_DESCRIPTION = "short_description"
ZENDESK_JSON_DESCRIPTION = "description"
ZENDESK_JSON_SUBJECT = "subject"
ZENDESK_JSON_NEW_TICKET_ID = "created_ticket_id"
ZENDESK_JSON_GOT_TICKET_ID = "queried_ticket_id"
ZENDESK_JSON_UPDATED_TICKET_ID = "updated_ticket_id"
ZENDESK_JSON_TICKET_ID = "id"
ZENDESK_JSON_FIELDS = "fields"
ZENDESK_JSON_RETURNED_TICKETS = "returned_tickets"
ZENDESK_JSON_QUERY = "query"
ZENDESK_JSON_API_TOKEN = "api_token"
ZENDESK_JSON_PER_PAGE = "max_results_per_page"
ZENDESK_JSON_PAGE = "page_number"

ZENDESK_ERR_API_INITIALIZATION = "API Initialization failed"
ZENDESK_ERR_CONNECTIVITY_TEST = "Connectivity test failed"
ZENDESK_SUCC_CONNECTIVITY_TEST = "Connectivity test passed"
ZENDESK_ERR_CREATE_TICKET_FAILED = "Ticket creation failed"
ZENDESK_SUCC_TICKET_CREATED = "Created ticket with key: {key}"
ZENDESK_ERR_LIST_TICKETS_FAILED = "Failed to get ticket listing"
ZENDESK_ERR_SERVER_CONNECTION = "Connection failed"
ZENDESK_ERR_FROM_SERVER = "API failed, Status code: {status}, Detail: {detail}"
ZENDESK_MSG_GET_INCIDENT_TEST = "Querying a recent tickets to check credentials"
ZENDESK_ERR_FIELDS_JSON_PARSE = "Unable to parse the fields parameter into a dictionary"
ZENDESK_ERR_API_UNSUPPORTED_METHOD = "Unsupported method"
ZENDESK_ERR_EMPTY_FIELDS = "The fields dictionary was detected to be empty"
ZENDESK_EMPTY_RESPONSE_STATUS_CODES = [201, 204]
ZENDESK_REQUEST_METHODS = ["put", "post"]
ZENDESK_CREATED_TICKET = "Created ticket"
ZENDESK_USING_BASE_URL = "Using url: {base_url}"
ZENDESK_ERR_JSON_PARSE = "Unable to parse reply as a Json, raw string reply: '{raw_text}'"

DEFAULT_MAX_RESULTS = 100
ZENDESK_TICKET_FOOTNOTE = "Added by Phantom for container id: "

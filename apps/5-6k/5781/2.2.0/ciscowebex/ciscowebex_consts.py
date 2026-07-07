# File: ciscowebex_consts.py
#
# Copyright (c) 2021-2025 Splunk Inc.
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

SCOPE = "spark:people_read spark:rooms_read spark:messages_write"
BASE_URL = "https://webexapis.com/v1"
AUTHORIZATION_URL = "/authorize?client_id={client_id}&response_type={response_type}&redirect_uri={redirect_uri}&scope={scope}&state={state}"

UNKNOWN_ERROR_MESSAGE = "Unknown error occurred. Please check the asset configuration and|or action parameters"
UNKNOWN_ERROR_CODE_MESSAGE = "Error code unavailable"

OAUTH_WAIT_INTERVALS = 35
OAUTH_WAIT_TIME = 3

WEBEX_STR_CODE = "code"
WEBEX_STR_TEXT = "text/plain"
WEBEX_STR_ACCESS_TOKEN = "access_token"
WEBEX_STR_TOKEN = "token"
WEBEX_STR_REFRESH_TOKEN = "refresh_token"
WEBEX_STR_CLIENT_ID = "client_id"
WEBEX_STR_SECRET = "client_secret"  # pragma: allowlist secret
WEBEX_STR_GRANT_TYPE = "grant_type"
WEBEX_STR_REDIRECT_URI = "redirect_uri"
WEBEX_STR_IS_ENCRYPTED = "is_encrypted"
WEBEX_STR_SCOPE = "scope"
WEBEX_JSON_HEADERS = {"Content-Type": "application/json"}

WEBEX_SUCCESS_CODE_RECEIVED_MESSAGE = "Code received. Please close this window, the action will continue to get new token"
WEBEX_SUCCESS_TEST_CONNECTIVITY = "Test Connectivity Passed"
WEBEX_SUCCESS_SEND_MESSAGE = "Message sent successfully"
WEBEX_SUCCESS_UPDATE_ROOM = "Updated the room successfully"

WEBEX_ERROR_EMPTY_RESPONSE = "Empty response and no information in the header Status Code: {}"
WEBEX_ERROR_ASSET_NAME_NOT_FOUND = "Asset Name for id: {0} not found"
WEBEX_ERROR_PHANTOM_BASE_URL_NOT_FOUND = "Phantom Base URL not found in System Settings. Please specify this value in System Settings"
WEBEX_ERROR_TIMEOUT = "Timeout. Please try again later"
WEBEX_ERROR_TOKEN_NOT_AVAILABLE = "Token not available. Please run Test Connectivity first"
WEBEX_ERROR_TEST_CONNECTIVITY = "Test Connectivity Failed"
WEBEX_ERROR_REQUIRED_CONFIG_PARAMS = "Please provide either api_key or client_id and client secret in config for authentication"
WEBEX_ERROR_USER_NOT_FOUND = "User not found"
WEBEX_ERR_NOT_IN_VAULT = "Vault ID not found in the vault"
WEBEX_ERROR_MESSAGE_REQUIRED = "Message is required when no card or vault_id is provided"
WEBEX_ENCRYPTION_ERROR = "Error occurred while encrypting the state file"
WEBEX_DECRYPTION_ERROR = "Error occurred while decrypting the state file"
WEBEX_INVALID_ASSET_ERROR = "In _{}_app_state: Invalid asset_id"
WEBEX_STATE_FILE_ERROR_MESSAGE = "Unable to load state file"
WEBEX_AUTHORIZATION_ERROR_MESSAGE = "Authorization code not received or not given"

PHANTOM_ASSET_ENDPOINT = "/asset/{asset_id}"
PHANTOM_SYSTEM_INFO_ENDPOINT = "/system_info"

WEBEX_ACCESS_TOKEN_ENDPOINT = "/access_token"
WEBEX_ROOMS_ENDPOINT = "/rooms"
WEBEX_UPDATE_ROOM_ENDPOINT = "/rooms/{room_id}"
WEBEX_GET_USER_ENDPOINT = "/people?email={0}"
WEBEX_MESSAGE_ENDPOINT = "/messages"
WEBEX_GET_MESSAGES_DETAILS_ENDPOINT = "/messages/{message_id}"
WEBEX_ADD_USER_ENDPOINT = "/memberships"
WEBEX_SCHEDULE_MEETINGS_ENDPOINT = "/meetings"
WEBEX_GET_MEETINGS_DETAILS = "/meetings/{meeting_id}"
WEBEX_MEETING_PARTICIPANTS_ENDPOINT = "/meetingParticipants"
WEBEX_GET_USER_DETAILS_ENDPOINT = "/people/{person_id}"
WEBEX_LIST_USERS_ENDPOINT = "/people"
WEBEX_RECORDING_DETAILS_BY_RECORDING_ID_ENDPOINT = "/recordings/{recording_id}"
WEBEX_RECORDING_DETAILS_BY_MEETING_ID_ENDPOINT = "/recordings?meetingId={meeting_id}"
WEBEX_LIST_RECORDINGS_ENDPOINT = "/recordings"
WEBEX_GET_AI_GENERATED_SUMMARY_ENDPOINT = "https://{site_url}/recordingservice/api/v1/recordings/{recording_id}/stream"
WEBEX_DEFAULT_TIMEOUT = 30

PARAMETER_LIST_FOR_SCHEDULE_MEETING = (
    ("timezone", "timezone"),
    ("description", "agenda"),
    ("password", "password"),
    ("enabled_auto_record_meeting", "enabledAutoRecordMeeting"),
    ("allow_any_user_to_be_co_host", "allowAnyUserToBeCoHost"),
    ("enabled_join_before_host", "enabledJoinBeforeHost"),
    ("join_before_host_minutes", "joinBeforeHostMinutes"),
    ("enable_connect_audio_before_host", "enableConnectAudioBeforeHost"),
    ("recurrence", "recurrence"),
    ("adhoc", "adhoc"),
    ("room_id", "roomId"),
    ("send_email", "sendEmail"),
    ("host_email", "hostEmail"),
    ("session_type_id", "sessionTypeId"),
    ("scheduled_type", "scheduledType"),
    ("enable_automatic_lock", "enableAutomaticLock"),
    ("automatic_lock_minutes", "automaticLockMinutes"),
    ("public_meeting", "publicMeeting"),
    ("reminder_time", "reminderTime"),
    ("unlocked_meeting_join_security", "unlockedMeetingJoinSecurity"),
)

PARAMETER_LIST_FOR_RETRIEVE_MEETING_PARTICIPANTS = {
    "breakoutSessionId": "breakout_session_id",
    "meetingStartTimeFrom": "meeting_start_time_from",
    "meetingStartTimeTo": "meeting_start_time_to",
    "hostEmail": "host_email",
    "joinTimeFrom": "join_time_from",
    "joinTimeTo": "join_time_to",
}

PARAMETER_LIST_FOR_LIST_MESSAGES = {
    "roomId": "room_id",
    "parentId": "parent_id",
    "before": "before",
    "beforeMessage": "before_message",
}

PARAMETER_LIST_FOR_LIST_USERS = {
    "email": "email",
    "displayName": "display_name",
    "id": "id",
    "orgId": "org_id",
    "roles": "roles",
    "locationId": "location_id",
}

ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
ERROR_NEG_INT_PARAM = "Please provide a positive integer value in the '{key}' parameter"
ERROR_ZERO_INT_PARAM = "Please provide a non-zero integer value in the '{key}' parameter"

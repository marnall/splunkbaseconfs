# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import json
import requests
requests.packages.urllib3.disable_warnings()

from datetime import datetime
from splunk.clilib.bundle_paths import make_splunkhome_path
from urllib.parse import quote_plus

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))

from ITOA.setup_logging import getLogger
from ITOA.itoa_common import get_conf_stanza, get_clear_password
from itsi.event_management.sdk.custom_group_action_base import CustomGroupActionBase
from ITOA.event_management.notable_event_ticketing import ExternalTicket
from ITOA.event_management.notable_event_utils import ActionDispatchConfiguration
import splunk.rest as splunk_rest
from splunk.util import safeURLQuote


class PagerDutyEvent(CustomGroupActionBase):
    """
    Class that performs action to trigger a PagerDuty event and link PagerDuty
    incident to the episode.
    """

    PAGER_DUTY_EVENTS_V2_API = 'https://events.pagerduty.com/v2/enqueue'
    TICKET_SYSTEM = 'PagerDuty'
    PAGERDUTY_REALM = 'itsi_pagerduty_account'
    CONF_FILE = 'itsi_pagerduty_accounts'
    APP = 'SA-ITOA'

    def __init__(self, settings):
        """
        Initialize the object
        @type settings: dict/basestring
        @param settings: incoming settings for this alert action that splunkd
            passes via stdin.
        @returns Nothing
        """
        self.logger = getLogger(logger_name="itsi.pagerduty.event")

        super(PagerDutyEvent, self).__init__(settings, self.logger)

        self.action_dispatch_config = ActionDispatchConfiguration(self.get_session_key(), self.logger)
        config = self.get_config()
        self.session_key = self.get_session_key()
        self.pd_account = config.get('pd_account', None)
        self.pd_dedup_key = config.get('pd_dedup_key', None)
        self.pd_event_action = config.get('pd_event_action', 'trigger')
        self.pd_source = config.get('pd_source', None)
        self.pd_summary = config.get('pd_summary', None)
        self.pd_severity = config.get('pd_severity', None)
        self.pd_link_text = config.get('pd_link_text', None)
        self.pd_link_href = config.get('pd_link_href', None)
        self.pd_class = config.get('pd_class', None)
        self.pd_component = config.get('pd_component', None)
        self.pd_group = config.get('pd_group', None)
        self.pd_timestamp = config.get('pd_timestamp', None)
        self.itsi_policy_id = self.settings.get('result', {}).get('itsi_policy_id', None)
        self.itsi_group_id = self.settings.get('result', {}).get('itsi_group_id', None)

        clear_password = get_clear_password(self.logger, self.session_key, self.PAGERDUTY_REALM, self.pd_account, self.APP)
        self.pd_api_token = clear_password['token']
        self.pd_routing_key = clear_password['routing_key']
        self.pd_url = 'https://api.pagerduty.com'

    def validate_required_fields(self):
        """
        Validates that all required fields are populated
        and not left blank or None
        Returns:
            bool: Returns true if all validation passes else returns false
        """

        required_fields = (self.pd_routing_key, self.pd_api_token, self.pd_account, self.pd_source, self.pd_summary, self.pd_severity, self.pd_event_action)
        if '' not in required_fields and None not in required_fields:
            if self.pd_severity not in ("critical", "warning", "error", "info"):
                self.logger.warn(f"PagerDuty Event severity value {self.pd_severity} is invalid. Setting severity to info")
                self.pd_severity = "info"

            if self.pd_event_action not in ("trigger", "acknowledge", "resolve"):
                self.logger.warn(f"PagerDuty Event Type value {self.pd_event_action} is invalid. Setting severity to trigger")
                self.pd_event_action = "trigger"

            return True
        self.logger.error("Invalid configuration found. Make sure that required fields containing Routing key, API token, account, source, summary, severity, action type are configured correctly.")
        return False

    def _to_details_object(self, raw):
        """
        Ensure we have a single dict for custom_details (PagerDuty expects an object, not an array).
        Accepts: a dict, or a list of row dicts (e.g. from get_group() as list).
        When given a list of multiple rows, merges all rows into one dict deterministically:
        duplicate keys get suffixed (_2, _3, ...) so no field from any row is lost.
        """
        if isinstance(raw, dict):
            return raw
        rows = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    rows.append(item)
                elif isinstance(item, list) and len(item) > 0 and isinstance(item[0], dict):
                    rows.append(item[0])
        if not rows:
            return {}
        if len(rows) == 1:
            return dict(rows[0])
        # Merge all rows: same key in later rows becomes key_2, key_3, etc.
        out = {}
        for row in rows:
            for key, value in row.items():
                key_str = str(key).strip() if key is not None else ''
                if not key_str:
                    continue
                base = key_str
                k = base
                i = 2
                while k in out:
                    k = f"{base}_{i}"
                    i += 1
                out[k] = value
        return out

    def _normalize_custom_details(self, raw):
        """
        Normalize only the first level of custom_details for PagerDuty Events API v2.
        Top-level keys become strings; primitives and None are normalized.
        Nested dicts and lists are passed through as-is (not normalized).
        """
        details = self._to_details_object(raw)
        if not details:
            return {}
        out = {}
        for key, value in details.items():
            key_str = str(key).strip() if key is not None else ''
            if not key_str:
                continue
            if value is None:
                out[key_str] = ''
            elif isinstance(value, (str, int, float, bool)):
                out[key_str] = value
            elif isinstance(value, (dict, list)):
                out[key_str] = value
            else:
                out[key_str] = str(value)
        return out

    def prepare_payload(self):
        """
        Prepares the payload that needs to be sent to PagerDuty

        Raises:
            Exception: Raises exception if validation has failed

        Returns:
            dict: Payload that needs to be sent to PagerDuty
        """
        if self.validate_required_fields():
            try:
                self.pd_timestamp = datetime.fromtimestamp(int(float(self.pd_timestamp))).isoformat() if self.pd_timestamp else datetime.now().isoformat()
            except Exception:
                self.logger.warn(f"Timestamp {self.pd_timestamp} is not in ISO Format")

            # PagerDuty expects custom_details as a flat object, not an array.
            # get_group() yields one dict per episode row; we merge all rows into one object (no data loss).
            try:
                groups = list(self.get_group())
                custom_details = self._normalize_custom_details(groups)
            except Exception as e:
                self.logger.warn("Could not read group data for custom_details: %s", e)
                custom_details = {}
            links = [{"href": self.pd_link_href, "text": self.pd_link_text}]
            body = {
                "event_action": self.pd_event_action,
                "routing_key": self.pd_routing_key,
                "dedup_key": self.pd_dedup_key,
                "payload": {
                    "source": self.pd_source,
                    "severity": self.pd_severity,
                    "summary": self.pd_summary,
                    "class": self.pd_class,
                    "component": self.pd_component,
                    "group": self.pd_group,
                    "custom_details": custom_details,
                    "timestamp": self.pd_timestamp
                }
            }

            if links[0]["href"] and links[0]["text"]:
                body['links'] = links

            return body
        self.logger.error("Validation for required fields failed")
        raise Exception("Invalid configuration")

    def send_payload_to_pagerduty(self, payload):
        """
        Sends event data to PagerDuty

        Args:
            payload (dict): Payload with event data
                            that needs to be sent to PagerDuty

        Raises:
            Exception: Raises exception if event is not received
                       successfully by PagerDuty
        """
        try:
            response, content = splunk_rest.simpleRequest(
                self.PAGER_DUTY_EVENTS_V2_API,
                method='POST',
                jsonargs=json.dumps(payload),
                sessionKey=self.session_key,
                raiseAllErrors=True,
                headers={"Content-Type": "application/json"}
            )

            if response.status != 202:
                message = f"Error in sending event to PagerDuty: {response.status}"
                self.logger.error(message)
                raise Exception(message)

            self.logger.info("Event sent successfully to PagerDuty" + str(content))
        except Exception as e:
            message = f"Error in sending event to PagerDuty: {e}"
            self.logger.error(message)
            raise Exception(message)

    def fetch_incident_from_pagerduty(self):

        """
        Fetches incident from PagerDuty based on group id

        Returns:
            tuple: Returns incident link and incident number
        """
        try:
            headers = {"Authorization": f"Token token={self.pd_api_token}"}

            response = requests.get(
                f"{self.pd_url}/incidents",
                params={"incident_key": self.pd_dedup_key},
                headers=headers,
                verify=False
            )

            # Check if any error has occurred. Will raise an HTTP Error for response code outside of 200-229
            response.raise_for_status()

            if response.status_code == 200:
                incidents = response.json()
                incident_details = incidents['incidents'][0]
                return incident_details['html_url'], str(incident_details['incident_number'])
        except Exception:
            message = f"Error fetching incidents from PagerDuty: {response.status_code}"
            self.logger.error(message)

    def upsert_ticket(self, itsi_group_id, incident_link, incident_number):
        """
        Links episode with PagerDuty incident

        Args:
            itsi_group_id (str): Episode id to be linked with incident
            incident_link (str): Link to the PagerDuty Incident
            incident_number (str): PagerDuty Incident Number
        """
        session_key = self.get_session_key()

        external_ticket = ExternalTicket(
            itsi_group_id, session_key, self.logger,
            action_dispatch_config=self.action_dispatch_config,
            current_user_name=self.settings.get('owner', None)
        )
        external_ticket.upsert(
            self.TICKET_SYSTEM,
            incident_number,
            incident_link,
            itsi_policy_id=self.itsi_policy_id
        )
        self.logger.info(f"Succesfully linked episode {itsi_group_id} with incident #{incident_number}")

    def execute(self):
        """
        Executes alert action
        """
        payload = self.prepare_payload()
        self.logger.info("Sending event to PagerDuty")
        self.send_payload_to_pagerduty(payload)

        if self.pd_event_action == 'trigger':
            self.logger.info(f"Fetching incident from PagerDuty for incident_key: {self.pd_dedup_key}")
            incident_link, incident_number = self.fetch_incident_from_pagerduty()
            self.logger.info(f"Linking incident #{incident_number}: {incident_link} to episode {self.itsi_group_id}")
            self.upsert_ticket(self.itsi_group_id, incident_link, incident_number)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        input_params = sys.stdin.read()
        pager_duty = PagerDutyEvent(input_params)
        pager_duty.execute()

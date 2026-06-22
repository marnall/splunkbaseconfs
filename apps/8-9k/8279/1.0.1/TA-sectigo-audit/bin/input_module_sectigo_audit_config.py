import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlencode

VERSION = "1.0.1"
USER_AGENT = "splunk-audit-connector v" + VERSION

STATE_KEY = 'state'
IMPORT_HISTORY_DAYS = 30


def validate_input(helper, definition):
    api_url = definition.parameters.get('api_url', None)
    if not api_url:
        raise ValueError("api_url must be provided")

    client_id = definition.parameters.get('client_id', None)
    if not client_id:
        raise ValueError("client_id must be provided")

    client_secret = definition.parameters.get('client_secret', None)
    if not client_secret:
        raise ValueError("client_secret must be provided")

    interval = int(definition.parameters.get('interval'))
    if interval < 5 and interval != -1:
        raise ValueError("please set 5 seconds or longer interval")


def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    audit_api_url = helper.get_arg('audit_api_url')
    audit_client_id = helper.get_arg('client_id')
    audit_client_secret = helper.get_arg('client_secret')
    # In single instance mode, to get arguments of a particular input, use
    audit_api_url = helper.get_arg('audit_api_url', stanza_name)
    audit_client_id = helper.get_arg('client_id', stanza_name)
    audit_client_secret = helper.get_arg('client_secret', stanza_name)

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    helper.get_input_stanza()
    # get specific input stanza with stanza name
    helper.get_input_stanza(stanza_name)
    # get all stanza names
    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    account = helper.get_user_credential_by_username("username")
    account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")

    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    helper.log("log message")
    # write to the log using specified log level
    helper.log_debug("log message")
    helper.log_info("log message")
    helper.log_warning("log message")
    helper.log_error("log message")
    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    # get the response headers
    r_headers = response.headers
    # get the response body as text
    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # get response cookies
    r_cookies = response.cookies
    # get redirect history
    historical_responses = response.history
    # get response status code
    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
    helper.save_check_point(key, state)
    # delete checkpoint
    helper.delete_check_point(key)
    # get checkpoint
    state = helper.get_check_point(key)

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    """

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''

    audit_api_url = helper.get_arg('api_url')
    audit_client_id = helper.get_arg('client_id')
    audit_client_secret = helper.get_arg('client_secret')

    state_raw = helper.get_check_point(STATE_KEY)
    state = State.from_dict(state_raw) if state_raw else None
    from_time = None
    if state is None:
        from_time = datetime.now(timezone.utc) - timedelta(days=IMPORT_HISTORY_DAYS)
        state = State(
            version=VERSION,
            data=StateData(
                connection_id=str(uuid.uuid4()),
                checkpoint='',
            )
        )

    client = AuditClient(
        state.data.connection_id,
        audit_api_url,
        audit_client_id,
        audit_client_secret,
        USER_AGENT,
        helper
    )

    try:
        records, next_token = client.next_page(from_time=from_time, checkpoint=state.data.checkpoint)
        if not records:
            return  # pagination exhausted, all caught up
        for record in records:
            line = record.inline_key_values()
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype(),
                data=line
            )
            ew.write_event(event)

        state.data.checkpoint = next_token
        helper.save_check_point(STATE_KEY, state.to_dict())
    except AuditClientError as e:
        helper.log_error(f'audit client error: {e}')
        raise e
    except Exception as e:
        helper.log_error(f'unknown error: {e}')
        raise e


class StateData:
    def __init__(self, connection_id: str, checkpoint: str):
        self.connection_id = connection_id
        self.checkpoint = checkpoint


class State:
    def __init__(self, version: str, data: StateData):
        self.version = version  # for future compatibility
        self.data = data

    @classmethod
    def from_dict(cls, d):
        data_field = d["data"]
        state_data = StateData(
            connection_id=data_field["connection_id"],
            checkpoint=data_field["checkpoint"]
        )
        return cls(
            version=d.get("version", "1.0"),
            data=state_data
        )

    def to_dict(self):
        return {
            "version": self.version,
            "data": {
                "connection_id": self.data.connection_id,
                "checkpoint": self.data.checkpoint,
            }
        }



class AduitRecord:
    def __init__(
            self,
            id: str,
            chain_id: str,
            timestamp: datetime,
            service: str,
            action: str,
            category: str,
            role: int,
            username: str,
            object_id: str,
            object_type: str,
            object_name: str,
            customer_id: Optional[int] = None,
            details: Optional[str] = None,
            json_details: Optional[Dict[str, Any]] = None,
            object_groups: Optional[List[int]] = None,
    ):
        self.id = id
        self.chain_id = chain_id
        self.timestamp = timestamp
        self.service = service
        self.action = action
        self.category = category
        self.role = role
        self.username = username
        self.object_id = object_id
        self.object_type = object_type
        self.object_name = object_name
        self.customer_id = customer_id
        self.details = details
        self.json_details = json_details
        self.object_groups = object_groups if object_groups is not None else []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AduitRecord':
        """Creates a Record instance from a dictionary."""
        return cls(
            id=data.get("id"),
            chain_id=data.get("chain_id"),
            timestamp=data.get("timestamp"),
            service=data.get("service"),
            action=data.get("action"),
            category=data.get("category"),
            role=data.get("role"),
            customer_id=data.get("customer_id"),
            username=data.get("username"),
            details=data.get("details"),
            json_details=data.get("json_details"),
            object_id=data.get("object_id"),
            object_type=data.get("object_type"),
            object_name=data.get("object_name"),
            object_groups=data.get("object_acls", []),
        )

    def inline_key_values(self) -> str:
        customer_id = "None"
        if self.customer_id is not None:
            customer_id = str(self.customer_id)

        # Currently, we only inline one level of Record.json_details
        extra_fields = ""
        json_details = self.json_details or {}
        if json_details and isinstance(json_details, dict):
            for key, val in json_details.items():
                extra_fields += f", detail/{key}={val}"
        else:
            extra_fields = f", detail/extra={json_details}"

        # build inline key-value log line
        line = (
            f"{self.timestamp} "
            f"Service={self.service}, "
            f"Event={self.action}, "
            f"Role ID={self.role}, "
            f"Customer ID={customer_id}, "
            f"Login ID={self.username}, "
            f"Details={self.details}{extra_fields}"
        )
        return line


class AuditClient:
    def __init__(self, connection_id: str, audit_url: str, audit_client_id: str, audit_client_secret: str,
                 user_agent: str, splunk_helper):
        self._connection_id = connection_id
        self._audit_url = audit_url
        self._audit_client_id = audit_client_id
        self._audit_client_secret = audit_client_secret

        self._user_agent = user_agent
        self._splunk_helper = splunk_helper
        self._access_token = None

    def next_page(self, from_time: Optional[datetime] = None, checkpoint: Optional[str] = None) -> Tuple[
        List[AduitRecord], Optional[str]]:
        """
        Returns a page of records, a next_token to continue pagination, or raises an error.
        """
        params = {'to': datetime.now(timezone.utc).isoformat()}
        if checkpoint:
            params['token'] = checkpoint
        elif from_time:
            params['from'] = from_time.isoformat()
        else:
            raise AuditClientError("Either 'checkpoint' or 'from_time' must be provided.")

        return self._list_records(params)

    def _list_records(self, params: Dict[str, str]) -> Tuple[List[AduitRecord], Optional[str]]:
        records_url = urljoin(self._audit_url, "/api/v1/records")
        request_id = str(uuid.uuid4())
        headers = {
            "X-Client-Id": self._connection_id,
            "X-Request-Id": request_id,
        }

        try:
            res = self._do("GET", records_url, parameters=params, headers=headers)
            res.raise_for_status()
        except Exception as e:
            msg = f"X-Request-Id: {request_id}, error: {e}"
            raise AuditClientError(msg)

        try:
            records_data = res.json()
            records = [AduitRecord.from_dict(r) for r in records_data]
            next_checkpoint = res.headers.get("Next-Token")
            return records, next_checkpoint
        except (json.JSONDecodeError, TypeError) as e:
            raise AuditClientError(f"Failed to decode records response body: {e}")

    def _obtain_token(self, auth_url: str) -> str:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": self._user_agent,
        }
        form_data = {
            "client_id": self._audit_client_id,
            "client_secret": self._audit_client_secret,
            "grant_type": "client_credentials",
        }
        try:
            res = self._splunk_helper.send_http_request(auth_url, "POST", headers=headers, payload=urlencode(form_data))
            res.raise_for_status()
        except Exception as e:
            # mask client_secret in error log
            form_data.update({"client_secret": "****"})
            raise AuditClientError(f"Failed to get access token: auth_url: {auth_url}, form data: {form_data}, error: {e}")
        access_token = res.json().get("access_token")
        if not access_token:
            raise AuditClientError("access_token not found in auth response")
        return access_token

    def _do(self, method: str, url: str, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._access_token}"
        headers["User-Agent"] = self._user_agent

        res = self._splunk_helper.send_http_request(url, method, headers=headers, **kwargs)

        if res.status_code != 401:
            return res

        # refresh the token and retry the request
        auth_url = self._extract_auth_url(res.headers)
        self._access_token = self._obtain_token(auth_url)

        headers["Authorization"] = f"Bearer {self._access_token}"
        res = self._splunk_helper.send_http_request(url, method, headers=headers, **kwargs)
        return res

    @staticmethod
    def _extract_auth_url(headers) -> str:
        auth_header = headers.get("Www-Authenticate", "")
        # Example: Bearer realm="example", authorization_uri="https://auth.example.com/token"
        parts = [p.strip() for p in auth_header.split(',')]
        for part in parts:
            if not part.lower().startswith("authorization_uri="):
                continue
            quited = part.replace("authorization_uri=", "")
            auth_url = quited.strip('"')
            return auth_url
        raise AuditClientError("Couldn't find authorization_uri in Www-Authenticate header")


class AuditClientError(Exception):
    """Base exception for the audit client."""
    pass

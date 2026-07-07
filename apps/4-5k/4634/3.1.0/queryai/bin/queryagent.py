from types import ModuleType
from typing import Any, Optional
import os
import sys
import json
import uuid
import inspect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

import logging

from utils import extract_error
from auth_token import (
    PROXY_REALM,
    API_KEY_REALM,
    PROXY_USERNAME,
    API_KEY_USERNAME,
    retrieve_password,
)
from loggerutil import setup_logging
from splunklib.searchcommands import Option, Configuration, ReportingCommand, dispatch
import requests

STAGE = os.getenv("APP_ENVIRONMENT", "PROD")
AGENTS_BASE_URL = f"https://api.{STAGE}.query.ai" if STAGE in ("dev", "test") else "https://api.query.ai"
AGENT_ID = "many_results_explanation_agent"
FSQL_AGENT_URL = f"{AGENTS_BASE_URL}/agno/a2a/agents/{AGENT_ID}/v1/message:send"


# Exception to be raised when there is any exception while making LLM API request
class FSQLAgentAPIError(Exception):
    pass


@Configuration(requires_preop=True)
class QueryAgentCommand(ReportingCommand):
    splunk_module: Optional[ModuleType] = None
    import splunk  # type: ignore

    splunk_module = splunk
    logger: logging.Logger = setup_logging(splunk_module, "queryagent")

    ask = Option(require=False)

    pid = str(os.getpid())
    agent_url = FSQL_AGENT_URL

    def __init__(self):
        super().__init__()
        self._query_id: Optional[str] = None
        self._accumulated_records: list = []
        # Guards against re-dispatching the agno request if reduce() is ever
        # invoked more than once with metadata.finished=True.
        self._dispatched: bool = False

    # Log error response with caller information and return the same
    def error_response(self, message: str):
        caller_info = inspect.stack()[1]  # Retrieve information about the immediate caller
        caller_name = caller_info.function
        caller_module = inspect.getmodule(caller_info.frame).__name__  # pyright: ignore[reportOptionalMemberAccess]
        line_number = caller_info.lineno

        full_message = f"PID {self.pid}: {message!r}. Called from {caller_module}.{caller_name} (Line {line_number})"
        self.logger.error(full_message)
        self.write_error(f"{message!r}")

    def remove_attribute(self, data: Any, attribute: str) -> Any:
        if isinstance(data, list):
            return [self.remove_attribute(item, attribute) for item in data]
        elif isinstance(data, dict):
            return {key: self.remove_attribute(value, attribute) for key, value in data.items() if key != attribute}
        return data

    @Configuration()
    def map(self, records):
        # Put your streaming preop implementation here, or remove the map method,
        # if you have no need for a streaming preop

        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service

        # The map phase can be used to prepare records if needed
        # In this case, we'll pass through the records directly
        self.logger.info(f"PID {self.pid}: Will map pipeline results.")
        for record in records:
            record = self.remove_attribute(record, "record_id")
            record = self.remove_attribute(record, "recordId")
            yield record
        self.logger.info(f"PID {self.pid}: Done with mapping.")

    def reduce(self, records):
        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service

        chunk = list(records)
        record_count = len(chunk)
        # Splunk batches large pipelines into multiple reduce() calls; only the
        # last call has metadata.finished=True. We accumulate on every call and
        # dispatch to the agno agent exactly once on the final call.
        if not getattr(self.metadata, "finished", False):
            self.logger.info(f"PID {self.pid}: Intermediate call with {record_count} records. Accummulating records.")
            self._accumulated_records.extend(chunk)
            return

        if self._dispatched:
            self.logger.warning(f"PID {self.pid}: reduce() invoked after dispatch; skipping duplicate request")
            return
        self._dispatched = True

        self.logger.info(f"PID {self.pid}: Final call with {record_count} records")
        self._accumulated_records.extend(chunk)

        self.logger.info(f"PID {self.pid}: Will process {len(self._accumulated_records)} records via queryagent")
        api_key = retrieve_password(self, API_KEY_REALM, API_KEY_USERNAME)
        if not api_key:
            return self.error_response("Query API Key not found in the configuration. Please complete the app setup.")

        proxy_server = retrieve_password(self, PROXY_REALM, PROXY_USERNAME)
        if proxy_server:
            self.logger.info(f"PID {self.pid}: proxy server is {proxy_server}")
            os.environ["HTTP_PROXY"] = proxy_server
            os.environ["HTTPS_PROXY"] = proxy_server

        if not self._accumulated_records:
            return self.error_response("Found no data!")

        # Trace ID is carried on the records produced by the queryai search command.
        if record_count > 0:
            self._query_id = self._accumulated_records[0].get("_query_id", None)
            self.logger.info(f"PID {self.pid}: Query ID is {self._query_id}")

        # Resolve the Splunk operator's email so the agno service can attribute the call to a user.
        splunk_user_email: Optional[str] = None
        try:
            searchinfo = getattr(self.metadata, "searchinfo", None)
            splunk_username = getattr(searchinfo, "username", None) if searchinfo else None
            if splunk_username and self.service:
                splunk_user_email = self.service.users[splunk_username].content.get("email") or None
        except Exception as e:
            self.logger.warning(f"PID {self.pid}: Failed to look up Splunk user email: {e}")

        user_question = self.ask if self.ask is not None else "Summarize and explain the following subset of results."

        # Shape expected by many_results_explanation_agent.
        inner_request = {
            "search_results": self._accumulated_records,
            "user_question": user_question,
        }
        if self._query_id is not None:
            inner_request["trace_id"] = self._query_id

        request_id = str(uuid.uuid4())
        request_data = json.dumps(inner_request)
        payload = {
            "method": "message/send",
            "id": request_id,
            "params": {
                "message": {
                    "messageId": f"msg-{request_id}",
                    "role": "user",
                    "agentId": AGENT_ID,
                    "parts": [{"type": "text", "text": request_data}],
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "splunk/app",
            "x-token-authorization": api_key,
        }
        if splunk_user_email:
            headers["X-QueryAI-APIKey-Email"] = splunk_user_email

        response: Optional[requests.Response] = None
        try:
            self.logger.info(f"PID {self.pid}: Submitting to queryagent ({self.agent_url})")
            response = requests.post(self.agent_url, data=json.dumps(payload), headers=headers)

            if response.status_code != 200:
                self.logger.warning(
                    f"PID {self.pid}: queryagent API gave {response.status_code}: {extract_error(response)}"
                )
                return self.error_response(extract_error(response))

            response_body = response.json()

            if "error" in response_body and response_body["error"]:
                err = response_body["error"]
                return self.error_response(f"queryagent returned error: {json.dumps(err)}")

            history = (response_body.get("result") or {}).get("history") or []
            if not history:
                return self.error_response("queryagent response missing history")

            parts = history[0].get("parts") or []
            if not parts:
                return self.error_response("queryagent response missing parts")

            reply_text = parts[0].get("text") or ""
            if not reply_text:
                return self.error_response("queryagent response text is empty")

            self.logger.info(f"PID {self.pid}: queryagent reply length: {len(reply_text)}")
            yield {"reply": reply_text}

        except Exception as e:
            self.logger.error(f"PID {self.pid}: queryagent API threw exception: {e}")
            detail = extract_error(response) if response is not None else str(e)
            return self.error_response(f"queryagent failure: {detail}")


dispatch(QueryAgentCommand, sys.argv, sys.stdin, sys.stdout, __name__)

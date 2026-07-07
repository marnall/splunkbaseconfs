"""Create tasks for CTIX indicators."""

import ta_cyware_ctix_declare  # noqa: F401

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import ta_cyware_ctix.logging_helper as logging_helper
import ta_cyware_ctix.proxy_helper as proxy_helper
import ta_cyware_ctix.ssl_helper as ssl_helper
import ta_cyware_ctix.conf_helper as conf_helper
from ta_cyware_ctix.ctix_exceptions import (
    CTIXAPIError, CTIXConnectionError, CTIXTimeoutError, CTIXConfigurationError, CTIXValidationError
)
from ta_cyware_ctix.ctix_connector import CTIXConnector as BaseCTIXConnector
from ta_cyware_ctix.constants import DEFAULT_TIMEOUT, USER_AGENT

import json
import sys
import time
import traceback
from ta_cyware_ctix.aob_py3 import requests


logger = logging_helper.get_logger("add_task")


class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for add task operations."""

    def add_task(self, object_id, text, priority="medium", status="not_started",
                 task_type="indicator", deadline=None, assignee=None):
        """
        Create a task for an indicator in CTIX.

        Args:
            object_id: CTIX indicator ID (UUID)
            text: Task description/text
            priority: Task priority (low, medium, high)
            status: Task status (not_started, in_progress, completed)
            task_type: Type of task (indicator, threatdata)
            deadline: Unix timestamp for task deadline (optional)
            assignee: UUID of user to assign task to (optional)

        Returns:
            dict: API response
        """
        logger.info(f"Add task action started for object ID: {object_id}")

        try:
            url = f"{self.api_url}/ingestion/tasks/"
            auth_params = self.auth()

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': USER_AGENT,
            }

            # Build payload with required fields
            payload = {
                "text": text,
                "priority": priority,
                "status": status,
                "type": task_type,
                "object_id": object_id
            }

            # Add optional fields if provided
            if deadline:
                try:
                    # Convert days to Unix timestamp (current time + days * 86400 seconds)
                    days = int(deadline)
                    deadline_timestamp = int(time.time()) + (days * 86400)
                    payload["deadline"] = deadline_timestamp
                    logger.debug(f"Converted deadline from {days} days to timestamp: {deadline_timestamp}")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid deadline value: {deadline}, skipping")

            if assignee:
                payload["assignee"] = assignee

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.info(f"Calling API to create task for object: {object_id}")
            logger.debug(f"API payload: {json.dumps(payload)}")

            response = requests.post(
                url=url,
                params=auth_params,
                headers=headers,
                json=payload,
                proxies=proxy_config,
                verify=ssl_verify,
                timeout=DEFAULT_TIMEOUT
            )

            if response.ok:
                logger.info(f"Successfully created task for object {object_id}")
                try:
                    result = response.json()
                    return result
                except json.JSONDecodeError:
                    return {"status": "success", "message": response.text}
            else:
                logger.error(f"Failed to create task - Status: {response.status_code}")
                raise CTIXAPIError(
                    f"API Error - URL: {url} - Status Code: {response.status_code}, Message: {response.text}"
                )
        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError(f"Request to CTIX API timed out after {DEFAULT_TIMEOUT} seconds") from e
        except requests.exceptions.ConnectionError as e:
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError):
            raise
        except Exception as e:
            logger.error(
                f"Error creating task: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error creating task: {str(e)}") from e


@Configuration()
class CTIXAddTaskCommand(GeneratingCommand):
    """Command to create tasks for CTIX indicators."""

    object_id = Option(require=False, default=None)
    text = Option(require=False, default="")
    priority = Option(require=False, default="medium")
    status = Option(require=False, default="not_started")
    type = Option(require=False, default="indicator")
    deadline = Option(require=False, default=None)
    assignee = Option(require=False, default=None)
    splunk_account = Option(require=False, default=None)

    def _get_friendly_error(self, error_msg):
        """Convert error message to user-friendly format."""
        if "Credentials missing" in error_msg:
            return "Account credentials not configured. Please check your Splunk account settings."
        if "Object ID is required" in error_msg:
            return "Please provide the CTIX Object ID (Indicator UUID)."
        if "Task description is required" in error_msg:
            return "Please provide task description/text."
        return error_msg

    def _build_output(self, result):
        """Build output dictionary."""
        output = {
            "task_description": result.get("text", ""),
            "assigned_to": result.get("assignee", ""),
            "task_status": result.get("status", "not_started"),
            "task_priority": result.get("priority", ""),
            "task_id": result.get("id", ""),
            "status": "success",
            "message": "Task successfully created",
            "_time": time.time(),
            "_raw": json.dumps(result)
        }

        return output

    def generate(self):
        """Generate command results."""
        try:
            logger.debug(f"Fetching credentials for account: {self.splunk_account}")
            session_key = self._metadata.searchinfo.session_key
            account_creds = conf_helper.get_account_credentials_for_search_command(
                self.splunk_account, logger, session_key
            )
            logger.info(f"Successfully fetched credentials for account: {self.splunk_account}")

            api_url = account_creds.get("base_url")
            client_id = account_creds.get("access_id")
            client_secret = account_creds.get("secret_key")

            if not client_id or not client_secret or not api_url:
                raise CTIXConfigurationError(
                    "Credentials missing. Please configure base_url, access_id, and "
                    "secret_key in Add-on Settings or select a valid account."
                )

            object_id = self.object_id
            text = self.text if self.text else ""
            priority = self.priority if self.priority else "medium"
            status = self.status if self.status else "not_started"
            task_type = self.type if self.type else "indicator"
            deadline = self.deadline if self.deadline else None
            assignee = self.assignee if self.assignee else None

            if not object_id:
                raise CTIXValidationError("Object ID is required. Please provide the indicator's CTIX ID.")

            if not text:
                raise CTIXValidationError("Task description is required. Please provide task text.")

            logger.info(f"Create Task: Creating task for object ID: {object_id}")

            result = CTIXConnector(api_url, client_id, client_secret, session_key).add_task(
                object_id=object_id,
                text=text,
                priority=priority,
                status=status,
                task_type=task_type,
                deadline=deadline,
                assignee=assignee
            )

            yield self._build_output(result)

        except Exception as err:
            logger.error(f"Create Task Error: {str(err)}")
            friendly_error = self._get_friendly_error(str(err))

            yield {
                "text": getattr(self, 'text', ''),
                "priority": getattr(self, 'priority', 'medium'),
                "object_id": getattr(self, 'object_id', ''),
                "status": "error",
                "message": friendly_error,
                "_raw": json.dumps({"error": str(err)}),
                "_time": time.time()
            }
            logger.error(err)


if __name__ == "__main__":
    dispatch(CTIXAddTaskCommand, sys.argv, sys.stdin, sys.stdout, __name__)

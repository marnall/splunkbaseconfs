import json
import os
import platform
import re
import subprocess
import sys
import traceback
import uuid

# Add the "lib" directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication

import splunklib
import splunklib.client as client
from typing import Any, Dict, Optional
from re import Pattern
from constants import *

from exec_anaconda import setup_psc_python_path
from util import setup_logging
from util.base_util import extract_management_port
from util.context_logging import get_context_logger, set_current_request_id, set_current_summarization_id

class SummarizeAPIHandler(PersistentServerConnectionApplication):
    """
    This class handles the API requests for the Summarize API.
    """
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()
        self.service = None
        # Initialize context logger that automatically includes request/summary IDs
        logger = setup_logging.get_logger()
        self.logger = get_context_logger(logger)

    """
    This method will initialize the Splunk service connection if it is not already initialized.
    It will also initialize its dependent objects.
    """
    def initialize_service_and_dependents_if_needed(self, request):
        if self.service is None:
            self.initialize_service_and_dependents(request)

    """Initialize the Splunk service connection and its dependents."""
    def initialize_service_and_dependents(self, request):
        try:
            session_key = request["session"]["authtoken"]
            port = extract_management_port(request)

            # Prepare arguments for client.Service
            service_kwargs = {
                "token": session_key,
                "owner": "nobody"
            }

            # Only add port to the arguments if it is not None
            if port is not None:
                service_kwargs["port"] = port

            self.service = client.Service(**service_kwargs)

        except Exception as e:
            self.logger.error(f"Failed to initialize Splunk service connection, error={str(e)}")
            self.service = None

    @staticmethod
    def extract_priority(request: Dict[str, Any]):
        """
        Extracts the 'priority' value from the request form.
        Expects: request['form'] = [['priority', '0'], ...]
        Returns: '0' or '1' if found, otherwise None.
        Returns: invalid_priority if the value is not '0' or '1'.
        """
        form_entries = request.get(FORM, [])
        for entry in form_entries:
            if (isinstance(entry, list) and len(entry) == 2 and entry[0] == PRIORITY):
                priority_value = entry[1]
                if priority_value in ('0', '1', 0, 1):
                    return int(priority_value)
                else:
                    return INVALID_PRIORITY
        # Return None if no priority was set, this will be set to LOW_PRIORITY
        return None


    """
    This method is called by the Splunk server when a request is received.
    """
    def handle(self, in_string):
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        
        # Set the request context for logging
        set_current_request_id(request_id)
        
        self.logger.info(f"Processing request")
        
        try:
            request = json.loads(in_string)
            method = request.get("method", "")
            if method not in ["POST", "DELETE"]:
                return self.create_response(405, error=METHOD_NOT_ALLOWED)  

            # If method is correct, extract the summarization_id and priority
            summarization_id = self.extract_summarization_id(request)
            if not summarization_id:
                return self.create_response(400, error=MISSING_SUMMARIZATION_ID)

            # Set summarization context for logging
            set_current_summarization_id(summarization_id)

            priority = self.extract_priority(request)
            if priority is None:
                priority = PRIORITY_LOW  # Default to low priority if not specified
            self.logger.info(f"Priority: {priority}")

            if priority == INVALID_PRIORITY:
                return self.create_response(400, error=INVALID_PRIORITY)

            self.logger.info(f"Processing request for summarization")

            self.initialize_service_and_dependents_if_needed(request)

            if method == "POST":
                response_code, result_str = self.handle_post(summarization_id, priority, request_id)
                return self.create_response(response_code, result=result_str)
            else: # Delete
                self.handle_delete(summarization_id, request_id)
                return self.create_response(200, result=f"Summary for summarization_id={summarization_id} is canceled")
        except splunklib.binding.HTTPError as e:
            return self.handle_http_error(e)
        except Exception as e:
            # Log with context
            self.logger.exception(f"Unexpected error processing request")
            # Return clean error message without exposing internal request_id
            full_traceback = traceback.format_exc()
            return self.create_response(500, error=f"Server error: {str(e)}, full trace back {full_traceback}")

    """
    This method extracts the summarization ID from the request url (passed along with the "rest_path" key)
    """
    @staticmethod
    def extract_summarization_id(request: Dict[str, Any]) -> Optional[str]:
        """
        Extracts the summarization_id from the request path.
        Expected the summarization_id being passed in the request:
        'rest_path': '/api/v1/itsi_summaries/summarize/abcdeft', 
        where the summarization_id is 'abcdeft'

        Args:
            request (dict): The request dictionary containing the summarization_id.

        Returns:
            str or None: The extracted summarization_id as a string, or None if not found.
        """
        rest_path = request.get(REST_PATH, None)
        # summarization_id must be at the end of the rest_path
        summarization_id_pattern = SummarizeAPIHandler.get_summarization_id_pattern()
        match = summarization_id_pattern.search(rest_path)
        if match:
            return match.group(1)
        return None
        
    def handle_post(self, summarization_id, priority, request_id='unknown'):
        """
        Handles the POST request to enqueue a summarization task.
        We had to move the logic to a separate script (enqueue_worker.py).
        The reason is that we can't use the normal mechanism in exec_anaconda.py to create a new process
        to replace the current process, because the Splunk server expects the process to be persistent.
        Instead, we use a subprocess to run the enqueue_worker.py script which will handle the queuing 
        of the summarization task.
        Args:
            summarization_id (str): The ID of the summarization task.
            priority (int): The priority of the task, either 0 (low) or 1 (high).
            request_id (str): Unique identifier for request tracing.
        Returns:
            tuple: A tuple containing the HTTP status code and a message.
            - 202 if the task is successfully queued.
            - 500 if there is an error in queuing the task.
        Associated Jira:  https://splunk.atlassian.net/browse/AI1Y-340
        """
        # Find the PSC python path
        python_path = setup_psc_python_path()
        script_path = os.path.join(os.path.dirname(__file__), "enqueue_worker.py")
        session_key = self.service.token

        cmd = [python_path, script_path, summarization_id, str(priority), session_key, request_id]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            result = json.loads(proc.stdout)
            if result.get("success"):
                return 202, f"Request with request_id={request_id} and summarization_id={summarization_id} is queued for processing"
            else:
                return 500, f"Failed to enqueue request_id={request_id} and summarization_id={summarization_id}, please retry"
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Subprocess failed: {e.stderr}")
            return 500, f"Failed to enqueue request_id={request_id} and summarization_id={summarization_id}, error: {e.stderr}"

    def handle_delete(self, summarization_id, request_id="unknown"):
        try:
            self.logger.info(f"Handling delete request")
            # TODO: stop the summary for this summarization_id
            pass
        except splunklib.binding.HTTPError as e:
            self.logger.exception(f"Failed to stop summarization, error: {e}")
            raise e

    @staticmethod
    def create_response(status, result=None, error=None):
        """
        Create response to send back to client.
        """
        if (result is None and error is None):
            payload = {}
        else:
            payload = {
                "result": result,
                "error": error
            }
        return {
            "payload": payload,
            "status": status
        }

    @staticmethod
    def get_summarization_id_pattern() -> Pattern:
        """
        Returns the regex pattern for the summarization_id.
        """
        # valid summarization_id is a string at the end of the rest_path
        # e.g. /api/v1/itsi_summaries/summarize/abcdeft, where the summarization_id is 'abcdeft'
        return re.compile(ITSI_SUMMARIZE_API_BASE_PATH + "/" + r"?([^/]+)?$")
import json
import os
import sys
from typing import Dict, Any

# Add the "lib" directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication

from util import setup_logging

from util.splunk_util import SplunkUtil
import splunklib.client as client
from itsi_ai_assistant_client import ITSIAIAssistantClient

from constants import STATUS_OK, STATUS_ERROR
from util.base_util import extract_management_port

# Set up logger
logger = setup_logging.get_logger()


class HealthAPIHandler(PersistentServerConnectionApplication):
    """
    This class handles the API requests for the Summarize API.
    """

    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            service = self._create_splunk_service(request)

            system_user_service = SplunkUtil.get_splunk_system_user_service(service)

            try:
                itsi_ai_assistant_tenant_url = SplunkUtil.get_itsi_ai_assistant_base_url(system_user_service)
            except Exception:
                logger.error("Failed to determine tenant specific ITSI AI Assistant URL")
                return

            itsi_ai_assistant_client = ITSIAIAssistantClient(itsi_ai_assistant_tenant_url, service=service)

            # Check the health of the ITSI AI Assistant service
            is_healthy = itsi_ai_assistant_client.check_service_health()

            if is_healthy:
                logger.debug("Health check successful for ITSI AI Assistant service.")
                return {"status": STATUS_OK, "payload": {"status": "ok"}}
            else:
                logger.warning("Health check failed for ITSI AI Assistant service. Service returned unhealthy status.")
                return {"status": STATUS_ERROR, "payload": {"status": "error"}}
        except Exception as e:
            logger.error(f"Unexpected error during health check for ITSI AI Assistant service: {str(e)}")
            return {"status": STATUS_ERROR, "payload": {"status": "error"}}

    def _create_splunk_service(self, request: Dict[str, Any]) -> client.Service:
        """
        Create a Splunk service instance using the request data.
        """
        session_key = request["session"]["authtoken"]
        port = extract_management_port(request)
        service_kwargs = {"token": session_key, "owner": "nobody"}
        if port:
            service_kwargs["port"] = port
        return client.Service(**service_kwargs)

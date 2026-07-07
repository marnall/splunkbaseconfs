import json
import os
import sys

current_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_path)

# since we are importing after some code, linting needs to be disabled for all imports
import import_declare_test  # noqa: F401, E402


from solnlib import log  # noqa: E402

from splunk.persistconn.application import (  # noqa: E402
    PersistentServerConnectionApplication,
)
from splunk_ta_talos_intelligence.talos_consts import (  # noqa: E402
    COLLECT_ENRICHMENT_ARA,
    NOTABLE_ENRICHMENT_ARA,
)

from splunk_ta_talos_intelligence.talos import TalosCloudIntelWebClient  # noqa: E402


class TalosRESTLogger:

    LOGGER_FILES = {
        COLLECT_ENRICHMENT_ARA: "intelligence_collection_from_talos_modalert",
        NOTABLE_ENRICHMENT_ARA: "intelligence_enrichment_with_talos_modalert",
    }

    ACTION_NAME = {
        COLLECT_ENRICHMENT_ARA: "intelligence_collection_from_talos",
        NOTABLE_ENRICHMENT_ARA: "intelligence_enrichment_with_talos",
    }

    def __init__(self, ara_type, settings):
        self.ara_type = ara_type
        self.settings = settings
        self.logger = log.Logs().get_logger(self.LOGGER_FILES[ara_type])
        self.log_message = (
            f'signature="{"{}"}" '
            f'action_name="{self.ACTION_NAME[ara_type]}" sid="{settings.get("sid")}"'
            f' app="{settings.get("app")}" user="{settings.get("owner")}"'
        )

    def log_info(self, message):
        self.logger.info(self.log_message.format(message))

    def log_debug(self, message):
        self.logger.debug(self.log_message.format(message))

    def log_error(self, message):
        self.logger.error(self.log_message.format(message))


class CustomTalosApiHandler(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """
        try:
            requests_data = json.loads(in_string)

            session_key = requests_data.get("system_authtoken")
            payload = json.loads(requests_data.get("payload", {}))

            config = payload.get("alert_action_settings", {})
            observable_type = payload.get("observable_type")
            observable_value = payload.get("observable_value")
            ara_type = payload.get("ara_type")

            logger = TalosRESTLogger(ara_type, config)
            client = TalosCloudIntelWebClient()
            client.initialize(config, session_key, ara_type, logger)

            content = {
                "url": client.handle_url_reputation,
                "ip": client.handle_ip_reputation,
                "domain": client.handle_domain_reputation,
            }.get(observable_type)(observable_value, logger)

        except Exception as e:
            return {"payload": {"msg": "Internal error", "e": f"{e}"}, "status": 503}

        return {"payload": {"msg": "success", "content": content}, "status": 200}

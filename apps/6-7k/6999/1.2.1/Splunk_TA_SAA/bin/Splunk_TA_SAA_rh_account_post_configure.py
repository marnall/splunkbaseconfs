import import_declare_test  # noqa: F401

from solnlib import log, conf_manager
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from saa_consts import ADDON_NAME
from urllib.parse import urlparse
from splunktaucclib.rest_handler.error import RestError
from saa_client import SAAClient, get_proxy_settings


def _validate_connection(session_key, base_url, api_key):
    logger = log.Logs().get_logger("saa_ta_configuration")

    try:
        proxies = get_proxy_settings(logger, session_key)
        client = SAAClient(logger, base_url, api_key, proxies=proxies)
        client.test_connectivity()
    except Exception as exc:
        raise RestError(400, f"Failed to validate account configuration: {str(exc)}")


class ConnectionSetupPostConfigure(AdminExternalHandler):
    log_filename = "Splunk_TA_SAA_account_post_configure"
    logger = log.Logs().get_logger(log_filename)

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        session_key = self.getSessionKey()

        _validate_connection(session_key, self.payload.get("base_url"), self.payload.get("api_key"))

        try:
            self._update_workflow_actions(confInfo)
        except Exception as exc:
            self.logger.info(f"Unable to update workflow_actions.conf {str(exc)}")
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        session_key = self.getSessionKey()
        _validate_connection(session_key, self.payload.get("base_url"), self.payload.get("api_key"))

        try:
            self._update_workflow_actions(confInfo)
        except Exception as exc:
            self.logger.info(f"Unable to update workflow_actions.conf {str(exc)}")
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        # Add your code here to delete the checkpoint!
        AdminExternalHandler.handleRemove(self, confInfo)

    def _update_workflow_actions(self, confInfo):
        session_key = self.getSessionKey()
        cfm = conf_manager.ConfManager(session_key, ADDON_NAME)

        # Update Workflow action paths
        workflow_actions_conf = cfm.get_conf("workflow_actions")
        stanzas = workflow_actions_conf.get_all(only_current_app=True)

        base_url = self.callerArgs.data.get("base_url", [""])[0]

        # base_url will have https

        if not base_url:
            base_url = "https://api.twinwave.io"

        # creat the appropriate app url
        app_url = base_url.replace("https://api.", "https://app.")
        parsed_app_url = urlparse(app_url)

        self.logger.info(f"updating workflow action definitions for {base_url}")

        for stanza, content in stanzas.items():
            parsed_workflow_action_url = urlparse(content["link.uri"])

            new_uri = content["link.uri"].replace(parsed_workflow_action_url.netloc, parsed_app_url.netloc)

            workflow_actions_conf.update(stanza, {"link.uri": new_uri})

        self.logger.info("updated workflow action definitions")

        workflow_actions_conf.reload()
        self.logger.info("reloading workflow_actions.conf")

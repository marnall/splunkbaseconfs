import import_declare_test  # noqa
from CiscoSecurityCloud.cii.access_token_manager import get_cii_access_token
from CiscoSecurityCloud.cii.hec_manager import (
    create_splunk_http_event_collector,
    extract_data_from_input_content,
    read_splunk_input_by_name,
    remove_splunk_http_event_collector,
)
from CiscoSecurityCloud.cii.secrets_proxy import (
    create_cii_client_secret_in_storage,
    delete_cii_client_secret_from_storage,
    read_cii_client_secret_from_storage,
    read_cii_s3_secret_from_storage,
    update_cii_client_secret_in_storage,
)
from CiscoSecurityCloud.cii.url_utils import is_localhost
from CiscoSecurityCloud.cii.webhook_connection.webhook_manager import (
    create_cii_webhook,
    remove_cii_webhook,
)
from CiscoSecurityCloud.config import (
    CII_CLIENT_SECRET,
    CII_ERROR,
    CII_WEBHOOK_ID,
    HEC_URL,
    REASON,
)
from CiscoSecurityCloud.secret_storage_manager import SecretsStorageManager
from CiscoSecurityCloud.utils import create_and_configure_logger
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

LOGGER = create_and_configure_logger(__name__)


class CustomCIIWebhookIntegration(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self.session_key = self.getSessionKey()
        self.hec_name = self.callerArgs.id
        self.secret_manager = SecretsStorageManager(self.session_key)
        self.is_cloud_instance = False

    def handleList(self, conf_info: dict):
        AdminExternalHandler.handleList(self, conf_info)

    def handleEdit(self, conf_info: dict):
        """
        If a CII client secret is provided in the payload:
            - Validate the secret by requesting a token from CII.
            - If secret is valid, update it in the secret storage.
        """

        disabled_flag = self.payload.get("disabled")
        if disabled_flag is not None:
            LOGGER.info(f"Set input 'disabled' to {bool(disabled_flag)}")
        else:
            new_cii_client_secret = self.payload.pop(CII_CLIENT_SECRET)
            if new_cii_client_secret:
                hec_data = read_splunk_input_by_name(
                    self.session_key, self.hec_name, logger=LOGGER
                )
                cii_data = extract_data_from_input_content(hec_data)
                cii_access_token = get_cii_access_token(
                    cii_data, new_cii_client_secret, LOGGER
                )
                if cii_access_token:
                    update_cii_client_secret_in_storage(
                        self.hec_name, self.secret_manager, new_cii_client_secret
                    )
        AdminExternalHandler.handleEdit(self, conf_info)

    def handleCreate(self, conf_info: dict):
        """
        Production flow on remote instance:
        - Generate an access token on the CII side.
        - Create a Splunk HEC token.
        - Register a webhook with CII using the generated HEC token.

        Local flow without webhook creation:
        - Use localhost hec_url
        - Generate an access token on the CII side.
        - Create a Splunk HEC token and verify the HEC URL.
        - Do not register a webhook.
        """
        cii_client_secret = self.payload.pop(CII_CLIENT_SECRET)
        hec_url = self.payload.get(HEC_URL, "")
        self.is_cloud_instance = (
            "splunkcloud.com" in hec_url or "splunkcloudgc.com" in hec_url
        )
        LOGGER.info(f"self.is_cloud_instance: {self.is_cloud_instance}")
        if not cii_client_secret:
            cii_client_secret = read_cii_s3_secret_from_storage(
                input_name=self.hec_name, secret_manager=self.secret_manager
            )
        cii_access_token = get_cii_access_token(
            self.payload, cii_client_secret, logger=LOGGER
        )
        hec_token = create_splunk_http_event_collector(
            self.session_key,
            self.hec_name,
            self.payload,
            is_cloud_instance=self.is_cloud_instance,
            logger=LOGGER,
        )

        create_cii_client_secret_in_storage(
            new_secret=cii_client_secret,
            hec_name=self.hec_name,
            secret_manager=self.secret_manager,
        )

        # if hec_url is localhost skip creating webhook
        if is_localhost(self.payload):
            self.payload[CII_WEBHOOK_ID] = "no_id"
        else:
            cii_webhook_id = create_cii_webhook(
                cii_access_token, hec_token, self.hec_name, self.payload, LOGGER
            )
            self.payload[CII_WEBHOOK_ID] = cii_webhook_id
        AdminExternalHandler.handleCreate(self, conf_info)

    def handleRemove(self, conf_info: dict):
        """
        - Read the HEC data and delete the HEC token.
        - Delete the CII client secret from secret storage.
        - Try to remove the webhook from CII, and notify if it fails.
        """
        hec_data = read_splunk_input_by_name(
            self.session_key, self.hec_name, logger=LOGGER
        )
        cii_data = extract_data_from_input_content(hec_data)
        hec_url = cii_data.get(HEC_URL, "")
        self.is_cloud_instance = (
            "splunkcloud.com" in hec_url or "splunkcloudgc.com" in hec_url
        )
        remove_splunk_http_event_collector(
            self.session_key,
            self.hec_name,
            logger=LOGGER,
            is_cloud_instance=self.is_cloud_instance,
        )
        cii_client_secret = read_cii_client_secret_from_storage(
            hec_name=self.hec_name, secret_manager=self.secret_manager
        )
        delete_cii_client_secret_from_storage(self.hec_name, self.secret_manager)
        try:
            cii_data = extract_data_from_input_content(hec_data)
            if not cii_data:
                LOGGER.error("HEC and CII data not found")
            cii_webhook_id = cii_data.get(CII_WEBHOOK_ID)
            cii_access_token = get_cii_access_token(cii_data, cii_client_secret, LOGGER)
        except (RestError, ValueError) as exc:
            LOGGER.error(f"{exc}")
            if cii_webhook_id:
                conf_info[CII_ERROR].append(REASON, "Access token is not valid")
                conf_info[CII_ERROR].append(CII_WEBHOOK_ID, cii_webhook_id)
            cii_access_token = ""
        if isinstance(cii_data, dict) and len(cii_access_token):
            try:
                remove_cii_webhook(cii_access_token, cii_webhook_id, cii_data, LOGGER)
            except (RestError, ValueError) as exc:
                LOGGER.error(f"{exc}")
                conf_info[CII_ERROR].append(REASON, "Webhook was not removed")
                conf_info[CII_ERROR].append(CII_WEBHOOK_ID, cii_webhook_id)
        AdminExternalHandler.handleRemove(self, conf_info)

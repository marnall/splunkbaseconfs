import import_declare_test  # noqa
from CiscoSecurityCloud.cii.access_token_manager import get_cii_access_token
from CiscoSecurityCloud.cii.aws_s3_connection.aws_s3_manager import (
    create_s3_input,
    form_aws_app_path,
    form_s3_params,
    get_region_from_sqs_url,
    is_aws_addon_installed,
    is_aws_data_valid,
    is_s3_path_valid,
    upsert_aws_account_input,
)
from CiscoSecurityCloud.cii.aws_s3_connection.cii_to_s3_connector import (
    create_cii_to_s3_connection,
    remove_cii_to_s3_connection,
)
from CiscoSecurityCloud.cii.hec_manager import (
    extract_data_from_input_content,
    read_splunk_input_by_name,
)
from CiscoSecurityCloud.cii.requests_proxy import make_request
from CiscoSecurityCloud.cii.secrets_proxy import (
    create_aws_secret_in_storage,
    create_cii_s3_secret_in_storage,
    delete_aws_secret_from_storage,
    delete_cii_s3_secret_from_storage,
    read_aws_secret_from_storage,
    read_cii_client_secret_from_storage,
    read_cii_s3_secret_from_storage,
    update_aws_secret_in_storage,
    update_cii_s3_secret_in_storage,
)
from CiscoSecurityCloud.config import (
    AWS_ACCESS_SECRET,
    CII_API_URL,
    CII_AWS_ACCOUNT_ERROR,
    CII_AWS_S3_INPUT_KEY,
    CII_CLIENT_SECRET,
    CII_ERROR,
    CII_S3_INPUT_ERROR,
    DELETE_CII_TO_S3_ERROR_MESSAGE,
    REASON,
)
from CiscoSecurityCloud.secret_storage_manager import SecretsStorageManager
from CiscoSecurityCloud.utils import create_and_configure_logger
from splunktaucclib.rest_handler.admin_external import (
    AdminExternalHandler,
    get_splunkd_endpoint,
)

LOGGER = create_and_configure_logger(__name__)


class CustomCIIS3Integration(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self.splunk_host = get_splunkd_endpoint()
        self.aws_addon_url = form_aws_app_path()
        self.aws_sqs_based_s3_endpoint = (
            f"{self.aws_addon_url}/splunk_ta_aws_aws_sqs_based_s3"
        )
        self.aws_addon_account_endpoint = (
            f"{self.aws_addon_url}/splunk_ta_aws_aws_account"
        )
        self.local_apps_url = f"{self.splunk_host}/services/apps/local"

        # To be defined on the fly
        self.input_name = self.callerArgs.id
        # to simplify the things, we use the same name
        self.aws_account = self.input_name
        self.session_key = self.getSessionKey()
        self.secret_manager = SecretsStorageManager(self.session_key)
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Splunk {self.session_key}",
        }
        self.region = None
        self.sqs_url = None

    def handleList(self, conf_info):
        AdminExternalHandler.handleList(self, conf_info)

    def handleEdit(self, conf_info):
        """
        If a CII client secret is provided in the payload:
            - Validate the secret by requesting a token from CII.
            - If valid, update the secret in the secure storage.
        """
        disabled_flag = self.payload.get("disabled")
        if disabled_flag is not None:
            LOGGER.info(f"Set input 'disabled' to {bool(disabled_flag)}")
        else:
            # Let's first make sure AWS Addon is installed
            is_aws_addon_installed(
                local_apps_url=self.local_apps_url, headers=self.headers, logger=LOGGER
            )

            url_s3_input = (
                f"{self.aws_sqs_based_s3_endpoint}/{self.input_name}?output_mode=json"
            )
            url_account = (
                f"{self.aws_addon_account_endpoint}/{self.aws_account}?output_mode=json"
            )

            # We check that the account and s3 input exists in aws addon
            make_request(
                url=url_account,
                on_error_message=CII_AWS_ACCOUNT_ERROR,
                headers=self.headers,
                logger=LOGGER,
            )
            make_request(
                url=url_s3_input,
                on_error_message=CII_S3_INPUT_ERROR,
                headers=self.headers,
                logger=LOGGER,
            )

            self.sqs_url = self.payload["sqs_queue_url"]
            self.region = get_region_from_sqs_url(self.sqs_url)

            new_cii_client_secret = self.payload.pop(CII_CLIENT_SECRET)
            s3_secret = self.payload.get(
                AWS_ACCESS_SECRET
            ) or read_aws_secret_from_storage(
                input_name=self.input_name,
                secret_manager=self.secret_manager,
            )

            is_aws_data_valid(
                region=self.region,
                aws_secret_key=s3_secret,
                aws_access_key=self.payload["aws_access_key_id"],
                sqs_queue_url=self.sqs_url,
                logger=LOGGER,
            )

            upsert_aws_account_input(
                aws_account=self.aws_account,
                aws_access_key_id=self.payload["aws_access_key_id"],
                aws_access_secret=s3_secret,
                url_acc=f"{self.aws_addon_account_endpoint}/{self.aws_account}?output_mode=json",
                headers=self.headers,
                logger=LOGGER,
            )

            if new_cii_client_secret:
                input_data_existing = read_splunk_input_by_name(
                    session_key=self.session_key,
                    input_name=self.input_name,
                    input_key=CII_AWS_S3_INPUT_KEY,
                    logger=LOGGER,
                )
                cii_data = extract_data_from_input_content(input_data_existing)
                cii_access_token = get_cii_access_token(
                    cii_data, new_cii_client_secret, logger=LOGGER
                )
                if cii_access_token:
                    update_cii_s3_secret_in_storage(
                        self.input_name, self.secret_manager, new_cii_client_secret
                    )

            if self.payload.pop(AWS_ACCESS_SECRET):
                LOGGER.warning(f"we have some AWS_ACCESS_SECRET: {AWS_ACCESS_SECRET}")
                update_aws_secret_in_storage(
                    self.input_name,
                    self.secret_manager,
                    s3_secret,
                )

            params = form_s3_params(
                input_name=self.input_name,
                index=self.payload["index"],
                aws_account=self.aws_account,
                region=self.region,
                sqs_url=self.sqs_url,
            )
            params.pop("name")

            response = make_request(
                url=url_s3_input,
                on_error_message="Failed to edit S3 input",
                headers=self.headers,
                logger=LOGGER,
                data=params,
                method="POST",
            )
            LOGGER.info(f"Edit CII S3 response: {response.json()}")

            self.payload.pop("cii_external_id", "")

        AdminExternalHandler.handleEdit(self, conf_info)

    def handleCreate(self, conf_info):
        is_aws_addon_installed(
            local_apps_url=self.local_apps_url, headers=self.headers, logger=LOGGER
        )

        self.sqs_url = self.payload["sqs_queue_url"]
        self.region = get_region_from_sqs_url(self.sqs_url)

        aws_secret = self.payload.pop(AWS_ACCESS_SECRET, "no_secret")

        is_aws_data_valid(
            region=self.region,
            aws_secret_key=aws_secret,
            aws_access_key=self.payload["aws_access_key_id"],
            sqs_queue_url=self.sqs_url,
            logger=LOGGER,
        )

        is_s3_path_valid(
            aws_secret_access_key=aws_secret,
            aws_access_key_id=self.payload["aws_access_key_id"],
            s3_url=self.payload["s3_bucket_url"],
            logger=LOGGER,
        )

        try:
            LOGGER.info("Reading cii_client_secret from payload")
            cii_client_secret = self.payload.pop(CII_CLIENT_SECRET, None)
            if not cii_client_secret:
                cii_client_secret = read_cii_client_secret_from_storage(
                    hec_name=self.input_name, secret_manager=self.secret_manager
                )
            LOGGER.info(f"CII client secret successfully retrieved {cii_client_secret}")
        except Exception as e:
            LOGGER.error(f"Failed to read CII client secret: {e}")
            raise ValueError("Client Secret Key retrieval error")

        try:
            cii_access_token = get_cii_access_token(
                self.payload, cii_client_secret, logger=LOGGER
            )
        except Exception as e:
            LOGGER.error(f"Failed to get CII access token: {e}")
            raise

        # Let's use AWS Addon endpoint and add Account input to it
        account_input = upsert_aws_account_input(
            aws_account=self.aws_account,
            aws_access_key_id=self.payload["aws_access_key_id"],
            aws_access_secret=aws_secret,
            url_acc=f"{self.aws_addon_account_endpoint}?output_mode=json",
            headers=self.headers,
            logger=LOGGER,
        )

        LOGGER.info(f'Accounted added: {account_input["entry"][0]["name"]}')

        # Let's create S3 input via AWS Addon endpoint
        s3_params = form_s3_params(
            input_name=self.input_name,
            index=self.payload["index"],
            aws_account=self.aws_account,
            region=self.region,
            sqs_url=self.sqs_url,
        )
        aws_s3_app_url = f"{self.aws_sqs_based_s3_endpoint}?output_mode=json"
        create_s3_input(
            s3_params=s3_params,
            aws_s3_app_url=aws_s3_app_url,
            headers=self.headers,
            logger=LOGGER,
        )

        aws_external_id = self.payload.pop("cii_external_id", None)
        if aws_external_id:
            LOGGER.info(f"aws_external_id: {aws_external_id}")
        else:
            LOGGER.error("aws_external_id is missing in payload")

        cii_s3_register_id = create_cii_to_s3_connection(
            cii_access_token=cii_access_token,
            cii_api_url=self.payload[CII_API_URL],
            bucket_url=self.payload["s3_bucket_url"],
            bucket_region=self.payload["s3_bucket_region"],
            sqs_url=self.sqs_url,
            external_id=aws_external_id,
            logger=LOGGER,
        )
        self.payload["cii_s3_register_id"] = cii_s3_register_id

        create_cii_s3_secret_in_storage(
            new_secret=cii_client_secret,
            input_name=self.input_name,
            secret_manager=self.secret_manager,
        )
        create_aws_secret_in_storage(
            new_secret=aws_secret,
            input_name=self.input_name,
            secret_manager=self.secret_manager,
        )

        AdminExternalHandler.handleCreate(self, conf_info)

    def handleRemove(self, conf_info):
        LOGGER.info(f"Starting handleRemove with params: {self.payload}")

        self.input_name = self.callerArgs.id

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Splunk {self.getSessionKey()}",
        }

        # Let's first make sure AWS Addon is installed
        is_aws_addon_installed(
            local_apps_url=self.local_apps_url,
            headers=self.headers,
            logger=LOGGER,
        )
        aws_addon_input_url = (
            f"{self.aws_sqs_based_s3_endpoint}/{self.input_name}?output_mode=json"
        )
        aws_addon_account_url = (
            f"{self.aws_addon_account_endpoint}/{self.input_name}?output_mode=json"
        )

        try:
            LOGGER.info(f"Removing input from AWS addon: {aws_addon_input_url}")
            error_msg = f"Failed to remove input in AWS addon: {aws_addon_input_url}."
            response = make_request(
                url=aws_addon_input_url,
                on_error_message=error_msg,
                headers=self.headers,
                logger=LOGGER,
                method="DELETE",
            )
            response.raise_for_status()
            LOGGER.info(f"{aws_addon_input_url} successfully removed.")
        except Exception:
            conf_info[CII_ERROR].append(REASON, error_msg)
            LOGGER.error(error_msg)

        # Remove Account
        try:
            LOGGER.info(f"Removing account from AWS addon: {aws_addon_account_url}")
            error_msg = (
                f"Failed to remove account in AWS addon: {aws_addon_account_url}."
            )
            response = make_request(
                url=aws_addon_account_url,
                on_error_message=error_msg,
                headers=self.headers,
                logger=LOGGER,
                method="DELETE",
            )
            response.raise_for_status()
            LOGGER.info(
                f"ACC {aws_addon_account_url} successfully removed. response {response}"
            )
        except Exception:
            conf_info[CII_ERROR].append(REASON, error_msg)
            LOGGER.error(error_msg)

        try:
            LOGGER.info("Reading cii_client_secret from storage")
            cii_client_secret = read_cii_s3_secret_from_storage(
                input_name=self.input_name, secret_manager=self.secret_manager
            )
            LOGGER.info("CII client secret successfully retrieved")
        except Exception as e:
            LOGGER.error(f"Failed to read CII client secret from storage: {e}")
            raise ValueError("CII Client Secret Key retrieval error")

        input_data_existing = read_splunk_input_by_name(
            session_key=self.session_key,
            input_name=self.input_name,
            input_key=CII_AWS_S3_INPUT_KEY,
            logger=LOGGER,
        )
        cii_data = extract_data_from_input_content(input_data_existing)

        try:
            cii_access_token = get_cii_access_token(
                payload=cii_data, cii_client_secret=cii_client_secret, logger=LOGGER
            )
        except Exception as e:
            LOGGER.error(f"Failed to get CII access token: {e}")
            raise

        try:
            remove_cii_to_s3_connection(
                cii_api_url=cii_data[CII_API_URL],
                cii_access_token=cii_access_token,
                register_id=cii_data["cii_s3_register_id"],
                logger=LOGGER,
            )
        except Exception as exc:
            conf_info[CII_ERROR].append(REASON, DELETE_CII_TO_S3_ERROR_MESSAGE)
            LOGGER.error(f"{DELETE_CII_TO_S3_ERROR_MESSAGE}: {exc}")

        # Remove CII client secret
        try:
            LOGGER.info("Try to remove CII client secret")
            delete_cii_s3_secret_from_storage(self.input_name, self.secret_manager)
            delete_aws_secret_from_storage(self.input_name, self.secret_manager)
            LOGGER.info("CII client secret removed")
        except Exception as e:
            conf_info[CII_ERROR].append(REASON, "Failed to remove CII client secret.")
            LOGGER.error(f"Failed to remove CII client secret: {e}")

        AdminExternalHandler.handleRemove(self, conf_info)

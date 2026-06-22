import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

# Add the bin directory to Python path for local imports
bin_path = os.path.dirname(__file__)
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)

splunk_home = os.environ.get("SPLUNK_HOME")
if splunk_home:
    tmpdir = os.path.join(splunk_home, "var", "run", Path(__file__).resolve().parents[1].name, "tmp")
    os.makedirs(tmpdir, mode=0o700, exist_ok=True)
    os.chmod(tmpdir, 0o700)
    os.environ["TMPDIR"] = tmpdir

from solnlib import conf_manager, log  # noqa: E402
from splunklib.modularinput import Argument, Scheme, Script  # noqa: E402
from validation.validation import validate_definition  # noqa: E402

from cfg.constants import (  # noqa: E402
    ADDON_NAME,
    TELEMETRY_APP_VERSION_KEY,
    TELEMETRY_APPS_COUNT_KEY,
    TELEMETRY_CHANGED_KEY,
    TELEMETRY_COMPONENT_VALUE,
    TELEMETRY_CONFIGURED_KEY,
    TELEMETRY_ERRORS_KEY,
    TELEMETRY_GUID_KEY,
    TELEMETRY_INTERVAL_KEY,
    TELEMETRY_OPT_IN_REQUIRED_VALUE,
    TELEMETRY_TYPE_VALUE,
)
from log.log import addon_logger  # noqa: E402
from manager.eds_manager import ExternalDataSourceManager  # noqa: E402
from utils.exceptions import (  # noqa: E402
    DownloadError,
    EDSInitializationError,
    ExistsCheckError,
    ExtractionError,
    LatestVersionError,
    TelemetryDataError,
    UnknownError,
)
from utils.splunk_utils import Splunk  # noqa: E402


class ExternalDataSourcesModularInput(Script):

    def get_scheme(self) -> Scheme:
        """
        Scheme definition for the modular input.
        This function is invoked once immediately after splunk starts.
        """
        scheme = Scheme("Agent management versioned app retrieval")
        scheme.description = "Apps will be downloaded and extracted to configured paths."
        scheme.use_single_instance = True
        scheme.use_external_validation = True

        repository_type_argument = Argument("repository_type")
        repository_type_argument.data_type = Argument.data_type_string
        repository_type_argument.description = "Type of the app source."
        repository_type_argument.required_on_create = True
        scheme.add_argument(repository_type_argument)

        extract_path_argument = Argument("extract_path")
        extract_path_argument.data_type = Argument.data_type_string
        extract_path_argument.description = "Path where downloaded apps will be extracted."
        extract_path_argument.required_on_create = True
        scheme.add_argument(extract_path_argument)

        extension_argument = Argument("extension")
        extension_argument.data_type = Argument.data_type_string
        extension_argument.description = "Artifact extension."
        extension_argument.required_on_create = True
        scheme.add_argument(extension_argument)

        auth_header_type_argument = Argument("auth_header_type")
        auth_header_type_argument.data_type = Argument.data_type_string
        auth_header_type_argument.description = "Type of the authentication header."
        auth_header_type_argument.required_on_create = True
        scheme.add_argument(auth_header_type_argument)

        secrets_storage_username_argument = Argument("secrets_storage_username")
        secrets_storage_username_argument.data_type = Argument.data_type_string
        secrets_storage_username_argument.description = "Username for accessing secrets storage."
        secrets_storage_username_argument.required_on_create = True
        scheme.add_argument(secrets_storage_username_argument)

        max_file_size_argument = Argument("max_file_size")
        max_file_size_argument.data_type = Argument.data_type_number
        max_file_size_argument.description = "Maximum size of file that will be downloaded (in MB)"
        max_file_size_argument.required_on_create = True
        scheme.add_argument(max_file_size_argument)

        timeout_argument = Argument("timeout")
        timeout_argument.data_type = Argument.data_type_number
        timeout_argument.description = "Timeout for the request."
        timeout_argument.required_on_create = True
        scheme.add_argument(timeout_argument)

        max_retries_argument = Argument("max_retries")
        max_retries_argument.data_type = Argument.data_type_number
        max_retries_argument.description = "Maximum number of retries for the request."
        max_retries_argument.required_on_create = True
        scheme.add_argument(max_retries_argument)

        address_argument = Argument("address")
        address_argument.data_type = Argument.data_type_string
        address_argument.description = (
            "Base address of GitLab, Sonatype Nexus Repository, JFrog Artifactory or GitHub app sources."
        )
        address_argument.required_on_create = True
        scheme.add_argument(address_argument)

        project_id_argument = Argument("project_id")
        project_id_argument.data_type = Argument.data_type_string
        project_id_argument.description = "Project ID of GitLab app source."
        project_id_argument.required_on_create = False
        scheme.add_argument(project_id_argument)

        owner_argument = Argument("owner")
        owner_argument.data_type = Argument.data_type_string
        owner_argument.description = "Owner of the GitHub repository."
        owner_argument.required_on_create = False
        scheme.add_argument(owner_argument)

        branch_argument = Argument("branch")
        branch_argument.data_type = Argument.data_type_string
        branch_argument.description = (
            "Branch or tag which should be looked for to download artifact from GitHub / GitLab."
        )
        branch_argument.required_on_create = False
        scheme.add_argument(branch_argument)

        repository_name_argument = Argument("repository_name")
        repository_name_argument.data_type = Argument.data_type_string
        repository_name_argument.description = (
            "Repository name of GitHub, Sonatype Nexus Repository or JFrog Artifactory app source."
        )
        repository_name_argument.required_on_create = False
        scheme.add_argument(repository_name_argument)

        path_argument = Argument("path")
        path_argument.data_type = Argument.data_type_string
        path_argument.description = (
            "Path to file in repository for Sonatype Nexus Repository / JFrog Artifactory app source."
        )
        path_argument.required_on_create = False
        scheme.add_argument(path_argument)

        artifact_name_argument = Argument("artifact_name")
        artifact_name_argument.data_type = Argument.data_type_string
        artifact_name_argument.description = (
            "Artifact name of Sonatype Nexus Repository / JFrog Artifactory app source."
        )
        artifact_name_argument.required_on_create = False
        scheme.add_argument(artifact_name_argument)

        return scheme

    def validate_input(self, definition: Any) -> None:
        """
        validate_input validates input parameters for the modular input.
        This function won't be called if configuration is added manually
        to the inputs.conf file.
        """
        validate_definition(definition.parameters)

    def stream_events(self, inputs: Any, ew: Any) -> None:
        """
        stream_events processes each input and downloads the specified versioned app sources.
        """

        for input_name, input_item in inputs.inputs.items():
            validate_definition(input_item)

        session_key = inputs.metadata.get("session_key")
        server_host = inputs.metadata.get("server_host")
        splunkd_uri = inputs.metadata.get("server_uri")
        split = urlsplit(splunkd_uri, allow_fragments=False)
        splunk_client = Splunk(session_key, split.scheme, server_host, split.port)

        logger = addon_logger()
        log_level = conf_manager.get_log_level(
            logger=logger,
            session_key=session_key,
            app_name=ADDON_NAME,
            conf_name=f"{ADDON_NAME.lower()}_settings",
        )

        logger.setLevel(log_level)
        log.modular_input_start(logger, ADDON_NAME)

        data = {
            TELEMETRY_CONFIGURED_KEY: {},
            TELEMETRY_CHANGED_KEY: {},
            TELEMETRY_ERRORS_KEY: {},
            TELEMETRY_APPS_COUNT_KEY: {},
        }  # type: ignore

        for key, func in [
            (TELEMETRY_APP_VERSION_KEY, splunk_client.addon_version),
            (TELEMETRY_INTERVAL_KEY, splunk_client.app_interval),
            (TELEMETRY_GUID_KEY, splunk_client.guid),
        ]:
            try:
                data[key] = func(key)
            except TelemetryDataError as e:
                log.log_exception(addon_logger(), e, "TelemetryRetrievalError")

        addon_logger().info(f"Telemetry data: {data}")
        for input_name, input_item in inputs.inputs.items():
            self._process_single_input(input_name, input_item, data, session_key)

        send_telemetry_data(
            splunk_client=splunk_client,
            data=data,
        )

        if len(data[TELEMETRY_CHANGED_KEY]) > 0:
            try:
                splunk_client.reload_deployment_server()
            except Exception as e:
                log.log_exception(
                    logger,
                    e,
                    "ReloadError",
                    msg_before="Error reloading Deployment Server: ",
                )

        log.modular_input_end(logger, ADDON_NAME)

    def _process_single_input(self, input_name: str, input_item: dict[str, str], data: dict, session_key: str) -> None:

        configuration_name = input_name.split("://")[1]
        repository_type = input_item["repository_type"]
        try:
            data[TELEMETRY_CONFIGURED_KEY][repository_type] = data[TELEMETRY_CONFIGURED_KEY].get(repository_type, 0) + 1

            # i.e. external_data_sources_add_on://example-data-source-1
            eds_manager = ExternalDataSourceManager(
                session_key,
                input_item,
                configuration_name,
                app_dir=Path(__file__).resolve().parents[1],
            )

            latest_version = eds_manager.get_latest_version()
            addon_logger().info(f"Latest artifact version for input: {input_name} is {latest_version}.")

            latest_successful_version = eds_manager.get_latest_successful_version()
            if latest_successful_version == latest_version:
                addon_logger().info(
                    (
                        f"Artifact for input: {input_name} already applied in version {latest_version}. "
                        "Skipping processing."
                    )
                )
                return

            artifact_exists = eds_manager.exists(latest_version)
            if artifact_exists:
                addon_logger().info(
                    (
                        f"Artifact for input: {input_name} already downloaded in version "
                        f"{latest_version}. Skipping download."
                    )
                )
            else:
                data[TELEMETRY_CHANGED_KEY][repository_type] = data[TELEMETRY_CHANGED_KEY].get(repository_type, 0) + 1
                addon_logger().info(f"Downloading artifacts for input: {input_name}.")
                eds_manager.download(latest_version)

            addon_logger().info(f"Extracting artifacts for input: {input_name}.")
            extracted_apps_count = eds_manager.extract(latest_version)

            eds_manager.save_latest_successful_version(latest_version)

            data[TELEMETRY_APPS_COUNT_KEY][repository_type] = (
                data[TELEMETRY_APPS_COUNT_KEY].get(repository_type, 0) + extracted_apps_count
            )
        except (
            EDSInitializationError,
            LatestVersionError,
            ExistsCheckError,
            DownloadError,
            ExtractionError,
        ) as e:
            existing_errs = data[TELEMETRY_ERRORS_KEY].get(repository_type, {})
            existing_errs[configuration_name] = str(e)
            data[TELEMETRY_ERRORS_KEY][repository_type] = existing_errs
            log.log_exception(
                addon_logger(),
                e,
                "ProcessingError",
                msg_before=f"Error processing artifact for configuration '{input_name}': ",
            )
        except Exception as e:
            existing_errs = data[TELEMETRY_ERRORS_KEY].get(repository_type, {})
            existing_errs[configuration_name] = str(repr(UnknownError()))
            data[TELEMETRY_ERRORS_KEY][repository_type] = existing_errs
            log.log_exception(
                addon_logger(),
                e,
                "ProcessingError",
                msg_before=f"Error processing artifact for configuration '{input_name}': ",
            )


def send_telemetry_data(splunk_client: Splunk, data: dict) -> None:
    payload = {
        "type": TELEMETRY_TYPE_VALUE,
        "component": TELEMETRY_COMPONENT_VALUE,
        "optInRequired": TELEMETRY_OPT_IN_REQUIRED_VALUE,
        "data": data,
    }

    splunk_client.send_telemetry_data(payload)


if __name__ == "__main__":
    sys.exit(ExternalDataSourcesModularInput().run(sys.argv))

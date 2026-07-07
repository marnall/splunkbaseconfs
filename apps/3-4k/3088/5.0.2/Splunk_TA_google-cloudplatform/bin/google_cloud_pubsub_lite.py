#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
from google_cloud_bootstrap import run_module
import sys
import traceback
from splunklib import modularinput as smi
import splunk.clilib.cli_common as scc
import splunk_ta_gcp.legacy.config as gconf
import splunk_ta_gcp.legacy.common as tacommon
from splunk_ta_gcp.common.credentials import CredentialFactory
import traceback
from splunk_ta_gcp.modinputs.pubsub_lite import GoogleCloudPubSubLite

import os.path as op
from solnlib import conf_manager
from solnlib.file_monitor import FileChangesChecker
import threading
import time
import os
import signal

APP_NAME = "Splunk_TA_google-cloudplatform"


class PubSubLiteConfMonitor(FileChangesChecker):
    """
    Class for Conf monitoring

    """

    def __init__(self, callback):
        super(PubSubLiteConfMonitor, self).__init__(callback, self.files())

    def files(self):
        """
        Files to check for monitoring

        """
        app_dir = op.dirname(op.dirname(op.abspath(__file__)))
        return (
            op.join(app_dir, "local", "inputs.conf"),
            op.join(app_dir, "local", "google_cloud_credentials.conf"),
            op.join(app_dir, "local", "google_cloud_global_settings.conf"),
        )


class PubSubLite(smi.Script):
    def __init__(self):
        super(PubSubLite, self).__init__()
        self.google_credentials_name = None
        self.session_key = None
        self.config = None
        self.logger = None

    def get_scheme(self):
        scheme = smi.Scheme("google_cloud_pubsub_lite")
        scheme.description = "Cloud Pub/Sub Lite"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )

        scheme.add_argument(
            smi.Argument(
                "google_credentials_name",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "google_project",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "location",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "pubsublite_regions",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "pubsublite_zones",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "pubsublite_subscriptions",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "number_of_threads",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "messages_outstanding",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "bytes_outstanding",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition):
        return

    def _validate_input(self, input_items):
        """
        Validate the input fields

        Args:
            input_items (list): A list of input items to retrieve Pub/Sub Lite subscriptions for.
        """
        self.google_credentials_name = input_items.get("google_credentials_name")

        if self.google_credentials_name is None:
            raise TypeError("Field 'Credentials' is required")

        project_id = input_items.get("google_project")

        if project_id is None:
            raise TypeError("Field 'Project' is required")

        location_type = input_items.get("location")
        pubsublite_region = input_items.get("pubsublite_regions")
        pubsublite_zone = input_items.get("pubsublite_zones")

        if location_type == "regional":
            if pubsublite_region is None:
                raise TypeError("Field 'Region' is required")
        else:
            if pubsublite_zone is None:
                raise TypeError("Field 'Zone' is required")

        pubsublite_subscriptions = input_items.get("pubsublite_subscriptions")

        if pubsublite_subscriptions is None:
            raise TypeError("Field 'Pub/Sub Lite Subscriptions' is required")

        thread_count = input_items.get("number_of_threads")

        if thread_count is None:
            raise TypeError("Field 'Number of Threads' is required")

        messages_outstanding = input_items.get("messages_outstanding")

        if messages_outstanding is None:
            raise TypeError("Field 'Messages Outstanding' is required")

        bytes_outstanding = input_items.get("bytes_outstanding")

        if bytes_outstanding is None:
            raise TypeError("Field 'Bytes Outstanding' is required")

    def get_credentials(self):
        """
        Get the credentials
        """
        return CredentialFactory.get_credential(self.config)

    def get_file_change_handler(self, meta_configs):
        """
        method to check which conf file is changed and reload the conf file after reading

        Args:
            meta_configs: to get the session key
        """

        def reload_and_exit(changed_files):
            self.logger.info("Reload conf %s", changed_files)
            changed_files = [op.basename(x) for x in changed_files]
            changed_files = [
                cf[:-5] if cf.endswith(".conf") else cf for cf in changed_files
            ]
            for conf_file in changed_files:
                cm = conf_manager.ConfManager(
                    meta_configs["session_key"],
                    APP_NAME,
                    realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                        APP_NAME, conf_file
                    ),
                )
                conf = cm.get_conf(conf_file, True)
                conf.reload()

        return reload_and_exit

    def check_conf_file_changed(self, conf_monitor):
        """
        Method to check the conf file if changed or not and if changed then exit the input gracefully

        """
        while True:
            is_conf_file_changed = conf_monitor.check_changes()

            if is_conf_file_changed:
                self.logger.info("Conf file is changed")
                os.kill(os.getpid(), signal.SIGTERM)
                break

            # Verify the conf file is modified or not, at every 1 minute
            time.sleep(60)

    def stream_events(self, inputs, ew):
        """
        Main entry of the code

        Args:
            input_items (list): A list of input items to retrieve Pub/Sub Lite subscriptions for.
            ew: Event writer
        """
        # Get the session key
        meta_configs = self._input_definition.metadata
        self.session_key = inputs.metadata["session_key"]

        input_name = list(inputs.inputs.keys())[0]

        input_items = inputs.inputs[input_name]
        log_file_name = "_".join(
            ["splunk_ta_google-cloudplatform", input_name.replace("://", "_")]
        )

        # Set the logger
        self.logger = tacommon.set_logger(
            scc.getMgmtUri(), self.session_key, log_file_name
        )

        try:
            self.logger.info("Modular input started")

            # Validate the fields for the input
            self._validate_input(input_items)

            # Get the config
            self.config = gconf.get_google_settings(
                scc.getMgmtUri(),
                self.session_key,
                cred_name=self.google_credentials_name,
            )

            # Get the credentials which will be used in the Admin client, Subscriber Client
            credential = self.get_credentials()

            # check for the proxy configuration, make the proxy uri and implemented the proxy
            tacommon.setup_env_proxy(self.config, self.logger)

            # Conf monitoring code block
            try:
                callback = self.get_file_change_handler(meta_configs)
                conf_monitor = PubSubLiteConfMonitor(callback)

                thread_conf_monitor = threading.Thread(
                    target=self.check_conf_file_changed, args=(conf_monitor,)
                )
                thread_conf_monitor.daemon = True
                # Start the thread
                thread_conf_monitor.start()

            except Exception as exc:
                self.logger.error(
                    "Error from conf file monitoring code: {0}".format(exc)
                )

            # create the data collector for pub/sub lite data
            pubsub_lite_collector = GoogleCloudPubSubLite(
                self.logger, self.session_key, self.config
            )

            # collect and index the data
            pubsub_lite_collector.get_pubsub_lite_data(input_items, credential)

        except Exception:
            self.logger.error(
                "An error occured while collecting data {}".format(
                    traceback.format_exc()
                )
            )
        finally:
            self.logger.info("Modular input exited")


if __name__ == "__main__":
    exit_code = PubSubLite().run(sys.argv)
    sys.exit(exit_code)

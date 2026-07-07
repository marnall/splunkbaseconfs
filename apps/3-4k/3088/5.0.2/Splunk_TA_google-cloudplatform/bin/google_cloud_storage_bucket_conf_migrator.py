#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
from google_cloud_bootstrap import run_module
import sys
import os
import copy
import logging
import time
import requests
import traceback
from urllib.parse import urlparse
from solnlib.splunkenv import get_splunkd_uri
from solnlib.conf_manager import ConfManager
from splunk_ta_gcp.common.settings import is_host_ipv6

APP_NAME = "Splunk_TA_google-cloudplatform"
STORAGE_BUCKETS_INPUTS_CONF = "google_cloud_storage_buckets"
INPUTS_CONF = "inputs"
NUMBER_OF_THREADS = 1
CONFIG_VERSION = "v1"


def make_log_file_path(filename):
    home = os.environ.get("SPLUNK_HOME", "")
    return os.path.join(home, "var", "log", "splunk", filename)


def make_storage_bucket_inputs_conf_path(filename):
    home = os.environ.get("SPLUNK_HOME", "")
    return os.path.join(home, "etc", "apps", APP_NAME, "local", filename)


def get_logger(log_name, log_level=logging.INFO):
    log_file = make_log_file_path("{}.log".format(log_name))
    log_dir = os.path.dirname(log_file)

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(log_name)

    handler_exists = any(
        [True for item in logger.handlers if item.baseFilename == log_file]
    )

    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, mode="a", maxBytes=25000000, backupCount=5
        )
        format_string = (
            "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s file=%(filename)s:%("
            "funcName)s:%(lineno)d | %(message)s "
        )
        formatter = logging.Formatter(format_string)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(log_level)
        logger.propagate = False

    return logger


def get_session_key():
    session_key = None
    session_key = sys.stdin.readline().strip()
    return session_key


def get_splunkd_info():
    splunkd_info = urlparse(get_splunkd_uri())
    return splunkd_info


logger = get_logger(
    "splunk_ta_google_cloud_platform_cloud_storage_bucket_conf_migration"
)


class CloudStorageBucketConfMigration:
    def __init__(self):
        self.failed_conf_migration = False

    def send_notification(self, message, severity):
        """
        Send the notification in the UI with the provided message once the migration for a stanza is done.

        Args:
            message (str): Successful migration message which would be visible in the UI under "messages" section
        """
        name = f"Cloud Storage Bucket conf migration successful for Splunk Add-on for Google Cloud Platform {time.time()}"
        if is_host_ipv6(self.splunkd_info.hostname):
            self.splunkd_info.hostname = f"[{self.splunkd_info.hostname}]"
        url: str = f"{self.splunkd_info.scheme}://{self.splunkd_info.hostname}:{self.splunkd_info.port}/services/messages"
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {self.session_key}",
        }
        payload = {"name": name, "value": message, "severity": severity}
        response = requests.post(url, data=payload, headers=headers, verify=False)
        if response.status_code != 201:
            logger.warn("Failed to send UI notification.")

    def check_is_conf_migrated(self, cfm_tasks):
        """
        Checks if any of the stanza in google_cloud_storage_buckets.conf has not been migrated

        Args:
            cfm_tasks (object): Confmanager object for google_cloud_storage_buckets.conf

        Returns:
            bool: Returns True only if all of the stanzas inside google_cloud_storage_buckets.conf has been migrated
        """
        stanzas = cfm_tasks.get_all()
        task_items = list(stanzas.items())
        for _, task_info in task_items:
            if not task_info.get("is_conf_migrated"):
                return False
        return True

    def perform_migration(
        self, task, task_info, inputs_configurations, cfm_input, cfm_tasks, input_items
    ):
        """
        Copies the content stanza content from google_cloud_storage_buckets.conf to inputs.conf under
        stanza name [google_cloud_bucket_metadata://task].
        'is_conf_migrated=1' would be stored in google_cloud_storage_buckets.conf to indicate that stanza content
        has been successfully copied/migrated to inputs.conf

        Args:
            task (str): Stanza which is present in google_cloud_storage_buckets.conf
            task_info (dict): Content of stanza which is present in google_cloud_storage_buckets.conf
            inputs_configurations (dict): A dictionary which would store the conf contents
            cfm_input (object): Confmanager object for inputs.conf
            cfm_tasks (object): Confmanager object for google_cloud_storage_buckets.conf
            input_items (dict): Content of inputs.conf
        """
        for stanza_name, stanza_info in input_items:
            if stanza_name.startswith(f"google_cloud_bucket_metadata://{task}"):
                # If this condition becomes true then it means that stanza was already migrated to inputs.conf and no need to further migrate
                # The condition will be useful when staza update to inputs.conf succeeds but stanza update to google_cloud_storage_buckets.conf fails
                logger.info(
                    f"Cloud Storage Bucket Input {task} has already been migrated hence skipping the migration."
                )
                try:
                    task_configurations = copy.deepcopy(task_info)
                    task_configurations["is_conf_migrated"] = 1
                    task_configurations.pop("eai:access", None)
                    cfm_tasks.update(task, task_configurations)
                except Exception:
                    logger.error(
                        f"An error occurred while updating the conf {STORAGE_BUCKETS_INPUTS_CONF} for stanza {task}. {traceback.format_exc()}"
                    )
                    pass
                return
        stanza_name = "google_cloud_bucket_metadata://" + task
        fields_to_include = [
            "disabled",
            "index",
            "polling_interval",
            "bucket_name",
            "google_project",
            "google_credentials_name",
            "chunk_size",
        ]
        for field in fields_to_include:
            value = task_info.get(field)
            if value is None:
                continue
            if field == "index" and value == "default":
                continue
            if field == "polling_interval":
                field = "interval"
            inputs_configurations[field] = value
        inputs_configurations["number_of_threads"] = NUMBER_OF_THREADS
        inputs_configurations["conf_version"] = CONFIG_VERSION
        try:
            cfm_input.update(stanza_name, inputs_configurations)
        except Exception as e:
            self.failed_conf_migration = True
            logger.error(f"Failed to migrate stanza {task} due to error {e}.")
            return
        try:
            task_configurations = copy.deepcopy(task_info)
            task_configurations["is_conf_migrated"] = 1
            task_configurations.pop("eai:access", None)
            cfm_tasks.update(task, task_configurations)
        except Exception:
            logger.error(
                f"An error occurred while updating the conf {STORAGE_BUCKETS_INPUTS_CONF} for stanza {task}. {traceback.format_exc()}"
            )
            pass

    def migrate_existing_inputs(self):
        """
        Migrates the staza from google_cloud_storage_buckets.conf to inputs.conf under stanza google_cloud_bucket_metadata
        """
        conf_mgr = ConfManager(self.session_key, APP_NAME)
        cfm_input = conf_mgr.get_conf(INPUTS_CONF)
        try:
            cfm_tasks = conf_mgr.get_conf(STORAGE_BUCKETS_INPUTS_CONF)
        except Exception as e:
            logger.info(
                f"{STORAGE_BUCKETS_INPUTS_CONF} conf file does not exist. Hence skipping the conf migration."
            )
            return
        stanzas = cfm_tasks.get_all()
        task_items = list(stanzas.items())
        input_stanzas = cfm_input.get_all(only_current_app=True)
        input_items = list(input_stanzas.items())
        logger.info(f"Found {len(task_items)} stanzas for Cloud Storage Bucket Input.")
        if task_items:
            for task, task_info in task_items:
                inputs_configurations = {}
                is_conf_migrated = task_info.get("is_conf_migrated")
                if is_conf_migrated:
                    logger.info(
                        f"Cloud Storage Bucket Input {task} has already been migrated hence skipping the migration."
                    )
                    continue
                logger.info(
                    f"Cloud Storage Bucket conf migration started for input {task}."
                )
                self.perform_migration(
                    task,
                    task_info,
                    inputs_configurations,
                    cfm_input,
                    cfm_tasks,
                    input_items,
                )
                if self.failed_conf_migration:
                    message = f"Splunk Add-on for Google Cloud Platform: Cloud Storage Bucket Conf migration failed for {task}."
                    severity = "error"
                    self.send_notification(message, severity)
                    # Make the flag value false for other stanzas
                    self.failed_conf_migration = False
                    continue
                logger.info(
                    f"Cloud Storage Bucket conf migration completed for input {task}."
                )
            storage_buckets_inputs_conf_path = make_storage_bucket_inputs_conf_path(
                "{}.conf".format(STORAGE_BUCKETS_INPUTS_CONF)
            )
            if self.check_is_conf_migrated(cfm_tasks):
                try:
                    os.remove(storage_buckets_inputs_conf_path)
                    logger.info(
                        f"Conf {STORAGE_BUCKETS_INPUTS_CONF} removed successfully."
                    )
                except Exception as e:
                    logger.error(
                        f"Unable to remove file {STORAGE_BUCKETS_INPUTS_CONF} due to error {e}",
                        exc_info=True,
                    )

    def run(self):
        """
        This method is responsible for performing conf migration of google_cloud_storage_buckets.conf to inputs.conf
        """
        self.splunkd_info = get_splunkd_info()
        self.session_key = get_session_key()
        logger.info(f"Cloud Storage Bucket conf migration started.")
        self.migrate_existing_inputs()
        logger.info(f"Cloud Storage Bucket conf migration completed.")


if __name__ == "__main__":
    conf_migration = CloudStorageBucketConfMigration()
    try:
        conf_migration.run()
    except Exception as e:
        logger.error(f"An error occured while conf migration. Error={e}", exc_info=True)
        message = f"Splunk Add-on for Google Cloud Platform: Cloud Storage Bucket Conf migration failed.Please reconfigure the inputs or rerun the 'google_cloud_storage_bucket_conf_migrator.py' scripted input from 'Data Inputs' section."
        severity = "error"
        conf_migration.send_notification(message, severity)

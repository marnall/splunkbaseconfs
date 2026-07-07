# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import logging
import sys
import time

import splunk.rest as rest
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

from ITOA.itoa_common import modular_input_should_run
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from ITOA.setup_logging import getLogger4ModInput
from itsi.objects.itsi_summarization import ItsiSummarization, Status
from ITOA.event_management.notable_event_utils import Audit
from ITOA.itoa_common import is_feature_enabled

DELETE_SUMMARY_ENDPOINT = '/servicesNS/nobody/SA-ITSI-AI-Summarization/api/v1/itsi_summaries/summarize'


class ITSIEpisodeSummarizationCleanup(ModularInput):
    """
    Modular input responsible for cleaning up long-running episode summarization jobs.
    """
    title = "IT Service Intelligence Episode Summarization Cleaner"
    description = "Terminates summarization jobs that have been running longer than the allotted time."
    handlers = None
    logger = None
    app = 'SA-ITOA'
    owner = 'nobody'
    name = 'itsi_episode_summarization_cleanup'
    use_single_instance = True
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [
            {
                'name': "log_level",
                'title': "Logging Level",
                'description': "This is the level at which the modular input will log data."
            }
        ]

    def read_configuration(self):
        try:
            cfm = ConfManager(self.session_key, self.app)
            conf = cfm.get_conf('itsi_summarization')
            self.episode_summarization_config = conf.get('itsi_episode_summarization')
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Unable to fetch the configuration from itsi_episode_summarization.conf')

    def get_configuration_value(self, key, default_value):
        if self.episode_summarization_config is not None:
            configured_value = self.episode_summarization_config.get(key)
            if configured_value is None:
                return default_value
            else:
                return configured_value
        else:
            return default_value

    def fetch_records(self, timeout_seconds):
        batch_size = 10
        timeout_time = time.time() - timeout_seconds

        # Only fetch in-progress records & records with a mod_timestamp before the timeout_time.
        fetch_filter = {'$and': [
            {'status': Status.STATUS_IN_PROGRESS},
            {"in_progress_time": {"$lt": timeout_time}}
        ]}

        return self.summarization_interface.get_bulk(self.owner, filter_data=fetch_filter, fields=['_key', 'itsi_policy_id', 'target_id', 'in_progress_time'], limit=batch_size)

    def do_run(self, stanzas):
        # Setup logging
        self.logger = getLogger4ModInput(stanzas)
        stanza_config = next(iter(stanzas.values()))
        level = stanza_config.get("log_level", 'INFO').upper()
        if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            level = "INFO"

        self.logger.setLevel(logging.getLevelName(level))

        if not is_feature_enabled('itsi-episode-summarization', self.session_key):
            self.logger.debug('Episode summarization feature not enabled')
            return

        if not modular_input_should_run(self.session_key, logger=self.logger):
            self.logger.info("Episode summarization cleanup job will not run on this node")
            return

        self.logger.info('Episode summarization cleanup job has started')

        # Run the cleanup job
        self.cleanup_summarization_jobs()

    def terminate_summarization(self, record):
        record_id = record.get('_key')
        errors = record.get('error_message', [])

        current_time = time.time()
        in_progress_time = record.get('in_progress_time')
        running_time = current_time - in_progress_time

        try:
            headers = {"content-type": "application/x-www-form-urlencoded"}

            # Send a request to the AI service to delete the summary
            response, _ = rest.simpleRequest(f"{DELETE_SUMMARY_ENDPOINT}/{record_id}",
                                             method='DELETE',
                                             sessionKey=self.session_key,
                                             headers=headers)
            if response.status != 200:
                self.logger.info(f"Failed to delete summarization with ID {record_id}, AI Service response: {response.status_code} - {response.text}")
                return

            # Update the summarization status and error message
            errors.append('Summarization job was terminated because it exceeded the allowed time.')
            self.summarization_interface.update(self.owner, record_id, data={
                'status': Status.STATUS_TERMINATE,
                'error_message': errors
            }, is_partial_data=True)
            self.logger.info(f"The summarization job {record_id} was stuck in progress for {running_time} seconds and has been terminated.")

            # If the record has an ITSI policy ID, send an audit event
            itsi_policy_id = record.get('itsi_policy_id', None)
            if itsi_policy_id:
                episode_id = record.get('target_id', None)
                audit = Audit(self.session_key, audit_token_name='Auto Generated ITSI Notable Index Audit Token')
                activity_type = 'Episode summarization'
                audit.send_activity_to_audit({
                    'event_id': episode_id,
                    'itsi_policy_id': record['itsi_policy_id']
                }, 'Episode summarization has been terminated because it exceeded the allowed time.', activity_type)
                self.logger.info(f"Audit event sent for episode summarization termination: {episode_id}, ITSI Policy ID: {itsi_policy_id}")
        except Exception as e:
            self.logger.info(f"Failed to terminate summarization: {e}")

    def cleanup_summarization_jobs(self):
        # Read the config file
        self.read_configuration()

        # Initialize the summarization interface
        self.summarization_interface = ItsiSummarization(self.session_key, self.owner)

        timeout = int(self.get_configuration_value('timeout', 600))
        records = self.fetch_records(timeout_seconds=timeout)

        self.logger.info(f"Records: {str(len(records))}")

        for record in records:
            record_id = record.get('_key')
            in_progress_time = record.get('in_progress_time')
            self.logger.info(f"Episode summarization job {record_id} has been running since {in_progress_time} and will be terminated")

            # Terminate summarization job that exceed the allowed runtime.
            self.terminate_summarization(record)


if __name__ == "__main__":
    worker = ITSIEpisodeSummarizationCleanup()
    worker.execute()
    sys.exit(0)

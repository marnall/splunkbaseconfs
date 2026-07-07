# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input that is intended to run forever. It does the following:
    1. Get the object count of itsi_notable_event_actions_queue collection
    2. Show the splunk message if the crosses provided the threshold
"""
import sys

import splunk.rest as rest
import splunk.search as splunk_search
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from ITOA.storage.itoa_storage import ITOAStorage
from itsi.constants import current_itsi_app_version
from itsi.itsi_utils import ITOAInterfaceUtils

from solnlib.modular_input import ModularInput

EVENT_ANALYTICS_MONITORING_URL = '/app/itsi/event_analytics_monitoring?form.contents=action_processing'
TROUBLESHOOTING_DOCUMENT = 'https://docs.splunk.com/Documentation/ITSI/latest/EA/TroubleshootRE'


class QueueConsumerSizeChecker(ModularInput):
    """
    Class that implements all the required steps. See method `do_run`.
    """

    title = 'Queue Consumer Size Checker'
    description = 'Queue Consumer Size Checker'
    app = 'SA-ITOA'
    name = 'itsi_queue_consumer_size_checker'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    collection = 'itsi_notable_event_actions_queue'
    object_type = 'action_queue_job'
    owner = 'nobody'

    def check_if_message_exist(self, logger):
        """
        Method that will fetch all the existing Splunk messages which contains the size of collection through SPL search.

        Args:
            logger (object): Object of logger to include logger functionality.

        Returns:
            Search result object: Search result object of SPL search of fetching existing splunk message
        """
        search_query = ('| rest /services/messages | search message="*The itsi_notable_event_actions_queue is reached to*" | table message')
        results = []
        try:
            job = splunk_search.dispatch(
                search=search_query,
                sessionKey=self.session_key,
                owner=self.owner,
                namespace=self.app,
                earliestTime="-30m"
            )
            if job.results:
                for result in job.results:
                    individual_result = None
                    for field in result:
                        individual_result = result.get(field)
                    results.append(str(individual_result))

        except Exception as exc:
            logger.error('Getting error while fetching existing Splunk messages: %s', exc)

        return results

    def get_queue_consumer_count(self, logger):
        """
        Method which retrieve the object count of itsi_notable_event_actions_queue

        Args:
            logger (object): Object of logger to include logger functionality.

        Returns:
            Integer: Object count of itsi_notable_event_actions_queue
        """
        try:
            storage_interface = ITOAStorage(collection=self.collection)
            objects_count = storage_interface.get_count(
                self.session_key, self.owner, self.object_type
            )
            logger.info(
                "Object counts for {0} is Fetched from collection=itsi_notable_event_actions_queue, objects_count={1}".format(
                    self.object_type, objects_count["count"]
                )
            )

            if not objects_count:
                return 0
            else:
                return int(objects_count["count"])

        except Exception as e:
            logger.error(
                "Error in fetching queue consumer size from KV Store. Exception: %s", e
            )

    @skip_run_during_migration
    def do_run(self, stanzas_config):
        """
        This is the method called by splunkd when mod input is enabled.
        @type stanzas_config: dict
        @param stanzas_config: input config for all stanzas passed down by
            splunkd.
        """

        logger = getLogger4ModInput(stanzas_config)
        stanza_config = next(iter(stanzas_config.values()))
        initial_threshold_limit = int(stanza_config.get("collection_size_initial_threshold", 10000))
        final_threshold_limit = int(stanza_config.get("collection_size_final_threshold", 100000))

        collection_size = self.get_queue_consumer_count(logger)
        messages = self.check_if_message_exist(logger)

        if collection_size and collection_size >= final_threshold_limit:
            WARNING_MESSAGE = (
                'The {0} is reached to {1}. '
                'Refer to the [{2} TroubleShooting Documentation] '
                'for reducing action processing latency. '
                'To get specific objects affecting the queue, view the  '
                '[[{3}|Event Analytics Monitoring Dashboard.]]'
            ).format(self.collection, final_threshold_limit, TROUBLESHOOTING_DOCUMENT, EVENT_ANALYTICS_MONITORING_URL)
            if not any((str(final_threshold_limit) in message for message in messages)):
                ITOAInterfaceUtils.create_message(
                    self.session_key, WARNING_MESSAGE, severity="warn"
                )
        elif collection_size and collection_size >= initial_threshold_limit:
            WARNING_MESSAGE = (
                'The {0} is reached to {1}. '
                'Refer to the [{2} TroubleShooting Documentation] '
                'for reducing action processing latency. '
                'To get specific objects affecting the queue, view the '
                '[[{3}|Event Analytics Monitoring Dashboard.]]'
            ).format(self.collection, initial_threshold_limit, TROUBLESHOOTING_DOCUMENT, EVENT_ANALYTICS_MONITORING_URL)
            if not any((str(initial_threshold_limit) in message for message in messages)):
                ITOAInterfaceUtils.create_message(
                    self.session_key, WARNING_MESSAGE, severity="warn"
                )


if __name__ == "__main__":
    worker = QueueConsumerSizeChecker()
    worker.execute()

# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input that is intended to run forever. It does the following:
    1. Poll kvstore collection which is being populated by a Producer.
    2. Consume entries in the order in which they were received.
    3. Audit success/failure in the ITSI Audit Index.

"""
import sys
import uuid
import json
from splunk.clilib.bundle_paths import make_splunkhome_path
import logging

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'bin']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from itsi.constants import current_itsi_app_version
import splunk.rest as splunk_rest
from solnlib.modular_input import ModularInput
from itsi.event_management.itsi_notable_event_queue_consumer import ITSINotableEventActionsQueueConsumer


class QueueConsumer(ModularInput):
    """
    Class that implements all the required steps. See method `do_run`.
    """

    title = 'IT Service Intelligence Actions Queue Consumer'
    description = 'Consumes producer data from the KV Store and executes an episode action.'
    app = 'SA-ITOA'
    name = 'itsi_notable_event_actions_queue_consumer'
    use_single_instance = False
    use_hec_event_writer = False
    kvstore_checkpointer_collection_name = 'itsi_notable_event_actions_queue_checkpointer_collection'
    SERVER_INFO_URI = '/services/server/info'

    def extra_arguments(self):
        return [
            {
                'name': 'exec_delay_time',
                'title': 'Execution delay time',
                'description': ('Induce some delay (in seconds) in execution after reading'
                                ' from queue. Defaults to 0 seconds')
            },
            {
                'name': 'timeout',
                'title': 'Timeout for given action',
                'description': 'Timeout value for action queue. Default timeout is 30 minutes.',
                'required_on_create': True,
                'required_on_edit': True
            },
            {
                'name': 'batch_size',
                'title': 'Batch size',
                'description': 'Number of jobs to be claimed in one request. Default value is 5.',
                'required_on_create': True,
                'required_on_edit': True
            }
        ]

    def get_search_head_name(self, logger):
        try:
            response, content = splunk_rest.simpleRequest(
                self.SERVER_INFO_URI,
                getargs={'output_mode': 'json'},
                sessionKey=self.session_key,
            )
        except Exception as e:
            logger.error(f'Failed to fetch server information: {e}')
            raise

        if response.status != 200:
            logger.error(f'Error response from server: Status {response.status}')
            raise Exception('Unable to fetch information for the server.')

        try:
            content = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f'Error decoding JSON content: {e}')
            raise

        entry = content.get('entry', [])
        if not entry:
            logger.error('No entry found in the response content.')
            raise Exception('No entry found in server response.')

        entry_content = entry[0].get('content', {})
        shc_label = entry_content.get('shcluster_label', None)
        instance_name = ''
        if shc_label:
            instance_name = entry_content.get('host', '')
        return instance_name

    @skip_run_during_migration
    def do_run(self, stanzas_config):
        """
        This is the method called by splunkd when mod input is enabled.
        @type stanzas_config: dict
        @param stanzas_config: input config for all stanzas passed down by
            splunkd.
        """

        logger = getLogger4ModInput(stanzas_config)
        stanza_name = next(iter(stanzas_config.keys()))
        stanza_config = next(iter(stanzas_config.values()))
        instance_name = self.get_search_head_name(logger)

        level = stanza_config.get("log_level", 'INFO').upper()
        if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            level = "INFO"

        logger.setLevel(logging.getLevelName(level))
        logger.info('Logger level for stanza %s set to level: %s', stanza_name, level)

        from ITOA.event_management.notable_event_utils import ActionDispatchConfiguration
        action_dispatch_config = ActionDispatchConfiguration(self.session_key, logger)

        # keyword 'master' should be deprecated going forward -> ITSI-10666
        if action_dispatch_config.ea_role == 'manager' or action_dispatch_config.ea_role == 'master':
            logger.info('%s shutting down. This host is configured as a manager host for action dispatch' % stanza_name)
            return

        try:
            exec_delay_time = float(stanza_config.get('exec_delay_time', 0))
        except (TypeError, ValueError):
            exec_delay_time = 0  # default to '0' seconds

        ck = self.checkpointer
        key = f'{stanza_name}{instance_name}id'
        modular_input_uuid = ck.get(key)

        if modular_input_uuid is None:
            modular_input_uuid = str(uuid.uuid1())
            # Save module id for this modular input so we can persist this id across splunk restart
            # we can't save in inputs.conf because it is being replicated on SHC
            ck.update(key, modular_input_uuid)
            logger.info(f'Checkpoint updated successfully, generated new UUID={modular_input_uuid} for key={key}')
        else:
            logger.info(f'Found existing UUID={modular_input_uuid} for key={key}')

        logger.info('Starting queue consumer=%s, id=%s', stanza_name, modular_input_uuid)
        timeout = stanza_config.get('timeout', 1800)
        batch_count = stanza_config.get('batch_size', 5)
        system_user_name = stanza_config.get('system_user_name', 'splunk-system-user')
        try:
            logger.info('%s with configuration=%s has started consuming queue contents..', stanza_name, stanza_config)
            consumer = ITSINotableEventActionsQueueConsumer(
                self.session_key,
                logger,
                exec_delay_time,
                modular_input_uuid,
                timeout,
                batch_count,
                stanza_name,
                system_user_name=system_user_name,
                action_dispatch_config=action_dispatch_config
            )
            consumer.consume_forever()
        except Exception as e:
            if "Splunkd daemon is not responding: " in str(e):
                logger.warning('Encountered connection issue when consuming. "%s". If this message occurs only once, '
                               'KV Store may still be initializing.', e)
            else:
                logger.exception('Encountered exception when consuming. "%s".', e)
            raise
        finally:
            logger.info('Shutting notable event action queue consumer stanza=%s, '
                        'it will resume on given interval [itsi=%s]', stanza_name, current_itsi_app_version)


if __name__ == "__main__":
    worker = QueueConsumer()
    worker.execute()

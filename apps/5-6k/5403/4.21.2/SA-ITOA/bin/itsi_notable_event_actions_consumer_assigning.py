# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input that assigns consumer IDs to notable group actions. It does the following:
    1. Get list of all enabled Notable Event Actions Queue Consumers.
       These consumers are Modular Inputs called itsi_notable_event_actions_queue_consumer
    2. Read the queue collection which has actions without consumers assigned. Name of that collection is
       itsi_notable_event_actions_queue_tmp.
    3. Assign the consumers (in Round Robin manner) to the actions and queue those actions in this
       collection: itsi_notable_event_actions_queue
    4. Once those the actions have consumers assigned, and they are queued in collection
       itsi_notable_event_actions_queue, then mark those actions for deletion in itsi_notable_event_actions_queue_tmp.
       Those actions will be later deleted at the specified interval. Default delete interval is 10 minutes.
   5. At the specified refresh interval rate, the Mod Input will also fetch the list of latest enabled modular input
      IDs for the consumers.
   6. At the specified delete objects interval (default 10 mins), the Mod Input will delete the objects marked for
      deletion. The reason for deleting only once in a while is that delete operations can be expensive. Hence,
      we don't want to delete too often.
"""
import logging
import sys
import time

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from ITOA.mod_input_utils import skip_run_during_migration
from ITOA.setup_logging import getLogger4ModInput
from ITOA.storage.itoa_storage import ITOAStorage
from itsi.constants import current_itsi_app_version

from solnlib.modular_input import ModularInput
from SA_ITOA_app_common.splunklib import results
from SA_ITOA_app_common.splunklib.searchcommands import Configuration, Option, GeneratingCommand, dispatch, validators
from itsi.itsi_utils import ITOAInterfaceUtils
import splunk.rest as splunk_rest
from splunk.util import safeURLQuote

from urllib.parse import urlparse, unquote
import asyncio


class ActionConsumerAssigner(ModularInput, GeneratingCommand):
    """
    Class that implements all the required steps. See method `do_run`.
    """

    title = 'IT Service Intelligence Episode Actions Consumer Assigning for High Scale EA'
    description = 'For High Scale EA, assign consumer modular input IDs to actions which are queued in KV Store'
    app = 'SA-ITOA'
    name = 'itsi_notable_event_actions_consumer_assigning'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    logger = None
    # key = consumer name, value = modular input id of the consumer
    consumer_id_map = {}
    enabled_modular_input_ids = []
    owner = 'nobody'
    current_consumer_id = 1
    # this is the collection which has actions without consumers assigned to them
    tmp_queue_collection = 'itsi_notable_event_actions_queue_tmp'
    # this is the collection where actions with consumer ids will be queued
    final_queue_collection = 'itsi_notable_event_actions_queue'
    batch_size = 1000
    read_delay_time = 0.1
    consumer_refresh_interval = 60  # seconds
    delete_objects_interval = 600  # seconds
    enabled_consumer_search = ('| rest /services/configs/conf-inputs splunk_server=local '
                               '| search id="*notable_event_actions_queue_consumer*" disabled="0" '
                               '| table id')

    @skip_run_during_migration
    def do_run(self, stanzas_config):
        """
        This is the method called by splunkd when mod input is enabled.
        @type stanzas_config: dict
        @param stanzas_config: input config for all stanzas passed down by
            splunkd.
        """

        self.logger = getLogger4ModInput(stanzas_config)
        default_stanza_config = next(iter(stanzas_config.values()))

        level = default_stanza_config.get("log_level", 'INFO').upper()
        if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            level = "INFO"
        self.logger.setLevel(logging.getLevelName(level))

        self.logger.info('stanzas_config=%s', stanzas_config)
        self.logger.info('default_stanza_config=%s', default_stanza_config)

        # Get the configs
        try:
            self.read_delay_time = float(default_stanza_config.get('read_delay_time', 0.1))
        except(TypeError, ValueError) as e:
            self.logger.error('Error in fetching read_delay_time configuration. Resorting to default value of 0.1. '
                              'Exception: %s', e)
            self.read_delay_time = 0.1
        try:
            self.delete_objects_interval = int(default_stanza_config.get('delete_objects_interval', 600))
        except(TypeError, ValueError) as e:
            self.logger.error('Error in fetching delete_objects_interval configuration. Resorting to default '
                              'value of 600. Exception: %s', e)
            self.delete_objects_interval = 600
        try:
            self.consumer_refresh_interval = int(default_stanza_config.get('consumer_refresh_interval', 60))
        except(TypeError, ValueError) as e:
            self.logger.error('Error in fetching consumer_refresh_interval configuration. Resorting to default '
                              'value of 60. Exception: %s', e)
            self.consumer_refresh_interval = 60
        try:
            self.batch_size = int(default_stanza_config.get('batch_size', 1000))
        except(TypeError, ValueError) as e:
            self.logger.error('Error in fetching batch_size configuration. Resorting to default value of 5000. '
                              'Exception: %s', e)
            self.batch_size = 1000

        consumer_search = self.get_search_for_enabled_consumers()
        if consumer_search is not None:
            self.enabled_consumer_search = consumer_search
        self.logger.info('enabled_notable_event_action_consumers_search=%s', self.enabled_consumer_search)

        self.owner = default_stanza_config.get('owner', 'nobody')

        self.logger.info('Starting actions consumer assigning')

        try:
            storage = ITOAStorage(collection=self.tmp_queue_collection, host_base_uri='')
            if not storage.wait_for_storage_init(self.session_key):
                raise Exception('KV store is not initialized.')

            self.get_all_enabled_action_consumers()
            self.consume_forever()
        except Exception as e:
            self.logger.exception('Encountered exception when assigning consumers to actions. "%s".', e)
            raise
        finally:
            self.logger.info('Shutting notable event actions consumer assigning [itsi=%s]', current_itsi_app_version)

    def get_search_for_enabled_consumers(self):
        try:
            uri_string = ('/servicesNS/{}/{}/properties/macros/'
                          'enabled_notable_event_action_consumers_search/definition').format(self.owner, self.app)
            uri = safeURLQuote(uri_string)
            res, content = splunk_rest.simpleRequest(uri, getargs={'output_mode': 'json'},
                                                     sessionKey=self.session_key)

            self.logger.info(
                'Result of getting enabled_notable_event_action_consumers_search from macros.conf: '
                'response=%s content=%s', res, content)

            if res.status not in [200, 201]:
                self.logger.error(
                    'Error in getting enabled_notable_event_action_consumers_search from macros.conf. Will '
                    'resort to using the default search. response=%s content=%s', res, content)
                return None
            if not content:
                self.logger.error(
                    'enabled_notable_event_action_consumers_search from macros.conf was not returned. Will '
                    'resort to using the default search.')
                return None
            return content
        except Exception:
            self.logger.error('Error in getting enabled_notable_event_action_consumers_search from macros.conf. Will '
                              'resort to using the default search.')
            return None

    @staticmethod
    def wait_for_job(search_job, maxtime=10):
        """
        Wait up to maxtime seconds for search_job to finish.  If maxtime is
        negative, waits forever.  Returns true, if job finished.
        """
        pause = 0.2
        lapsed = 0.0
        while not search_job.is_done():
            time.sleep(pause)
            lapsed += pause
            if maxtime >= 0 and lapsed > maxtime:
                break
        return search_job.is_done()

    def wait_for_search(self, search_query):
        try:
            enabled_consumers_search_job = ITOAInterfaceUtils.run_search(self.session_key, self.logger, search_query)
            if not self.wait_for_job(enabled_consumers_search_job, 10):
                raise Exception("Search for enabled actions consumer Modular Inputs timed out.")
            rr = results.ResultsReader(enabled_consumers_search_job.results())
            return rr
        except Exception as e:
            self.logger.error(
                'Error occurred while searching for list of enabled actions consumer Modular Inputs: %s', e)
            return []

    def get_all_enabled_action_consumers(self):
        """
        It fetches all the enabled consumers via a search job, extracts the consumer name, fetches the consumer IDs
        for those consumers from KV Store, stores the map of consumer name and their corresponding IDs in class level
        variable.
        """
        results = self.wait_for_search(self.enabled_consumer_search)
        new_consumer_ids = []
        for r in results:
            # sample config_id:
            # 'https://127.0.0.1:8089/servicesNS/nobody/SA-ITOA/configs/conf-inputs/itsi_notable_event_actions_queue_consumer%3A%252F%252Falpha'
            config_id = r['id']
            # config_id needs to be parsed to extract the consumer name and to unquote the consumer name
            parsed = urlparse(config_id)
            consumer_name = parsed.path.rpartition('/')[2]
            # consumer name has to be unquoted twice because of the double slashes in the consumer name
            # sample consumer name: itsi_notable_event_actions_queue_consumer://alpha
            consumer_name = unquote(unquote(consumer_name))

            # If it doesn't contain the consumer name, which is followed by "://" then this is not actual consumer
            if (":/" in consumer_name) is False:
                self.logger.debug(':/ is not present in consumer_name. consumer_name=%s', consumer_name)
                continue

            self.logger.debug('Enabled consumer=%s', consumer_name)
            if consumer_name in self.consumer_id_map:
                new_consumer_ids.append(self.consumer_id_map[consumer_name])
            else:
                # fetch the consumer ids from KV Store
                self.fetch_consumer_registration_objects_from_kvstore(object_type='consumer_registration',
                                                                      collection_name='itsi_notable_event_actions_queue')
                """
                Even after fetching the data from KV Store, if Modular Input ID is not found for the consumer,
                then log an error.
                """
                if consumer_name in self.consumer_id_map:
                    new_consumer_ids.append(self.consumer_id_map[consumer_name])
                else:
                    self.logger.error('Failed to get modular input id for consumer: %s', consumer_name)
        self.logger.debug('list of enabled consumer ids fetched from enabled_notable_event_action_consumers_search: %s.'
                          ' consumer_id_map=%s',
                          new_consumer_ids, self.consumer_id_map)
        if len(new_consumer_ids) == 0:
            self.logger.error('No enabled consumers found')
        self.enabled_modular_input_ids = new_consumer_ids

    def fetch_consumer_registration_objects_from_kvstore(self, object_type='consumer_registration',
                                                         collection_name=final_queue_collection):
        """
        It fetches the consumer names and consumer IDs from the KV Store. It stores the
        map of consumer names and the corresponding consumer IDs in class level variable.
        """
        self.logger.info('About to fetch consumer_registration objects')
        try:
            storage_interface = ITOAStorage(collection=collection_name)
            objects = storage_interface.get_all(
                self.session_key, self.owner, object_type,
                current_user_name=self.owner
            )

            self.logger.info('Fetched %s consumer_registration objects from collection=%s. objects=%s',
                             len(objects), collection_name, objects)

            if not objects or len(objects) == 0:
                return

            for obj in objects:
                if 'consumer_name' in obj and '_key' in obj:
                    self.consumer_id_map[obj['consumer_name']] = obj['_key']
                    self.logger.info('consumer_name=%s  modular_input_id=%s', obj['consumer_name'], obj['_key'])
                else:
                    self.logger.error('Invalid consumer_registration object found. Either _key or consumer_name is '
                                      'missing. obj=%s', obj)
        except Exception as e:
            self.logger.error('Error in fetching consumer ids from KV Store. Exception: %s', e)

    def consume_forever(self):
        """
        Consume forever for action objects: read them from the tmp action queue, assign consumers to them, store them
        in the final action queue, mark them for deletion in the tmp action queue
        At the specified refresh interval, get the list of latest enabled Modular Inputs
        At the specified delete interval, delete the objects marked for deletion from the tmp action queue
        """
        # refresh rate to get the list of latest enabled consumer Modular Inputs
        refresh_time = time.time()
        delete_time = time.time()
        try:
            while True:
                count = self.consume_once()
                # sleep for a second if no data was consumed.
                if not count:
                    time.sleep(1)
                if time.time() - refresh_time >= self.consumer_refresh_interval:
                    # reset refresh time
                    refresh_time = time.time()
                    # get the latest list of all enabled action consumers
                    self.get_all_enabled_action_consumers()
                if time.time() - delete_time >= self.delete_objects_interval:
                    # reset delete time
                    delete_time = time.time()
                    # Asynchronously delete the objects marked for deletion
                    asyncio.run(self.async_delete_objects())
                time.sleep(self.read_delay_time)
        except Exception as e:
            if "Splunkd daemon is not responding: " not in str(e):
                self.logger.exception('Exception when reading and assigning consumers to actions objects. "%s"', e)
            raise  # modular input should catch this and log

    def consume_once(self, objecttype='action_queue_job'):
        """
        Consume batch_size number of action objects from itsi_notable_event_actions_queue_tmp.
        Consumption entails:
            1. read the actions (objects) from itsi_notable_event_actions_queue_tmp
            2. Assign consumer IDs to those action objects
            3. Queue those action objects to itsi_notable_event_actions_queue
            4. Mark those objects for deletion in itsi_notable_event_actions_queue_tmp.
               Those objects will be later deleted asynchronously at the specified interval in this Mod Input.

        In case there is any exception encountered in any of the above steps, the action objects will not be marked for
        deletion in the tmp queue. This is so we can attempt to process those objects in the next iteration.

        @rtype: int
        @return: count of objects that were consumed. If an error is encountered while consuming, then return 0.
        """
        objects = []
        initial_start = time.time()
        start = time.time()
        # Read the action objects from the tmp queue
        try:
            tmp_queue_storage = ITOAStorage(collection=self.tmp_queue_collection)
            filter_data = {'to_be_deleted': {'$ne': 1}}

            objects = tmp_queue_storage.get_all(
                self.session_key,
                self.owner,
                objecttype,
                sort_key="create_time",
                sort_dir="asc",
                filter_data=filter_data,
                limit=self.batch_size,
                current_user_name=self.owner
            )
            if not objects:
                self.logger.debug('No actions found')
                return 0
            self.logger.info("number_of_objects_fetched=%s", len(objects))
        except Exception as e:
            self.logger.error('Unable to fetch objects from collection=%s. Will not be be able to assign consumers to '
                              'actions', self.tmp_queue_collection)
            self.logger.exception(e)
            return 0
        end = time.time()
        self.logger.debug("time_to_fetch_objects=%s seconds, number_of_objects=%s", round(end - start, 2),
                          len(objects))

        start = time.time()
        # Assign consumer IDs to the actions and batch save those actions in the regular actions queue collection
        try:
            objects = self.assign_consumer_ids(objects)
            queue_storage = ITOAStorage(collection=self.final_queue_collection)
            queue_storage.batch_save(self.session_key, self.owner, objects, objecttype)
        except Exception as e:
            self.logger.error('Unable to assign consumer IDs to the actions or unable to save the objects '
                              'in the actions queue kvstore collection. collection=%s', self.final_queue_collection)
            self.logger.exception(e)
            return 0
        end = time.time()
        self.logger.debug("time_to_save_objects=%s seconds, number_of_objects=%s", round(end - start, 2), len(objects))

        start = time.time()
        # Mark the objects for deletion in the tmp queue collection
        try:
            for o in objects:
                o['to_be_deleted'] = 1
            tmp_queue_storage = ITOAStorage(collection=self.tmp_queue_collection)
            tmp_queue_storage.batch_save(self.session_key, self.owner, objects, objecttype)
        except Exception as e:
            self.logger.error('Unable to to mark objects for deletion in the tmp actions queue. '
                              'collection=%s', self.tmp_queue_collection)
            self.logger.exception(e)
            return 0
        end = time.time()
        self.logger.debug("time_to_mark_objects_for_deletion=%s seconds, number_of_objects=%s",
                          round(end - start, 2), len(objects))

        last_end = time.time()
        self.logger.debug("time_to_complete=%s seconds, number_of_objects=%s", round(last_end - initial_start, 2),
                          len(objects))
        return len(objects) if objects else 0

    def assign_consumer_ids(self, objects):
        # Assign consumer IDs to actions in Round Robin manner
        for obj in objects:
            obj['id'] = self.enabled_modular_input_ids[self.current_consumer_id]
            if self.current_consumer_id == (len(self.enabled_modular_input_ids) - 1):
                self.current_consumer_id = 0
            else:
                self.current_consumer_id += 1
        return objects

    async def delete_objects(self, objecttype='action_queue_job'):
        # Read the action objects from the tmp queue
        try:
            filter_data = {'to_be_deleted': 1}
            self.logger.info('About to delete objects from collection=%s. objecttype=%s filter_data=%s',
                             self.tmp_queue_collection, objecttype, filter_data)
            tmp_queue_storage = ITOAStorage(collection=self.tmp_queue_collection)

            tmp_queue_storage.delete_all(
                self.session_key,
                self.owner,
                objecttype,
                filter_data=filter_data,
                current_user_name=self.owner
            )
            # Since delete_all doesn't return anything, we don't know if the objects were successfully deleted or
            # not hence we can't log a success info log here :(
        except Exception as e:
            self.logger.error('Unable to delete objects from collection=%s. objecttype=%s filter_data=%s',
                              self.tmp_queue_collection, objecttype, filter_data)
            self.logger.exception(e)

    async def async_delete_objects(self, objecttype='action_queue_job'):
        await self.delete_objects(objecttype)


if __name__ == "__main__":
    worker = ActionConsumerAssigner()
    worker.execute()

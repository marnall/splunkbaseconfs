# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import logging

import time
import json

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

from ITOA.itoa_object import ItoaObject
from itsi.objects.itsi_entity import ItsiEntity
from itsi.objects.itsi_entity_discovery_search import ItsiEntityDiscoverySearch

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from SA_ITOA_app_common.splunklib.searchcommands import Configuration, GeneratingCommand, dispatch, Option, validators
from ITOA.setup_logging import setup_logging, InstrumentCall
from ITOA.saved_search_utility import SavedSearch
from itsi.csv_import.itoa_bulk_import_entity import ImportedEntity
from ITOA import itoa_common
from ITOA.itoa_common import SplunkUser
from user_access_errors import UserAccessError
from user_access_utils import UserAccess

logger = setup_logging("itsi_entity_discovery_search_cleaner.log", "itsi_entity_discovery_search_cleaner")
logger.info("Initialized entity discovery search cleaner log.")

CAPABILITY_ADMIN_ALL_OBJECTS = 'admin_all_objects'


@Configuration()
class CleanEntityDiscoverySearches(GeneratingCommand):

    entity_batch_size = Option(
        doc='''
                **Syntax:** **entity_batch_size=***<Integer>*
                **Description:** batch size to use when we are processing entities for cleanup''',
        require=False,
        validate=validators.Integer(),
    )
    search_ids = Option(
        doc='''
            **Syntax:** **search_ids=***<search id>,<search id..>*
            **Description:** list of search ids to clean up. If provided, only searches specified here will be used''',
        default='',
        require=False,
    )

    owner = 'nobody'
    current_user = 'nobody'

    discovery_search_kv_collections = [
        'itsi_bulk_import_entities_status_cache',
        'itsi_import_objects_cache',
        'itsi_entity_discovery_search'
    ]

    def __init__(self):
        super().__init__()
        self.transaction_id = None

        self._instrumentation = InstrumentCall(logger)
        self.user_specified_searches_to_clean = []
        self.req_source = 'entity_discovery_search_cleaner'

    def generate(self):
        try:
            with self._instrumentation.track(
                    'CleanEntityDiscoverySearches.generate'
            ) as transaction_id:
                self.transaction_id = transaction_id
                logger.info(f'tid={self.transaction_id} Cleaning up entity discovery searches')

                self.process_command_inputs()

                # if user specified search_ids to clean up, we will not look for other searches
                # this is useful in case some searches are not cleaned up through background process
                # i.e. a search is deleted from kv collections but was half removed in entities for whatever reason.
                if self.user_specified_searches_to_clean:
                    logger.info(f'tid={self.transaction_id} User specified searches to clean, '
                                f'they are: {self.user_specified_searches_to_clean}')
                    all_obsolete_searches = self.user_specified_searches_to_clean
                else:
                    # 1. find all the disabled searches ourselves
                    all_obsolete_searches = self.find_searches_to_clean()
                    logger.info(f'tid={self.transaction_id} User did not specify searches to clean. '
                                f'Found: {all_obsolete_searches}')

                # 2. generate search for finding all the matching entity_ids(bulk_get)
                # 3. use batches to process entity_ids in chunks (what happens if one fails?)
                # 3.1 check if any of the searches is in entity's list of searches, remove if found
                # 4. use batch_save to save updated entities
                if all_obsolete_searches:
                    self.scrub_entity_searches(all_obsolete_searches)

                    # 5. delete search from all the kv collection caches
                    self.delete_searches_from_caches(all_obsolete_searches)
                else:
                    logger.info(f'tid={self.transaction_id} No searches to clean.')

            data_to_return = {
                'tid': self.transaction_id,
                '_raw': 'Completed cleaning up obsolete entity discovery searches.',
                'searches': all_obsolete_searches,
                '_time': time.time()
            }
            logger.info(data_to_return)
            yield data_to_return
        except Exception as e:
            data_to_return = {
                'tid': self.transaction_id,
                '_raw': f'Completed cleaning up obsolete entity discovery searches with error. {e}',
                'log_level': 'ERROR',
                '_time': time.time()
            }
            logger.info(data_to_return)
            # Explicitly specify Exception message due to missing Python3 support in error_exit()
            self.error_exit(e, message=str(e))

    def is_user_capable(self):
        """Checking if the current user has appropriate capability to run the command. We need
        admin_all_objects in order to make sure we can 'see' ALL searches, including private ones
        from everyone.

        @rtype: bool
        @return: whether the current user is capable of running command
        """
        user_is_capable = False
        search_user = self.metadata.searchinfo.username
        try:
            user_is_capable = UserAccess.is_user_capable(
                search_user,
                CAPABILITY_ADMIN_ALL_OBJECTS,
                self.service.token,
                logger)
        except Exception as e:
            message = f'tid={self.transaction_id} Failed to check for user capability {CAPABILITY_ADMIN_ALL_OBJECTS}, {e}'
            logger.error(message)
            raise Exception(message)

        if user_is_capable:
            logger.info(f'tid={self.transaction_id} User has capability: {CAPABILITY_ADMIN_ALL_OBJECTS}')
        else:
            logger.info(f'tid={self.transaction_id} User is missing capability: {CAPABILITY_ADMIN_ALL_OBJECTS}')

        return user_is_capable

    def validate_user_access_before_running_command(self):
        '''Will check whether user meets following criteria:
        1. has admin_all_objects capability
        2. has itoa_admin role

        @raises: ItoaAccessDeniedError
        '''

        has_access = True
        access_error_msgs = []

        # validate user has required capability to proceed
        user_is_capable = self.is_user_capable()
        if not user_is_capable:
            has_access = False
            access_error_msgs.append(f'missing {CAPABILITY_ADMIN_ALL_OBJECTS} capability')

        # validate user also has itoa_admin role to proceed
        roles_for_current_user, all_roles_for_current_user = SplunkUser.get_roles_for_user(
            self.current_user, self.service.token, logger)
        logger.info(f'tid={self.transaction_id}, roles_for_current_user={roles_for_current_user}, '
                    f'all_roles_for_current_user={all_roles_for_current_user}')
        if 'itoa_admin' not in all_roles_for_current_user:
            has_access = False
            access_error_msgs.append('missing itoa_admin role')

        if not has_access:
            # combine access errors
            combined_error = " and ".join(access_error_msgs)
            error_msg = f'tid={self.transaction_id} Access denied. Current user is {combined_error}.'
            logger.error(error_msg)
            raise Exception(error_msg)

    def process_command_inputs(self):
        """process the command line inputs provided by the user.

        :return: fill in search ids that were provided by the user in self
        """
        logger.info(f'tid={self.transaction_id} Input Params: '
                    f'entity_batch_size={self.entity_batch_size}, search_id={self.search_ids}')

        # validate user has proper access to run the command
        self.validate_user_access_before_running_command()

        # validate and massage search_ids
        user_specified_searches_to_clean = self.get_user_provided_searches()
        self.user_specified_searches_to_clean = self.validate_and_massage_user_specified_search_ids(
            user_specified_searches_to_clean)

        # validate and massage entity_batch_size
        default_batch_size = itoa_common.get_object_batch_size(self.service.token)
        config_entity_batch_size = itoa_common.get_object_batch_size(self.service.token, 'entity')
        if self.entity_batch_size is None:
            self.entity_batch_size = default_batch_size
            logger.info(f'tid={self.transaction_id} No entity_batch_size specified. '
                        f'Will use default batch size from config: {default_batch_size}')
        elif self.entity_batch_size > config_entity_batch_size or self.entity_batch_size < 0 or \
                self.entity_batch_size == 0:
            logger.warn(f'tid={self.transaction_id} Invalid entity_batch_size specified: {self.entity_batch_size}. '
                        f'Will use default entity batch size from config: {config_entity_batch_size}')
            self.entity_batch_size = config_entity_batch_size

    def validate_and_massage_user_specified_search_ids(self, input_search_ids):
        """validate and massage the user specified search ids.

        It gets all active discovery searches first. if any active searches are found in the input list, they will be
        removed from the input

        :param input_search_ids: Get the active discovery searches
        :return: A set of search ids that are not active
        """
        if not input_search_ids:
            return input_search_ids

        active_discovery_searches = self.get_active_discovery_searches()
        if not active_discovery_searches:
            return input_search_ids

        active_searches_in_input = [search for search in input_search_ids if search in active_discovery_searches]
        logger.warn(f'tid={self.transaction_id} Active searches specified: '
                    f'{active_searches_in_input}. They will be skipped')
        filtered_searche_ids = list(set(input_search_ids) - set(active_searches_in_input))
        return filtered_searche_ids

    def get_active_discovery_searches(self):
        """returns a list of all active entity discovery searches.

        :return: A list of active discovery searches
        """
        active_discovery_searches = SavedSearch.get_all_searches(
            self.service.token,
            namespace='-',
            owner='-',
            search='action.itsi_import_objects=1 AND disabled=0'  # only entity discovery searches
        )
        search_ids = [search.name for search in active_discovery_searches]
        return search_ids

    def find_searches_to_clean(self):
        """finds all discovery searches that are no longer active or deleted.

        :return: A list of searches that are no longer in use
        """
        # 1. get a list of ALL discovery searches (all known discovery searches)
        # 2. check the searches in the discovery search kv, see if any of them are NOT in the list of all known
        # discovery searches → these are the deleted searches

        with self._instrumentation.track(
                'CleanEntityDiscoverySearches.find_searches_to_clean',
                transaction_id=self.transaction_id
        ):
            discovery_searches = SavedSearch.get_all_searches(
                self.service.token,
                namespace='-',
                owner='-',
                search='action.itsi_import_objects=1'   # only entity discovery searches
            )

            # find all the discovery searches we currently have (disabled or not)
            all_search_ids = []
            if discovery_searches:
                all_search_ids = [search.name for search in discovery_searches]

            # filter for 'disabled' searches
            inactive_search_ids = [search.name for search in discovery_searches if
                                   SavedSearch.is_search_inactive(search)]
            logger.debug(f'tid={self.transaction_id} '
                         f'All inactive searches ({len(inactive_search_ids)}): {inactive_search_ids}')

            # getting searches from discovery search cache (ones which discovered entities)
            kv_entity_discovery_search = ItsiEntityDiscoverySearch(
                self.service.token, self.current_user)
            try:
                cached_searches = kv_entity_discovery_search.get_bulk(self.owner,
                                                                      fields=['_key'])
                logger.debug(f'tid={self.transaction_id} Found cached searches: {cached_searches}')
            except Exception as ex:
                # if we hit exception loading from cache, we should just give up
                logger.exception(f'tid={self.transaction_id} caught exception {ex}')
                raise ex

            cached_search_ids = []
            if cached_searches:
                cached_search_ids = [search['_key'] for search in cached_searches]

            # finding inactive and deleted searches based on what's in the cache
            set_all_discovery_search_ids = set(all_search_ids)
            set_cached_search_ids = set(cached_search_ids)
            deleted_searches = list(set_cached_search_ids - set_all_discovery_search_ids)
            inactive_cached_searches = list(set(cached_search_ids).intersection(inactive_search_ids))

            obsolete_searches = list(set(inactive_cached_searches + deleted_searches))
            logger.debug(f'tid={self.transaction_id} Found '
                         f'obsolete searches ({len(obsolete_searches)}): {obsolete_searches}')
            return obsolete_searches

    def scrub_entity_searches(self, all_obsolete_searches):
        """Used to remove obsolete searches from the entities that were discovered
        by these searches

        The function iterates through entities in batches and remove any references to those obsolete searches.
        It will continue until processed all the entities that reference an obsolete search.
        By the end of this, all the entities are updated and persisted with updated status

        :param all_obsolete_searches: all the searches to be removed from the entities
        """
        if not all_obsolete_searches:
            return

        chunk_size = self.entity_batch_size
        batch_count = 0
        total_entities_processed = 0

        with self._instrumentation.track(
                'CleanEntityDiscoverySearches.scrub_entity_searches',
                transaction_id=self.transaction_id, owner=self.owner
        ):
            # Create a search filter that looks for any entities that reference any of
            # the obsolete searches.
            # How big can the filter_data be? how many searches can be passed in the filter?
            # looks like allowable size can be between 2k-8k, if we go with 5k, it can accommodate about
            # 100 searches in the query
            filter_for_searches = self.construct_filter_using_search_ids(all_obsolete_searches)
            logger.debug(f'tid={self.transaction_id} '
                         f'Object size of filter: {CleanEntityDiscoverySearches.get_nested_size(filter_for_searches)}')

            while True:
                logger.debug(f'tid={self.transaction_id} batch_count={batch_count}, batch_size={chunk_size}')

                try:
                    entities = self.find_entities_to_clean(filter_for_searches,
                                                           batch_size=chunk_size
                                                           # not needed because as we remove the searches, the next query
                                                           # will no longer include the searches we updated. so the size
                                                           # of total search will become smaller and smaller with each
                                                           # subsequent query
                                                           # skip_count=batch_count * chunk_size
                                                           )
                    logger.debug(f'tid={self.transaction_id} '
                                 f'Object size of entities: {CleanEntityDiscoverySearches.get_nested_size(entities)}')
                except Exception as ex:
                    logger.exception(f'tid={self.transaction_id} Encountered exception while '
                                     f'find_entities_to_clean. {ex}')
                    break

                if not entities:
                    logger.info(f'tid={self.transaction_id} No matching entities returned.')
                    break

                # remove obsolete searches from all the entities in this batch
                entities = self.cleanup_searches_from_entities(entities, all_obsolete_searches)

                try:
                    # persist entities after cleaning out the searches
                    self.save_cleansed_entities(entities)
                except Exception as ex:
                    logger.exception(f'tid={self.transaction_id} Encountered exception while saving entities. '
                                     f'Will bail out now. Total entities processed '
                                     f'so far: {total_entities_processed} {ex}')
                    break

                batch_count += 1
                total_entities_processed += len(entities)
                logger.debug(f'tid={self.transaction_id} Total entities processed so far: {total_entities_processed}')

                if len(entities) < chunk_size:
                    logger.info(f'tid={self.transaction_id} We are done. No more matching entities.'
                                f'Total entities processed so far: {total_entities_processed}')
                    break

    def cleanup_searches_from_entities(self, entities, all_obsolete_searches):
        """Cleans obsolete searches from all incoming entities

        It takes in a list of entities and a list of all obsolete searches, then iterates through each entity.
        For each entity, it calls cleanup_searches_from_one_entity to remove any obsolete searches from that
        entity's search history.

        :param entities: incoming entities we need to go through and clean searches for
        :param all_obsolete_searches: all the obsolete search ids
        :return: The entities after it cleans up the searches
        """
        entity_ids = []
        with self._instrumentation.track(
                'CleanEntityDiscoverySearches.cleanup_searches_from_entities',
                transaction_id=self.transaction_id, owner=self.owner
        ):
            for entity in entities:
                self.cleanup_searches_from_one_entity(entity, all_obsolete_searches)
                entity_ids.append(entity.get('_key', ''))

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'tid={self.transaction_id} Cleaned up ({len(entity_ids)}): {entity_ids}')
            else:
                logger.info(f'tid={self.transaction_id} Cleaned up ({len(entity_ids)}) entities.')

        return entities

    def cleanup_searches_from_one_entity(self, entity, all_obsolete_searches):
        """remove obsolete searches from an entity's status breakdown.

        update entity with any obsolete search removed from its status breakdown.
        also recalculates the overall status for the entity after removing any obsolete search.

        :param entity: incoming entity to clean
        :param all_obsolete_searches: all the obsolete searches
        :return: The entity with the searches_to_remove removed
        """
        saved_search_names_for_entity = list(entity.get('_status', {}).get('breakdown', {}).keys())

        searches_to_remove = self.extract_obsolete_searches_from_list(saved_search_names_for_entity,
                                                                      all_obsolete_searches)

        logger.debug(f'tid={self.transaction_id} entity={entity.get("_key", "")} '
                     f'saved_search_names={saved_search_names_for_entity}'
                     f'searches_to_remove={searches_to_remove}')

        if searches_to_remove:
            status_dict = {k: v
                           for k, v in entity['_status']['breakdown'].items()
                           if k not in searches_to_remove}

            # recalculate status
            status_repr = ImportedEntity.get_status_storage_repr(status_dict)
            entity['_status'] = status_repr

            # remove _itsi_entity_status_lookups so it will get refilled during 'save' based on
            # updated _status
            if entity.get('_itsi_entity_status_lookups'):
                entity.pop('_itsi_entity_status_lookups')

        return entity

    def extract_obsolete_searches_from_list(self, original_search_list, all_obsolete_searches):
        """extract obsolete search from the original_search_list

        :param original_search_list: list of searches containing one or more obsolete searches
        :param all_obsolete_searches: list of searches that are no longer active
        :return: A list of searches that have been identified as obsolete from the original search list
        """
        obsolete_searches_in_original = []
        if not all_obsolete_searches or not original_search_list:
            return obsolete_searches_in_original

        obsolete_searches_in_original = [s for s in all_obsolete_searches if s in original_search_list]
        return obsolete_searches_in_original

    def find_entities_to_clean(self, filter_for_searches, batch_size=None, skip_count=None):
        """find entities that need their searches to be cleaned.

        :param filter_for_searches: Query filter with all the obsolete searches
        :param batch_size: Limit the number of entities returned in a single batch
        :param skip_count: Skip a certain number of entities
        :return: A list of entities that match the search criteria
        """
        with self._instrumentation.track(
                'CleanEntityDiscoverySearches.find_entities_to_clean',
                transaction_id=self.transaction_id, owner=self.owner
        ):
            entities_list = []
            itsi_entity = ItsiEntity(self.service.token, self.current_user)

            try:
                entities_list = itsi_entity.get_bulk(self.owner,
                                                     filter_data=filter_for_searches,
                                                     limit=batch_size,
                                                     skip=skip_count,
                                                     req_source=self.req_source,
                                                     replace_raw_status=False,
                                                     transaction_id=self.transaction_id
                                                     )
            except Exception as ex:
                logger.exception(f'tid={self.transaction_id} Encountered exception doing get_bulk on entities. {ex}')
                raise ex

            return entities_list

    def construct_filter_using_search_ids(self, searches):
        """Given a list of search ids and returns a filter that can be
        used to find all entities with those search ids.

        :param searches: a list of searche ids
        :return: A filter
        """
        search_filter_list = []

        not_null_expression = {"$ne": None}

        cleaned_searches = [s.strip() for s in searches if s and s.strip()]

        for search in cleaned_searches:
            # sample query would be the following so it can find
            # records where the value could be just_now or a number or an object
            # { "_status.breakdown.ITSI Import Objects - OS": { "$ne": null} }
            query_key = f'_status.breakdown.{search}'
            not_null_filter = {query_key: not_null_expression}
            search_filter_list.append(not_null_filter)

        object_type_filter = {"object_type": "entity"}
        if len(search_filter_list) > 1:
            search_filter = {"$or": search_filter_list}
        else:
            search_filter = search_filter_list[0]

        final_filter = {"$and": [object_type_filter, search_filter]}

        logger.debug(f'tid={self.transaction_id} {json.dumps(final_filter)}')

        return final_filter

    def save_cleansed_entities(self, entities):
        """save the updated entities with their obsolete searches removed

        :param entities: Pass in the list of entities that we want to save
        """
        if not entities:
            return

        with self._instrumentation.track(
                'CleanEntityDiscoverySearches.save_cleansed_entities',
                transaction_id=self.transaction_id, owner=self.owner
        ):
            entity_ids = [entity.get('_key', '') for entity in entities]
            try:
                ItsiEntity(self.service.token,
                           self.current_user).save_batch(
                    owner=self.owner,
                    data_list=entities,
                    validate_names=False,
                    transaction_id=self.transaction_id
                )
                logger.info(f'tid={self.transaction_id} Just saved {len(entity_ids)} entities')
            except Exception as ex:
                logger.exception(f'tid={self.transaction_id} Failed to save {len(entity_ids)} entities: {ex}')
                raise ex

    def delete_searches_from_caches(self, obsolete_searches):
        """deletes the obsolete searches from the cache kv collection

        :param obsolete_searches: obsolete search ids
        """

        with self._instrumentation.track(
                'CleanEntityDiscoverySearches.delete_searches_from_caches',
                transaction_id=self.transaction_id, owner=self.owner
        ):
            for collection_name in CleanEntityDiscoverySearches.discovery_search_kv_collections:
                entity_status_cache = ItoaObject(self.service.token,
                                                 self.current_user,
                                                 collection_name,
                                                 collection_name=collection_name,
                                                 title_validation_required=False)
                search_ids_filter = ItoaObject.get_filter_data_for_keys(obsolete_searches)

                try:
                    entity_status_cache.delete_bulk(self.owner,
                                                    filter_data=search_ids_filter,
                                                    req_source=self.req_source,
                                                    transaction_id=self.transaction_id)
                except Exception as ex:
                    logger.exception(f'tid={self.transaction_id} Failed to clean searches from {collection_name} {ex}')

    def get_user_provided_searches(self):
        """takes the search_ids parameter from the request and returns a list of
        search IDs.
                :param self: Refer to the object itself
        :return: A list of search ids
        """
        logger.info(f'tid={self.transaction_id} self.search_ids = {self.search_ids}')
        if not self.search_ids or len(self.search_ids.strip()) == 0:
            return []

        searches = self.search_ids.split(",")

        # Strip any leading or trailing whitespace from each search
        searches = [s.strip() for s in searches]

        # Remove any empty search
        searches = [s for s in searches if s]

        logger.info(f'tid={self.transaction_id} Input search_ids={searches}')
        return searches

    @staticmethod
    def get_nested_size(obj):
        """roughly calculates the size of an object for debugging

        :param obj: object we want to get the size of
        :return: The size of the object in bytes
        """
        size = sys.getsizeof(obj)
        if isinstance(obj, (list, tuple, set)):
            size += sum(CleanEntityDiscoverySearches.get_nested_size(item) for item in obj)
        elif isinstance(obj, dict):
            size += sum(CleanEntityDiscoverySearches.get_nested_size(k)
                        + CleanEntityDiscoverySearches.get_nested_size(v) for k, v in obj.items())
        return size


dispatch(CleanEntityDiscoverySearches, sys.argv, sys.stdin, sys.stdout, __name__)

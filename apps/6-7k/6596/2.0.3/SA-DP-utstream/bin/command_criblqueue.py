#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: command_criblqueue.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import time
import re
import uuid
import traceback
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from splunklib import results, client

from _env import CONFIG

from utstream_template.factory_dataset import DatasetFactory

from utstream.service_collection_handler import CollectionHandlerService
from utstream.helper_collection_entry_replay_job import HelperCollectionEntryReplayJob

from utstream_template.factory_logger import Logger

@Configuration()
class CriblQueue(GeneratingCommand):

    _key = Option(require=False)
    index = Option(require=False)
    host = Option(require=False)
    sourcetype = Option(require=False)
    earliest = Option(require=False)
    latest = Option(require=False)

    utstream_discovery_inventory_collection = ""
    utstream_replay_jobs_collection = ""
    utstream_discovery_results_collection = ""
    search_results_info = ""
    uuid = ""

    app_owner = "admin"
    logger = None

    def generate(self):
        self.uuid = str(uuid.uuid4())
        self.logger = Logger('command', self.uuid)

        dataset_factory = DatasetFactory( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key )
        self.dataset_confs = dataset_factory.get_dataset_service( "confs" )
        self.dataset_search = dataset_factory.get_dataset_service( "search" )

        self._validate_args()
        self._load_config()

        try:            
            self.uuid = uuid.uuid4()
            self.logger.info("action=\"\"create\"\",status=\"success\",queue_job=\"{}\",result=\"created\",cribl_discovery_inventory_collection=\"{}\",cribl_replay_jobs_collection=\"{}\",cribl_discovery_results_collection=\"{}\",user=\"{}\"".format(
                str(self.uuid), self.utstream_discovery_inventory_collection, self.utstream_replay_jobs_collection, self.utstream_discovery_results_collection, self._metadata.searchinfo.username))

            count = self.distinct()
            self.logger.info("action=\"\"done\"\",status=\"success\",queue_job=\"{}\",result=\"done\"".format(str(self.uuid)))

            yield {
                "_raw": f"done, added {count} entries"
            }
            
        except Exception as e:
            self.logger.error("action=\"\"failed\"\",status=\"failure\",queue_job=\"{}\",result=\"failed\",error=\"{}\"".format(str(self.uuid), e))
            self.logger.error(traceback.format_exc())
            raise e

    def _load_config(self):
        self.utstream_discovery_inventory_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_discovery_inventory_collection']
        self.utstream_discovery_results_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_discovery_results_collection']
        self.utstream_replay_jobs_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_replay_jobs_collection']
        self.utstream_replay_results_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_replay_results_collection']

        self.cribl_discovery_inventory_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_discovery_inventory_collection, self.uuid)
        self.cribl_discovery_results_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_discovery_results_collection, self.uuid)
        self.cribl_replay_jobs_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_replay_jobs_collection, self.uuid)
        self.cribl_replay_results_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_replay_results_collection, self.uuid)
            
    def _validate_args(self):
        # Check if _key is given
        if self._key is None or self._key == "":
            raise Exception( "_key required")

    def distinct(self) -> int:
        keys = [x.strip(' ') for x in self._key.split(",")]
        self.logger.debug("action=\"\"start\"\",status=\"success\",queue_job=\"{}\",key_count=\"{}\"".format(str(self.uuid), len(keys)))

        # Get all indexes the user is allowed to access for access control
        allowed_indexes = []
        index_seach = "| eventcount summarize=false index=* index=_* | dedup index | fields index"
        for index in self.dataset_search.run_blocking_search(index_seach, 0, int(time.time())):
            if not isinstance(index, results.Message):
                allowed_indexes.append(index['index'])

        # Split keys into batches of 1000
        batches = [keys[i:i + 1000] for i in range(0, len(keys), 1000)]
        entries = 0

        for batch in batches:
            self.logger.debug("action=\"\"start\"\",status=\"success\",queue_job=\"{}\",key_count=\"{}\",batch_count=\"{}\"".format(str(self.uuid), len(keys), len(batches)))
            entries += self._distinct_handle_batch(batch, allowed_indexes)
        return entries

    def _distinct_handle_batch(self, keys: list, allowed_indexes) -> int:

        # Get CollectionEntryDiscoveryResult for every _key
        discovery_result_objects = self.cribl_discovery_results_handler.get_entries_query("{\"$or\": [" + ",".join(["{\"_key\":\"" + key + "\"}" for key in keys]) + "]}")
        discovery_result_sources = [result['cribl_source'] for result in discovery_result_objects]
        discovery_result_indexes = set([result['index'] for result in discovery_result_objects])

        # Check if there are any not allowed indexes in the list
        illegal_indexes = []
        for index in discovery_result_indexes:
            if index not in allowed_indexes:
                illegal_indexes.append(index)

        # Check if tere are any illegal indexes given and remove objects for theese indexes
        if len(illegal_indexes) > 0:
            discovery_result_objects_checked = [o for o in discovery_result_objects if o['index'] not in illegal_indexes]
            self.logger.warning(f"action=\"access_control\",status=\"access_denied\",illegal_indexes=\"{illegal_indexes}\",original_count=\"{len(discovery_result_objects)}\",allowed_count=\"{len(discovery_result_objects_checked)}\"")
            if len(discovery_result_objects_checked) == 0:
                raise PermissionError("No allowed index given")
            discovery_result_objects = discovery_result_objects_checked
        
        # Get query with all sources to be staged
        sources_query = "{\"$or\": [" + ",".join(["{\"cribl_source\":\"" + source + "\"}" for source in discovery_result_sources]) + "]}"

        # Get all entries from cribl_replay_jobs with the same cribl_source
        cribl_replay_jobs_conflicts = self.cribl_replay_jobs_handler.get_entries_query(sources_query)

        # Get all entries from cribl_replay_results with the same cribl_source
        cribl_replay_results_conflicts = self.cribl_replay_results_handler.get_entries_query(sources_query)

        # Check for conflicts and remove them 
        if len(cribl_replay_jobs_conflicts) > 0 or len(cribl_replay_results_conflicts) > 0:
            cleaned_discovery_result_objects = []

            conflicting_sources = {}
            for c in cribl_replay_jobs_conflicts:
                conflicting_sources[f"{c['cribl_source']}::{c['instance']}::{c['cribl_collector']}"] = True
            for c in cribl_replay_results_conflicts:
                conflicting_sources[f"{c['cribl_source']}::{c['instance']}::{c['cribl_collector']}"] = True

            for discovery_result_object in discovery_result_objects:
                source = discovery_result_object['cribl_source']
                instance = discovery_result_object['instance']
                cribl_collector = discovery_result_object['cribl_collector']

                if f"{source}::{instance}::{cribl_collector}" in conflicting_sources:
                    continue
                else:
                    cleaned_discovery_result_objects.append(discovery_result_object)
            discovery_result_objects = cleaned_discovery_result_objects

        # Add to stage
        entries = []
        for discovery_result_object in discovery_result_objects:
            entries.append(HelperCollectionEntryReplayJob(
                discovery_result_object['instance'],
                discovery_result_object['index'],
                discovery_result_object['host'],
                discovery_result_object['sourcetype'],
                discovery_result_object['filename'],
                discovery_result_object['cribl_source'],
                discovery_result_object['cribl_size'],
                discovery_result_object['cribl_collector'],
                discovery_result_object['cribl_discovery_job'],
                discovery_result_object['earliest'],
                discovery_result_object['latest'],
                self._metadata.searchinfo.username,
                str(self.uuid),
                ""
            ))

        self.cribl_replay_jobs_handler.add_entries(entries)
        self.cribl_replay_jobs_handler.sync_changes()

        return len(entries)


    def _get_time_from_source(self, cribl_source):
        regex = "^[^\/]+\/(?P<year>[^\/]+)\/(?P<month>[^\/]+)\/(?P<day>[^\/]+)\/(?P<hour>[^\/]+)"
        match = re.search(regex, cribl_source, re.IGNORECASE)

        if match:
            year = int(match.group('year'))
            month = int(match.group('month'))
            day = int(match.group('day'))
            hour = int(match.group('hour'))
            epoch = datetime(year, month, day, hour).timestamp()
            return epoch, epoch + 86400
        else:
            self.logger.error("action=\"get_time_from_source\",status=\"error\",result=\"failed\",queue_job=\"{}\",cribl_source=\"{}\"".format(
                str(self.uuid), cribl_source))
            return 0, int(time.time())


dispatch(CriblQueue, sys.argv, sys.stdin, sys.stdout, __name__)

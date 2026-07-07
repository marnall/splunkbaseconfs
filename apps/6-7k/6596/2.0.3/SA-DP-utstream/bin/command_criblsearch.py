#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: command_criblsearch.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals
from argparse import ArgumentError
import os
import sys
import time
import traceback
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from _env import CONFIG

from utstream_template.factory_dataset import DatasetFactory

from utstream.service_collection_handler import CollectionHandlerService
from utstream.helper_collection_entry_discovery_job import HelperCollectionEntryDiscoveryJob

from utstream_template.factory_logger import Logger

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from splunklib import results, client

@Configuration()
class CriblSearch(GeneratingCommand):

    index = Option(require=True)
    sourcetype = Option(require=True)
    host = Option(require=True)
    instance = Option(require=True)
    collector = Option(require=True)
    alert_action = Option(require=False)

    app_owner = "admin"
    utstream_discovery_jobs_collection = ""
    logger = None

    def generate(self):
        try:
            self.uuid = str(uuid.uuid4())
            self.logger = Logger('command', self.uuid)

            # Set up API service and all required variables
            dataset_factory = DatasetFactory( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key )
            self.dataset_confs = dataset_factory.get_dataset_service( "confs" )
            self.dataset_search = dataset_factory.get_dataset_service( "search" )

            self.utstream_discovery_jobs_collection = CONFIG["UTSTREAM_COLLECTIONS"]["utstream_discovery_jobs_collection"]

            search_et = -1
            search_lt = -1        

            try:
                search_et = int(self._metadata.searchinfo.earliest_time)
            except:
                search_et = 0

            try:
                search_lt = int(self._metadata.searchinfo.latest_time)
            except:
                search_lt = int(time.time())

            self.logger.info("action=\"create\",status=\"success\",result=\"created\",utstream_discovery_jobs_collection=\"{}\",index=\"{}\",sourcetype=\"{}\",host=\"{}\",earliest=\"{}\",latest=\"{}\",user=\"{}\"".format(self.utstream_discovery_jobs_collection, self.index, self.sourcetype, self.host, search_et, search_lt, self._metadata.searchinfo.username))

            # Either no indexes selected or all indexes not allowed
            self._handle_index_access_control()
            if not self.selected_indexes:
                self.logger.info("action=\"create\",status=\"error\",result=\"no_index_selected\"")
                yield {
                    '_serial': 0,
                    '_time': int(time.time()),
                    '_raw': "No index selected",
                }
                return

            # Format indexes, hosts and sourcetypes to a string
            indexes = self.selected_indexes
            hosts = [x.strip(' ') for x in self.host.split(",")]
            sourcetypes = [x.strip(' ') for x in self.sourcetype.split(",")]

            # Round times to MM:00 for earliest and MM:59 for latest
            search_et = int(search_et//60 * 60)
            search_lt = int(search_lt//60 * 60 + 59)
            
            if self.alert_action is None:
                self.alert_action = ""

            # Get CollectionHandlerService for discovery jobs
            collection_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_discovery_jobs_collection, self.uuid)
            job = HelperCollectionEntryDiscoveryJob(self.instance, self.collector, indexes, hosts, sourcetypes, self._metadata.searchinfo.username, search_et, search_lt, self.alert_action)

            # Add job to collection
            collection_handler.add_entry(job) 
            collection_handler.sync_changes()

            self.logger.info("action=\"done\",status=\"success\",result=\"done\",creation_time=\"{}\",user=\"{}\",index=\"{}\",sourcetype=\"{}\",host=\"{}\",earliest=\"{}\",latest=\"{}\"".format(job.creation_time, job.user, job.index, job.sourcetype, job.host, job.earliest, job.latest))

            yield {
                '_serial': 0,
                '_time': int(time.time()),
                '_raw': "Added to job list: {}".format(job.get_dict())
            }

        except Exception as e:
            self.logger.error("action=\"error\",status=\"error\",result=\"error\",error=\"{}\"".format(e))
            self.logger.error(traceback.format_exc())
            yield {
                '_serial': 0,
                '_time': int(time.time()),
                '_raw': "Error: {}".format(e)
            }

    def _handle_index_access_control(self):
        # Access control for indexes
        self.selected_indexes = []
        allowed_indexes = []
        index_seach = "| eventcount summarize=false index=* index=_* | dedup index | fields index"
        for result in self.dataset_search.run_blocking_search(index_seach, 0, int(time.time())):
            if not isinstance(result, results.Message):
                allowed_indexes.append(result['index'])

        # Set indexes to all allowed indexes in case of wildcard
        if "*" in self.index.split(","):
            self.selected_indexes = allowed_indexes
        else:
            # Loop through selected indexes and check if they are allowed
            for index in [x.strip(' ') for x in self.index.split(",")]:
                if index in allowed_indexes:
                    # Selected Index allowed
                    self.selected_indexes.append(index)
                else:
                    # Selected Index not allowed
                    self.logger.info("action=\"access_control\",status=\"error\",result=\"index_not_allowed\",requested_index=\"{}\",allowed_indexes=\"{}\"".format(index, ",".join(allowed_indexes)))

dispatch(CriblSearch, sys.argv, sys.stdin, sys.stdout, __name__)

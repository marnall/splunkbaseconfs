#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: modinput_cribldiscovery.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import json
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import *
from splunklib import client

from _env import CONFIG

from utstream_template.factory_dataset import DatasetFactory
from utstream_template.service_proxy import ProxyService

from utstream.service_cribl_instance import CriblInstanceService
from utstream.service_collection_handler import CollectionHandlerService

from utstream.helper_cribl_instance_interaction import HelperCriblInstanceInteraction
from utstream.helper_collection_entry_discovery_job import HelperCollectionEntryDiscoveryJob
from utstream.helper_collection_entry_discovery_result import HelperCollectionEntryDiscoveryResult
from utstream.helper_collection_entry_discovery_inventory import HelperCollectionEntryDiscoveryInventory
from utstream.helper_cribl_job_discovery import HelperCriblDiscoveryJob
from utstream.helper_cribl_job_runner import HelperCriblJobRunner

from utstream_template.factory_logger import Logger

class CriblDiscovery(Script):

    # Constants: so static that not kept in a config file
    app_owner = "admin"

    # Constants: set using Splunk API
    utstream_discovery_jobs_collection = ""
    utstream_discovery_inventory_collection = ""
    utstream_discovery_results_collection = ""
    utstream_discovery_results_collection = ""

    instance = ""
    uuid = ""

    # Cribl object
    cribl = None

    def get_scheme(self):
        scheme = Scheme("UTStream Discovery Orchestrator")
        scheme.description = ("Orchestrate Discovery Jobs in Cribl using UTStream")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        cribl_instance_arg = Argument("cribl_instance")
        cribl_instance_arg.data_type = Argument.data_type_string
        cribl_instance_arg.description = "Cribl Instance as configured in UTStream"
        cribl_instance_arg.required_on_create = True
        cribl_instance_arg.required_on_edit = True
        scheme.add_argument(cribl_instance_arg)

        cribl_collector_arg = Argument("cribl_collector")
        cribl_collector_arg.data_type = Argument.data_type_string
        cribl_collector_arg.description = "Cribl Collector to use for UTStream Operations"
        cribl_collector_arg.required_on_create = True
        cribl_collector_arg.required_on_edit = True
        scheme.add_argument(cribl_collector_arg)

        cribl_max_jobs_arg = Argument("cribl_max_jobs")
        cribl_max_jobs_arg.data_type = Argument.data_type_number
        cribl_max_jobs_arg.description = "Maximum number of jobs to run in parallel"
        cribl_max_jobs_arg.required_on_create = True
        cribl_max_jobs_arg.required_on_edit = True
        scheme.add_argument(cribl_max_jobs_arg)

        return scheme


    def validate_input(self, validation_definition):
        pass # passing as there is no input provided to this modular input


    def stream_events(self, inputs, ew):
        """
        Do the actual work

        """
        try:
            self.uuid = str(uuid.uuid4())
            self.logger = Logger("modinput", self.uuid)

            # Parse used provided inputs
            self._parse_args(inputs)
            dataset_factory = DatasetFactory( uuid=self.uuid, client=client, session_key = self.session_key, user="splunk-system-user" )

            self.dataset_environment = dataset_factory.get_dataset_service( "environment" )
            self.dataset_confs = dataset_factory.get_dataset_service( "confs" )
            self.dataset_messages = dataset_factory.get_dataset_service( "messages" )
            self.dataset_users = dataset_factory.get_dataset_service( "users" )
            self.dataset_search = dataset_factory.get_dataset_service( "search" )

            # Get configuration from Splunk API
            self._load_config()

            # Check if supposed to run on this host
            if not self.dataset_environment.get_shc_captain_or_standalone():
                self.logger.debug("instance=\"{}\",action=\"applicability_check\",result=\"false\",reason=\"not_shc_captain\"".format(self.instance))
                exit(0)
            self.logger.info("instance=\"{}\",action=\"applicability_check\",result=\"true\",reason=\"standalone_or_captain\"".format(self.instance))

            self.logger.info("instance=\"{}\",action=\"discovery\",status=\"success\",result=\"created\"".format(self.instance))
            
            discovery_jobs_query = "{ \"$and\": [ {\"instance\":\"" + self.instance + "\"}, {\"cribl_collector\":\"" + self.cribl_collector + "\"} ] }"
            self.discovery_job_collection_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_discovery_jobs_collection, self.uuid)
            discovery_jobs = self.discovery_job_collection_handler.get_entries_query(discovery_jobs_query)

            if len(discovery_jobs) == 0:
                self.logger.info("instance=\"{}\",action=\"discovery\",status=\"success\",result=\"done\",reason=\"no_jobs_found\"".format(self.instance))
                exit(0)
            self.logger.info("instance=\"{}\",action=\"discovery\",status=\"success\",result=\"starting\",reason=\"job_found\",count=\"{}\"".format(self.instance, len(discovery_jobs)))

            cribl_instance_service = CriblInstanceService( uuid=self.uuid, client=client, session_key=self.session_key, user="splunk-system-user" )
            cribl_object = cribl_instance_service.get_instance(self.instance)
            proxy_service = ProxyService( uuid=self.uuid, client=client, session_key=self.session_key, user="splunk-system-user" )
            cribl_interaction_helper = HelperCriblInstanceInteraction(instance=cribl_object, uuid=self.uuid, proxy=proxy_service.get_httpx_info())

            self.cribl = cribl_object.get_private_dict()

            dicovery_job_objects = []
            for discovery_job in discovery_jobs:
                dicovery_job_objects.append(HelperCollectionEntryDiscoveryJob(**discovery_job).get_cribl_discovery_job(self.uuid))

            # Get all handlers for kvstore
            self.discovery_result_collection_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_discovery_results_collection, self.uuid)
            self.replay_result_collection_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_replay_results_collection, self.uuid)
            self.discovery_inventory_collection_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_discovery_inventory_collection, self.uuid)

            # Create a job runner and run jobs
            job_runner = HelperCriblJobRunner(
                cribl_instance=self.cribl, 
                cribl_interaction_helper=cribl_interaction_helper, 
                uuid=self.uuid, 
                cribl_collector=self.cribl_collector, 
                cribl_max_jobs=self.cribl_max_jobs
            )
            done_jobs = job_runner.run_jobs(dicovery_job_objects)

            discovered_files = 0
            job: HelperCriblDiscoveryJob
            for job in done_jobs:

                # Check if job was successful
                if job.status != "finished":
                    self.logger.error("instance=\"{}\",action=\"discovery\",status=\"error\",result=\"{}\"".format(self.instance, job.status))
                    self.dataset_messages.insert(name=f"UTStream - Discovery Job - {job.instance} {job.collector} {job.status}", value=f"Discovery Job for instance \"{job.instance}\" and collector \"{job.collector}\" failed with status \"{job.status}\"", severity="error", roles=["admin", "utstream_admin", "utstream_writer"])
                    continue

                # Get results for jobs
                has_results, results = job.get_results()
                if has_results:
                    discovered_files += self._handle_discovery_results(job, results)
                
                # Handle entries in cribl_discovery_inventory and cribl_discovery_jobs
                self.discovery_inventory_collection_handler.add_entry(HelperCollectionEntryDiscoveryInventory(
                    self.instance,
                    job.collection_entry.index,
                    job.collection_entry.host,
                    job.collection_entry.sourcetype,
                    job.collection_entry.user,
                    job.collection_entry.earliest,
                    job.collection_entry.latest,
                    int(job.start_time),
                    int(job.end_time),
                    job.collector,
                    job.job_id,
                    job.collection_entry.alert_action
                ))
                self.discovery_job_collection_handler.delete_entry(job.collection_entry)

                # Write changes to kvstore
                self.discovery_inventory_collection_handler.sync_changes()
                self.discovery_job_collection_handler.sync_changes()

                # Inform user about progress
                if self.inform_user and job.collection_entry.alert_action == "":
                    subject = f"UTStream: Discovery job finished, found {discovered_files} files"
                    email = self.dataset_users.get_by_id( job.collection_entry.user )["email"]
                    if email != "" and email != "changeme@example.com":
                        email_search = f"| makeresults | sendemail to=\"{email}\" format=html subject=\"{subject}\""
                        self.dataset_search.run_blocking_search( search=email_search )
                    else:
                        self.dataset_messages.insert( name=f"UTStream - Email not found - {job.collection_entry.user}", value=f"UTStream: Discovery job finished, but no email address was found for user \"{job.collection_entry.user}\"", severity="warn", roles = ["utstream_admin", "admin"])
                elif job.collection_entry.alert_action == "":
                    message = f"UTStream: Discovery job for instance \"{job.instance}\" and collector \"{job.collector}\" started by \"{job.collection_entry.user}\" finished, found {discovered_files} files"
                    self.dataset_messages.insert(name=f"UTStream - Discovery Job - {job.instance} {job.collector} {job.start_time} {job.end_time}", value=message, severity="info", roles=["admin", "utstream_admin", "utstream_writer"])

            self.logger.info("instance=\"{}\",action=\"discovery\",status=\"success\",result=\"done\",jobs=\"{}\",discovered_files=\"{}\"".format(self.instance, len(done_jobs), discovered_files))

        except Exception as e:
            self.logger.exception("instance=\"{}\",action=\"discovery\",status=\"error\",result=\"{}\"".format(self.instance, str(e)))


    def _search_already_discovered_files(self, discovery_result_object_batch, cribl_sources):
        """
        Searches for already discovered files in the cribl_discovery_inventory collection based on the cribl_source 

        :param cribl_sources: List of cribl_sources to search for
        :return: None
        """
        if len(cribl_sources) == 0:
            return

        already_replayed_query = "{\"$or\": [" + ",".join(cribl_sources) + "]}"
        already_replayed_matching = self.replay_result_collection_handler.get_entries_query(query=already_replayed_query)

        # Add information to collection entry if cribl_source is already found in cribl_replay_results_collection
        
        if len(already_replayed_matching) > 0:
            self.logger.info(f"instance=\"{self.instance}\",action=\"discovery\",status=\"success\",result=\"searching\",reason=\"already_replayed\",matching_count=\"{len(already_replayed_matching)}\",total_count=\"{len(cribl_sources)}\"")

            # Build hashmap using cribl_source as key based on discovery_result_object_batch
            self.logger.debug(f"instance=\"{self.instance}\",action=\"discovery\",status=\"success\",result=\"searching\",reason=\"building_hashmap\"")
            cribl_source_hashmap = {}
            for discovery_result_object in discovery_result_object_batch:
                cribl_source_hashmap[discovery_result_object.cribl_source] = discovery_result_object
            self.logger.debug(f"instance=\"{self.instance}\",action=\"discovery\",status=\"success\",result=\"searching\",reason=\"building_hashmap_done\"")

            # Iterate over already_replayed_matching and add information to discovery_result_object_batch if cribl_source is found
            for already_replayed in already_replayed_matching:
                if already_replayed['cribl_source'] in cribl_source_hashmap:
                    self.logger.debug(f"instance=\"{self.instance}\",action=\"discovery\",status=\"success\",result=\"already_replayed_found\",reason=\"found_in_hashmap\",source=\"{already_replayed['cribl_source']}\"")
                    cribl_source_hashmap[already_replayed['cribl_source']].cribl_already_replayed = already_replayed['cribl_replay_job']


    def batch(self, iterable, n=1):
        l = len(iterable)
        for ndx in range(0, l, n):
            yield iterable[ndx:min(ndx + n, l)]


    def _handle_discovery_results(self, job, results):
        """
        Process resultrs returned by an discovery job

        :param job: HelperCriblDiscoveryJob object
        :param results: List of results returned by the discovery job

        :return: Number of files discovered by the job
        """
        self.logger.info("instance=\"{}\",action=\"discovery\",status=\"got_results\",job_id=\"{}\",expression=\"{}\",result_count=\"{}\"".format(self.instance, job.job_id, job.expression, len(results)))

        self.discovery_result_objects = []
        discovered_files = 0

        for result in results:

            discovered_files += 1
            result_json = json.loads(result)           
            self.discovery_result_objects.append(HelperCollectionEntryDiscoveryResult(
            self.instance,
            result_json['fields']['index'],
            result_json['fields']['host'],
            result_json['fields']['sourcetype'],
            result_json['fields']['filename'],
            int(job.time_start),
            int(job.time_end),
            result_json['source'],
            result_json['size'],
            result_json['collectorId'],
            job.job_id,
            ""
           ))

        self.logger.debug(f"instance=\"{self.instance}\",action=\"discovery\",status=\"starting_batching\"")
        for discovery_result_object_batch in self.batch(self.discovery_result_objects, 1000):
            cribl_sources = []
            discovery_result_object: HelperCollectionEntryDiscoveryResult
            for discovery_result_object in discovery_result_object_batch:
                cribl_sources.append("{\"cribl_source\":\"" + discovery_result_object.cribl_source + "\"}")
  
            self.logger.info("status=searching_for_already_replayed_batch")
            self._search_already_discovered_files(discovery_result_object_batch, cribl_sources)

        self.logger.debug(f"instance=\"{self.instance}\",action=\"discovery\",status=\"finished_batching\"")

        self.logger.debug(f"instance=\"{self.instance}\",action=\"discovery\",status=\"starting_insert\"")
        self.discovery_result_collection_handler.add_entries(self.discovery_result_objects)
        self.logger.debug(f"instance=\"{self.instance}\",action=\"discovery\",status=\"finished_insert\"")
        
        self.logger.debug(f"instance=\"{self.instance}\",action=\"discovery\",status=\"starting_sync\"")
        self.discovery_result_collection_handler.sync_changes()
        self.logger.debug(f"instance=\"{self.instance}\",action=\"discovery\",status=\"finished_sync\"")

        if job.collection_entry.alert_action != "":
            self._handle_alert_action(job, self.discovery_result_collection_handler)

        return discovered_files


    def _handle_alert_action(self, job, discovery_results_collection_handler):
        """
        Handles alert action for a result

        :param job: HelperCriblDiscoveryJob
        :param discovery_results_collection_handler: CollectionHandlerService
        :return: None
        """
        # Set query to get all _key for results be the discovery job
        job_id = job.job_id
        query = "{\"cribl_discovery_job\":\"" + job_id + "\"}"

        # Get all results for the job
        discovery_results = discovery_results_collection_handler.get_entries_query(query=query)

        # Get all keys
        keys = [discovery_result['_key'] for discovery_result in discovery_results]

        # Build splunk query
        splunk_query = "| criblqueue _key=\"" + ",".join(keys) + "\""

        # Queue all found _keys in a non blocking fashion
        self.dataset_search.run_non_blocking_search(splunk_query, 0 , 1)


    def _parse_args(self, inputs):
        """
        Parse arguments provided by the modular input

        :param inputs: Arguments provided by the modular input
        :return: None
        """
        self.input_name, self.input_items = inputs.inputs.popitem()
        self.session_key = self._input_definition.metadata["session_key"]
        self.instance = self.input_items["cribl_instance"]
        self.cribl_collector = self.input_items["cribl_collector"]
        self.cribl_max_jobs = int(self.input_items["cribl_max_jobs"])
        self.inform_user = self.input_items["cribl_inform_user"] in ["true", "True", "T", "t", "1", 1]
        
        self.logger.debug(f"instance=\"{self.instance}\",cribl_collector=action=\"{self.cribl_collector}\",parse_args\",status=\"success\",result=\"done\",input_items=\"{self.input_items}\"")


    def _load_config(self):
        """
        :return: None
        """
        self.utstream_discovery_jobs_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_discovery_jobs_collection']
        self.utstream_discovery_inventory_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_discovery_inventory_collection']
        self.utstream_discovery_results_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_discovery_results_collection']
        self.utstream_replay_results_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_replay_results_collection']
        self.utstream_replay_jobs_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_replay_jobs_collection']


if __name__ == "__main__":
    exitcode = CriblDiscovery().run(sys.argv)
    sys.exit(exitcode)

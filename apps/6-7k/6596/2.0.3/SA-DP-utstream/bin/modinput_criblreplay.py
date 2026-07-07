#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: modinput_criblreplay.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
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
from utstream.helper_collection_entry_replay_job import HelperCollectionEntryReplayJob
from utstream.helper_collection_entry_replay_result import HelperCollectionEntryReplayResult
from utstream.helper_cribl_job_replay import HelperCriblReplayJob
from utstream.helper_cribl_job_optimizer import HelperCriblJobOptimizer
from utstream.helper_cribl_job_runner import HelperCriblJobRunner

from utstream_template.factory_logger import Logger

class CriblReplay(Script):

    # Constants: so static that not kept in a config file
    app_owner = "admin"

    # Constants: set using Splunk API
    utstream_replay_jobs_collection = ""
    utstream_replay_results_collection = ""
    cribl_max_optimize = 1
    cribl_use_optimized = False
    uuid = ""
    
    # Splunk SDK object
    instance = ""

    def get_scheme(self):
        scheme = Scheme("UTStream Replay Orchestrator")
        scheme.description = ("Orchestrate Replay Jobs in Cribl using UTStream")
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

        cribl_max_optimize_arg = Argument("cribl_max_optimize")
        cribl_max_optimize_arg.data_type = Argument.data_type_number
        cribl_max_optimize_arg.description = "Maximum number of jobs to optimize into a single job"
        cribl_max_optimize_arg.required_on_create = True
        cribl_max_optimize_arg.required_on_edit = True
        scheme.add_argument(cribl_max_optimize_arg)

        cribl_use_optimized_arg = Argument("cribl_use_optimized")
        cribl_use_optimized_arg.data_type = Argument.data_type_boolean
        cribl_use_optimized_arg.description = "Use optimized jobs"
        cribl_use_optimized_arg.required_on_create = True
        cribl_use_optimized_arg.required_on_edit = True
        scheme.add_argument(cribl_use_optimized_arg)

        cribl_pipeline_arg = Argument("cribl_pipeline")
        cribl_pipeline_arg.data_type = Argument.data_type_string
        cribl_pipeline_arg.description = "Pipeline to use for UTStream Operations"
        cribl_pipeline_arg.required_on_create = True
        cribl_pipeline_arg.required_on_edit = True
        scheme.add_argument(cribl_pipeline_arg)

        cribl_destination_arg = Argument("cribl_destination")
        cribl_destination_arg.data_type = Argument.data_type_string
        cribl_destination_arg.description = "Output to use for UTStream Operations"
        cribl_destination_arg.required_on_create = True
        cribl_destination_arg.required_on_edit = True
        scheme.add_argument(cribl_destination_arg)

        return scheme

    def validate_input(self, validation_definition):
        pass # passing as there is no input provided to this modular input

    def stream_events(self, inputs, ew):
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

            self.logger.info("instance=\"{}\",action=\"replay\",status=\"success\",result=\"created\"".format(self.instance))

            # This is a hack to get around the legacy CollectionHandlerService
            replay_jobs_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_replay_jobs_collection, self.uuid)
            replay_results_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_replay_results_collection, self.uuid)

            # Get replay jobs from stage with matching instance and collector
            replay_jobs_query = "{ \"$and\": [ {\"instance\":\"" + self.instance + "\"}, {\"cribl_collector\":\"" + self.cribl_collector + "\"} ] }"
            replay_jobs = replay_jobs_handler.get_entries_query(replay_jobs_query)

            # Check if we got any replay jobs
            if len(replay_jobs) == 0:
                self.logger.info("instance=\"{}\",action=\"replay\",status=\"success\",result=\"done\",reason=\"no_jobs_found\"".format(self.instance))
                exit(0)
            self.logger.info("instance=\"{}\",action=\"replay\",status=\"success\",result=\"starting\",reason=\"job_found\",count=\"{}\"".format(self.instance, len(replay_jobs)))

            cribl_instance_service = CriblInstanceService( uuid=self.uuid, client=client, session_key=self.session_key, user="splunk-system-user" )
            cribl_object = cribl_instance_service.get_instance(self.instance)

            proxy_service = ProxyService( uuid=self.uuid, client=client, session_key=self._input_definition.metadata["session_key"], user="splunk-system-user" )
            cribl_interaction_helper = HelperCriblInstanceInteraction(instance=cribl_object, uuid=self.uuid, proxy=proxy_service.get_httpx_info())

            self.cribl = cribl_object.get_private_dict()

            # Create replay jobs objects based on the replay jobs we got from the stage into a list of batch jobs
            replay_job_batch_list = []
            for replay_job_batch in [replay_jobs[i:i + 1000] for i in range(0, len(replay_jobs), 1000)]:
                replay_job_batch_objects = []
                for replay_job in replay_job_batch:
                    replay_job_batch_objects.append(HelperCollectionEntryReplayJob(**replay_job).get_cribl_replay_job(self.uuid))
                replay_job_batch_list.append(replay_job_batch_objects)

            replay_job_objects = []
            for replay_job_batch in replay_job_batch_list:
                # Check if any of the sources fetched from the stage are already in the results collection
                sources_query = "{\"$or\": [" + ",".join(["{\"cribl_source\":\"" + job.collection_entry.cribl_source + "\"}" for job in replay_job_batch]) + "]}"
                cribl_replay_results_conflicts = replay_results_handler.get_entries_query(sources_query)

                self.logger.debug("instance=\"{}\",action=\"conflict_detection\",status=\"start\"".format(self.instance))

                # Check if there are any conflicts and if so, delete them
                if len(cribl_replay_results_conflicts) > 0:
                    self.logger.debug("instance=\"{}\",action=\"conflict_detection\",status=\"success\",result=\"found\",count=\"{}\"".format(self.instance, len(cribl_replay_results_conflicts)))

                    cleaned_replay_job_objects = []

                    conflicting_sources = {}
                    for c in cribl_replay_results_conflicts:
                        conflicting_sources[c['cribl_source']] = {"instance": c['instance'], "cribl_collector": c['cribl_collector']}

                    for result_object in replay_job_batch:
                        source = result_object.collection_entry.cribl_source
                        instance = result_object.collection_entry.instance
                        cribl_collector = result_object.collection_entry.cribl_collector

                        if f"{source}::{instance}::{cribl_collector}" not in conflicting_sources:
                            cleaned_replay_job_objects.append(result_object)
                            self.logger.debug("instance=\"{}\",collector=\"{}\",source=\"{}\",action=\"conflict_detection\",status=\"success\",result=\"done\",reason=\"cleaned_replay_job_object\"".format(instance, cribl_collector, source))
                        else:
                            replay_jobs_handler.delete_entry(result_object.collection_entry)
                            self.logger.debug("instance=\"{}\",collector=\"{}\",source=\"{}\",action=\"conflict_detection\",status=\"success\",result=\"conflict\",reason=\"source_conflict\"".format(instance, cribl_collector, source))
                    
                    replay_job_objects.extend(cleaned_replay_job_objects)
                
                else:
                    self.logger.debug("instance=\"{}\",action=\"conflict_detection\",status=\"success\",result=\"non_found\",count=\"{}\"".format(self.instance, len(cribl_replay_results_conflicts)))
                    replay_job_objects.extend(replay_job_batch)

            if len(replay_job_objects) == 0:
                self.logger.info("instance=\"{}\",action=\"replay\",status=\"success\",result=\"done\",reason=\"no_not_conflicting_jobs_found\"".format(self.instance))
                exit(0)

            # Optimize the replay jobs if needed
            if bool(self.cribl_use_optimized):
                optimizer = HelperCriblJobOptimizer(
                    self.cribl,
                    self.uuid,
                    self.cribl_max_optimize
                )
                replay_job_objects = optimizer.optimize_jobs(replay_jobs)

            # Start the replay
            job_runner = HelperCriblJobRunner(
                cribl_instance = self.cribl, 
                cribl_interaction_helper = cribl_interaction_helper, 
                uuid = self.uuid, 
                cribl_collector = self.cribl_collector, 
                cribl_max_jobs = self.cribl_max_jobs,
                cribl_pipeline = self.cribl_pipeline,
                cribl_destination = self.cribl_destination
            )
            done_jobs = job_runner.run_jobs(replay_job_objects)
            done_jobs_by_queue_job = {}

            replayed_files = 0
            job: HelperCriblReplayJob
            for job in done_jobs:
                # Check if job was successful
                if job.status != "finished":
                    self.logger.error("instance=\"{}\",action=\"replay\",status=\"error\",result=\"{}\"".format(self.instance, job.status))
                    self.dataset_messages.insert( name=f"UTStream - Replay Job - {job.instance} {job.collector} {job.status}", value=f"UTStream: Replay Job for instance \"{job.instance}\" and collector \"{job.collector}\" failed with status \"{job.status}\"", severity="error", roles = ["utstream_admin", "admin"] )
                    continue

                # Split up optimized jobs into a single job per file for utstream_replay_results
                for job_result_entry in job.collection_entry:
                    replayed_files += 1
                    collection_entry = job_result_entry
                    collection_entry['cribl_replay_job'] = job.job_id
                    collection_entry['run_time'] = job.start_time
                    replay_results_handler.add_entry(HelperCollectionEntryReplayResult(**collection_entry))

                    # Group jobs by queue_job for user interfaction
                    if job.collection_entry[0]["queue_job"] not in done_jobs_by_queue_job:
                        done_jobs_by_queue_job[job.collection_entry[0]["queue_job"]] = { "user": job.collection_entry[0]["user"], "count": 1 }
                    else:
                        done_jobs_by_queue_job[job.collection_entry[0]["queue_job"]]["count"] = done_jobs_by_queue_job[job.collection_entry[0]["queue_job"]]["count"] + 1

                replay_jobs_handler.delete_entries(job.collection_entry)
                replay_jobs_handler.sync_changes()

            # Inform user about the jobs that were replayed
            if self.inform_user:
                for done_job in done_jobs_by_queue_job:
                    subject = f"UTStream: Replay job finished, replayed { done_jobs_by_queue_job[done_job]['count'] } files"
                    email = self.dataset_users.get_by_id( done_jobs_by_queue_job[done_job]['user'] )["email"]
                    if email != "" and email != "changeme@example.com":
                        email_search = f"| makeresults | sendemail to=\"{email}\" format=html subject=\"{subject}\""
                        self.dataset_search.run_blocking_search( search=email_search )
                    else:
                        self.dataset_messages.insert( name=f"UTStream - Email not found - {done_jobs_by_queue_job[done_job]['user']}", value=f"UTStream: Replay job finished, replayed {done_jobs_by_queue_job[done_job]['count']} files, but no email address was found for user \"{done_jobs_by_queue_job[done_job]['user']}\"", severity="warn", roles = ["utstream_admin", "admin"])
            else:
                for done_job in done_jobs_by_queue_job:
                    message = f"UTStream: Replay job \"{done_job}\" started by \"{done_jobs_by_queue_job[done_job]['user']}\" finished, replayed {done_jobs_by_queue_job[done_job]['count']} files"
                    self.dataset_messages.insert( name=f"UTStream - Replay Job - {done_job} {done_jobs_by_queue_job[done_job]['user']}", value=message, severity="info", roles = ["utstream_writer", "utstream_admin", "admin"] )
                    
            # Write changes to kvstrores back
            replay_jobs_handler.sync_changes()
            replay_results_handler.sync_changes()

            self.logger.info("instance=\"{}\",action=\"replay\",status=\"success\",result=\"done\",jobs=\"{}\",replayed_files=\"{}\"".format(self.instance, len(done_jobs), replayed_files))
            
        except Exception as e:
            self.logger.exception("instance=\"{}\",action=\"replay\",status=\"error\",result=\"failed\",reason=\"exception\",error=\"{}\"".format(self.instance, e))
            raise

    def _load_config(self):
        self.utstream_replay_jobs_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_replay_jobs_collection']
        self.utstream_replay_results_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_replay_results_collection']

    def _parse_args(self, inputs):
        self.input_name, self.input_items = inputs.inputs.popitem()
        self.session_key = self._input_definition.metadata["session_key"]    
        self.instance = self.input_items["cribl_instance"]
        self.cribl_collector = self.input_items["cribl_collector"]
        self.cribl_max_jobs = int(self.input_items["cribl_max_jobs"])
        self.cribl_max_optimize = int(self.input_items["cribl_max_optimize"])
        self.cribl_use_optimized = bool(self.input_items["cribl_use_optimized"])
        self.cribl_destination = self.input_items["cribl_destination"]
        self.cribl_pipeline = self.input_items["cribl_pipeline"]
        self.inform_user = self.input_items["cribl_inform_user"] in ["true", "True", "T", "t", "1", 1]


if __name__ == "__main__":
    exitcode = CriblReplay().run(sys.argv)
    sys.exit(exitcode)
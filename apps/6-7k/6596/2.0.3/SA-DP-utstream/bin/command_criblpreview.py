#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: command_criblpreview.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import time
import json
import traceback
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import splunklib.results as results
from splunklib import client
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

from _env import CONFIG

from utstream_template.factory_dataset import DatasetFactory
from utstream_template.service_proxy import ProxyService

from utstream.service_cribl_instance import CriblInstanceService
from utstream.helper_cribl_instance_interaction import HelperCriblInstanceInteraction

from utstream.service_collection_handler import CollectionHandlerService
from utstream.helper_cribl_job_runner import HelperCriblJobRunner
from utstream.helper_cribl_job_preview import HelperCriblPreviewJob

from utstream_template.factory_logger import Logger

@Configuration()
class CriblPreview(GeneratingCommand):

    _key = Option(require=True)
    count = Option(require=True)
    duration = Option(require=True)
    instance = Option(require=True)
    collector = Option(require=True)

    utstream_discovery_results_collection = ""
    utstream_discovery_inventory_collection = ""

    app_owner = "admin"
    uuid = ""

    session_key = ""
    logger = None

    def generate(self):
        self.uuid = str(uuid.uuid4())
        self.logger = Logger('command', self.uuid)

        dataset_factory = DatasetFactory( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key )
        self.dataset_confs = dataset_factory.get_dataset_service( "confs" )
        self.dataset_search = dataset_factory.get_dataset_service( "search" )

        self._load_config()

        try:
            # Get instance
            cribl_instance_service = CriblInstanceService( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key, user=self._metadata.searchinfo.username )
            cribl_object = cribl_instance_service.get_instance(self.instance)
            proxy_service = ProxyService( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key, user=self._metadata.searchinfo.username )
            cribl_interaction_helper = HelperCriblInstanceInteraction(instance=cribl_object, uuid=self.uuid, proxy=proxy_service.get_httpx_info())

            self.logger.info("action=\"preview\",status=\"success\",result=\"created\",cribl_discovery_results_collection=\"{}\",_key=\"{}\",count=\"{}\",user=\"{}\"".format(self.utstream_discovery_results_collection, self._key, self.count, self._metadata.searchinfo.username))

            discovery_result_objects = self.cribl_discovery_results_handler.get_entries_query({'_key': self._key})

            if len(discovery_result_objects) != 1:
                self.logger.error("action=\"preview\",status=\"failed\",result=\"failed\",reason=\"key_not_found_or_multiple\",_key=\"{}\"".format(self._key))
                yield {
                    '_serial': 0,
                    '_time': int(time.time()),
                    '_raw': "action=preview,status=failed,result=failed,reason=key_not_found_or_multiple,_key={}".format(self._key)
                }
                return
            discovery_result_object = discovery_result_objects[0]

            # Access Control
            allowed_indexes = []
            index_seach = "| eventcount summarize=false index=* index=_* | dedup index | fields index"

            for result in self.dataset_search.run_blocking_search(index_seach, 0, int(time.time())):
                if not isinstance(result, results.Message):
                    allowed_indexes.append(result['index'])

            if discovery_result_object['index'] not in allowed_indexes:
                self.logger.error("action=\"access_control\",status=\"error\",result=\"access_control_failed\",_key=\"{}\",requested_index=\"{}\",allowed_indexes=\"{}\"".format(self._key, discovery_result_object['index'], ",".join(allowed_indexes)))
                yield {
                    '_serial': 0,
                    '_time': int(time.time()),
                    '_raw': "action=\"access_control\",status=\"error\",result=\"access_control_failed\",_key=\"{}\",requested_index=\"{}\",allowed_indexes=\"{}\"".format(self._key, discovery_result_object['index'], ",".join(allowed_indexes))
                }
                return
            else:
                self.logger.debug("action=\"access_control\",status=\"success\",result=\"access_control_passed\",_key=\"{}\"".format(self._key))

            preview_job = HelperCriblPreviewJob(discovery_result_object["instance"], discovery_result_object["index"], discovery_result_object["host"], discovery_result_object["sourcetype"], discovery_result_object["filename"], discovery_result_object["earliest"], discovery_result_object["latest"], self.uuid)
            job_runner = HelperCriblJobRunner(
                cribl_instance = cribl_object.get_private_dict(), 
                cribl_interaction_helper = cribl_interaction_helper, 
                uuid = self.uuid, 
                cribl_collector = self.collector, 
                cribl_max_jobs = 1,
            )

            preview_job.set_duration(self.duration)
            preview_job.set_max_events(self.count)

            preview_available, preview_results = job_runner.run_preview_jobs(preview_job)
            if preview_available:
                serial = 0
                for capture in filter(None, preview_results.split("\n")):
                    capture_json = json.loads(capture)
                    yield {
                        '_serial': serial,
                        '_time': capture_json['_time'],
                        '_raw': capture_json['_raw'],
                        'source': capture_json['source'],
                        'index': capture_json['index'],
                        'host': capture_json['host'],
                        'sourcetype': capture_json['sourcetype'],
                    }
                    serial += 1
            else:
                yield {
                        '_serial': 0,
                        '_time': int(time.time()),
                        '_raw': "No preview available",
                    }

        except Exception as e:
            self.logger.error("action=\"preview\",status=\"failed\",result=\"failed\",reason=\"error\",_key=\"{}\"".format(self._key))
            self.logger.error(traceback.format_exc())
            yield {
                '_serial': 0,
                '_time': int(time.time()),
                '_raw': "Error: {}".format(e)
            }

    def _load_config(self):
        self.utstream_discovery_inventory_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_discovery_inventory_collection']
        self.utstream_discovery_results_collection = CONFIG["UTSTREAM_COLLECTIONS"]['utstream_discovery_results_collection']

        self.cribl_discovery_inventory_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_discovery_inventory_collection, self.uuid)
        self.cribl_discovery_results_handler = CollectionHandlerService(self.dataset_confs.splunk_service.kvstore, self.utstream_discovery_results_collection, self.uuid)

dispatch(CriblPreview, sys.argv, sys.stdin, sys.stdout, __name__)

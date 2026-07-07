#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: alertaction_criblautoreplay.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from argparse import ArgumentError
import sys
import json
import time
import uuid
import os
import traceback


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib import results, client

from utstream_template.factory_dataset import DatasetFactory
from utstream_template.factory_logger import Logger

class CriblAutoReplay():


    def __init__(self, configuration, payload):
        try:
            self.configuration = configuration
            self.payload = payload

            self._parse_args()
            self._run()

        except Exception as e:
            logger.error("action=\"criblautoreplay\",status=\"failed\",message=\"{}\"".format(str(e)))
            logger.error(traceback.format_exc())
            self.dataset_messages.insert( name=f"UTStream: {self.search_name} failed", value=f"UTStream: {self.search_name} failed to execute criblautoreplay: {str(e)}", severity="error", roles=["admin", "utstream_admin", "utstream_reader"] )
            raise


    def _parse_args(self):
        dataset_factory = DatasetFactory(uuid=alert_uuid, client=client, session_key=self.payload.get('session_key'))
        self.dataset_search = dataset_factory.get_dataset_service( 'search' )
        self.dataset_confs = dataset_factory.get_dataset_service( 'confs' )
        self.dataset_messages = dataset_factory.get_dataset_service( 'messages' )

        # Getting the search details from params
        self.sid = self.payload.get('sid')
        self.search_name = self.payload.get('search_name')
        self.index = self.configuration.get('index')
        self.sourcetype = self.configuration.get('sourcetype')
        self.host = self.configuration.get('host')
        self.earliest = float(self.configuration.get('earliest'))
        self.latest = float(self.configuration.get('latest'))
        self.instance = self.configuration.get('instance').split("::")[0]
        self.collector = self.configuration.get('instance').split("::")[1]

        job = self.dataset_search.get_job_by_sid( self.sid )

        self.user = job.access.get('owner')
            
        # Rounding self.earliest & self.latest
        self.earliest = int(self.earliest//60 * 60)
        self.latest = int(self.latest//60 * 60 + 59)   

        # Settingh searchname if used with sendalert
        if self.search_name == "":
            self.search_name = "ad-hoc"


    def _run(self):
        logger.info("action=\"criblautoreplay\",status=\"success\",result=\"created\",index=\"{}\",sourcetype=\"{}\",host=\"{}\",earliest=\"{}\",latest=\"{}\",instance=\"{}\",user=\"{}\",search=\"{}\",sid=\"{}\"".format(self.index, self.sourcetype, self.host, self.earliest, self.latest, self.instance, self.user, self.search_name, self.sid))
        search = "| criblsearch index=\"{}\" sourcetype=\"{}\" host=\"{}\" instance=\"{}\" collector=\"{}\" alert_action=\"{}\"".format(self.index, self.sourcetype, self.host, self.instance, self.collector, alert_uuid)
        logger.debug("action=\"querybuilder\",status=\"success\",result=\"created\",search\"{}\",earliest=\"{}\",latest=\"{}\"".format(search, self.earliest, self.latest))

        # Run search and get the results
        for result in self.dataset_search.run_blocking_search(search=search, earliest=self.earliest, latest=self.latest):
            if isinstance(result, results.Message):
                logger.error("action=\"criblautoreplay\",status=\"error\",result=\"{}\"".format(result.message))
                raise ArgumentError(result.message)

if __name__ == '__main__':
    start = time.time()
    global logger
    global alert_uuid
    alert_uuid = str(uuid.uuid4())
    logger = Logger('modalert', alert_uuid)

    if len(sys.argv) > 1 and "--execute" in sys.argv:
        payload = json.loads(sys.stdin.read())
        configuration = payload.get('configuration')

        if len(configuration) == 0:
            logger.error("action=\"create\",status=\"error\",message=\"not_all_fields_given\",alert_uuid=\"{}\"".format(alert_uuid))
            exit(1)

        missing = []
        if not configuration.get('index'):
            missing.append('index')

        if not configuration.get('sourcetype'):
            missing.append('sourcetype')

        if not configuration.get('host'):
            missing.append('host')

        if not configuration.get('instance'):
            missing.append('instance')

        if not configuration.get('earliest'):
            missing.append('earliest')

        if not configuration.get('latest'):
            missing.append('latest')

        if len(missing) > 0:
            logger.error("action=\"create\",status=\"error\",message=\"not_all_fields_given\",missing=\"{}\"".format(",".join(missing)))
            exit(1)

        logger.info("action=\"create\",status=\"ok\",alert_uuid=\"{}\"".format(alert_uuid))
        CriblAutoReplay(configuration, payload)

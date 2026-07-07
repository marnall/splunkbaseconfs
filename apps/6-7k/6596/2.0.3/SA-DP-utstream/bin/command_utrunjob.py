#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: command_utrunjob.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals

# Import modules from system
import sys, os, uuid, time, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Import modules from ../lib
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from splunklib import client

from utstream.service_cribl_instance import CriblInstanceService

from utstream.helper_cribl_instance_interaction import HelperCriblInstanceInteraction
from utstream.helper_cribl_job_generic import HelperCriblGenericJob

from utstream_template.factory_logger import Logger
from utstream_template.service_proxy import ProxyService

@Configuration(type='reporting')
class utrunjob(GeneratingCommand):
    """ 
    ##Syntax

    | utrunjob instance="<cribl_instance>" job_name="<job_name>" expression="<expression>" | outputlookup <lookup_name> 

    ##Description

    Custom search command to write result set of a search to a lookup table in Cribl Stream.

    """

    instance = Option(require=True)
    job_name = Option(require=True)
    expression = Option(require=True)

    cribl_instance = None
    logger = None

    def generate(self):
        try:
            self.uuid = str(uuid.uuid4())
            self.logger = Logger('command', self.uuid)

            cribl_instance_service = CriblInstanceService( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key, user=self._metadata.searchinfo.username )
            proxy_service = ProxyService( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key, user=self._metadata.searchinfo.username )

            cribl_objects = []

            for instance in self.instance.split(","):
                # Get instance
                check = cribl_instance_service.get_instance(instance)
                if check is None:
                    raise Exception("Instance {} not found".format(instance))
                check_interaction_helper = HelperCriblInstanceInteraction(instance=check, uuid=self.uuid, proxy=proxy_service.get_httpx_info())
                jobs = check_interaction_helper.get_jobs()
                if self.job_name not in jobs:
                    raise Exception("Job {} does not exist on instance {}".format(self.job_name, instance))
                cribl_objects.append(check)

            for cribl_object in cribl_objects:
                cribl_interaction_helper = HelperCriblInstanceInteraction(instance=cribl_object, uuid=self.uuid, proxy=proxy_service.get_httpx_info())

                # Create a job, job runner and run jobs
                job =  HelperCriblGenericJob(self.expression, self.instance, self._metadata.searchinfo.earliest_time, self._metadata.searchinfo.latest_time, self.uuid)
                job.set_cribl_interaction_helper(cribl_interaction_helper)
                job.set_collector(self.job_name)
                job.set_url(cribl_interaction_helper.cribl_adapted_api_collection['jobs_url'])
                job.start_job()

                self.write_info("Started job \"{}\" with job id \"{}\" on instance \"{}\"".format(self.job_name, job.get_job_id(), cribl_interaction_helper.used_url))

            yield {'_time': time.time(), '_raw': "Done"}

        except Exception as e:
            self.logger.error("action=\"\"failed\"\",status=\"failure\",result=\"failed\",error=\"{}\"".format(e))
            self.logger.error(traceback.format_exc())
            raise e

dispatch(utrunjob, sys.argv, sys.stdin, sys.stdout, __name__)

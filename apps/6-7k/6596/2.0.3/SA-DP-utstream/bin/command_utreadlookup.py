#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: command_utreadlookup.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals

# Import modules from system
import sys, os, uuid, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Import modules from ../lib
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from splunklib import client

from utstream.service_cribl_instance import CriblInstanceService
from utstream.helper_cribl_instance_interaction import HelperCriblInstanceInteraction

from utstream_template.factory_logger import Logger
from utstream_template.service_proxy import ProxyService

@Configuration(distributed=False, type='reporting')
class utreadlookup(GeneratingCommand):
    """ 
    ##Syntax

    | utreadlookup instance="<cribl_instance>" lookup_name="<lookup_name>" | outputlookup <lookup_name> 

    ##Description

    Custom search command to write result set of a search to a lookup table in Cribl Stream.

    """

    instance = Option(require=True)
    lookup_name = Option(require=True)

    cribl_instance = None
    logger = None

    app_owner = "admin"

    def generate(self):
        try:

            self.uuid = str(uuid.uuid4())
            self.logger = Logger('command', self.uuid)
            
            cribl_instance_service = CriblInstanceService( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key, user=self._metadata.searchinfo.username )
            proxy_service = ProxyService( uuid=self.uuid, client=client, session_key=self._metadata.searchinfo.session_key, user=self._metadata.searchinfo.username )

            cribl_objects = []

            for instance in self.instance.split(","):
                # Get instance
                cribl_object = cribl_instance_service.get_instance(instance)
                if cribl_object is None:
                    raise Exception("Instance {} not found".format(instance))
                cribl_objects.append(cribl_object)

            for cribl_object in cribl_objects:
                cribl_interaction_helper = HelperCriblInstanceInteraction(instance=cribl_object, uuid=self.uuid, proxy=proxy_service.get_httpx_info())

                found = False
                for row in cribl_interaction_helper.get_lookup_file(self.lookup_name):
                    if len(cribl_objects) > 1:
                        row['instance'] = cribl_object.name 
                    found = True
                    yield row

                if not found:
                    self.write_error("Lookup file '{}' not found at Cribl instance '{}'".format(self.lookup_name, cribl_interaction_helper.used_url))
                else:
                    self.write_info("Successfully read lookup file '{}' from Cribl instance '{}'.".format(self.lookup_name, cribl_interaction_helper.used_url))

        except Exception as e:
            self.logger.error("action=\"\"failed\"\",status=\"failure\",result=\"failed\",error=\"{}\"".format(e))
            self.logger.error(traceback.format_exc())
            raise e

dispatch(utreadlookup, sys.argv, sys.stdin, sys.stdout, __name__)

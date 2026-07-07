#!/usr/bin/env python

import os
import sys
import datetime
import platform

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


import dragoslib.utils
import dragoslib.ioc_inactive_list
import dragoslib.ioc_cache_tracker
import dragoslib.splunk_collections


@Configuration()
class DragosResetKVStores(GeneratingCommand):

    def generate(self):        
        try:
            self.logger.info("Dragos Clearing All KV Stores")
            self.logger.info("Python version %s" % platform.python_version())
            
            service_with_app = dragoslib.utils.create_app_specific_service(service=self.service, owner='nobody')
            
            self._verify_input_not_active(service_with_app)

            kv_stores = [
                dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE,
                dragoslib.splunk_collections.COLLECTION_NAME_HISTORY,
                dragoslib.splunk_collections.COLLECTION_NAME_STATUS,
                dragoslib.splunk_collections.COLLECTION_NAME_INACTIVE_LIST
            ]

            for store_name in kv_stores:
                if store_name in service_with_app.kvstore:
                    store_instance = service_with_app.kvstore[store_name]
                    store_instance.data.delete()

            yield {'status': "Success", 'message': "Dragos KV Stores Cleared"}

        except Exception as e:
            yield {'status': "Error", 'message': str(e)}


    def _verify_input_not_active(self, service):
        # In order to avoid a race condition require that the
        # dragos ioc input is either deleted or disabled

        # Verify that the dragos ioc modular input is either
        # deleted or disabled

        if 'dragos_iocs' in service.inputs:
            ioc_input = service.inputs['dragos_iocs']
            if ioc_input.disabled != '1':
                raise Exception("Please disable the Dragos IOC input prior to deleting the IOC list")
        else:
            # if it doesn't exist then we are OK
            pass

dispatch(DragosResetKVStores, sys.argv, sys.stdin, sys.stdout, __name__)
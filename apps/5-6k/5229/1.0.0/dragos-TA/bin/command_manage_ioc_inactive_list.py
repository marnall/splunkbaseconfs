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
class DragosManageIOCInactiveListCommand(GeneratingCommand):

    action = Option(
        doc='''
        **Syntax:** **action=***add|remove|clear_inactive_list|clear_ioc_list*
        **Description:** Are we adding or removing an IOC from the inactive_list?''',
        require=True, validate=validators.Set('add', 'remove', 'clear_inactive_list', 'clear_ioc_list'))

    ioc_ids = Option(
        doc='''
        **Syntax:** **ioc_id=***"id"*
        **Description:** The ID of the IOC''',
        require=False)

    def generate(self):
        message = "Unknown"

        try:
            self.logger.info("Dragos Managing IOC Inactive List")
            self.logger.info("Python version %s" % platform.python_version())
            
            service_with_app = dragoslib.utils.create_app_specific_service(service=self.service, owner='nobody')
            inactive_list = dragoslib.ioc_inactive_list.IOCInactiveList(service_with_app, self.logger)
            
            ioc_ids = []
            if self.ioc_ids:
                ioc_ids = self.ioc_ids.split(",")

            if self.action in ["add", "remove"]:
                if len(ioc_ids) == 0:
                    raise Exception("Must specify at least 1 IOC to %s. Use the option: ioc_ids=\"1111\"" % self.action)
                for ioc_id in ioc_ids:
                    try:
                        int(ioc_id)
                    except ValueError as e:
                        raise Exception("Invalid IOC ID %s" % ioc_id)
            if self.action in ["clear_inactive_list", "clear_ioc_list"]:
                if len(ioc_ids) != 1 or ioc_ids[0] != "DELETE":
                    raise Exception("You must set the ioc_ids field to 'DELETE' in order to use the command %s" % self.action)

            if self.action == "add":
                message = inactive_list.add_iocs_to_inactive_list(ioc_ids)
            elif self.action == "remove":
                message = inactive_list.remove_iocs_from_inactive_list(ioc_ids)
            elif self.action == "clear_inactive_list":
                message = inactive_list.remove_iocs_from_inactive_list("*")
            elif self.action == "clear_ioc_list":
                self._clear_ioc_list(service_with_app, inactive_list)
                message = "Dragos active and inactive IOC lists have been successfully cleared."

            yield {'status': "Success", 'message': message}

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


    def _clear_ioc_list(self, service, inactive_list):
        self._verify_input_not_active(service)

        inactive_list.delete_entire_inactive_list()
        if dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE in service.kvstore:
            ioc_kvstore = service.kvstore[dragoslib.splunk_collections.COLLECTION_NAME_IOC_STORE]
            ioc_kvstore.data.delete()
        cache_tracker = dragoslib.ioc_cache_tracker.IOCCacheTracker(service, logger_obj=self.logger)
        cache_tracker.record_new_ioc_pull(datetime.datetime.now(), 0, "IOC Cache manually deleted.", success=True)
        cache_tracker.reset_cache_timestamp()



dispatch(DragosManageIOCInactiveListCommand, sys.argv, sys.stdin, sys.stdout, __name__)
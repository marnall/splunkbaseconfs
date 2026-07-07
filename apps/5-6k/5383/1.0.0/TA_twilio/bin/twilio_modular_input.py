from __future__ import absolute_import
import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as util
_APP_NAME = 'TA_twilio'
import os.path

base_location = sys.path[0].split(os.path.sep)
base_location.pop(-1)
base_location.append(os.path.sep.join(["lib", "python3.7", "site-packages"]))
sys.path.pop(0)
sys.path.insert(0, os.path.sep.join(base_location))
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))

from modular_input import modular_input
import requests as request
import json
from twilio.rest import Client
from apiclient import errors


class twilio_modular_input(modular_input):

    def __init__(self, app_name="NO NAME SPECIFIED", scheme={}):
        modular_input.__init__(self, app_name, scheme)
        self.__http = None
        self.__proxy_info = None
        self.bq_client = None
        self._app_local_directory = None
        
    @property
    def http_session(self):
        return self.__http
        
    @http_session.setter
    def http_session(self, http):
        self.__http = http
        
    def set_logger(self, log):
        self.log = log
        
    def get_twilio_studio_events(self, client):
        try:
            self.info("function=all_studio_events status=starting")
            error_found = False
            next_page_url = None           
            while True and not error_found:
                try:
                    if next_page_url is None:
                        flows = client.studio.flows.page()                    
                    else:
                        flows = flows.next_page()
                    if flows is not None:
                        next_page_url = flows.next_page_url
                        for flow in flows:
                            self.get_executions(client, flow.sid)
                    if next_page_url is None:
                        break
                except errors.HttpError as error:
                    self.log.info(error.content)
                    self.log.info("action=no_data_found")
                    error_found = True
                    break
                except Exception as e:
                    self.log.debug("action=caught_admin_error error_type={} error={}".format(type(e), e))
                    self._catch_error(e)
                    error_found = True
            return True
        except Exception as e:
            self._catch_error(e)
            
    def get_executions(self, client, sid):
        try:
            self.info("function=get_executions status=starting")
            error_found = False
            next_page_url = None           
            while True and not error_found:
                try:
                    if next_page_url is None:
                        executions = client.studio.flows(sid).executions.page()                    
                    else:
                        executions = executions.next_page()
                    if executions is not None:
                        next_page_url = executions.next_page_url
                        for execution in executions:
                            execution_context = client.studio.flows(sid).executions(execution.sid).execution_context().fetch()
                            self.sourcetype("twilio:studio:executions")
                            self.print_event("{}".format((json.dumps(execution_context.context))))
                    if next_page_url is None:
                        break
                except errors.HttpError as error:
                    self.log.info(error.content)
                    self.log.info("action=no_data_found")
                    error_found = True
                    break
                except Exception as e:
                    self.log.debug("action=caught_admin_error error_type={} error={}".format(type(e), e))
                    self._catch_error(e)
                    error_found = True
            return True
        except Exception as e:
            self._catch_error(e)
    
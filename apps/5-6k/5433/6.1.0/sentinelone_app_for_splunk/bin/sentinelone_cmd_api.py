"""
Written by Kyle Smith for Aplura, LLC
Copyright (C) 2016-2024 Aplura, LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import sys
import logging
from Utilities import KennyLoggins
from s1_command import S1Command
import s1_paths
from s1_app_properties import __app_name__
import multiprocessing.dummy as mp
# These require the _paths import
from splunklib.searchcommands import Configuration, EventingCommand, Option, validators, dispatch

_cmd_name = "sentineloneapi"
kl = KennyLoggins()

# Global Constants
_ACTIVITY_TYPES = "activity_types"


@Configuration()
class S1APICommand(EventingCommand):
    """ %(synopsis)
    ##Syntax
    %(syntax)
    ##Description
    %(description)
    """
    management = Option(doc='''
                        **Syntax:** **management=***<field_name_with_management_host>*
                        **Description:** The field name with the Management Host''',
                        validate=validators.Fieldname())

    _clients = {}
    _log = kl.get_logger(app_name=__app_name__, file_name=_cmd_name, log_level=logging.INFO)
    _cmd_name = _cmd_name
    _results = []
    _catch_error = S1Command.handle_error
    _action = None

    _approved_actions = [_ACTIVITY_TYPES]

    def _activity_types_threaded_action(self, evt, mgmt_host_field):
        try:
            mgmt_host = evt[mgmt_host_field]
            self._log.debug("action=performing_threaded_action mgmt_host={}".format(mgmt_host))
            self._log.debug("action=performing_threaded_action event={}".format(evt))
            for mgmt_url in self._clients.items():
                if mgmt_host in mgmt_url:
                    self._log.debug("action=performing_api_call action={} mgmt_host={}".format(self._action, mgmt_host))
                    api_results = self._clients[mgmt_host].activities.get_types().json["data"]
                    self._log.debug("action=performing_api_call found_results={}".format(len(api_results)))
                    [self._results.append(at) for at in api_results]
                else:
                    self._log.warning(
                        "action=process api_call, msg=mgmt_host not found in instantiated clients: mgmt_host: {}, mgmt_url: {}".format(
                            mgmt_host, mgmt_url))
        except Exception as e:
            self._log.error(f"action=performing_api_call exception={e}")
            evt["error"] = "{}: {}".format(type(e), e)
            self._results.append(evt)

    def transform(self, events):
        """
        Splunk requires generate function to behave as main, upon search command
        trigger the generate function will be called with the arguments provided
        by the command issuer (The SentinelOne App UI or the search GUI)
        """
        try:
            session_key = "{}".format(self.metadata.searchinfo.session_key)
            s1_client = S1Command(_cmd_name, session_key)
            s1_client.setup()
            self._clients = s1_client.clients_by_url()
            mgmt_host_field = self.management or "management"
            p = mp.Pool(10)
            self._log.info(f"action=starting_command self={list(self.__dict__.keys())} fieldnames={self._fieldnames}")
            if self._fieldnames and len(self._fieldnames) == 1 and self._fieldnames[0] in self._approved_actions:
                self._action = self._fieldnames[0]
            elif self._fieldnames and len(self._fieldnames) == 1 and self._fieldnames not in self._approved_actions:
                raise Exception("Invalid Action Provided: {}".format(self._fieldnames[0]))
            elif self._fieldnames and len(self._fieldnames) > 1:
                raise Exception("Too many API Actions provided")
            else:
                raise Exception("No API Action provided")
            matrix = [(evt, mgmt_host_field) for num, evt in
                      enumerate(events)]
            selected_function = None
            if self._action == _ACTIVITY_TYPES:
                selected_function = self._activity_types_threaded_action
            if selected_function is None:
                raise Exception("Unable to find the correct API operation")
            p.starmap(selected_function, matrix)
            p.close()
            p.join()
            self._log.info(
                "action=cmd_result_evt type={1} results_length={0}".format(len(self._results), type(self._results)))

            for evt in self._results:
                yield evt
        except Exception as e:
            self._log.error(f"action=cmd_result_evt exception={e}")
            self.write_error("{}".format(e), type(e))


dispatch(S1APICommand, sys.argv, sys.stdin, sys.stdout, __name__)

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

_cmd_name = "sentineloneagentaction"
kl = KennyLoggins()


@Configuration()
class S1AgentCommand(EventingCommand):
    """ %(synopsis)
    ##Syntax
    %(syntax)
    ##Description
    %(description)
    """
    action_type = Option(doc='''
                **Syntax:** **action_type=***<string>*
                **Description:** Action to take on the agents''',
                         require=True, validate=validators.Fieldname())
    agent_id = Option(doc='''
                **Syntax:** **agent_id=***<field_name_with_agent_id>*
                **Description:** The field name with the agent id''',
                      validate=validators.Fieldname())
    site_id = Option(doc='''
                    **Syntax:** **site_id=***<field_name_with_site_id>*
                    **Description:** The field name with the threat id''',
                     validate=validators.Fieldname())
    mgmt_host = Option(doc='''
                        **Syntax:** **mgmt_host=***<field_name_with_mgmt_host>*
                        **Description:** The field name with the Management Host''',
                       validate=validators.Fieldname())

    _clients = {}
    _log = kl.get_logger(app_name=__app_name__, file_name=_cmd_name, log_level=logging.INFO)
    _cmd_name = _cmd_name
    _results = []
    _catch_error = S1Command.handle_error
    
    def threaded_action(self, evt, action_type, agent_id_field, site_id_field, mgmt_host_field):
        try:
            agent_id = evt[agent_id_field]
            site_id = evt[site_id_field]
            mgmt_host = evt[mgmt_host_field]
            self._log.debug("action=performing_threaded_action mgmt_host={} action_type={} agent_id={} agent_id_field={} site_id={} site_id_field={} "
                            .format(mgmt_host, action_type, agent_id, agent_id_field,site_id, site_id_field))
            self._log.debug("action=performing_threaded_action event={}".format(evt))
            for mgmt_url in self._clients.items():
                if mgmt_host in mgmt_url:
                    if action_type == "disconnect":
                        self._log.info(
                            "action=disconnect mgmt_host={} agent_id={} site_id={}".format(mgmt_host, agent_id,
                                                                                           site_id))
                        evt["affected_agent_count"] = self._clients[mgmt_host].agent_actions.disconnect_from_network(
                            ids=[agent_id],
                            siteIds=[site_id]).data
                    elif action_type == "connect":
                        self._log.info(
                            "action=connect mgmt_host={} agent_id={} site_id={}".format(mgmt_host, agent_id, site_id))
                        evt["affected_agent_count"] = self._clients[mgmt_host].agent_actions.connect_to_network(
                            ids=agent_id,
                            siteIds=[
                                site_id]).data
                    else:
                        self._log.warning(
                            "action={} mgmt_host={} agent_id={} site_id={}".format(mgmt_host, action_type, agent_id,
                                                                                   site_id))
                        raise Exception("Action Type not recognized: {}".format(action_type))
                    self._results.append(evt)
                else:
                    self._log.warning(
                        "action=process agent action: {}, msg=mgmt_host not found in instantiated clients: mgmt_host: {}, mgmt_url: {}".format(
                            action_type, mgmt_host, mgmt_url))

        except Exception as e:
            self._catch_error(e, self._cmd_name)
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
            agent_id_field = self.agent_id or "id"
            site_id_field = self.site_id or "siteId"
            action_type = self.action_type or "connect"
            mgmt_host_field = self.mgmt_host or "management"
            p = mp.Pool(10)
            self._log.info(f"action=starting_command action_type={action_type} id_field={agent_id_field}")
            matrix = [(evt, action_type, agent_id_field, site_id_field, mgmt_host_field) for num, evt in
                      enumerate(events)]
            p.starmap(self.threaded_action, matrix)
            p.close()
            p.join()
            self._log.info("action=cmd_result_evt type={1} results={0}".format(self._results, type(self._results)))
            for evt in self._results:
                yield evt
        except Exception as e:
            self._catch_error(e, _cmd_name)
            self.write_error("{}".format(e), type(e))


dispatch(S1AgentCommand, sys.argv, sys.stdin, sys.stdout, __name__)

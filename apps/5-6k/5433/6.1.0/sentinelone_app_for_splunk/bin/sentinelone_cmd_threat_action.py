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
# These libraries require _paths import
from splunklib.searchcommands import Configuration, EventingCommand, Option, validators, dispatch

_cmd_name = "sentinelonethreataction"

kl = KennyLoggins()


@Configuration()
class S1ThreatCommand(EventingCommand):
    """ %(synopsis)
    ##Syntax
    %(syntax)
    ##Description
    %(description)
    """
    status = Option(doc='''
                **Syntax:** **status=***<string>*
                **Description:** Status to set the incident''',
                    require=True, validate=validators.Fieldname())
    site_id = Option(doc='''
                        **Syntax:** **site_id=***<field_name_with_site_id>*
                        **Description:** The field name with the threat id''',
                     validate=validators.Fieldname())
    threat_id = Option(doc='''
                **Syntax:** **threat_id=***<field_name_with_threat_id>*
                **Description:** The field name with the threat id''',
                       validate=validators.Fieldname())
    verdict = Option(doc='''
                **Syntax:** **verdict=***<string>*
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

    def threaded_action(self, evt, incident_status, threat_id_field, site_id_field, mgmt_host_field, verdict):
        try:
            threat_id = evt[threat_id_field]
            site_id = evt[site_id_field]
            mgmt_host = evt[mgmt_host_field]
            self._log.info(
                "action=update_threat_incident mgmt_host={} threat_id={} site_id={} status={} verdict={}".format(
                    mgmt_host, threat_id, site_id, incident_status, verdict))
            for mgmt_url in self._clients.items():
                if mgmt_host in mgmt_url:
                    evt["affected_agent_count"] = self._clients[mgmt_host] \
                        .threats.update_threat_incident(incident_status,
                                                        analyst_verdict=verdict,
                                                        ids=[threat_id],
                                                        siteIds=[site_id]
                                                        ).data
                    self._results.append(evt)
                else:
                    self._log.warning("action=process threat action, "
                                    "msg=mgmt_host not found in instantiated clients: "
                                    "mgmt_host: {}, mgmt_url: {}".format(mgmt_host, mgmt_url))

        except Exception as e:
            self._catch_error(e, self._cmd_name)
            evt["command_error"] = "{}: {}".format(type(e), e)
            self._results.append(evt)

    def transform(self, records):
        """
        Splunk requires generate function to behave as main, upon search command
        trigger the generate function will be called with the arguments provided
        by the command issuer (The SentinelOne App UI or the search GUI)
        """
        try:
            self._log.info("action=starting_transform")
            session_key = "{}".format(self.metadata.searchinfo.session_key)
            s1_client = S1Command(_cmd_name, session_key)
            self._log.info("action=starting_setup")
            s1_client.setup()
            self._clients = s1_client.clients_by_url()
            self._log.info("action=setup_complete")
            threat_id_field = self.threat_id or "id"
            site_id_field = self.site_id or "siteId"
            incident_status = self.status or "unresolved"
            mgmt_host_field = self.mgmt_host or "management"
            verdict = self.verdict or None
            valid_status = ['unresolved', 'in_progress', 'resolved']
            valid_verdict = ["true_positive", "undefined", "false_positive", "suspicious"]
            if incident_status not in valid_status:
                raise ValueError("{} is not a valid incident status.".format(incident_status))
            if incident_status == 'resolved' and verdict not in valid_verdict:
                raise ValueError("{} is not a valid verdict for incident_status".format(verdict))
            p = mp.Pool(10)
            matrix = [(evt, incident_status, threat_id_field, site_id_field, mgmt_host_field, verdict) for num, evt in
                      enumerate(records)]
            p.starmap(self.threaded_action, matrix)
            p.close()
            p.join()
            for evt in self._results:
                yield evt
        except Exception as e:
            self._catch_error(e, _cmd_name)
            self.write_error("{}".format(e), type(e))


dispatch(S1ThreatCommand, sys.argv, sys.stdin, sys.stdout, __name__)

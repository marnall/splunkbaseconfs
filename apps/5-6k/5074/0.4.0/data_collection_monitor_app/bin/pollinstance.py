#!/usr/bin/env python3
"""
pollinstance.py - Splunk app Data Collection Monitor's 'pollinstance' custom command
Copyright (C) 2015-2020 Joe Misner <joe@misner.net>
http://tools.misner.net/

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

Dependencies:
- Splunk Enterprise v8.0+
- Misner Splunkd Wrapper v2020.06.20

Changelog:
0.2.0 - initial version
"""

import sys
import os
#import time
import socket
import json
from collections import OrderedDict
from collections.abc import Iterable
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import splunklib.binding as binding
import misnersplunkdwrapper

__version__ = '0.2.0'

#splunkhome = os.environ['SPLUNK_HOME']
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))


@Configuration(retainsevents=True, type='reporting', local=True)
class PollInstanceCommand(GeneratingCommand):
    splunk_host = Option(
        doc='''**Syntax:** **splunk_host=***<string>*
        **Description:** Specifies the Splunk host from which to return results.
        ''',
        require=True)
    splunk_port = Option(
        doc='''**Syntax:** **splunk_port=***<int>*
        **Description:** Specifies the management port on the Splunk host.
        **Default:** 8089
        ''',
        require=False, validate=validators.Integer())
    account = Option(
        doc='''**Syntax:** **account=***<string>*
        **Description:** Name of saved account which holds administrative credentials to access the Splunk instance.
        ''',
        require=True)
    object = Option(
        doc='''**Syntax:** **object=***<string>*
        **Description:** Specifies what data to retrieve from the Splunk instance.
        'rest' performs a REST API query, i.e.: | pollinstance splunk_host="splunk.mycorp.com" object="rest" /services/server/info
        Specify a comma-separated list including one or more of the following values to poll Splunkd data:
        info, settings, messages, confs, inputstatus, apps, data, kvstore, cluster, shcluster, deployment, licenser, search, health, status
        ''',
        require=True)

    def generate(self):
        # Retrieve SPL arguments
        splunk_host = self.splunk_host
        splunk_port = self.splunk_port
        account = self.account
        object = self.object
        try:
            uri = self.fieldnames[0]
        except IndexError as e:
            uri = ""
            if object == "rest":
                self.error_exit(e, "Error in 'pollinstance' command: Missing URI (| instancepoll object=rest <uri>)")

        # Check fields
        if not splunk_host:
            message = "Error in 'pollinstance' command: Missing address (splunk_host=<string>)"
            self.error_exit(ValueError(message), message)
        if ':' in splunk_host:
            splunk_host, splunk_port = self.ui.comboAddress.currentText().split(':')
            splunk_port = int(splunk_port)
        elif not splunk_port:
            splunk_port = 8089
        if not 0 < splunk_port < 65536:
            message = "Error in 'pollinstance' command: Invalid port specified (must be 1-65535)"
            self.error_exit(ValueError(message), message)
        if not object:
            message = "Error in 'pollinstance' command: Missing object (object=<string>)"
            self.error_exit(ValueError(message), message)
        if not account:
            message = "Error in 'pollinstance' command: Missing account (account=<string>)"
            self.error_exit(ValueError(message), message)

        # Retrieve credentials for account
        splunk_user = ""
        splunk_pass = ""
        for entry in self.service.storage_passwords:
            entry_account_name, entry_account_number = entry.content.get('username').split('``splunk_cred_sep``')
            if entry_account_name == account and entry_account_number == '1':
                splunk_user = self.service.confs['data_collection_monitor_app_account'][account]['username']
                splunk_pass = json.loads(entry.content.get('clear_password'))['password']
                break
        if not splunk_user and not splunk_pass:
            message = "Error in 'pollinstance' command: Credentials not found for given account"
            self.error_exit(ValueError(message), message)

        # Connect to Splunk instance
        host = "'%s:%s'" % (splunk_host, splunk_port)
        self.logger.debug("Connecting to host %s..." % host)
        try:
            splunkd = misnersplunkdwrapper.Splunkd(splunk_host, splunk_port, splunk_user, splunk_pass)
        except binding.AuthenticationError as e:
            self.error_exit(e, "Error in 'pollinstance' command: Authentication error connecting to host %s" % host)
        except socket.gaierror as e:
            self.error_exit(e, "Error in 'pollinstance' command: Unable to connect to host %s" % host)
        except socket.error as e:
            self.error_exit(e, "Error in 'pollinstance' command: Unable to connect to host %s:\n%s" % (host, e))
        else:
            self.logger.debug('Connected')

        # Read in data by entry
        if object == "rest":
            data = dict(splunkd.rest_call(uri))['feed']['entry']
            i = 0
            for entry in data:
                i += 1
                # Clean up and sort the fields
                entry.pop('content', None)
                entry.pop('link', None)
                entry['splunk_host'] = splunk_host
                entry['author'] = entry['author']['name']
                entry['_serial'] = i
                sorted_entry = OrderedDict(sorted(entry.items()))
                yield sorted_entry
        else:
            objects = object.split(",")
            data = {}
            if 'info' in objects or 'all' in objects:
                splunkd.poll_service_info()
                data.update({
                    'info.version': splunkd.version,
                    'info.guid': splunkd.guid,
                    'info.startup_time': splunkd.startup_time,
                    'info.startup_time_formatted': splunkd.startup_time_formatted,
                    'info.cores': splunkd.cores,
                    'info.ram': splunkd.ram,
                    'info.roles': json.dumps(splunkd.roles),
                    'info.product': splunkd.product,
                    'info.mode': splunkd.mode,
                    'info.actual_role': splunkd.actual_role,
                    'info.type': splunkd.type,
                    'info.os': splunkd.os
                })
            if 'settings' in objects or 'all' in objects:
                splunkd.poll_service_settings()
                data.update({
                    'settings.host': splunkd.host,
                    'settings.SPLUNK_HOME': splunkd.SPLUNK_HOME,
                    'settings.SPLUNK_DB': splunkd.SPLUNK_DB,
                    'settings.server_name': splunkd.server_name,
                    'settings.http_port': splunkd.http_port,
                    'settings.http_ssl': splunkd.http_ssl,
                    'settings.http_server': splunkd.http_server
                })
            if 'messages' in objects or 'all' in objects:
                splunkd.poll_service_messages()
                data.update({
                    'messages.messages': splunkd.messages
                })
            if 'confs' in objects or 'all' in objects:
                try:
                    # Check if configuration filename is valid
                    filename = self.fieldnames[0]
                    splunkd.get_service_confs()
                    if filename not in splunkd.configuration_files:
                        message = "Error in 'pollinstance' command: Invalid conf file specified"
                        self.error_exit(ValueError(message), message)

                    contents = splunkd.get_configuration_kvpairs(filename)

                    data.update({
                        'confs.filename': filename,
                        'confs.contents': contents
                    })
                except IndexError as e:
                    splunkd.get_service_confs()
                    data.update({
                        'confs.configuration_files': splunkd.configuration_files,
                        'confs.deployment_server': splunkd.deployment_server
                    })
            if 'inputstatus' in objects or 'all' in objects:
                splunkd.get_services_admin_inputstatus()
                data.update({
                    'inputstatus.fileinput_status': splunkd.fileinput_status,
                    'inputstatus.execinput_status': splunkd.execinput_status,
                    'inputstatus.modularinput_status': splunkd.modularinput_status,
                    'inputstatus.rawtcp_status': splunkd.rawtcp_status,
                    'inputstatus.cookedtcp_status': splunkd.cookedtcp_status,
                    'inputstatus.udphosts_status': splunkd.udphosts_status,
                    'inputstatus.tcprawlistenerports_status': splunkd.tcprawlistenerports_status,
                    'inputstatus.tcpcookedlistenerports_status': splunkd.tcpcookedlistenerports_status,
                    'inputstatus.udplistenerports_status': splunkd.udplistenerports_status
                })
            if 'apps' in objects or 'all' in objects:
                splunkd.poll_service_apps()
                data.update({
                    'apps.apps': splunkd.apps
                })
            if 'data' in objects or 'all' in objects:
                splunkd.get_services_data()
                data.update({
                    'data.receiving_ports': splunkd.receiving_ports,
                    'data.rawtcp_ports': splunkd.rawtcp_ports,
                    'data.udp_ports': splunkd.udp_ports,
                    'data.forward_servers': splunkd.forward_servers
                })
            if 'kvstore' in objects or 'all' in objects:
                splunkd.get_services_kvstore()
                data.update({
                    'kvstore.kvstore_port': splunkd.kvstore_port
                })
            if 'cluster' in objects or 'all' in objects:
                splunkd.get_services_cluster()
                data.update({
                    'cluster.master_uri': splunkd.cluster_master_uri,
                    'cluster.mode': splunkd.cluster_mode,
                    'cluster.site': splunkd.cluster_site,
                    'cluster.label': splunkd.cluster_label,
                    'cluster.replicationport': splunkd.cluster_replicationport,
                    'cluster.replicationfactor': splunkd.cluster_replicationfactor,
                    'cluster.searchfactor': splunkd.cluster_searchfactor,
                    'cluster.maintenance': splunkd.cluster_maintenance,
                    'cluster.rollingrestart': splunkd.cluster_rollingrestart,
                    'cluster.initialized': splunkd.cluster_initialized,
                    'cluster.serviceready': splunkd.cluster_serviceready,
                    'cluster.indexingready': splunkd.cluster_indexingready,
                    'cluster.alldatasearchable': splunkd.cluster_alldatasearchable,
                    'cluster.searchfactormet': splunkd.cluster_searchfactormet,
                    'cluster.replicationfactormet': splunkd.cluster_replicationfactormet,
                    'cluster.peers': splunkd.cluster_peers,
                    'cluster.peers_searchable': splunkd.cluster_peers_searchable,
                    'cluster.peers_up': splunkd.cluster_peers_up,
                    'cluster.indexes': splunkd.cluster_indexes,
                    'cluster.indexes_searchable': splunkd.cluster_indexes_searchable,
                    'cluster.searchheads': splunkd.cluster_searchheads,
                    'cluster.searchheads_connected': splunkd.cluster_searchheads_connected
                })
            if 'shcluster' in objects or 'all' in objects:
                splunkd.get_services_shcluster()
                data.update({
                    'shcluster.label': splunkd.shcluster_label,
                    'shcluster.replicationport': splunkd.shcluster_replicationport,
                    'shcluster.replicationfactor': splunkd.shcluster_replicationfactor,
                    'shcluster.captainlabel': splunkd.shcluster_captainlabel,
                    'shcluster.captainuri': splunkd.shcluster_captainuri,
                    'shcluster.captainid': splunkd.shcluster_captainid,
                    'shcluster.dynamiccaptain': splunkd.shcluster_dynamiccaptain,
                    'shcluster.electedcaptain': splunkd.shcluster_electedcaptain,
                    'shcluster.rollingrestart': splunkd.shcluster_rollingrestart,
                    'shcluster.serviceready': splunkd.shcluster_serviceready,
                    'shcluster.minpeersjoined': splunkd.shcluster_minpeersjoined,
                    'shcluster.initialized': splunkd.shcluster_initialized,
                    'shcluster.members': splunkd.shcluster_members,
                    'shcluster.deployer': splunkd.shcluster_deployer
                })
            if 'deployment' in objects or 'all' in objects:
                splunkd.get_services_deployment()
                data.update({
                    'deployment.clients': splunkd.deployment_clients
                })
            if 'licenser' in objects or 'all' in objects:
                splunkd.get_services_licenser()
                data.update({
                    'licenser.slaves': splunkd.license_slaves,
                    'licenser.master': splunkd.license_master
                })
            if 'search' in objects or 'all' in objects:
                splunkd.get_services_search()
                data.update({
                    'search.distributedsearch_peers': splunkd.distributedsearch_peers
                })
            if 'health' in objects or 'all' in objects:
                splunkd.get_services_server_health_details()
                data.update({
                    'health.splunkd_overall': splunkd.health_splunkd_overall,
                    'health.splunkd_features': splunkd.health_splunkd_features
                })
            if 'status' in objects or 'all' in objects:
                splunkd.get_services_server_status()
                data.update({
                    'status.disk_partitions': splunkd.disk_partitions,
                    'status.cpu_usage': splunkd.cpu_usage,
                    'status.mem_usage': splunkd.mem_usage,
                    'status.swap_usage': splunkd.swap_usage,
                    'status.splunk_processes': splunkd.splunk_processes
                })

            # Convert select iterable values to JSON
            for field in data:
                if isinstance(data[field], (list, dict, set)):
                    data[field] = json.dumps(data[field])

            # Send to Splunk
            data = [data]
            #i = 0
            for entry in data:
                #i += 1
                #entry['_serial'] = i
                sorted_entry = OrderedDict(sorted(entry.items()))
                yield sorted_entry


if __name__ == "__main__":
    dispatch(PollInstanceCommand, sys.argv, sys.stdin, sys.stdout, __name__)

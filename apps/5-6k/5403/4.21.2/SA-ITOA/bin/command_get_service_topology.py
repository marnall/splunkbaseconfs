# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import json
import socket
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

from SA_ITOA_app_common.splunklib.searchcommands import StreamingCommand, dispatch, Configuration
import splunk.rest as rest
from ITOA.setup_logging import setup_logging
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager


@Configuration()
class GetServiceTopology(StreamingCommand):
    logger = setup_logging('get_service_topology.log', 'itsi.get_service_topology')
    SERVICE_TREE_ENDPOINT = "/servicesNS/nobody/SA-ITOA/itoa_interface/get_service_trees"
    service_edges = {}
    parents = {}
    _topology_fetch_attempted = False
    formatted_parents = {}
    output_fields = {'serviceid': 'parent_service_ids_apply_entity_lookup', 'service_ids': 'parent_service_ids_filter_maintenance_services'}

    def construct_service_graph(self):
        '''
        Constructs the service graph from the service topology endpoint
        Example of service_edges= {'A': ['B'], 'B': ['C'], 'C': []}
        This means B is a parent of A, C is a parent of B, and C has no parents
        '''
        try:
            cfm = ConfManager(self.service.token, 'SA-ITOA')
            conf = cfm.get_conf('itsi_event_management')
            settings = conf.get('service_topology')
            timeout = int(settings.get('service_tree_rest_timeout_seconds', 60))
            response, content = rest.simpleRequest(
                path=self.SERVICE_TREE_ENDPOINT,
                method='GET',
                sessionKey=self.service.token,
                getargs={'use_cache': '1'},
                timeout=timeout
            )
            if response.status != 200:
                self.logger.error('Failed to fetch service topology: %s', content)
                raise Exception("Failed to fetch service topology: {}".format(content))
            content = json.loads(content)
            for graph in content['graphs']:
                if not graph['has_cycle']:
                    for edges in graph['edges']:
                        if edges['target'] not in self.service_edges:
                            self.service_edges[edges['target']] = [edges['source']]
                        else:
                            self.service_edges[edges['target']].append(edges['source'])
                for vertices in graph['vertices']:
                    if vertices['id'] not in self.service_edges:
                        self.service_edges[vertices['id']] = []
        except Exception as e:
            if isinstance(e, socket.timeout) or isinstance(getattr(e, 'reason', None), socket.timeout):
                self.logger.warning(
                    'get_service_trees timed out after %d seconds; continuing without service topology',
                    timeout
                )
            else:
                self.logger.error('Error constructing service graph: %s', e)

    def merge_parent_trees(self, tree1, tree2):
        '''
        Merges two parent trees together
        Example:
        tree1 = {'A': 1, 'B': 2}
        tree2 = {'B': 1, 'C': 3}
        Merges to: {'A': 1, 'B': 1, 'C': 3}
        '''
        if tree2:
            for node, distance in tree2.items():
                if node in tree1:
                    tree1[node] = min(tree1[node], distance)
                else:
                    tree1[node] = distance
        return tree1

    def get_service_parents(self, service_id, seen=None):
        '''
        Populates self.parents with the parents of the given service_id
        and how far it is from the current service
        Example:
        service_id = 'A'
        service.edges = {'A': ['B'], 'B': ['C'], 'C': []}
        parents = {'A': 0, 'B': 1, 'C': 2}
        This means A is the current service, B is 1 away from A, and C is 2 away from A
        '''
        if seen is None:
            seen = set()
        cur_service = {service_id: 0}
        # if parents have already been calculated, return them
        if service_id in self.parents:
            cur_service.update(self.parents[service_id])
            cur_service[service_id] = 0  # preserve root distance
            return cur_service
        # grab direct parents (avoid KeyError for missing service_id)
        direct_parents = self.service_edges.get(service_id, [])
        # if no parents, return cur service only
        if not direct_parents:
            self.parents[service_id] = {}
            return cur_service
        # detect cycles to avoid infinite recursion
        if service_id in seen:
            return cur_service
        seen.add(service_id)
        cur_parents = {}
        for parent in direct_parents:
            parent_tree = self.get_service_parents(parent, seen)
            self.merge_parent_trees(cur_parents, parent_tree)
        seen.discard(service_id)
        # increase distance by 1 for the current node
        for node, distance in cur_parents.items():
            cur_parents[node] = distance + 1
        # Drop root (service_id) from stored parents to avoid cycle overwriting root distance
        self.parents[service_id] = {n: d for n, d in cur_parents.items() if n != service_id}
        cur_service.update(self.parents[service_id])
        cur_service[service_id] = 0  # always preserve root distance
        return cur_service

    def get_formatted_parents(self, service_id, parent_level):
        '''
        Returns the formatted parents for the given service_id.
        The formatted parents are a list of parents less than parent_level away
        from the service sorted in order by distance from the service
        Example:
        service_id = 'A'
        parent_level = 3
        parents = {'A': {'B': 1, 'C': 2, 'D': 3, 'E': 4}}
        return ['A', 'B', 'C'] because these B, C, D are less parent_level away from A
        '''
        if service_id in self.formatted_parents:
            return self.formatted_parents[service_id]

        parent_by_level = [[] for _ in range(parent_level)]
        for parent_service_id, level in self.parents[service_id].items():
            if level < parent_level:
                parent_by_level[level].append(parent_service_id)
        parents = [service_id]
        for parents_in_level in parent_by_level:
            parents += parents_in_level
        self.formatted_parents[service_id] = parents
        return parents

    def stream(self, records):
        # get service topology max parent level from conf (cached across chunks)
        if not hasattr(self, '_parent_level') or self._parent_level is None:
            cfm = ConfManager(self.service.token, 'SA-ITOA')
            conf = cfm.get_conf('itsi_event_management')
            settings = conf.get('service_topology') or {}
            self._parent_level = int(settings.get('service_topology_parent_level', 3))
        parent_level = self._parent_level

        for record in records:
            if not GetServiceTopology._topology_fetch_attempted and not self.service_edges:
                GetServiceTopology._topology_fetch_attempted = True
                self.construct_service_graph()

            # extract service_id(s) from record. only calculate parents if it has not been calculated yet
            for service_id_field in self.output_fields:
                service_ids = []
                if service_id_field in record and self.output_fields[service_id_field] not in record:
                    cur_service_ids = record[service_id_field]
                    if isinstance(cur_service_ids, str):
                        service_ids.append(cur_service_ids)
                    else:
                        service_ids.extend(cur_service_ids)

                    parents_topology = {}
                    for service_id in service_ids:
                        if service_id not in self.service_edges:
                            continue
                        self.get_service_parents(service_id)
                        parents = self.get_formatted_parents(service_id, parent_level)
                        cur_service_topology = {}
                        for parent in parents:
                            cur_service_topology[parent] = self.service_edges[parent]
                        parents_topology[service_id] = cur_service_topology

                    record[self.output_fields[service_id_field]] = parents_topology
            record['itsi_service_topology_hierarchy_level'] = parent_level
            yield record


dispatch(GetServiceTopology, sys.argv, sys.stdin, sys.stdout, __name__)

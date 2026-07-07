from __future__ import absolute_import
from __future__ import division
from future import standard_library
standard_library.install_aliases()  # noqa: E402
from builtins import str
from past.utils import old_div
import splunk
from . import helper
from .pbs_global_configs import PbsGlobalConfigs as pbsConf
from .messaging import Messaging as msging
import copy
import json


class Workers(splunk.rest.BaseRestHandler):
    # Spark Status, Spark Master, Spark Web UI, Health Status
    def get_spark_usage(self, spark_data, global_errors):
        try:
            res = {
                'spark_status': 'running' if spark_data['status'] == 'ALIVE' else 'down',
                'cores_used': spark_data['coresused'],
                'total_cores': spark_data['cores'],
                'memory_used': spark_data['memoryused'],
                'total_memory': spark_data['memory'],
                'alive_workers': spark_data['aliveworkers'],
            }

        except Exception as e:
            global_errors.append(msging.error_obj_map["general_error"].to_json(e.message))
            return None

        return res

    @staticmethod
    def get_worker_state(state):
        pretty_state = state
        if state == "ALIVE":
            pretty_state = "up"
        elif state == "DEAD":
            pretty_state = "down"

        return pretty_state

    def get_worker_info(self, spark_data):
        worker_map = {}
        workers = spark_data['workers']
        for node in workers:
            if node['state'] != "DEAD":
                worker_info = {}
                host = node['host']
                worker_info['coresused'] = node['coresused']
                worker_info['state'] = Workers.get_worker_state(node['state'])
                worker_info['cores'] = node['cores']
                worker_info['memoryused'] = node['memoryused']
                worker_info['totalmemory'] = node['memory']
                worker_info['worker_id'] = node['id']
                worker_map[host] = worker_info

        return worker_map

    def run_splunk_search(self, query, header, mgmt_port):
        success = False
        try:
            response = helper.RestComm.start_search_using_rest(query, header, mgmt_port)
            sid = response["sid"]

            is_query_finished = False
            while not is_query_finished:
                response = helper.RestComm.check_search_status_using_rest(sid, header, mgmt_port)
                is_query_finished = response["entry"][0]["content"]["isDone"]
            result = helper.RestComm.get_search_result_using_rest(sid, header, mgmt_port)
            result = result.get('results')
            success = True
        except Exception as e:
            result = "Failed: " + e.message

        return success, result

    def get_app_installed(self, mgmt_port, header):
        query = """
                | rest /services/apps/local/{}
                | stats values(splunk_server)
                | rename values(splunk_server) as "host_fqdn"
                """.format(pbsConf.app_name)
        success, search_results = self.run_splunk_search(query, header, mgmt_port)
        app_installed_list = set(search_results[0].get("host_fqdn", [])) if len(search_results) > 0 else set()
        return success, app_installed_list

    def get_idx_sites(self, mgmt_port, header, global_warnings, multisite_warnings):
        site_map = {}
        resp = helper.RestComm.splunk_rest('services/cluster/searchhead/generation', header, '127.0.0.1',
                                           mgmt_port)

        if resp is None:
            if helper.RestComm.get_sh_site_info(mgmt_port, header, global_warnings, multisite_warnings) != '-':
                multisite_warnings.append(msging.warn_obj_map["mul_site_no_info"].to_json())
                global_warnings.append(msging.warn_obj_map["mul_site_no_info"].to_json())
            return site_map

        cluster_peer_data = resp['entry']
        cluster_peers = cluster_peer_data[0]['content']['generation_peers']

        if cluster_peers is not None:
            for key, peer in list(cluster_peers.items()):
                host_port = peer['host_port_pair']
                site = peer['site']
                host, _ = host_port.split(':')
                site_map[host] = site

        return site_map

    def get_resource_utils(self, mgmt_port, header):
        query = """
                | rest /services/server/status/resource-usage/hostwide
                | rename values(splunk_server) as "host_fqdn"
                """.format(pbsConf.app_name)
        success, app_response = self.run_splunk_search(query, header, mgmt_port)

        utilization_obj = {}

        if success and app_response:
            for content in app_response:
                host_fqdn = content['splunk_server']
                cpu_system_pct = float(content['cpu_system_pct'])
                cpu_user_pct = float(content['cpu_user_pct'])
                mem_used = float(content['mem_used'])
                mem = float(content['mem'])

                cpu_percent = cpu_system_pct + cpu_user_pct
                mem_percent = old_div(mem_used, mem) * 100
                resource_utilization = max(cpu_percent, mem_percent)

                utilization_obj[host_fqdn] = {
                    'system_utilization': round(resource_utilization, 2),
                    'memory_utilization': round(mem_percent, 2),
                    'avg_cpu_utilization': round(cpu_percent, 2)
                }

        return success, utilization_obj

    def check_host_existence(self, host_id_list, target_set):
        for host_id in host_id_list:
            if host_id in target_set:
                return True, host_id
        return False, None

    def get_active_worker_info(self, header, mgmt_port):
        query = """
                search index=_internal sourcetype="splunk_dfs_manager_active_worker"
                | head 1
                | fields active_worker_list hostname master_instance_id replication_id role
                """
        results = helper.RestComm.run_splunk_search(query, header, mgmt_port)
        try:
            return json.loads(results[0]["_raw"])["active_worker_list"]
        except Exception as e:
            return {"Error": e.message}

    def get_indexer_info(self, mgmt_port, header, peer_map, site_map, worker_map, guid_list, active_worker_list,
                         global_errors):
        dict_res = {}
        fail_phase = "get app installed"
        success, app_install_list = self.get_app_installed(mgmt_port, header)
        if not success:
            msg = fail_phase + "Failed to get APP installation information from Search Head"
            global_errors.append(msging.error_obj_map["general_error"].to_json(msg))

        fail_phase = "get resource utilization"
        success, hostwide_utilization = self.get_resource_utils(mgmt_port, header)
        if not success:
            msg = fail_phase + "Failed to get resource utilization information from Search Head"
            global_errors.append(msging.error_obj_map["general_error"].to_json(msg))

        peer_info_template = {
            'splunk_instance_name': '',
            'peer_uri': '',
            'search_peer_state': '',
            'dfs_worker_state': 'down',
            'spark_core_usage': '-',
            'spark_mem_usage': '-',
            'spark_total_mem': '-',
            'active': False,
            'site': '',
            'warnings': []
        }
        for guid in guid_list:
            fail_phase = "init"
            peer_info = copy.deepcopy(peer_info_template)
            try:
                peer_data = peer_map[guid]
                host, port = peer_data['peer_uri'].split(':')
                host_fqdn = peer_data['host_fqdn']
                hostname = peer_data['host']

                host_id_list = (host, hostname, host_fqdn)

                fail_phase = "get_worker_id"
                if guid in active_worker_list:
                    peer_info['active'] = True
                    if_exists, key_exists = self.check_host_existence(host_id_list, worker_map)
                    if if_exists:
                        worker_info = worker_map[key_exists]
                        peer_info['worker_id'] = worker_info['worker_id']
                        peer_info['spark_core_usage'] = worker_info['coresused']
                        peer_info['spark_cores_allocated'] = worker_info['cores']
                        peer_info['spark_mem_usage'] = worker_info['memoryused']
                        peer_info['dfs_worker_state'] = worker_info['state'].lower()
                        peer_info['spark_total_mem'] = worker_info['totalmemory']
                        if len(peer_info['warnings']) > 0:
                            peer_info['dfs_worker_state'] = "sick"
                    else:
                        peer_info['worker_id'] = '-'
                        peer_info['warnings'].append(msging.warn_obj_map["no_worker_mapping"].to_json())

                peer_info['splunk_instance_name'] = peer_data['host']
                peer_info['peer_uri'] = peer_data['peer_uri']
                peer_info['search_peer_state'] = peer_data['status'].lower()
                peer_info['site'] = helper.Helper.get_node_site_info(host, site_map)

                peer_info['system_utilization'] = '-'
                peer_info['memory_utilization'] = '-'
                peer_info['avg_cpu_utilization'] = '-'

                fail_phase = "get_app_installed"
                app_installed, _ = self.check_host_existence(host_id_list, app_install_list)
                if app_installed is False:
                    peer_info['warnings'].append(msging.warn_obj_map["no_app_install"].to_json())
                peer_info['pbs_installed'] = app_installed

                fail_phase = "get_resource_utilization"
                if_exists, key_exists = self.check_host_existence(host_id_list, hostwide_utilization)
                if if_exists:
                    utilization = hostwide_utilization[key_exists]
                    peer_info['system_utilization'] = utilization['system_utilization']
                    peer_info['memory_utilization'] = utilization['memory_utilization']
                    peer_info['avg_cpu_utilization'] = utilization['avg_cpu_utilization']
                else:
                    peer_info['warnings'].append(msging.warn_obj_map["unavai_resource_utils"].to_json())

            except KeyError as e:
                msg = fail_phase + " " + e.message
                error_msg = msging.error_obj_map["clstr_no_idx"].to_json(msg)
                peer_info = {'errors': msg}
                global_errors.append(error_msg)

            except Exception as e:
                msg = fail_phase + " " + e.message
                error_msg = msging.error_obj_map["general_error"].to_json(msg)
                peer_info = {'errors': msg}
                global_errors.append(error_msg)

            dict_res[guid] = peer_info

        try:
            fail_phase = "Fail to get down indexers information."
            active_worker_info = self.get_active_worker_info(header, mgmt_port)
            for item in active_worker_info:
                temp = copy.deepcopy(peer_info_template)
                if item["guid"] not in peer_map:
                    temp['splunk_instance_name'] = item['hostname']
                    temp['peer_uri'] = item['uri']
                    temp['active'] = True
                    temp['warnings'] = ["This indexer might not be running."]
                    dict_res[item["guid"]] = temp
        except Exception as e:
            msg = fail_phase + " " + e.message
            error_msg = msging.error_obj_map["general_error"].to_json(msg)
            global_errors.append(error_msg)

        return dict_res

    def handle_GET(self):
        header = {'Authorization': 'Splunk ' + self.sessionKey}

        global_errors = []
        global_warnings = []
        multisite_warnings = []

        adding_workers_bool = True

        res = {
            'workers': {},
            'errors': [],
            'warnings': []
        }

        mgmt_port = helper.Helper.get_splunkd_mgmt_port()
        if mgmt_port is None:
            res['errors'].append(msging.error_obj_map["mgmt_port"].to_json())
            helper.Helper.write_json_response(self.response, res)
            return

        try:
            app_config = helper.RestComm.get_app_config(mgmt_port, header)

            spark_master_ip = app_config.get(pbsConf.spark_master_host_key, None)
            spark_master_ui = app_config.get(pbsConf.spark_master_webui_port_key, None)
            active_list = app_config.get(pbsConf.active_list_key, "")
            active_worker_list_res = (set(active_list.split(",")))
            active_worker_list_res.discard('')

            if len(active_worker_list_res) == 0 and (not adding_workers_bool):
                global_errors.append(msging.error_obj_map["clstr_no_workers"].to_json())
                res['errors'] = global_errors
                res['warnings'] = global_warnings
                helper.Helper.write_json_response(self.response, res)
                return

            # get spark ip/ports info from splunkd and spark master
            spark_data = helper.RestComm.get_spark_info(spark_master_ip, spark_master_ui)

            if spark_data is None:
                global_errors.append(msging.error_obj_map["clstr_no_spark_info"].to_json())
                res['errors'] = global_errors
                res['warnings'] = global_warnings
                helper.Helper.write_json_response(self.response, res)
                return

            spark_usage = self.get_spark_usage(spark_data, global_errors)

            if spark_usage is None:
                global_errors.append(msging.error_obj_map["clstr_no_spark_master_card"].to_json())
                res['errors'] = global_errors
                res['warnings'] = global_warnings
                helper.Helper.write_json_response(self.response, res)
                return

            res['summary'] = spark_usage

            worker_map = self.get_worker_info(spark_data)

            guid_list, hosts_list, peer_map = helper.RestComm.get_search_peers_keys_app(mgmt_port, header)

            considered_list = active_worker_list_res
            if adding_workers_bool:
                considered_list = guid_list

            site_map = self.get_idx_sites(mgmt_port, header, global_warnings, multisite_warnings)
            res['workers'] = self.get_indexer_info(mgmt_port, header, peer_map, site_map, worker_map,
                                                   considered_list, active_worker_list_res, global_errors)

            res['errors'] = global_errors
            res['warnings'] = global_warnings
            res['site_affinity_warnings'] = multisite_warnings
            helper.Helper.write_json_response(self.response, res)
        except Exception as e:
            self.response.write("Failed: " + e.message)

    def spark_worker_handle_cmd(self, mgmt_port, cmd, header, peers):
        try:
            active_list = helper.RestComm.get_config_using_rest(pbsConf.conf_name, pbsConf.conf_stanza, "active_list",
                                                                header, mgmt_port, "127.0.0.1")
            active_set = set(active_list.split(","))
            peer_set = set(peers)

            if cmd == "add":
                updated_active_set = active_set.union(peer_set)
            else:
                updated_active_set = active_set.difference(peer_set)

            updated_active_set.discard("")
            peer_list_to_write = ",".join(updated_active_set)
            success = helper.RestComm.modify_config_using_rest(pbsConf.conf_name, pbsConf.conf_stanza, "active_list",
                                                               peer_list_to_write, header, mgmt_port, pbsConf.app_name)

            if success is None:
                return False

        except Exception:
            return False

        return True

    def handle_POST(self):
        header = {'Authorization': 'Splunk ' + self.sessionKey}
        res = {'errors': []}
        accepted_commands = {'add': 'add', 'remove': 'remove'}

        mgmt_port = helper.Helper.get_splunkd_mgmt_port()

        if mgmt_port == '':
            res = ['errors'].append(msging.error_obj_map["mgmt_port"].to_json())
            helper.Helper.write_json_response(self.response, res)
            return

        try:
            payload = self.request['payload']
            req = json.loads(payload)
            cmd = req["action"].lower()
            peers = req["peer_uris"]

            if cmd not in accepted_commands:
                res['errors'].append(msging.error_obj_map["invalid_cmd"].to_json(suffix=cmd))
                helper.Helper.write_json_response(self.response, res)
                return

            success = self.spark_worker_handle_cmd(mgmt_port, cmd, header, peers)
            if success is False:
                suffix = cmd + " workers " + str(peers)
                res['errors'].append(msging.error_obj_map["failed_add"].to_json(suffix=suffix))

            helper.Helper.write_json_response(self.response, res)

        except Exception as e:
            self.response.write("Failed: " + e.message)

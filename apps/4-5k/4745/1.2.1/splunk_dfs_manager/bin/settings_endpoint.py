from __future__ import absolute_import
import splunk
from . import helper
import json
from .messaging import Messaging as msging
from .settings_utils import SettingsUtils as settingUtil


class SettingsManage(splunk.rest.BaseRestHandler):

    def handle_POST(self):
        header = {'Authorization': 'Splunk ' + self.sessionKey}
        res = {'errors': []}

        try:
            mgmt_port = helper.Helper.get_splunkd_mgmt_port()
            if mgmt_port is None:
                res['errors'].append(msging.error_obj_map["mgmt_port"].to_json())
                helper.Helper.write_json_response(self.response, res)
                return

            payload = self.request['payload']
            req = json.loads(payload)

            port_map, _ = settingUtil.get_current_settings(mgmt_port, header)
            has_dup_port_vals = settingUtil.duplicate_port_check(port_map, req)

            if has_dup_port_vals:
                res['errors'].append(msging.error_obj_map["sett_dup_error"].to_json())
                helper.Helper.write_json_response(self.response, res)
                return

            # Populating result object
            for param in req:
                param_type = None
                for key, data in list(settingUtil.file_stanza_mapping.items()):
                    accepted_list = data.acceptedCommands
                    if param in accepted_list:
                        param_type = key
                        break

                if param_type is not None:
                    file_stanza = settingUtil.file_stanza_mapping[param_type]
                    conf_name = file_stanza.confName
                    stanza_name = file_stanza.confStanza

                    # TODO: Detect SHC and adjust dfc_num_slots either dfw or dfc param
                    res[param] = ""
                    success = helper.RestComm.\
                        modify_config_using_rest(conf_name, stanza_name, param, req[param], header, mgmt_port)

                    if success:
                        res[param] = req[param]
                    else:
                        res['errors'].append(msging.error_obj_map["sett_rest_error"].to_json(suffix=param))
                else:
                    res['errors'].append(msging.error_obj_map["sett_key_error"].to_json(param))

            helper.Helper.write_json_response(self.response, res)

        except Exception as e:
            self.response.write("Failed: " + e.message)

    def get_idx_sites(self, mgmt_port, header, site_affinity, global_warnings, multisite_warnings):
        site_map = {}
        resp = helper.RestComm.splunk_rest('services/cluster/searchhead/generation', header, '127.0.0.1',
                                           mgmt_port)

        if resp is None:
            if site_affinity != '-':
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

    def get_site_list(self, mgmt_port, header, site_affinity, global_errors, global_warnings, multisite_warnings):
        guid_list, _, peer_map = helper.RestComm.get_search_peers_keys_app(mgmt_port, header)
        site_map = self.get_idx_sites(mgmt_port, header, site_affinity, global_warnings, multisite_warnings)
        site_list = set()
        for guid in guid_list:
            try:
                host, port = peer_map[guid]['peer_uri'].split(':')
                site = helper.Helper.get_node_site_info(host, site_map)
                if site != '-':
                    site_list.add(site)

            except KeyError as e:
                msg = e.message
                global_errors.append(msging.error_obj_map["clstr_no_idx"].to_json(msg))
            except Exception as e:
                msg = "Failed to get indexer site" + e.message
                global_errors.append(msging.error_obj_map["general_error"].to_json(msg))

        return list(site_list)

    def handle_GET(self):
        header = {'Authorization': 'Splunk ' + self.sessionKey}
        res = {
            'settings': None,
            'errors': [],
            'warnings': [],
            'sites': [],
            'site_affinity_warnings': []
        }

        global_errors = []
        global_warnings = []
        multisite_warnings = []

        mgmt_port = helper.Helper.get_splunkd_mgmt_port()
        if mgmt_port is None:
            res['errors'].append(msging.error_obj_map["mgmt_port"].to_json())
            helper.Helper.write_json_response(self.response, res)
            return

        try:
            _, settings_info = settingUtil.get_current_settings(mgmt_port, header)
            site_affinity = helper.RestComm.get_sh_site_info(mgmt_port, header, global_warnings, multisite_warnings)

            res['settings'] = settings_info
            res['settings']['site_affinity'] = site_affinity
            res['sites'] = self.get_site_list(mgmt_port, header, site_affinity, global_errors, global_warnings,
                                              multisite_warnings)

        except Exception as e:
            msg = "Failed to get settings from Search Head: " + e.message
            global_errors.append(msging.error_obj_map['general_error'].to_json(msg))

        res['site_affinity_warnings'] = multisite_warnings
        res['warnings'] = global_warnings
        res['errors'] = global_errors
        helper.Helper.write_json_response(self.response, res)

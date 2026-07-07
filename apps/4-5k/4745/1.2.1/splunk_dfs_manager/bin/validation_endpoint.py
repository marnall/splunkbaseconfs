from __future__ import absolute_import
import splunk
from . import helper
from .pbs_global_configs import PbsGlobalConfigs as pbsConf
from .instance_utils import InstanceUtils as instanceUtil
from .messaging import Messaging as msging
import sys


class Validation(splunk.rest.BaseRestHandler):

    def license_check(self, mgmt_port, header, res):
        end_point = "services/licenser/licenses"
        license_data = helper.RestComm.splunk_rest(end_point, header, mgmt_port=mgmt_port)['entry']

        if license_data is None:
            res['has_dfs_license'] = False
            return

        for ld in license_data:
            license_list = ld['content']['features']
            for license in license_list:
                if license == pbsConf.base_lic_name or license == pbsConf.prem_lic_name:
                    res['meta']['has_dfs_license']['success'] = True
                    res['has_dfs_license'] = True

                if license == pbsConf.base_lic_name:
                    res['meta']['has_dfs_license']['basic_lic'] = True

                if license == pbsConf.prem_lic_name:
                    res['meta']['has_dfs_license']['prem_lic'] = True

    # TODO: If 'packaging' is available in Splunk package, replace this function with it
    def parse_version_string(self, version_string):
        return tuple(version_string.split('.'))

    def sh_version_check(self, mgmt_port, header, res):
        endpoint = "/services/server/info"
        resp = helper.RestComm.splunk_rest(endpoint, header, '127.0.0.1', mgmt_port)
        if resp is None:
            error_message = msging.error_obj_map['sh_ver_endpoint_error'].to_json()
            res['errors'].append(error_message)
            res['meta']['sh_version']['success'] = False
            return

        content = resp['entry'][0]['content']

        if 'version' in content:
            res['meta']['sh_version']['version'] = content['version']
            if self.parse_version_string(content['version']) < self.parse_version_string('8.0.0'):
                error_message = msging.error_obj_map['vers_bda'].to_json("Search head")
                res['errors'].append(error_message)
                res['meta']['sh_version']['success'] = False
        else:
            error_message = msging.error_obj_map['sh_ver_info_missing_error'].to_json()
            res['errors'].append(error_message)
            res['meta']['sh_version']['success'] = False

    def indexer_version_check(self, mgmt_port, header, peer_map, res):
        try:
            active_list = helper.RestComm.get_config_using_rest(pbsConf.conf_name, pbsConf.conf_stanza, "active_list",
                                                                header, mgmt_port, '127.0.0.1')
            active_set = set(active_list.split(","))
            active_set.discard("")

            for worker in active_set:
                if worker in peer_map:
                    idx_info = peer_map[worker]
                    res['meta']['indexer_version']['versions'].append(worker + ': ' + idx_info['version'])
                    # Commenting out the scenario for federated currently
                    # if self.parse_version_string(idx_info['version']) < self.parse_version_string('6.5.5'):
                    #     error_message = msging.error_obj_map["vers_fed"].to_json(worker)
                    #     res['errors'].append(error_message)
                    #     res['meta']['indexer_version']['success'] = False

                    if self.parse_version_string(idx_info['version']) < self.parse_version_string('8.0.0'):
                        error_message = msging.error_obj_map['vers_bda'].to_json(worker)
                        res['errors'].append(error_message)
                        res['meta']['indexer_version']['success'] = False

                else:
                    res['warnings'].append(msging.warn_obj_map["lost_peer_warn"].to_json(suffix=worker))

        except Exception as e:
            res['errors'].append(msging.error_obj_map["exception"].to_json("Validation ", e.message))

    def os_check(self, peer_map, res):
        res['meta']['os_check']['success'] = True
        for peer in peer_map:
            os = peer_map[peer]['os_name']
            if os == "":
                res['warnings'].append(msging.warn_obj_map["os_warn"].to_json())

            if os.lower() != "linux":
                prefix = peer + " OS is " + os + "."
                res['errors'].append(msging.error_obj_map['os_error'].to_json(prefix))
                res['meta']['os_check']['success'] = False

    def conf_check(self, mgmt_port, header, res):
        dfs_disabled = helper.RestComm.get_config_using_rest("server", pbsConf.dfs_stanza, "disabled", header,
                                                             mgmt_port)
        if dfs_disabled is True:
            res['errors'].append(msging.error_obj_map["dfs_disabled"].to_json())
            res['dfs_enabled'] = False
            return

        res['dfs_enabled'] = True

    def handle_GET(self):
        with open("/tmp/py_ver", "w") as f:
            f.write("DFS Manager running Python {}\n".format(sys.version))

        header = {'Authorization': 'Splunk ' + self.sessionKey}
        res = {
            'is_admin': None,
            'user': '',
            'instance_type': '',
            'sh_captain': '',
            'actionable_errors': [],
            'dfs_enabled': '',
            'errors': [],
            'warnings': [],
            'meta': {
                'warn': [],
                'sh_version': {'version': "", 'success': True},
                'indexer_version': {'versions': [], 'success': True},
                'os_check': {'success': True},
                'spark_master_check': {'success': True},
                'spark_history_check': {'success': True}
            }
        }

        mgmt_port = helper.Helper.get_splunkd_mgmt_port()
        if mgmt_port is None:
            res['errors'].append(msging.error_obj_map["mgmt_port"].to_json())
            helper.Helper.write_json_response(self.response, res)
            return

        phase = "Getting user, role and clustering information"
        try:
            role, valid_role = instanceUtil.get_instance_type(mgmt_port, header, res)
            phase = "Checked roles"
            instanceUtil.get_user(mgmt_port, header, res)
            phase = "Checked user"
            if res["is_admin"] is True:
                instanceUtil.get_sh_captain(mgmt_port, header, res)
                phase = "Checked Captain"
                self.sh_version_check(mgmt_port, header, res)
                phase = "Checked Search Head Version"

                # gate checks based on whether we're on a valid role
                if valid_role is True:
                    _, _, peer_map = helper.RestComm.get_search_peers_keys_app(mgmt_port, header)
                    phase = "Checked Peers"
                    # self.license_check(mgmt_port, header, res)
                    self.indexer_version_check(mgmt_port, header, peer_map, res)
                    self.os_check(peer_map, res)
                    self.conf_check(mgmt_port, header, res)
                elif role == "sh":
                    self.conf_check(mgmt_port, header, res)
                else:
                    res['meta']['warn'].append("Currently not on a valid PBS search head")
            else:
                res['errors'].append(msging.error_obj_map["user_role_error"].to_json())
            helper.Helper.write_json_response(self.response, res)
        except Exception as e:
            self.response.write("Failed: " + phase + " - " + e.message)

    handle_POST = handle_GET

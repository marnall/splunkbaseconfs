from __future__ import absolute_import
from builtins import object
from . import helper
from .pbs_global_configs import PbsGlobalConfigs as pbsConf
from .messaging import Messaging as msging


class InstanceUtils(object):
    @staticmethod
    def pretty_role(role):
        output = role
        if role == "shc_member":
            output = "sh"
        if role == "search_head":
            output = "sh"
        if role == "shc_captain":
            output = "sh"

        return output

    @staticmethod
    def get_server_info(mgmt_port, header):
        get_path = "/services/server/info"
        try:
            resp = helper.RestComm.splunk_rest(get_path, header, '127.0.0.1', mgmt_port)
            content = resp['entry'][0]['content']
            sh_server_roles = content['server_roles']
            host = content['host']
            guid = content['guid']
        except Exception:
            return None, None, None

        return sh_server_roles, host, guid

    @staticmethod
    def get_search_head_info(mgmt_port, header):
        res = {"valid_sh_role": False, "role": ""}
        server_roles, host, guid = InstanceUtils.get_server_info(mgmt_port, header)
        if server_roles:
            # host_ip = socket.gethostbyname(host)
            is_sh = "search_head" in server_roles
            is_sh_clustered = ("shc_member" in server_roles) or ("shc_captain" in server_roles)
            is_captain = "shc_captain" in server_roles
            is_indexer = "indexer" in server_roles

            if is_sh_clustered:
                res['role'] = "shc_member"

            if not is_sh and is_indexer:
                res['role'] = helper.RestComm.get_config_using_rest(pbsConf.conf_name, pbsConf.conf_stanza, "role",
                                                                    header, mgmt_port, "127.0.0.1")

            if is_captain or (is_sh and not is_sh_clustered):
                if is_captain:
                    res['role'] = "shc_captain"
                else:
                    res['role'] = "search_head"
                res['valid_sh_role'] = True

        return res

    @staticmethod
    def get_instance_type(mgmt_port, header, res):
        role, role_info = "", {}
        try:
            role_info = InstanceUtils.get_search_head_info(mgmt_port, header)
            role = InstanceUtils.pretty_role(role_info['role'])
            if role_info['valid_sh_role'] is True:
                role = "sh_editable"

        except Exception:
            res['errors'].append(msging.error_obj_map["lost_role"].to_json())

        res['instance_type'] = InstanceUtils.pretty_role(role)
        return role, role_info['valid_sh_role']

    @staticmethod
    def get_user(mgmt_port, header, res):
        endpoint = "/services/authentication/current-context/context"
        context_object = helper.RestComm.splunk_rest(endpoint, header, mgmt_port=mgmt_port)
        username = context_object['entry'][0]['content']['username']
        res['user'] = username
        roles = context_object['entry'][0]['content']['roles']
        res['is_admin'] = True if "admin" in roles else False

    @staticmethod
    def get_sh_captain(mgmt_port, header, res):
        server_roles, _, _ = InstanceUtils.get_server_info(mgmt_port, header)
        if ("shc_member" in server_roles) or ("shc_captain" in server_roles):
            end_point = "/services/shcluster/status"
            shc_info = helper.RestComm.splunk_rest(end_point, header, '127.0.0.1', mgmt_port)
            if not shc_info:
                res['errors'].append(msging.error_obj_map['miss_capt'].to_json())

        captain_uri = helper.RestComm.get_config_using_rest(pbsConf.conf_name, pbsConf.conf_stanza,
                                                            'splunk_master_uri', header, mgmt_port)
        if not captain_uri:
            captain_uri = "-"
            res['warnings'].append(msging.warn_obj_map["no_cap_addrs"].to_json())

        res['sh_captain'] = captain_uri

from __future__ import absolute_import
from builtins import object
import os
from . import helper
from .pbs_global_configs import PbsGlobalConfigs as pbsConf


# Simple class for storing all file, stanza, and accepted params
class FileStanzaMap(object):
    def __init__(self, confName, confStanza, acceptedCommands):
        self.confName = confName
        self.confStanza = confStanza
        self.acceptedCommands = acceptedCommands


class SettingsUtils(object):

    # All of these params must be under [pbs] stanza
    accepted_pbs_confs = [
        'spark_master_port',
        'spark_master_webui_port',
        'spark_history_webui_port',
        'security',
        'site_affinity',
        'spark_local_dirs_root',
        'spark_local_dirs_auto_clean_up_enabled',
        'spark_local_dirs_ttl_sec'
    ]

    # All of these params must be under [dfs] stanza
    accepted_lim_confs = [
        'dfs_max_remote_pipeline',
        'dfc_num_slots',
        'dfs_max_num_keepalives',
        'dfs_remote_search_timeout',
        'dfw_receiving_data_port',
        'dfw_receiving_data_port_count',
        'dfc_control_port'
    ]

    # All of these params must be under [dfs] stanza
    accepted_ser_confs = [
        'port'
    ]

    file_stanza_mapping = {
        "pbs": FileStanzaMap(pbsConf.conf_name, pbsConf.conf_stanza, accepted_pbs_confs),
        "lim": FileStanzaMap(pbsConf.dfs_limits_conf_name, pbsConf.dfs_stanza, accepted_lim_confs),
        "ser": FileStanzaMap(pbsConf.dfs_server_conf_name, pbsConf.dfs_stanza, accepted_ser_confs)
    }

    @staticmethod
    def get_confs_from_generic_request(response):
        conf_map = {}
        for elem in response["entry"]:
            name = elem["name"]
            val = elem["content"]
            conf_map[name] = val
        return conf_map

    @staticmethod
    def get_current_settings(mgmt_port, header):
        conf_data_map = {
            "pbs": SettingsUtils.get_confs_from_generic_request(
                helper.RestComm.get_config_using_rest(pbsConf.conf_name, pbsConf.conf_stanza, "", header, mgmt_port)),
            "lim": SettingsUtils.get_confs_from_generic_request(
                helper.RestComm.get_config_using_rest(pbsConf.dfs_limits_conf_name, pbsConf.dfs_stanza, "", header,
                                                      mgmt_port)),
            "ser": SettingsUtils.get_confs_from_generic_request(
                helper.RestComm.get_config_using_rest(pbsConf.dfs_server_conf_name, pbsConf.dfs_stanza, "", header,
                                                      mgmt_port))
        }

        extracted_confs_map = {}
        port_map = {}

        # Can conf data be None, currently we just skip and continue populating the object
        for conf, conf_data in list(conf_data_map.items()):
            accept_params = SettingsUtils.file_stanza_mapping[conf].acceptedCommands
            if conf_data is not None:
                for key, value in list(conf_data.items()):
                    if key in accept_params:
                        # TODO: if need more key specific filters create helper for this
                        if 'port' in key and key != 'dfw_receiving_data_port_count':
                            value = str(value)
                            port_map[key] = value

                        # eliminating env variables for full path
                        if key == "spark_local_dirs_root":
                            value = os.path.expandvars(value)

                        if key == "spark_local_dirs_auto_clean_up_enabled":
                            # possible that we get 0/1 ?
                            # Defaulting value to true for now. May need to handle each case explicitly
                            val = value.lower()
                            value = True
                            if val == "false":
                                value = False

                        if key == "spark_local_dirs_ttl_sec":
                            value = float(value)

                        extracted_confs_map[key] = value

        return port_map, extracted_confs_map

    # TODO: Extend this to support advanced settings port ranges
    @staticmethod
    def duplicate_port_check(port_map, req):
        for param in req:
            if 'port' in param and param != 'dfw_receiving_data_port_count':
                port_map[param] = int(req[param])

        port_vals = port_map.values()
        has_dup_port_vals = len(port_vals) > len(set(port_vals))
        return has_dup_port_vals

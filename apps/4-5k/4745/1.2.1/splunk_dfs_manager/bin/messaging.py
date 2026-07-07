from __future__ import absolute_import
from builtins import object
from .pbs_global_configs import PbsGlobalConfigs as pbsConf


class Message(object):
    m_type = None
    message = None

    def __init__(self, m_type, message):
        self.m_type = m_type
        self.message = message

    def to_json(self, prefix=None, suffix=None):
        final_message = self.message

        if prefix:
            final_message = prefix + " " + final_message

        if suffix:
            final_message = final_message + " " + suffix

        msg = {
            "type": self.m_type,
            "message": final_message
        }
        return msg


class Messaging(object):
    type_map = {
        "warn_multi_site": "multi_site_warning",
        "warn_lost_peer": "missing_peer_warning",
        "version": "version_error",
        "mgmt_port": "unknown_management_port",
        "exception": "general_exception",
        "spark_master": "spark_master_error",
        "spark_history": "spark_history_warning",
        "shc_error": "search_head_clustering_error",
        "os_error": "operating_system_error",
        "conf_error": "configuration_error",
        "role_error": "instance_role_error",
        "setting_error": "settings_update_error",
        "manage_error": "spark_manage_error",
        "spark_cluster_info": "spark_cluster_info_error",
        "no_worker_map": "spark_worker_mapping_error",
        "general_error": "general_error",
        "user_role": "user_role_error"
    }

    error_obj_map = {
        "general_error": Message(type_map["general_error"], ""),
        "vers_fed": Message(type_map["version"], "has Splunk version less than 6.5.5. Splunk version under 6.5.5 is "
                                                 "unsupported for federated queries. "),
        "vers_bda": Message(type_map["version"], ' has Splunk version less than 8.0.0. Splunk version under 8.0.0 '
                                                 'is unsupported for DFS Manager App. '),
        "mgmt_port": Message(type_map["mgmt_port"], "Management port error: Failed to access the management port."),
        "miss_capt": Message(type_map["shc_error"], "Search head cluster error: Search head cluster has been detected, "
                                                    "but no search head captain is present. "
                                                    "Please wait until a captain has been elected and refresh. "),
        "exception": Message(type_map["exception"], "General Exception:"),
        "os_error": Message(type_map["os_error"], "Operating system error: DFS only runs on Linux x86-64 systems. "),
        "dfs_disabled": Message(type_map["conf_error"], "Configuration setting error: DFS is not enabled in the"
                                                        " server configuration file. "),
        "lost_role": Message(type_map["role_error"], "Component identification error: Unable to identify the"
                                                     " component (search head / indexer). "),
        "sett_key_error": Message(type_map["setting_error"], "is not a valid key. "),
        "sett_dup_error": Message(type_map["setting_error"], "Failed to apply settings, duplicate ports were detected, "
                                                             "please try again"),
        "sett_rest_error": Message(type_map["setting_error"], "Setting error: Unable to modify parameter:"),
        "invalid_cmd": Message(type_map["manage_error"], "Invalid command:"),
        "failed_add": Message(type_map["manage_error"], "Add worker error: Failed to add Spark worker. "),
        "clstr_no_workers": Message(type_map["spark_cluster_info"], "No workers registered to spark master. "),
        "clstr_no_spark_info": Message(type_map["spark_cluster_info"], "Spark master error: Failed to get"
                                                                       " Spark master information. "),
        "clstr_no_spark_master_card": Message(type_map["spark_cluster_info"], "Failed to get spark master details. "),
        "clstr_no_idx": Message(type_map["spark_cluster_info"], "is not registered as an indexer. "),
        "sh_ver_endpoint_error": Message(type_map["version"], "Could not access the server info for the search head. "),
        "sh_ver_info_missing_error": Message(type_map["version"], "Version information not populated in "
                                                                  "search head server/info. "),
        "spark_master_connect_error": Message(type_map["spark_master"], "Unable to connect to the Spark Master. "),
        "spark_master_precheck_error": Message(type_map["spark_master"], "Error while trying to get the "
                                                                         "spark master / history server details. "),
        "user_role_error": Message(type_map["user_role"], "Administrator privileges required to use Splunk DFS Manager. ")
    }

    warn_obj_map = {
        "clstr_no_history_info": Message(type_map["spark_cluster_info"], "Spark history error: Failed to get"
                                                                         " Spark history information. "),
        "spark_history_connect_error": Message(type_map["spark_history"],
                                               "Unable to connect to the Spark History Server. "),
        "mul_site_connect_warn": Message(type_map["warn_multi_site"], "Multisite warning: Local host cannot connect to "
                                                                      "the REST endpoint "
                                                                      "services/cluster/searchhead/searchheadconfig	"),
        "mul_site_clustering_warn": Message(type_map["warn_multi_site"], "Multisite cluster warning: Multi-site clustering "
                                                                         "is not set on the search head. "
                                                                         "Please set multisite=true in server.conf. "),
        "mul_site_no_site_warn": Message(type_map["warn_multi_site"], "Site not set on the search head for "
                                                                      "multi-clustering deployment. "),
        "mul_site_no_info": Message(type_map["warn_multi_site"], "Could not get site information for the workers. "),
        "lost_peer_warn": Message(type_map["warn_lost_peer"], "Could not find the peer:"),
        "no_worker_mapping": Message(type_map["no_worker_map"], "Couldn't find a worker id for this peer. "
                                                                "Please ensure the DFSManager app modular input is running. "),
        "unavai_resource_utils": Message(type_map["spark_cluster_info"], "Could not access resource "
                                                                         "utilization information for this peer. "),
        "os_warn": Message(type_map["os_error"], " Unable to reach this peer for the Operating System Check. "
                                                 "Please ensure this peer is running. "),
        "no_cap_addrs": Message(type_map["shc_error"], "Unable to determine Search Head (Captain) address. "),
        "no_app_install": Message(type_map["spark_cluster_info"], (pbsConf.app_name + " app is not active, if this "
                                                                                      "warning persists please check that"
                                                                                      " the app is installed and enabled"
                                                                                      " on this search peer. "))
    }

from future.standard_library import install_aliases
install_aliases()  # noqa: E402
from builtins import object


class PbsGlobalConfigs(object):
    base_lic_name = "DataFabricSearch"
    prem_lic_name = "FederatedSearchPremium"
    dfs_stanza = "dfs"
    app_name = "splunk_dfs_manager"
    conf_name = 'spark_app'
    dfs_limits_conf_name = 'limits'
    dfs_server_conf_name = 'server'
    conf_stanza = 'pbs'
    wrkr_objs = 'worker_objects'
    spark_version = '2.3.3'
    worker_objects_response = {}
    spark_master_host_key = "spark_master_host"
    spark_master_port_key = "spark_master_port"
    spark_master_webui_port_key = "spark_master_webui_port"
    spark_history_webui_port_key = "spark_history_webui_port"
    history_server_enabled_key = "history_server_enabled"
    active_list_key = "active_list"
    security_status_key = "security"

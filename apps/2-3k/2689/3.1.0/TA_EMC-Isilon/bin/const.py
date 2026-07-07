import platform

SOURCETYPE = "emc:isilon:rest"
VERIFY_SSL = True
TA_NAME = "TA_EMC-Isilon"

DEFAULT_MANAGEMENT_PORT = "8089"

AUTH_TYPE = "basic"
RESPONSE_TYPE = "json"
REQUEST_TIMEOUT = 120
BACKOFF_TIME = 10
HTTP_METHOD = "GET"
ISILON_PORT = "8080"

UID_TO_USERNAME_ENDPOINT = "https://{}:{}/platform/1/auth/users/UID:{}"

# For retry mechanism
RETRY_ATTEMPTS = 3
BACKOFF_FACTOR = 1
STATUS_FORCELIST = list(range(500, 600)) + [429]
ALLOWED_METHODS = False

if platform.system() == "Windows":
    UPGRADE_SCRIPT_STANZA = "script://$SPLUNK_HOME\\etc\\apps\\TA_EMC-Isilon\\bin\\upgrade_existing_app.py"
else:
    UPGRADE_SCRIPT_STANZA = "script://$SPLUNK_HOME/etc/apps/TA_EMC-Isilon/bin/upgrade_existing_app.py"

INPUTS_CONF_FILE = "inputs"
ACCOUNTS_CONF_FILE = "ta_emc_isilon_account"

DYNAMIC_API_VERSION_CONFIGURATION = {
    "AD": {
        "onefs_base_version": "9.2.0.0",
        "API_base_version": "1",
        "API_alternate_version": "12"
    },
    "Quotas": {
        "onefs_base_version": "9.2.0.0",
        "API_base_version": "10",
        "API_alternate_version": "12"
    }
}

MAPPING_DICT = {
    "/platform/1/statistics/current?keys=node.ifs.bytes.in.rate,node.ifs.bytes.out.rate&devid=all": "platform_1_statistics_current_keys_in_out_devid_all",
    "/platform/1/statistics/current?substr=true&keys=node.clientstats.active&devid=all": "platform_1_statistics_current_substr_true_keys_client_stats_active_devid_all",
    "/platform/1/statistics/current?substr=true&keys=node.clientstats.connected&devid=all": "platform_1_statistics_current_substr_true_keys_connected_devid_all",
    "/platform/1/statistics/current?keys=cluster.cpu.user.max,cluster.cpu.sys.max": "platform_1_statistics_current_keys_user_max_sys_max",
    "/platform/1/statistics/current?keys=node.net.ext.bytes.in.rate,node.net.ext.bytes.out.rate&devid=all": "platform_1_statistics_current_keys_in_rate_out.rate_devid_all",
    "/platform/1/statistics/current?substr=true&keys=node.ifs.heat&devid=all": "platform_1_statistics_current_substr_true_keys_heat_devid_all",
    "/platform/1/statistics/current?substr=true&keys=node.ifs.cache&devid=all": "platform_1_statistics_current_substr_true_keys_cache_devid_all",
    "/platform/1/statistics/current?substr=true&keys=cluster.protostats": "platform_1_statistics_current_substr_true_keys_protostats",
    "/platform/1/statistics/current?substr=true&keys=node.sensor.volt.volts,node.sensor.temp.celsius,node.sensor.fan.rpms,sensor.power.watts&devid=all": "platform_1_statistics_current_substr_true_keys_volts_celsius_rpms_watts_devid_all",
    "/platform/1/statistics/current?keys=cluster.net.ext.bytes.in.rate,cluster.net.ext.bytes.out.rate": "platform_1_statistics_current_keys_cluster_in_rate_cluster_out_rate",
    "/platform/1/statistics/current?keys=ifs.bytes.in.rate,ifs.bytes.out.rate": "platform_1_statistics_current_keys_ifs_in_rate_ifs_out_rate",
    "/platform/1/statistics/current?key=cluster.node.count.down": "platform_1_statistics_current_key_cluster_down",
    "/platform/1/statistics/current?keys=node.memory.free,node.memory.used&devid=all": "platform_1_statistics_current_keys_memory_free_memory_used_devid_all",
    "/platform/3/statistics/summary/system": "platform_3_statistics_summary_system",
    "/platform/1/statistics/current?keys=node.cpu.user.max,node.cpu.sys.max,node.health&devid=all": "platform_1_statistics_current_keys_user_max_sys_max_health_devid_all",
    "/platform/1/statistics/current?keys=node.ifs.bytes.used,node.ifs.bytes.free,node.ifs.bytes.total,node.ifs.ssd.bytes.used,node.ifs.ssd.bytes.total,node.ifs.ssd.bytes.free&devid=all": "platform_1_statistics_current_keys_bytes_used_bytes_free_bytes_total_bytes_used_bytes_total_bytes_free_devid_all",
    "/platform/1/statistics/current?keys=ifs.bytes.avail,ifs.bytes.free,ifs.bytes.used,ifs.bytes.total,ifs.percent.used,ifs.percent.avail,ifs.ssd.bytes.free,ifs.ssd.bytes.used&devid=all": "platform_1_statistics_current_keys_ifs_avail_ifs_free_ifs_used_ifs_total_ifs_used_ifs_avail_ifs_free_ifs_used_devid_all",
    "/platform/1/statistics/current?key=node.disk.access.latency.avg&devid=all": "platform_1_statistics_current_key_latency_avg_devid_all",
    "/platform/1/statistics/current?key=node.uptime&devid=all": "platform_1_statistics_current_key_node_uptime_devid_all",
    "/platform/1/statistics/current?substr=true&keys=node.disk.health&devid=all": "platform_1_statistics_current_substr_true_keys_node_disk_health_devid_all",
    "/platform/7/network/interfaces": "platform_7_network_interfaces",
    "/platform/3/event/eventlists?begin=$get_events_from_version$": "platform_3_event_eventlists_begin_get_events_from_version",
    "/platform/1/statistics/current?keys=cluster.node.list.all,cluster.node.list.diskless,cluster.node.list.readonly": "platform_1_statistics_current_keys_cluster_all_cluster_diskless_cluster_readonly",
    "/platform/1/statistics/current?key=node.cpu.count&devid=all": "platform_1_statistics_current_key_cpu_count_devid_all",
    "/platform/1/storagepool/storagepools": "platform_1_storagepool_storagepools",
    "/platform/1/protocols/smb/shares": "platform_1_protocols_smb_shares",
    "/platform/1/zones": "platform_1_zones",
    "/platform/1/protocols/nfs/exports": "platform_1_protocols_nfs_exports",
    "/platform/1/cluster/config": "platform_1_cluster_config",
    "/platform/1/statistics/current?substr=true&keys=node.disk.name,node.disk.lnum,node.disk.type&devid=all": "platform_1_statistics_current_substr_true_keys_node_disk_name_disk_lnum_disk_type_devid_all",
    "/platform/1/storagepool/tiers": "platform_1_storagepool_tiers",
    "/platform/1/storagepool/settings": "platform_1_storagepool_settings",
    "/platform/1/storagepool/nodepools": "platform_1_storagepool_nodepools",
    "/platform/1/license/licenses": "platform_1_license_licenses",
    "/platform/1/cluster/external-ips": "platform_1_cluster_external_ips",
    "/platform/1/auth/users": "platform_1_auth_users",
    "/platform/1/cluster/statfs": "platform_1_cluster_statfs",
    "/platform/<api_version>/auth/providers/ads/$get_ad_domains$/search?search_users=true&limit=1000": "platform_auth_providers_ads_get_ad_domains_search_users_true_limit_1000",
    "/platform/1/statistics/current?key=node.clientstats.active.cifs&devid=all": "platform_1_statistics_current_key_active_cifs_devid_all",
    "/platform/1/statistics/current?key=node.clientstats.connected.cifs&devid=all": "platform_1_statistics_current_key_connected_cifs_devid_all",
    "/platform/1/statistics/current?key=cluster.protostats.cifs.total": "platform_1_statistics_current_key_cifs_total",
    "/platform/1/statistics/current?key=node.clientstats.active.nfs&devid=all": "platform_1_statistics_current_key_active_nfs_devid_all",
    "/platform/<api_version>/quota/quotas": "platform_quota_quotas"
}

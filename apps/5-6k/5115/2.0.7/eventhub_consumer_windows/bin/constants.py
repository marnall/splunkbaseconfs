APP_NAME = 'eventhub_collector'
EVENTHUB_CONF_FILE = 'eventhubs'
GLOBAL_STANZA = 'global'
PASSWORD_MASK = '*****'
EVENTHUB_FIELDS = {
    "eventhub_name": str,
    "namespace": str,
    "sas_policy": str,
    "storage_type": str,
    "blob_storageaccount": str,
    "blob_container": str,
    "consumer_group": str,
    "prefetch": int,
    "timeout": int,
    "run_duration": int
}



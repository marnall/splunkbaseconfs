from constants import EVENTHUB_CONF_FILE, GLOBAL_STANZA

GLOBALS = {}


class EventHub:

    def __init__(self, **kwargs):
        self.namespace = kwargs.get('eventhub_namespace', '')
        self.event_hub = kwargs.get('eventhub_name', '')
        user = kwargs.get('sas_policy', '')
        self.sas_policy = user.split(':')[1] if ':' in user else user
        self.realm = user.split(':')[0] if ':' in user else None
        self.sas_key = kwargs.get('sas_key', '')
        self.storage = kwargs.get('storage_type', '')
        blob_user = kwargs.get('blob_storageaccount', '')
        self.storageaccount = blob_user.split(':')[1] if ':' in blob_user else blob_user
        self.blob_key = kwargs.get('blob_storageaccount_key', '')
        self.blob_realm = blob_user.split(':')[0] if ':' in blob_user else None
        self.container = kwargs.get('blob_container', '')
        self.consumer_group = kwargs.get('consumer_group', '$Default')
        self.prefetch = kwargs.get('prefetch', 100)
        self.timeout = kwargs.get('timeout', 10)
        self.run_duration = kwargs.get('run_duration', 60)

    def as_dict(self):
        return {
            'eventhub_namespace': self.namespace,
            'eventhub_name': self.event_hub,
            'sas_policy':  f'{self.realm}:{self.sas_policy}' if self.realm else self.sas_policy,
            'sas_key': self.sas_key,
            'storage_type': self.storage,
            'blob_storageaccount':  f'{self.blob_realm}:{self.storageaccount}' if self.blob_realm else self.storageaccount,
            'blob_storageaccount_key': self.blob_key,
            'blob_container': self.container,
            'consumer_group': self.consumer_group,
            'prefetch': self.prefetch,
            'timeout': self.timeout,
            'run_duration': self.run_duration
        }

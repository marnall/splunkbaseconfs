[eventhub_consumer://<name>]

eventhub_name = <value>
* The name of the Azure EventHub to retrieve data from.

eventhub_namespace = <value>
* The Azure namespace the EventHub instance belongs to.

sas_policy = <value>
* The name of the SAS policy credential as defined above.

sas_key = <value>
* The SAS policy credential key.

storage_type = <value>
* Storage type used for EventHub checkpoint data.

blob_container = <value>
* Azure Blob storage container. Required when using Blob storage.

blob_storageaccount = <value>
* Azure Blob storage account credential. Required when using Blob storage.

blob_storageaccount_key = <value>
* Azure Blob storage account credential key. Required when using Blob storage.

consumer_group = <value>
* Azure EventHub consumer group.

prefetch = <value>
* Number of messages to pre-fetch from each partition.

timeout = <value>
* Azure EventHub read timeout (in seconds).

run_duration = <value>
* Number of seconds the Event Processor will run for. Should generally be less than the input interval.



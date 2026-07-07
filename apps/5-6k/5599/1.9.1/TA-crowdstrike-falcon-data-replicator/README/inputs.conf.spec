[crowdstrike_fdrv2_aidmaster://<name>]
credentials = 
sqs_queue = Enter the SQS URL provide by CrowdStrike
start_date = On the initial collection only data that was sent to the S3 bucket on and after this date will be collected.
force_start_date = This will force the collection to use the 'Initial Start Date' field, ignoring and overwriting any existing saved checkpoints. Uncheck after initial collection.

[crowdstrike_fdrv2_managed_assets://<name>]
credentials = 
sqs_queue = Enter the SQS queue information provided by CrowdStirke
start_date = Data that was sent to the S3 bucket on and after this date will be collected (first ingest only)
force_start_date = This will force the collection to use the 'Initial Start Date' field, ignoring and overwriting any existing saved checkpoints. Uncheck after initial collection.

[crowdstrike_fdrv2_userinfo://<name>]
credentials = 
sqs_queue = Enter the SQS URL provided by CrowdStrike
start_date = On the initial collection only data that was sent to the S3 bucket on and after this date will be collected.
force_start_date = This will force the collection to use the 'Initial Start Date' field, ignoring and overwriting any existing saved checkpoints. Uncheck after initial collection.

[crowdstrike_fdrv2_notmanaged://<name>]
credentials = 
sqs_queue = 
start_date = On the initial collection only data that was sent to the S3 bucket on and after this date will be collected.
force_start_date = This will force the collection to use the 'Initial Start Date' field, ignoring and overwriting any existing saved checkpoints.

[crowdstrike_fdr_data://<name>]
credentials = Select the appropriate FDR account
sqs_queue = Enter the FDR SQS URL from the Falcon UI
filter_option = Select if the Event Types in the 'Select Data Folder Event Types' should be included or excluded from collection
event_types_data = Select the Event Types to include or exclude from collection
start_date = Only data that was sent to the S3 bucket after this date will be collected (initial ingest only)
force_start_date = While selected this will force all collections to use the 'Initial Start Date', ignoring and overwriting existing saved checkpoints

[crowdstrike_fdrv2_appinfo://<name>]
credentials = 
sqs_queue = Enter the SQS URL provide by CrowdStrike
start_date = On the initial collection only data that was sent to the S3 bucket on and after this date will be collected.
force_start_date = This will force the collection to use the 'Initial Start Date' field, ignoring and overwriting any existing saved checkpoints. Uncheck after initial collection.
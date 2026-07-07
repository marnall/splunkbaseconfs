

[googleworkspace-pubsub]
param._cam       = <value>
* CIM Actions / Adaptive Response Requirement
param.credential = <value>
* The credential guid to use
param.topic_id   = <value>
* THe topic ID to publish to
param.project_id = <value>
* The project ID that contains the topic id

[googleworkspace-vault-matter]
param._cam            = <value>
* CIM Actions / Adaptive Response Requirement
param.action          = <value>
* The Matter Action to perform
param.matter_id_field = <value>
* The field that contains the matter id
param.credential      = <value>
* The credential guid to us

[googleworkspace-write-big-query]
param._cam             = <object>
* Common Alert Model configuration object.
param.project_id       = <string>
* The Google Big Query Project ID
param.dataset_id       = <string>
* The Google Big Query Dataset ID
param.table_id         = <string>
* The Google Big Query Table ID
param.write_preference = <string>
* Please see the documentation for guidance on choices (https://cloud.google.com/bigquery/docs/batch-loading-data#appending_to_or_overwriting_a_table)
param.credential       = <string>
* The Google Workspace Credential to use
adaptive_results_spl   = <string>

[googleworkspace-alert-action-gmail-send]
param._cam          = <object>
* Common Alert Model configuration object.
param.recipients    = <string>
* The recipient(s) [comma-separated]. If this is a "field name", and the field is in the results, that value will be used instead.
param.subject       = <string>
* Use "${field}" notation to substitute variables. If this is a "field name", and the field is in the results, that value will be used instead.
param.one_email     = <string>
* Should all the results be sent in a single email? If "No", then each result sends a single email.
param.credential    = <string>
param.cc            = <string>
* The CC recipient(s) [comma-separated]. If this is a "field name", and the field is in the results, that value will be used instead.
param.bcc           = <string>
* The BCC recipient(s) [comma-separated]. If this is a "field name", and the field is in the results, that value will be used instead.
param.body_template = <string>
param.use_google    = <string>
param.sender        = <string>
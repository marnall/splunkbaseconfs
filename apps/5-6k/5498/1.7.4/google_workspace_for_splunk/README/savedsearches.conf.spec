[global]
action.googleworkspace-pubsub                                      = [0|1]
* GCP Pub Sub Alert Action
action.googleworkspace-pubsub.param._cam                           = <object>
* Common Alert Model configuration object.
action.googleworkspace-vault-matter                                = [0|1]
* Google Vault Matter Alert Action
action.googleworkspace-vault-matter.param._cam                     = <object>
* Common Alert Model configuration object.
action.googleworkspace-write-big-query                             = [0|1]
* GCP BigQuery Write Table Action
action.googleworkspace-write-big-query.param._cam                  = <object>
* Common Alert Model configuration object.
action.googleworkspace-write-big-query.param.project_id            = <string>
* The Google BigQuery Project ID
action.googleworkspace-write-big-query.param.dataset_id            = <string>
* The Google BigQuery Dataset ID
action.googleworkspace-write-big-query.param.table_id              = <string>
* The Google BigQuery Table ID
action.googleworkspace-write-big-query.param.write_preference      = <string>
* Please see the documentation for guidance on choices (https://cloud.google.com/bigquery/docs/batch-loading-data#appending_to_or_overwriting_a_table)
action.googleworkspace-write-big-query.param.credential            = <string>
* The Google Workspace Credential to use
action.gw-alert-action-gmail-send                                  = [0|1]
* Google Send Email Alert Action
action.gw-alert-action-gmail-send.param._cam                       = <object>
action.gw-alert-action-gmail-send.param.to                         = <string>
action.gw-alert-action-gmail-send.param.recipients                 = <string>
action.gw-alert-action-gmail-send.param.subject                    = <string>
* Use "${field}" notation to substitute variables. If this is a "field name", and the field is in the results, that value will be used instead.
action.gw-alert-action-gmail-send.param.one_email                  = <string>
* Should all the results be sent in a single email? If "No", then each result sends a single email.
action.gw-alert-action-gmail-send.param.credential                 = <string>
action.googleworkspace-alert-action-gmail-send                     = [0|1]
* Google Send Email Alert Action
action.googleworkspace-alert-action-gmail-send.param._cam          = <object>
* Common Alert Model configuration object.
action.googleworkspace-alert-action-gmail-send.param.recipients    = <string>
* The recipient(s) [comma-separated]. If this is a "field name", and the field is in the results, that value will be used instead.
action.googleworkspace-alert-action-gmail-send.param.subject       = <string>
* Use "${field}" notation to substitute variables. If this is a "field name", and the field is in the results, that value will be used instead.
action.googleworkspace-alert-action-gmail-send.param.one_email     = <string>
* Should all the results be sent in a single email? If "No", then each result sends a single email.
action.googleworkspace-alert-action-gmail-send.param.credential    = <string>
action.googleworkspace-alert-action-gmail-send.param.cc            = <string>
* The CC recipient(s) [comma-separated]. If this is a "field name", and the field is in the results, that value will be used instead.
action.googleworkspace-alert-action-gmail-send.param.bcc           = <string>
* The BCC recipient(s) [comma-separated]. If this is a "field name", and the field is in the results, that value will be used instead.
action.googleworkspace-alert-action-gmail-send.param.body_template = <string>
action.googleworkspace-alert-action-gmail-send.param.use_google    = <string>
action.googleworkspace-alert-action-gmail-send.param.sender        = <string>
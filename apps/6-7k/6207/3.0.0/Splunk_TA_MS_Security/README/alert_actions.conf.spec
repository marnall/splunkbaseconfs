
[defender_advanced_hunting]
python.version = python3
param._cam = <json> Active response parameters.
param.account_name = <string> Account Name.
param.environment = <list> Environment.
param.query = <string> Query.
param.tenant_id = <string> Tenant ID.

[defender_update_incident]
python.version = python3
param.incident_id = <string> Incident ID.
param.status = <list> Status.
param.assigned_to = <string> Assigned to.
param.classification = <list> Classification.
param.determination = <list> Determination.
param.tags = <string> Tags.
param.account = <string> Account.
param.environment = <list> Environment
param.tenant_id = <string> Tenant ID.

[defender_update_incident_graph]
python.version = python3
param.incident_id = <string> Incident ID.
param.status = <list> Status.
param.assigned_to = <string> Assigned to.
param.classification = <list> Classification.
param.determination = <list> Determination.
param.customTags = <string> Tags.
param.account = <string> Account.
param.environment = <list> Environment
param.tenant_id = <string> Tenant ID.

[defender_dismiss_azure_alert]
python.version = python3
param.account_name = <string> Account Name.
param.alert_location = <string> Alert Location. It's a required parameter.
param.alert_name = <string> Alert Name. It's a required parameter.
param.subscription_id = <string> Subscription ID. It's a required parameter.

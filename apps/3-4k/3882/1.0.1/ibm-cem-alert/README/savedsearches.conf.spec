[cem_alert_name]
* (Unique) name for your IBM Cloud Event Management alert.

action.cem_webhook = <string>
* Webhook URL auto-generated when creating splunk event source in IBM Cloud Event Management
* (required)

action.cem_resource_name = <string>
* The name of the resource causing the event. Identifies the primary resource that the event is affecting
* (required)

action.cem_resource_type = <string>
* The type of the resource causing the event. Should be used to identify the primary resource that the event is affecting. The value of the type field can be one of the defined key types for resources, eg application, hostname, service. Or it can be a user defined value. If a defined value is used, then the event processing may make use of it during processing, i.e. Server, Database, Storage, etc.
* (required)

action.cem_event_type = <string>
* Description of the type of the event. E.g. Utilization, System status, Threshold breach
* (required)

action.cem_severity = <string>
* The event severity level, which indicates how the perceived capability of the managed object has been affected: Critical, Major, Minor, Warning, Information, Indeterminate
* (required)

action.cem_summary = <string>
* Contains text which describes the event condition. Typically should include the cem_resource_name, cem_resource_type
* (required)

action.cem_custom = <string>
* The additional key-value pairs information with format cem-fields:value separated by comma. E.g. sender.name:$owner$,expiryTime:900,type.statusOrThreshold:$result.OpenFiles$
* (optional)

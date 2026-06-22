[censys_proactive_alert_enrichment_triage]
param.indicator_field = <string> The name of the field whose value will be sent to Censys
param.global_account = <string> The name of the Censys acccount
param._cam = <json> Active response parameters.
param.indicator_type = <string> The indicator type. Valid values are host, web_property and certificate.
param.indicator_port_field = <string> (Optional) The name of the field whose value contains the port.

[censys_reactive_alert_enrichment_triage_es]
param._cam = <json> Adaptive Response parameters.
param.global_account = <string> The name of the Censys acccount
param.field_name = <string> Field Name. It's a required parameter.
param.indicator_type = <string> The indicator type. Valid values are host, web_property and certificate.
param.indicator_port_field = <string> (Optional) The name of the field whose value contains the port.
param.scan_type = <string> (Optional) The scan type. Valid values are manual and automatic.

[censys_reactive_alert_enrichment_ir_rescan_es]
param._cam = <json> Adaptive Response parameters.
param.global_account = <string> The name of the Censys account
param.indicator_type = <string> The indicator type. Valid values are host and web_property.
param.service_ip_field = <string> Field name containing IP address. Required for host indicator type.
param.service_port_field = <string> Field name containing port. Required for host indicator type.
param.service_protocol_field = <string> Field name containing protocol. Required for host indicator type.
param.service_transport_protocol_field = <string> (Optional) Field name containing transport protocol. If not provided, "unknown" will be used.
param.web_origin_hostname_field = <string> Field name containing hostname. Required for web_property indicator type.
param.web_origin_port_field = <string> Field name containing web port. Required for web_property indicator type.

[censys_reactive_alert_enrichment_ir_history_es]
param._cam = <json> Adaptive Response parameters.
param.global_account = <string> The name of the Censys account
param.host_ip_field = <string> Field name containing the IP address. It's a required parameter.
param.start_time = <string> Start time of the host timeline. Equivalent to the To field in the event history UI. This must be the timestamp closest to the current time. Example: 2025-01-02T00:00:00Z or "now" for current time. It's a required parameter.
param.end_time = <string> End time of the host timeline. Equivalent to the From field in the event history UI. This must be the timestamp furthest from the current time. Example: 2025-01-01T00:00:00Z or "-30d@d" for 30 days ago. It's a required parameter.

[censys_reactive_alert_enrichment_ir_related_infra_es]
param._cam = <json> Adaptive Response parameters.
param.global_account = <string> The name of the Censys account
param.indicator_type = <string> The indicator type. Valid values are host, web_property and certificate. It's a required parameter.
param.field = <string> Field name to search upon. It's a required parameter.
param.value = <string> Value to search upon. It's a required parameter.

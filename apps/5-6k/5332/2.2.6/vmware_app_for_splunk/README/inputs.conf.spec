[vmware-cbc-alerts://<default>]
*This is how the Alerts Endpoint is configured

input_name = <value>
* Input Descriptive Name

guid = <value>
* The Distinct Identifier for Table operations

severity = <value>
* The severity level

alert_type = <value>
* The alert type (both, whitelist, analytics)

lookback = <value>
* The number of days to default looking back

query = <value>
* (Optional) The string filter query to perform on the endpoint

credential_guid = <value>
* The guid of the Tenant to use for Authentication

proxy_guid = <value>
* The guid of the proxy to use. Optional.

enrich_events = <boolean>
* Enable to allow additional events. Defaults false.

debug_cbapi = <value>
* Set to "enable" if debug is required.

[vmware-cbc-assets://<default>]
*This is how the Assets Endpoint is configured

input_name = <value>
* Input Descriptive Name

guid = <value>
* The Distinct Identifier for Table operations

include_deregistered = <boolean>
* Should include deregistered devices?

credential_guid = <value>
* The guid of the Tenant to use for Authentication

proxy_guid = <value>
* The guid of the proxy to use. Optional.

debug_cbapi = <value>
* Set to "enable" if debug is required.

deployment_type = <value>
* Comma seperated list of deployment types to gather.

[vmware-cbc-audit://<default>]
*This is how the Audit Logs Endpoint is configured

input_name = <value>
* Input Descriptive Name

guid = <value>
* The Distinct Identifier for Table operations

credential_guid = <value>
* The guid of the Tenant to use for Authentication

proxy_guid = <value>
* The guid of the proxy to use. Optional.

debug_cbapi = <value>
* Set to "enable" if debug is required.

[vmware-cbc-live-query://<default>]
*This is how the Audit Logs Endpoint is configured

input_name = <value>
* Input Descriptive Name

guid = <value>
* The Distinct Identifier for Table operations

credential_guid = <value>
* The guid of the Tenant to use for Authentication

proxy_guid = <value>
* The guid of the proxy to use. Optional.

result_query = <value>
* The query used to retrieve live query results.

lookback = <value>
* The lookback in days used to retrieve results.

debug_cbapi = <value>
* Set to "enable" if debug is required.

[vmware-cbc-vuln://<default>]
*This is how the Vuln Endpoint is configured

input_name = <value>
* Input Descriptive Name

guid = <value>
* The Distinct Identifier for Table operations

risk = <value>
* The minimum risk level

query = <value>
* (Optional) The string filter query to perform on the endpoint

credential_guid = <value>
* The guid of the Tenant to use for Authentication

proxy_guid = <value>
* The guid of the proxy to use. Optional.

debug_cbapi = <value>
* Set to "enable" if debug is required.

[cbc_upgrader://<default>]
* This does Upgrade checking on restarts

guid = <value>
* This should be static at B309635C-9A2D-4535-B78C-4FFC3F198901

[vmware-cbc-authentication-events://<default>]
* Consumes Authentication Events

input_name = <value>
* Input Descriptive Name

guid = <value>
* The Distinct Identifier for Table operations

credential_guid = <value>
* The guid of the Tenant to use for Authentication

proxy_guid = <value>
* The guid of the proxy to use. Optional.

debug_cbapi = <value>
* Set to "enable" if debug is required.

lookback = <value>
* The lookback in days used to retrieve results.
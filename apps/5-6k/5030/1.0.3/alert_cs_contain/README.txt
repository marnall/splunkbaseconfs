###########################################################
####	Host Auto-Containment for CrowdStrike
###########################################################

####	Version Info
This Version:	1.0.3
Release Date:	07/09/2020
App Author:	GROUND Security

####	System Requirements
1) The Splunk server that this alert app runs on needs to be able to send outbound requests to the CrowdStrike API on port 443/tcp.
2) App tested with Splunk Enterprise v8.0.1, but should work for all v8.0.x and may even work on 7.x versions.
3) Requires either the CrowdStrike Falcon App for Splunk (provided by CrowdStrike) or CrowdStrike Falcon Event Streams Technical Add-On (provided by CrowdStrike) for expected log format.
4) This lightweight app should run on any server that Splunk Enterprise is able to run on.

####	How to Use
Note: full instructions available at https://www.groundsecurity.com/crowdstrike-auto-contain/
*** CAUTION! Use of this app will automatically network-contain hosts that match the search! Hosts will need to be lifted from containment using the Falcon console or API! ***
1) Install app on Search Head(s).
2) Add “CrowdStrike Host Contain” action to an alert.
3) Configure action fields:
	a) OAuth2 API Client ID: generate this value from your CrowdStrike console (https://falcon.crowdstrike.com/support/api-clients-and-keys)
	b) OAuth2 API Client Secret: generate this value from your CrowdStrike console (https://falcon.crowdstrike.com/support/api-clients-and-keys)
	It is recommended that you dedicate an API client specifically for this alert action. The only Scope required is Hosts:write.
4) Create your search query on a detection
*** RECOMMENDED: Control the severity level that you use this action on. Here's an example that will auto-contain hosts with a 'High' or 'Critical' severity: 
'cs_get_index' metadata.eventType="DetectionSummaryEvent" | search "event.Severity" > 3

####	Need Support?
Run the search:	index=_internal action=alert_cs_contain
Look for the error code that the script exits with (should be exit code=0)
Email support at info@groundsecurity.com if needed.
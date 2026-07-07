###########################################################
####	URLSonar Threat Scanning for Splunk
###########################################################

####	Version Info
This Version:	1.0.0
Release Date:	12/06/2019
App Author:	GROUND Security

####	System Requirements
1) The Splunk server that this alert app runs on needs to be able to send outbound requests on port 443/tcp.
2) App tested with Splunk Enterprise v8.0.0
3) This lightweight app will run on any server that Splunk is able to run on.

####	How to Use
Note: full instructions available at https://www.groundsecurity.com/splunk-app-urlsonar-threat-scanning/
1) Install app on Search Head(s).
2) Add “Scan URL using URLSonar” action to an alert.
3) Configure action fields:
	a) VirusTotal API Key: join the VirusTotal community at no cost to obtain an API key for your use.
	b) License Key: URLSonar is an affordable subscription-based service; a 7-day trial license can be obtained for no cost, or you can purchase either monthly or annual subscriptions. Subscribe at https://www.groundsecurity.com
	c) Respond To: URLSonar will send the scan results to this endpoint of your choice. Details and the format of this response can be found at https://www.groundsecurity.com/urlsonar-api-docs/
4) Save action and save alert.
5) Pass a field titled "url" in the search for your alert to be sent to URLSonar. Results will be sent to the server listed in the "Respond To" field that you configured on the alert action. 

####	Need Support?
Run the search:	index=_internal *urlsonar*
Look for the error code that the script exits with.
Email support at info@groundsecurity.com if needed.
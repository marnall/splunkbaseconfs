# Cloudsploit Add-on For Splunk

This app contains field mappings to make data from CloudSploit's Splunk integration CIM compliant. For bringing Cloudsploit scan results, events, and alerts into Splunk, follow the below installation instructions.

### Sourcetypes

The accompanying Cloudsploit integration will send data to Splunk in three different sourcetypes: cloudsploit:scan_results, cloudsploit:event, and cloudsploit:alert. cloidsploit:scan_results fits into the CIM Vulnerabilities datamodel.

### Installation

1. Create an HTTP Event Collector input. In Splunk's web interface, select Settings->Data Inputs->HTTP Event Collector and then click New Token. Name your input whatever you'd like, select an index and leave sourcetype on "Automatic". Choose an index if you'd like. Click submit and copy "Token Value" for future use.
2. Click "Global Settings" and make sure that the "All Tokens" option is enabled. Enable it if not. Take note of the HTTP port number here. The default setting is 8088. 
3. Add a new Cloudsploit integration at https://console.cloudsploit.com/integrations. Choose a name and select "Splunk" in the Type dropdown.  Fill in your Token Value from step 1 in the "Token" field. For Splunk Endpoint, use the format https://\<hostname\>:\<port\>/services/collector/event. Hostname is the hostname of the Splunk server you added an input to in step 1. Port will be the port from step 2. An example value for this setting would be https://splunkforwarder01.mycompany.com:8088/services/collector/event
4. Add this routing to any and all events/scans you'd like fed into Splunk. For scans, navigate to Scans->Report Deliveries->Third-Party Integrations in the Cloudsploit console. For events, go to Events->Routings. 
5. You're done! Search for your new data with the Splunk search: "sourcetype=cloudsploit:*"

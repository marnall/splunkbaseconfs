Shibboleth App for Splunk

Thank you for downloading the Shibboleth App for Splunk.
The app should be installed on the indexer and Search Head.
After installation you will need to restart Splunk.

When pointing Shibboleth data to Splunk point all logs to the sourcetype shibboleth:process such as the example below.

inputs.conf
[monitor://<Path to Shibboleth data>]
index = <index where shibboleth data will be sent>
sourcetype = shibboleth:process

After the file monitor is pointed towards the correct sourcetype the app will parse the data according to its log type.

This app is designed to help ingest and visualize data coming from a user's Shibboleth SSO logs. The app will ingest the log data from the shibboleth process log and extract the audit and access events. The resulting data is Cim compliant against the Authentication data model.
# Binary File Declaration

## Delphix Dashboards app for Splunk


### Getting Started


### Prerequisites



*   Splunk version 7.x or later
*   Delphix Engine 5.3.x or later
*   Delphix Dashboards app from Splunkbase or Github


### Steps:



1. Install the Delphix Dashboards app on Splunk
2. Configure the events and metrics indexes
3. Update Macros if Necessary
4. Configure Splunk HEC Token. 
5. Configure Splunk integration on each Delphix Engine


### Install the Delphix Dashboards app on Splunk



1. In Splunk, Apps>Install app from file
2. Browse to the Delphix Dashboards app package. It will be named delphix_dashboards-&lt;version>.tar.gz
3. Only select Upgrade app if there is already an older version of the app installed.
4. Click Upload
5. 
6. The Delphix Dashboards App will now be available on the Apps Menu


### Configure the Splunk HEC Token



1. HEC Tokens are configured under Settings>Data Inputs>HTTP Event Collector
2. Give the token a name
3. Set the Source type to Automatic
4. Set the App Context to Delphix Dashboards
5. Set Allowed indexes to delphix_events and delphix_metrics
6. Set the default index to delphix_events
7. Review and Submit
8. Find the Token Value in Data Inputs > HTTP Event Collector
9. Find HEC Port and SSL Settings inData Inputs > HTTP Event Collector>Global Settings


### Configure the Indexes



1. Indexes are configured under Settings>Indexes
2. Create a new event index for Delphix events (recommended name is ‘delphix_events’)
3. Create a new metrics index for Delphix metrics (recommended name is ‘delphix_metrics’)


### Update Macros if Necessary



1. Macros are configured under Settings>Advanced Search>Search Macros
2. If the index for Delphix events is named something other than ‘delphix_events’, update the ‘delphix_events_index’ macro definition to match: index = “&lt;index_name>”
3. If the index for Delphix metrics is named something other than ‘delphix_metrics’, update the ‘delphix_events_index’ macro definition to match: index = “&lt;index_name>”


### Configure Splunk integration



1. In Delphix Setup>Preferences>Splunk Configuration
2. Enter Splunk Host IP
3. Enter Spunk Port
4. Enter HEC Token Value
5. Set Main Index to delphix_events
6. Change Push Frequency if desired
7. Set SSL to match Splunk Settings
8. Enable Metrics
9. Set Metrics Index to delphix_metrics
10. Change Push Frequency if desired
11. Change Performance Data Granularity if desired
12. Click Send Test Data to test the connection
13. If successful, click Save


### Install the Delphix Dashboards app on Splunk



1. In Splunk, Apps>Install app from file
2. Browse to the Delphix Dashboards app package. It will be named delphix_dashboards-&lt;version>.tar.gz
3. Only select Upgrade app if there is already an older version of the app installed.
4. Click Upload
5. The Delphix Dashboards App will now be available on the Apps Menu
6. Happy Splunking!


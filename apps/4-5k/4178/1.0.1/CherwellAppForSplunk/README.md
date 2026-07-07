Cherwell App For Splunk
==============================

Overview
------------------------------
Cherwell App for Splunk provides an insight into the incidents, configuration item, change requests, tasks and problems that are reported on your Cherwell instance.

* Author - Cherwell
* Version - 1.0.1
* Build - 1
* Creates Index - False
* Uses KV Store - False
* Uses Source type - cherwell:bo:<business_object_name_for_which_data_is_collected>
* Prerequisite - Cherwell Add-on For Splunk
* Compatible with:
    - Splunk Enterprise version: 6.6.x, 7.0.x and 7.1.x
    - OS: Platform independent

Application Installation
------------------------------
This application should be installed on Splunk Search Head instance in your deployment. Follow the link below to install the app based on your deployment:
* [Single-instance Splunk Enterprise](http://docs.splunk.com/Documentation/AddOns/latest/Overview/Singleserverinstall)
* [Distributed Splunk Enterprise](http://docs.splunk.com/Documentation/AddOns/latest/Overview/Distributedinstall)
* [Splunk Cloud](http://docs.splunk.com/Documentation/AddOns/latest/Overview/SplunkCloudinstall)

Setup
----------------------------
Once the app has been installed successfully, you need to change the definition of "cherwell_index" macro used by this app to point to the index in which the data is collected by "Cherwell Add-on For Splunk". By default this macro points to **main** index. Follow below instructions to change the macro definition:
* Login to Splunk Web UI.
* Navigate to **Settings > Advanced search > Search macros**.
* Search for **"cherwell_index"** macro and click on it to edit.
* In the definition text box modify the index name to the one in which the data is being collected by "Cherwell Add-on For Splunk".
* Click on **Save**.

Note: You don't require to change the macro definition if the data is being collected into the **main** index. 

Dashboards
------------------------------
This app contains various dashboards to give you insight into your Cherwell data. Below table provides brief description of each dashboard present in the app:

  | Dashboard Name | Description |
  |---|---|
  | Overview | This dashboard provides a summary of the open incidents, tasks, change requests, and problems on the Cherwell instance.|
  |Incident Summary | This dashboard provides summary of the incidents reported on Cherwell instance.|
  |Incident Analysis | This dashboard provides analysis on the incidents that are reported on Cherwell instance like open incidents based on priority, category and team, average closure time of the incident, etc.|
  |Splunk Created Incidents|This dashboard provides information on the incidents that are reported using Splunk on Cherwell. |
  |Incident Details|This dashboard provides detailed information like owner, customer, status, priority, etc for each incident in a tabular format.|
  |Change Request Summary| This dashboard provides summary of the change requests reported on Cherwell instance.|
  |Change Request Analysis|This dashboard provides analysis on the change requests that are reported on Cherwell instance like open change requests based on priority and team and change requests over time.|
  |Change Request Details|This dashboard provides detailed information like owner, start date, end date, status, priority, etc for each change request in a tabular format.|
|Problem Summary|This dashboard provides summary of the problems reported on Cherwell instance.|
|Problem Details|This dashboard provides detailed information like owner, service, status, priority, etc for each problem in a tabular format.|
|Task Summary|This dashboard provides summary of the tasks reported on Cherwell instance.|
|Task Details|This dashboard provides detailed information like owner, created date, closed date, status, etc for each task in a tabular format.|
|CMDB Summary|This dashboard provides summary of the configuration items and assets.|
|CMDB Details|This dashboard provides detailed information like type, manufacturer, vendor, owner, etc of each configuration item.|


Troubleshooting
------------------------------
* **Visualizations Not Populating**: Verify that "Cherwell Add-on For Splunk" has been installed and configured. You can also verify if the data is being collected or not by using **\`cherwell_index\` sourcetype="cherwell:bo:\*"** query.

Known Limitations
------------------------------
* Sometimes you might observe widgets are being displayed in "All Time" duration and not being displayed or showing inaccurate data in a particular time duration ex: "Last 2 hours" though the data is present. This is because of the Daylight time issue in "Splunk Add-on For Cherwell". Because of this issue in add-on some events may get indexed in future date time when daylight saving is on due to which Splunk fails to capture those events though being present. However these events are captured when "All Time" duration is selected.


Support 
------------------------------

* Is this App supported ? : Yes
* Support Email : integrations@cherwell.com
EVOLVEN CHANGE ANALYTICS (TA)
==================================

https://www.evolven.com

Evolven tracks down granular changes carried out in your end-to-end environment. 
Evolven uses patented machine learning analytics for analyzing the changes it 
collects, and correlating them with ITSI and Splunk events and KPIs. 

This technology add-on imports changes collected by Evolven into Splunk. It provudes 
users with precisely the actionable  insights they need for troubleshooting or 
preventing incidents before the trouble starts.


# Data Collection Setup

Data collection setup involves three steps:
1. Prepare data in Evolven that will be exported
2. Setup up task in Evolven that will peridoically export the data
3. Setup Splunk Universal Forwarder to collect exported data and push them into Evolven


### 1. Setup data to be exported

1. Login to Evolven 
2. Go to Inventory
3. Add new Environment, for example, "Splunk export"
4. Add hosts and environments for which you want to export the changes. You can also use 
rules/filter to dynamically select all hosts/environments that match specifc criteria. 

For more information how to edit environments please look at the Evolven Manual.



### 2. Setup data export in Evolven

Evolven exports data periodically to a file in CSV format. To setup the data export task, 
use the following steps:

1. Login to Evolven
2. Go to section Admin/Reports
3. Click + icon to add new report
4. Fill in the form details:
	- Name: Splunk data export
	- Report type: monitoring
	- Report template: Splunk CSV
	- Schedule: every hour at 00 minutes past hour
	- Environment: "Splunk export" (or other selected environment)
	- Timeframe: last 1 hour
	- Output folder: "C:\Evolven data export" (or other selected folder)
	- Other fields can be left blank or at defualt values
5. Click "Save and Execute Now"

If the task is executed successfully, you should be able to see a newly created file at "C:\Evolven Data Export"


### 3. Setup Splunk Universal Forwarder

1. Install Splunk Universal Forwarder (if not installed already)
2. Open "C:\Program Files\SplunkUniversalForwarder\etc\system\local\inputs.conf"
3. Add the following configurations to monitor data exported by Evolven:
	```
	[monitor://C:\Evolven data export]
	crcSalt = <SOURCE>
	sampletype = csv
	```
4. Save the file and restart Splunk Universal Forwarder service

More information on configuring Splunk Universal Forwarder can be found at 
https://docs.splunk.com/Documentation/Forwarder/7.2.6/Forwarder/Abouttheuniversalforwarder


### Troubleshooting

Please send an email to support@evolven.com.

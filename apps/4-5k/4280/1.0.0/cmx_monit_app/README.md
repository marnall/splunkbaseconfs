****Block Solutions CMX Monitoring App for Splunk****

### OVERVIEW

Overview:	This Splunk app is a single dashboard that displays the key system metrics from CMX.
Author: 		Mike Crooks - Block Solutions
App Name: 	cmx_monit_app 
Version:		v.1.0.0
Vendor Products:	Cisco CMX Application 
Dependencies:	Installation of TA_cmx_monit as this add on collects the data

The cmx_monit_app visualises the key data from a CMX application which allows IT operations to monitor the health of their CMX appliance(s).  Multiple inputs can be used to collect data from multiple CMX instances ensuring that data is all in one place for easy visualisation.  This app simply visualises a single instance of CMX and could be extended by leveraging custom sourcetypes per CMX instance

### INSTALLATION AND CONFIGURATION

Testing

This application has only been tested on single server instance. 
This application has been tested 6.3 + 
Tests have been run on an apple mac

To install this application, follow either of the mechanisms detailed below;

Install .spl file

Launch Splunk Enterprise
Navigate from the home screen to the apps page via the app settings icon
Click install from file
Browse to the .spl file upload

Manually install

•	Download the .zip file
•	Extract the zip file 
•	Copy contents to splunk/etc/apps
•	Restart Splunk 

Configuration

There is no configuration required unless using multiple data inputs.  In this case the dashboard and subsequent dashboards will require ammendent of the searches to include a custom sourcetype.  This app assumes that a sourcetype of "cmx_monit" has been allocated to the modular input and also that a cmx_monit index exists


**SUPPORT**

For queries please contact mcrooks@block.co.uk

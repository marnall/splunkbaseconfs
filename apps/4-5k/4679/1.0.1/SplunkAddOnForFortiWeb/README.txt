*********************************************
*
* Add-On: Fortinet Fortiweb Add-On for Splunk
* Current Version: 1.0
* Last Modified: Jul 2019
* Splunk Version: 7.x
* Author: Fortinet Inc.
*
*********************************************



**** Overview ****

Fortinet FortiWeb Add-On for Splunk is the technical add-on (TA) developed by
Fortinet, Inc. The add-on enables Splunk Enterprise to ingest or map security
, traffic and event logs collected from FortiWeb physical and virtual appliances 
across domains. The key features include:

1. Streamlining authentication and access from FortiWeb such as administrator
  login, user login to Splunk Enterprise Security Access Center

2. Mapping FortiWeb threats information into Splunk Enterprise Security Endpoint Malware
  Center

3. Ingesting attack logs, traffic logs and event logs etc.

Fortinet FortiWeb Add-On for Splunk provides common information model (CIM)
knowledge, advanced “saved search”, indexers and macros to use with other
Splunk Enterprise apps such as Splunk App for Enterprise Security.

**** Dependencies ****

Please make sure FortiWeb version is 6.2.0 or later.

**** Configuration Steps ****

Install Fortinet FortiWeb Add-on for Splunk on search head, indexer, forwarder or single instance Splunk server:

There are three ways to install the add-on:

1. Install from Splunk web UI: Manage Apps->Browse more apps->Search keyword “Fortiweb” and find the add-on with Fortinet logo->Click “Install free” button->Click restart splunk service.
2. Install from file on Splunk web UI: Manage Apps->Install from file->Upload the .tgz file which is downloaded from https://splunkbase.splunk.com/apps ->check the upgrade box-> click restart splunk service.
3. Install from file on Splunk server CLI interface: Extract the .tgz file->Place the SplunkAddOnForFortiWeb folder under $SPLUNK_HOME/etc/apps-> Restart Splunk service.
Add data input on Splunk server:

Through Splunk Web UI:
Settings->Data Input->UDP
Port: 514 (Example, can be modified according to your own plan) 
leave other parameters as is, then click Next.

Source type select 'fwb_log', leave other parameters as is.

Note: the UDP port, 514 in this example should be opened in firewall for logs to pass through.

Fortinet FortiWeb Add-On for Splunk will by default automatically extract FortiWeb log data from inputs with sourcetype 'fwb_log'. 

**** Release Notes ****

v1.0: Jul 2019
        - Initial release

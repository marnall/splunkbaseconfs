Firegen for Microsoft IIS Splunk App version 1.0.
Copyright (C) 2017 Adrian Grigorof All Rights Reserved.

The Firegen for Microsoft IIS app provides several dashboards with statistics compiled from log recorded by Microsoft IIS web server.

The dashboards includes summary, traffic information and errors.

Configuration instructions:

The app is assuming that the Microsoft IIS is configured to the web log activity and that the logs are indexed by Splunk. When accessed for the first time, the application will initiate a setup procedure where the index that contains the Microsoft IIS logs can be specified.

If Splunk is not yet configured to collect Microsoft IIS logs we recommend the following steps:

Configure the IIS logging using the Internet Information Services (IIS) Manager.
Set the logging format as W3C. From the Selected fields, add Bytes Sent and Bytes Received fields (by default they are not logged).
Install the Splunk Add-on for Microsoft IIS (https://splunkbase.splunk.com/app/3185/). This will create the required sourcetype.
Configure Splunk to collect the IIS logs (locally if the Splunk server is on the same server as IIS) or via the Syslog Universal Forwarder installed on the IIS server. 
By default, the websites logs are stored under C:\inetpub\logs\LogFiles. 
During the configuration, we recommend the creation of a dedicated index for the Microsoft IIS logs. 
Once the logs are starting to be indexed by Splunk, the Firegen for Microsoft IIS Splunk app is read to compile the dashboards.
Note: The app will use the local DNS configuration to resolve the IP addresses included in the reports to their corresponding host names. If an IP address does not have a host name associated with it
the app will use the IP address itself in the reports.

For support and comments/suggestions, please contact Adrian Grigorof, adigrio@gmail.com or support@firegen.com.

Copyright (C) 2013 Bee Ware Inc. All Rights Reserved.

Add-on:             Bee Ware
Last Modified:	    14/02/13
Splunk Version:	    4.3 or higher
Author:             Bee Ware

Configure Beeware application for splunk

This application is designed to work with data processed by Beeware ISuite products. You can access to information page at any time in the "Manage Apps" menu, by clicking on "Set up" in beeware app.
Configure the data inputs and source type

In order to see the logs in the beeware application, you will have to configure a data input connected with the source type "beeware".

    If your splunk server is only intended to get logs from beeware iboxes, then just create a data input on the protocol/port you wish (e.g. UDP 514) and select beeware in the list of source types.
    If your splunk server is retreiving logs from other sources, then you can dedicate a listening port to your iboxes. Just create a new data input on that port and select beeware in the list of source types.
    If your splunk server is retreiving logs from other sources and you need to use the same listening port for beeware iboxes. Then you will have to delete that global data input, create one data input by ibox, restricted to its IP address and mapped to the beeware source type. Finally, recreate the global data input initialy deleted.

In the future, remember that if you want to create a customised dashboards, you will need to specify "sourcetype=beeware" in your queries.

Configure syslog alerts on ISuite

Connect to the management ibox with the gui interface and navigate to Management > Alerting.
First of all, you will need to declare the splunk server as a new alerting profile. Clic on "Alerting Profile" and "Add". Specify the profile name (e.g. "splunk"), the IP address of the splunk server, the port and protocol you configured in the data input section just above (e.g. UDP 514).
Now you can do the following actions :

    To store event logs, clic on "Event Log Destination" and "Add". enter a name and select the splunk destination. Clic on the Filters tab and adjust the logs.
    To configure delayed log alerting, clic on "Log Alerting configurations", specify the frequency in minutes, leave format as default and select the splunk server as destination.
    To configure realtime logs, navigate to Setup > Tunnels. Double clic on the tunnel and select the "Logs" tab. Select the types of logs you need and the splunk server as destination. If asked, the alerting format must be set to Default on i-boxes starting from version 5.5 and Light on older versions

Finally, apply your configuration changes. No reboot is needed.
If you need help about configuring syslog alerts on ISuite, you will find usefull information in the mybeeware knowledge base.

MAXMIND App

You will need to install the MAXMIND app in order to translate external IPs to Geo info for the flash maps and geo based reports to work. 
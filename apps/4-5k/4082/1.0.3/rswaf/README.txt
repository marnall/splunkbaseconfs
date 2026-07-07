Copyright (C) 2018 Rohde and Schwarz Cybersecurity Inc. All Rights Reserved.

Add-on:             rswaf
Last Modified:      22/06/2018
Splunk Version:     4.3 or higher
Author:             Rohde and Schwarz Cybersecurity

Configure rswaf application for splunk

This application is designed to work with data processed by rswaf products. You can access to information page at any time in the "Manage Apps" menu, by clicking on "Set up" in rswaf app.
Configure the data inputs and source type

In order to see the logs in the rswaf application, you will have to configure a data input connected with the source type "rswaf".

    If your splunk server is only intended to get logs from rswaf iboxes, then just create a data input on the protocol/port you wish (e.g. UDP 514) and select rswaf in the list of source types.
    If your splunk server is retreiving logs from other sources, then you can dedicate a listening port to your iboxes. Just create a new data input on that port and select rswaf in the list of source types.
    If your splunk server is retreiving logs from other sources and you need to use the same listening port for rswaf iboxes. Then you will have to delete that global data input, create one data input by ibox, restricted to its IP address and mapped to the rswaf source type. Finally, recreate the global data input initialy deleted.

In the future, remember that if you want to create a customised dashboards, you will need to specify "`default_index` sourcetype=rswaf" in your queries.

Configure syslog alerts on Web Application Firewall

Connect to the management ibox with the gui interface and navigate to Management > Alerting.
First of all, you will need to declare the splunk server as a new alerting profile. Clic on "Alerting Profile" and "Add". Specify the profile name (e.g. "splunk"), the IP address of the splunk server, the port and protocol you configured in the data input section just above (e.g. UDP 514).
Now you can do the following actions :

    To store event logs, clic on "Event Log Destination" and "Add". enter a name and select the splunk destination. Clic on the Filters tab and adjust the logs.
    To configure delayed log alerting, clic on "Log Alerting configurations", specify the frequency in minutes, leave format as default and select the splunk server as destination.
    To configure realtime and access logs, navigate to Setup > Tunnels. Double clic on the tunnel and select the "Logs" tab. Select the types of logs you need and the splunk server as destination. If asked, the alerting format must be set to Default on rswaf starting from version 5.5 and Light on older versions

Finally, apply your configuration changes. No reboot is needed.
If you need help about configuring syslog alerts on Web Application Firewall, you will find usefull information in the myrswaf knowledge base.

---Index of rswaf
You will need to configure the macro of your index for this application by the following action:
    In Splunk Web, click Settings, then click Advanced search.
    Next to select "Search macros" and choice "R&S®Web Application Firewall" app  from dropdown list
    Select "default_index" and type your index in format: index=<your_index>.

---MAXMIND App
You will need to install the MAXMIND app in order to translate external IPs to Geo info for the flash maps and geo based reports to work.

Common problem with MAXMIND module:
Problem: The dots are not displayed on map
Reason: The path to GeoLiteCity.dat is not correctly set in default configuration of MAXMIND.
Solution: Edit the file {SPLUNK_HOME}/etc/apps/MAXMIND/bin/geoip.py to make the 2 lines at beginning of file look like this:
DB_PATH = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'MAXMIND','bin','GeoLiteCity.dat')
#DB_PATH=('GeoLiteCity.dat')
Save the file then restart splunk.

---HTTP-User_agent_parser
You will need to install the HTTP-User-Agent_parser app in order to extract formated fields from user agents.

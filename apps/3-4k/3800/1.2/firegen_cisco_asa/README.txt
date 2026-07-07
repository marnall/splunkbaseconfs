Firegen Log Analyzer for Cisco ASA Firewalls App version 1.2.
Copyright (C) 2017 Adrian Grigorof All Rights Reserved.

The Firegen Log Analyzer for Cisco ASA Firewall app provides several dashboards with statistics compiled from the syslog messages recorded by Cisco ASA firewalls.

The dashboards includes summaries, traffic information, denials, reverse DNS for IP addresses included in the reports, management messages and ability to monitor connections to known hacker havens such as Russia and China.

Configuration instructions:

When accessed for the first time, the application will initiate a setup procedure where the index that contains the Cisco ASA logs can be specified.

If Splunk is not yet configured to collect Cisco ASA logs we recommend the following steps:

Install the Splunk Add-on for Cisco ASA: https://splunkbase.splunk.com/app/1620/#/overview. The installation of the add-on is a requirement.

Configure the firewall(s) to send the logs to a dedicated syslog server (using the Splunk UDP collector as "syslog" server is not the optimal way), though the syslog server may run on the Splunk server itself.
Configure Splunk to collect the syslog logs (locally if the syslog server is on the same server as Splunk) or via the Syslog Universal Forwarder installed on the syslog server.
We recommend the creation of a dedicated index with the sourcetype set as cisco:asa. The sourcetype is created once the Splunk Add-on for Cisco ASA is installed.

Note: The app will use the local DNS configuration to resolve the IP addresses included in the reports to their corresponding host names. If an IP address does not have a host name associated with it the app will use the IP address itself in the reports.

For support and comments/suggestions, please contact Adrian Grigorof, adigrio@gmail.com or support@firegen.com.

Splunk App for Juniper SSG Firewalls version 1.1.
Copyright (C) 2017 Adrian Grigorof All Rights Reserved.

The Juniper SSG Firewall Log Analysis app provides several dashboards with statistics compiled from the syslog messages recorded by Juniper SSG Firewalls.

The dashboards includes summaries, traffic information, denials, reverse DNS for IP addresses included in the reports, management messages and ability to monitor connections to known hacker havens such as Russia and China.

Configuration instructions:

When accessed for the first time, the application will initiate a setup procedure where the index that contains the Juniper SSG logs can be specified.

If Splunk is not yet configured to collect Juniper logs we recommend the following steps:

Configure the firewall(s) to send the logs to a dedicated syslog server (using the Splunk UDP collector as "syslog" server is not the optimal way), though the syslog server may run on the Splunk server itself
Configure Splunk to collect the syslog logs (locally if the syslog server is on the same server as Splunk) or via the Syslog Universal Forwarder installed on the syslog server
During the configuration, create a dedicated index for the Juniper SSG logs.
Once the logs are starting to be indexed by Splunk, the Juniper SSG Firewall Log Analysis app is read to compile the dashboards.

Note: The app will use the local DNS configuration to resolve the IP addresses included in the reports to their corresponding host names. If an IP address does not have a host name associated with it
the app will use the IP address itself in the reports.

For support and comments/suggestions, please contact Adrian Grigorof, adigrio@gmail.com or support@firegen.com.

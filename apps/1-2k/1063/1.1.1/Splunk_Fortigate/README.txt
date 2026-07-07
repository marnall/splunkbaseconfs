# ### ### ### ### ### ### ### ### ### ### ### ### ##
#                                                 ##
#   Splunk for Fortigate                          ##
#                                                 ##
#   Description:                                  ##
#       Field extractions and sample reports,     ##
#        and dashboards for the Fortinet          ##
#        Firewall                                 ##
#                                                 ##
#                                                 ##
#                                                 ##
#   Splunk Version:  4.2.x                        ##
#   App Version: 1.1.1                            ##
#   Last Modified:   Mar - 2012                   ##
#   Authors: Abel                                 ##
#   FortiOS supported : 4.0MR3                    ##
#                                                 ##
#                                                 ##
#                                                 ##
#                                                 ##
#                                                 ##
#                                                 ##
# ### ### ### ### ### ### ### ### ### ### ### ### ##


*** Installing ***

To install this app:
- Unpack this file into $SPLUNK_HOME/etc/apps
- Restart Splunk


*** Configuring ***

To get the firewall data into Splunk:

- Configure a port on the Splunk server to listen for UDP traffic. If you do not know how to do this, refer to the online documentation here:

  http://www.splunk.com/base/Documentation/latest/admin/MonitorNetworkPorts

Important: When you configure the input port, you must set the sourcetype of the firewall data to fortigate. Otherwise, the app will not work. 

If you are using UDP input, you will also need to add:

  no_appending_timestamp = true

to the UDP stanza in your inputs.conf file. For example:

[udp://512]
connection_host = ip
sourcetype = fortigate
no_appending_timestamp = true

- Next, configure the firewall device to direct log traffic to the Splunk server on the network port that you specified.


*** Source types ***

As Splunk indexes your Fortigate firewall data, the app will rename the sourcetypes to fortigate_virus, fortigate_ips, fortigate_app-ctrl, fortigate_webfilter, fortigate_traffic, fortigate_sslvpn, fortigate_event_wireless, fortigate_event_auth_captive_portal, fortigate_event_auth_FSSO, fortigate_event_dhcp, fortigate_event_pattern, fortigate_event_his_performance, fortigate_event_config, fortigate_event_ipsec, fortigate_event_system, fortigate_event_dns, fortigate_event
 depending on the logging facility.



*****************************************
*										
* App: Splunk for FortiOS 5			
* Current Version: 1.0					
* Last Modified: Oct 2014				
* Splunk Version: 5.x / 6.x		
* Author: Open3S						
*										
*****************************************

Disclaimer
----------------------------------------
All trademarks and registered trademarks displayed on this app as well as all logos shown are the property of their respective owners.

Overview
-----------------------------------------
Splunk for FortiOS 5 provides visibility into the FortiGate firewall logs. Based on the original app created by Abel.

As you may know with the new release of FortiOS the old app do not work due mainly to changes in the log format. This first release (beta) is aimed to provide the same functionality that have the original app for FortiOS 4.

NOTE: The app will only work with FortiOS 5 logs

Features
--------
 - New extractions based on the FortiOS 5 new log format
 - Some minor fixes on the app

Sourcetypes
-----------
This app contains the following sourcetypes:

 * fortios5_app-ctrl
 * fortios5_event_auth_captive_portal
 * fortios5_event_dhcp
 * fortios5_event_his_performance
 * fortios5_event_ipsec
 * fortios5_event_pattern
 * fortios5_ips
 * fortios5_sslvpn
 * fortios5_traffic
 * fortios5_virus
 * fortios5_webfilter



Feedback is Welcome
-------------------
We plan to continue the development of the app. We are really excited to update it with new features such as Geolocalization and new dashboards!

 - Email: info@open3s.com
 - Website: www.open3s.com


Installation Instructions
-----------------------------------------
The Splunk for FortiOS 5 can be installed by either the Splunk app setup screen, or by manually installing and configuring the app.

Once the app is installed, you need to configure the FortiGate firewall to send the logs to Splunk (udp/513 port). Below is shown the required commands to configure the firewall to send the logs (at date, FortiOS 5 do not support syslog configuration in the Web UI):

# config log syslogd setting
#  set status enable
#  set server <splunk_ip
#  set port 513
# end



Enjoy!


Release Notes
-----------------------------------------
v1.0: Oct 2014
--------------
 - Initial release

v1.1: Feb 2015
--------------
 - Disabled field extractions as are uneeded (will be permanently removed in future releases).
 - Converted dashboards from advanced XML to simple XML
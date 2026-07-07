-----------------------------------------------------------------------------------------------------
---                                    Sophos XG App for Splunk                                   ---
-----------------------------------------------------------------------------------------------------


Description :

This app is compatible and was created with the current 19.5.0 XG Firewall version.
This app is an upgraded version of the Sophos editor add-on "Sophos Next-Gen Firewall" also available on the Splunkbase (https://splunkbase.splunk.com/app/6187).
It replaces any Sophos XG add-on that you might have. Of course you can combine apps if you want, and only use the "TA part" or the "DA part" of this app.
It contains the same base configuration as the official add-on, but it was added :
- a better parsing and field extraction
- a better CIM compliance coverage
- a full web interface to visualize the data, such as security incidents investigation, network and performance troubleshooting, etc.

NB : 
From the overview dashboard, click anywhere to move to the related investigation dashboard. From there, every click will lead you to the related event. 
A few visualizations has been left over, like detail anti-spam and IPS information as we are not using those modules yet.
The app will be updaded with new content as soon as this content is available to me.


How to install :

1. Configure the syslog output on your firewall.
Detailed procedure here : 
https://community.sophos.com/sophos-integrations/w/integrations/106/splunk-add-on-for-sophos-next-gen-firewall.

2. Create your own inputs.conf file within this app :
- Create your local directory.
- Create your inputs.conf file with this template for example :

[udp://your_syslog_port]
acceptFrom = your_firewall_ip_address
connection_host = none
host = your_host_value
index = your_index_value
sourcetype = sophos:xg:logs
source = syslog_udp_sophos_xg
disabled = 0


3. Change the index value with your own :
Copy the eventtypes.conf file in the local app directory and change the index value in the first stanza "sophosxg_idx"

4. Copy the app on your Splunk instance(s). Restart Splunk.
Now the app is accessible from the Manage Apps menu or the Apps dropdown Splunk menu.

5. (optional) Add your own firewall web administration URL link into the app :
Go to "splunk/etc/apps/SA_Sophos_XG_PIT/default/data/ui/nav".
Copy the default.xml file into your local directory ("splunk/etc/apps/SA_Sophos_XG_PIT/local/data/ui/nav").
Edit this new file and add your FW XG URL at the 7th line.
Now from the Splunk app, you'll be able to use the 6th tab.

6. Enjoy. Feedbacks are welcome.

Overview
--------
 
Splunk for AeroHive Security allows to synthesize in some dashboards the IP DoS attacks, the MAC DoS attacks, the spoofing attacks of SSID, the administration authentication attacks and the Access Point IP traffic.
Five types of email alerts are offered: Rogue SSID, IP DoS, MAC DoS SSID,/HIVE, MAC DoS Station, Admin Authentication.
For each AP Aerohive, you can have different alert email addresses.  

Installation
------------
link which gives more graphic indications of installation : https://splunkbase.splunk.com/app/3317/#/details

Enabling AeroHive Security Objects

To use "Splunk for AeroHive Security" with AeroHive AP you must first create Management and Security Objects in AeroHive HiveManager, section Advanced Configuration. 
Then Create a syslog server Object (Splunk Server IP address): Management Services / Syslog Assignments section.
And apply it in your Network Policy: Configure Interfaces and User Access / Additional Settings / Management Server Settings / Syslog Server.
Clone Aerohive-IP-DoS Default, give a name, enable IP DoS attack and save.
Clone Aerohive-MAC-DoS Default, give a name, choose SSID/Hive, enable MAC DoS attack and save.
Clone Aerohive-MAC-DoS Default, give a name, choose Station, enable MAC DoS attack and save.
Apply the three Objects "IP DoS/ MAC DoS / MAC DoS station" in your Network Policy: Configure Interfaces and User Access / SSID / Optional setting / DoS Prevention and Filters.
	* Create IP Firewall Policies object, give a name
	* Choose [-any-] for source IP, destination IP and Service
	* Choose Permit for Action and Both for Logging
	* Save

Apply this object "IP Firewall Policies" in your Network Policy: Configure Interfaces and User Access / User Profile / IP Firewall Policy.
Create WIPS Policies Object, give a name, enable SSID Detection and save.
Apply this object "WIPS Policies" in your Network Policy: Configure Interfaces and User Access / Additional Settings / Service Settings / WPIS Policy.

Update your AP with this new Network Policy and Install "Splunk for AeroHive Security" in your Splunk server.

Enabling Splunk Alerts

To activate your alerts by email you must change \Splunk\etc\apps\Splunk_for_AeroHive_Security\lookups\Hostname_Mail.csv.

Hostname_Mail.csv file structure : 
AEROHIVE_Detector_AP,host,SSID1,SSID2,SSID3,SSID4,SSID5,AEROHIVE_mail 
For each AP Aerohive fill in the hostname of your Aerohive AP, the IP address of your Aerohive AP, the different SSIDs used with your Aerohive AP and an e-mail address of alert.
If you want several alert email addresses, enter email addresses this way "Email1, Email2, Email3".
By default you can give five different SSID by AP for SSID spoofing alerts.

Splunk Implementation
---------------------
If you want to use an Index, you can set it in Splunk Settings / Indexes / New Index.

It is necessary to define source in Splunk Settings / Data inputs / UDP as below.
Choose UDP 514 as Source Port, syslog as Source Type and your Index Name.

In your Splunk software choose the Aerohive Security application.
After, you can edit the sourcelog macro in Advanced search / Search macros and put your specifics inputs as below.

Replace ““ by index=aerohive

Contact and Support
-------------------

This app is maintained by Jean-Louis SABAUT : suggestions, help and bug reports are appreciated.
Support for this application is done by email : jlsabaut@gmail.com



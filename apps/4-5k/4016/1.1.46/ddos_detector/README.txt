Copyright (C) 2015-2018 NetFlow Logic Corporation. All Rights Reserved.

App:                DDoS Detector App for Splunk
Current Version:    1.1.x
Last Modified:      2024-04-04
Splunk Version:     8.x
Author:             NetFlow Logic

This App relies on NetFlow Optimizer software, and Technology Add-On for NetFlow (version 4.1.x or above).
To download a free trial of NetFlow Optimizer, please visit
https://www.netflowlogic.com/downloads/

##### NEW INSTALLATION #####

Please review the documentation : https://docs.netflowlogic.com/integrations-and-apps/splunk-integration/overview

BEFORE YOU BEGIN:
•	Download and install Technology Add-On for NetFlow: https://splunkbase.splunk.com/app/1838/

•	Visit https://www.netflowlogic.com/download/ and download:
	o	NetFlow Optimizer
	o	External Data Feeder
	o	DDoS Detector Module
•	Request a free 60 day NetFlow Optimizer trial license by completing the simple registration form: https://www.netflowlogic.com/free-trial/
•	Install and configure NetFlow Optimizer input to receive NetFlow/sFlow/IPFIX, and output to send NFO syslogs to your Splunk system
•	Install External Data Feeder to connect NFO to MaxMind for GeoIP resolution
•	Upload DDoS Detector Module to NFO and configure IPv4 address block and country code parameter for GeoIP map

For more information about NetFlow Optimizer and external Data Feeder for NFO, visit Getting Started Guide: NFO at https://docs.netflowlogic.com/get-started-nfo

If you need to alter the index, please follow Configuration>App Setup steps.

###### Saved Searches which are running frequently ######

    The following saved searches are enabled by default and are executed every minute. The time range for these searches is set to 1 minute. 
This is done so the users are alerted as soon as possible in case of a DDoS attack, and so the dashboards accurately show the types of the attacks :

    1) ddos_alert - sending an email alert if ddos attack above certain level is detected, frequency : 1m
    2) ddos_20196_20064 - adding aggregate values to summary index to speed up the dashboards, frequency : 1m
    3) ddos_20196_20067 - adding aggregate values to summary index to speed up the dashboards, frequency : 1m
    4) ddos_20196_20195 - adding aggregate values to summary index to speed up the dashboards, frequency : 1m
    5) ddos_20196_20198 - adding aggregate values to summary index to speed up the dashboards, frequency : 1m
    6) ddos_20196_20200 - adding aggregate values to summary index to speed up the dashboards, frequency : 1m

###### Get Help ######

Have questions or need assistance? We are here to help! Please visit
https://www.netflowlogic.com/support/

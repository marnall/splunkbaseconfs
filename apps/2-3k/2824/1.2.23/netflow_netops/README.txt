Copyright (C) 2015-2024 NetFlow Logic Corporation. All Rights Reserved.

App:                V2P Network Visibility App for Splunk
Current Version:    1.2.x
Last Modified:      2024-04-03
Splunk Version:     9.x
Author:             NetFlow Logic

This App relies on NetFlow Optimizer software, and Technology Add-On for NetFlow (version 4.1.x or above).
To download a free trial of NetFlow Optimizer, please visit
https://www.netflowlogic.com/downloads/

##### BEFORE YOU UPGRADE #####

    In this version the default setup of index=flowintegrator is no longer supported. To continue using this index, please create
  the local/indexes.conf file if it does not already exist, and add the following lines to it:

[flowintegrator]
homePath    = $SPLUNK_DB/flowintegrator/nfi_traffic/db
coldPath    = $SPLUNK_DB/flowintegrator/nfi_traffic/colddb
thawedPath  = $SPLUNK_DB/flowintegrator/thaweddb

    Restart splunk for the index configuration to take effect.

##### NEW INSTALLATION #####

Please review the documentation : https://docs.netflowlogic.com/solutions/v2p-network-visibility/

BEFORE YOU BEGIN:
•	Download and install Technology Add-On for NetFlow: https://splunkbase.splunk.com/app/1838/

•	Visit https://www.netflowlogic.com/download/ and download:
	o	NetFlow Optimizer
	o	External Data Feeder
	o	V2P Network Visibility Module
•	Request a free 60 day NetFlow Optimizer trial license by completing the simple registration form: https://www.netflowlogic.com/download/register-form/
•	Install and configure NetFlow Optimizer input to receive NetFlow/sFlow/IPFIX, and output to send NFO syslogs to your Splunk system
•	Install External Data Feeder to connect NFO to VMware vCenter
•	Upload V2P Network Visibility Module to NFO and configure vCenter integration

For more information about NetFlow Optimizer and external Data Feeder for NFO, visit Getting Started Guide: NFO at https://docs.netflowlogic.com/get-started-nfo

If you need to alter the index, please follow Settings>App Setup steps.

###### Get Help ######

Have questions or need assistance? We are here to help! Please visit
https://www.netflowlogic.com/support/

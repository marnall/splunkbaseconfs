Copyright (C) 2015-2017 NetFlow Logic Corporation. All Rights Reserved.

App:                Technology Add-On for NetFlow
Supported products: Netflow Analytics for Splunk (version 3.6 or above) and Enterprise Security (version 3.0 or above)
Last Modified:      2017-01-19
Splunk Version:     6.x
Author:             NetFlow Logic

This TA relies on NetFlow Optimizer software.
To download a free trial of NetFlow Optimizer, please visit
https://www.netflowlogic.com/downloads/.

This TA provides CIM compliant field names, eventtypes and tags for NetFlow Optimizer data.
The TA can also be used to generate sample events for testing purposes, it contains samples of netflow data and config files for the event generator.


##### BEFORE YOU UPGRADE #####

    In this version the default setup of index=flowintegrator is no longer supported. To continue using this index, please create 
  the TA-netflow/local/indexes.conf file if it does not already exist, and add the following lines to it:

[flowintegrator]
homePath    = $SPLUNK_DB/flowintegrator/nfi_traffic/db
coldPath    = $SPLUNK_DB/flowintegrator/nfi_traffic/colddb
thawedPath  = $SPLUNK_DB/flowintegrator/thaweddb

    Restart splunk for the index configuration to take effect.
    
    Another change in this version is that the UDP 10514 input is no longer configured by default, it should be added manually. See below.

##### Installation #####

1. Download TA-netflow from  https://apps.splunk.com/app/1838/ and install it
2. Set up an input and configure sourcetype for it:

  Netflow Optimizer is sending events by default to UDP 10514. The TA-netflow is expecting that the sourcetype of events sent from Netflow Optimizer would be set to "flowintegrator". Based on this an example input file could look like this :

[udp://10514]
sourcetype = flowintegrator

these lines should be placed in TA-netflow/local/inputs.conf


   If you want to send the events from Netflow Optimizer to a specific already created index, for example an index called "mynetflow", the above example should be extended like:
   
[udp://10514]
sourcetype = flowintegrator
index = mynetflow

   After creating the inputs file please restart Splunk.


##### Usage with Enterprise Security

   Input requirements: If they are applicable, then the following rules should be enabled in NetFlow Optimizer :

        10020/20020 ( Top Policy Violators for Cisco ASA )
        10032/20032 ( Hosts with Most Policy Violations for Palo Alto Networks )
        10050/20050 ( Botnet Command and Control Traffic Monitor )
        10052/20052 ( Peer by Reputation Monitor )
        10053/20053 ( Threat Feeds Traffic Monitor )
        10067/20067 ( Top Traffic Monitor)

   By default the netflow data is routed by default to index=flowintegrator.
   The admin role must be configured to look also at the index where netflow data is stored.
   This can be achieved by changing the admin role with adding the additional index to the list of “Indexes searched by default”.

   Warning : When adding indexes to the default search indexes do not include any summary indexes, as this can cause a search and summary index loop.
   
   If you want to use Module 10967/20967 (Top Traffic Monitor Geo Country) or Module 10867/20867 (Top Traffic Monitor Geo City) instead of 
   Module 10067/20067 ( Top Traffic Monitor), please do the following:

	1) Copy TA-netflow/default/eventtypes.conf to TA-netflow/local/eventtypes.conf
	2) In the new file the following line :
		search = sourcetype="flowintegrator" ( nfc_id=20067 OR nfc_id=20020 OR nfc_id=20032 OR nfc_id=20050 OR nfc_id=20052 OR nfc_id=20053 )
	   replace nfc_id=20067 with nfc_id=20967 (or nfc_id=20867). e.g:
		search = sourcetype="flowintegrator" ( nfc_id=20967 OR nfc_id=20020 OR nfc_id=20032 OR nfc_id=20050 OR nfc_id=20052 OR nfc_id=20053 )
        3) Restart Splunk

##### How to enable the netflow event generator for testing purposes

    This functionality relies on the "The Splunk Event Generator" software available from https://github.com/splunk/eventgen

    Install the eventgen app and after that:
    1) Create directory $SPLUNK_ROOT/etc/apps/TA-netflow/local/ if it doesn't exist
    2) Copy eventgen.conf from /default to /local folder and change the line:
        disabled = true
      to
        disabled = false
    3) Restart Splunk

##### Documentation #####

To get the most up-to-date information on how to install, configure, and use the App,
download "NetFlow Analytics for Splunk User Manual" pdf document 
by visiting https://www.netflowlogic.com/resources/documentation/

###### Get Help ######

Have questions or need assistance? We are here to help! Please visit
https://www.netflowlogic.com/connect/support/

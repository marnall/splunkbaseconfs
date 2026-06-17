Copyright (C) 2012-2025 NetFlow Logic Corporation. All Rights Reserved.

App:                NetFlow Analytics for Splunk
Last Modified:      2025-02-05
Splunk Version:     9.2.x
Author:             NetFlow Logic

This App relies on NetFlow Optimizer software and Technology Add-On for NetFlow (version 4.5.56 or above).
To download a free trial of NetFlow Optimizer, please visit
https://www.netflowlogic.com/downloads/.


##### Installation #####

a) Deploy to single server instance

1. Download TA-netflow from  https://apps.splunk.com/app/1838/ and install it
2. Download netflow from  https://apps.splunk.com/app/489/ and install it
3. Access the app to configure it (click on “Set up now” button).

b) Deploy to distributed deployment

  **Install to indexers**
  1. Download TA-netflow from  https://apps.splunk.com/app/1838/ and install it
 
  **Install to search heads**
  1. Download TA-netflow from  https://apps.splunk.com/app/1838/ and install it
  2. Download netflow from  https://apps.splunk.com/app/489/ and install it
  3. Access the app to configure it (click on “Set up now” button).


#### Configuration in case of an update


Step1. Check that the index is properly configured.

  In case a specific index in TA-netflow was set up to receive the events please follow the following procedure:

    Create a directory $SPLUNK_ROOT/etc/apps/netflow/local/ if it doesn't exist;

    Create the file:

    $SPLUNK_ROOT/etc/apps/netflow/local/macros.conf

    with the following lines:

    [netflow_index]
    definition = (index=main OR index=<change_me>) sourcetype=flowintegrator


    Save the configuration file ($SPLUNK_ROOT/etc/apps/netflow/local/macros.conf);

    Restart Splunk for the changes to take effect.

##### Documentation #####

To get the most up-to-date information on how to install, configure, and use the App, 
visit https://docs.netflowlogic.com/

###### Get Help ######

Have questions or need assistance? We are here to help! Please visit
https://www.netflowlogic.com/support/
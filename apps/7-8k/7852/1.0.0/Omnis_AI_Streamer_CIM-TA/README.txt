# Copyright (C) 2023 Netscout Systems Inc. All Rights Reserved.
#
# Technology Add-on for NetScout Omnis Data Streamer
#
# Enables collection and parsing of CI log data for integration into Splunk.
# See also: netscout_nsa app for visualizations.

CHANGELOG
1.0.0 (05/16/25) - Initial release of Omnis AI Streamer CIM TA

INSTALLATION
Install this TA on your indexers, heavy forwarders, and search heads.


CONFIGURATION

Getting Data In:

Configuration of Splunk Universal Forwarder on the OMNIS AI Streamer
1.  From a Splunk server where the OMNIS AI Streamer add-on has been installed, copy inputs.conf in the $SPLUNK_HOME/etc/apps/Omnis_AI_Streamer_CIM-TA/default/ directory to the OMNIS AI Streamer server.

2.  On the OMNIS AI Streamer server copy inputs.conf into $SPLUNK_FORWARDER/etc/system/local/inputs.conf for editing. 
Create “local” folder if it does not already exist.

3.  In the $SPLUNK_FORWARDER/etc/system/local inputs.conf file, check to confirm that inputs are enabled for each flow and source type.  All inputs are enabled by default, i.e. “disabled=false”
    a. Confirm index name, the default index is aistreamer
    b. Confirm Monitor stanza location of flows

4.  Save the $SPLUNK_FORWARDER/etc/system/local/inputs.conf file.

5.  Update the $SPLUNK_FORWARDER/etc/system/local/outputs.conf to the relevant Splunk instance, i.e. indexer or heavy forwarder.

6.  Restart the Splunk forwarder
    $SPLUNK_FORWARDER/bin/splunk restart


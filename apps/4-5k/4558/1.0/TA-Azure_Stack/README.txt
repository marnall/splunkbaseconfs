======================================================================
This package is a Microsoft Azure Stack Technology Addon (TA).  There are no visual components to this TA. 
======================================================================
Author:                  Splunk Works
Add-on Name:             Microsoft Azure Stack Add-on for Splunk
Add-on Version:          1.0.0

Vendor Product(s):       Microsoft Azure Stack
Splunk Platform(s):      Splunk 7.x

Description
------------------------------
The TA receives CEF data from Microsoft Azure Stack and parses the data into fields and values.


Installation and Configuration
------------------------------
Although Azure Stack syslog data can be sent directly to a Splunk instance, it is reccomended to send the syslog data from Azure Stack to a syslog server.
Then, use a Splunk Universal Forwarder with this TA installed to forward the data to your Splunk indexing tier.


Installation of the add-on to the search head
=============================================

Extract to $SPLUNK_HOME/etc/apps

Installation of the add-on to the indexers
=============================================

Extract to $SPLUNK_HOME/etc/apps


Installation of the add-on to a forwarder
=============================================

Extract to $SPLUNK_HOME/etc/apps


Copyright (C) 2019 Splunk Inc. All Rights Reserved.







======================================================================
This package is a Microsoft Azure Stack Splunk Application.
This application contains visualizations for data gathered via the 
Microsoft Azure Stack Add-on for Splunk.
======================================================================
Author:                  Splunk Works
Add-on Name:             Microsoft Azure Stack App for Splunk
Add-on Version:          1.0.0

Vendor Product(s):       Microsoft Azure Stack
Splunk Platform(s):      Splunk 7.x

Description
------------------------------
This application contains dashboards for Microsoft Azure Stack data:
* Privileged Endpoint Events
* Code Integrity
* Windows Defender

Installation and Configuration
------------------------------

* Install on a single instance
If your Splunk Enterprise deployment is a single instance, install both the app and the add-on to your single instance. You can use the Install app from file feature in the Manage Apps page in Splunk Web to install both packages, or install manually using the command line.

* Install in a non-clustered distributed environment
If your Splunk Enterprise deployment is distributed and non-clustered, follow these steps.

1. Install both the app and add-on to your search heads.
2. Distribute the summary index configurations to the indexer.
3. Install the add-on to a Universal Forwarder containing the Azure Stack syslog data.


* Install in a clustered distributed environment
Install the app and the add-on using the deployer. See Use the deployer to distribute apps and configuration updates in the Distributed Search manual in the Splunk Enterprise documentation.

Copyright (C) 2019 Splunk Inc. All Rights Reserved.







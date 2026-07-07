	Language:       Python

	Version:        1.20

	Original Date:  08-31-2016

	Author:         Derek Arnold

 	Company:        Optiv Security

 	Purpose:        Optiv Decept System is a Splunk App that monitors for unauthorized and/or malicious activity on your organization’s network.
			By placing several honeypots that listen on many ports at strategic locations, we can detect early stage attacks.
			The app can provide increased visibility to potentially malicious activity going on in the organization.

   	Copyright (C):  2017 Derek Arnold (ransomvik)

 	License:	This program is free software: you can redistribute it and/or modify
			it under the terms of the GNU General Public License as published by
			the Free Software Foundation, either version 3 of the License, or
			any later version.

        	    	This program is distributed in the hope that it will be useful,
                	but WITHOUT ANY WARRANTY; without even the implied warranty of
               		MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
               		GNU General Public License for more details. See <http://www.gnu.org/licenses/>

	  Support:	This is an open source project, no support provided, public repository available.
 			https://github.com/ransomvik/optiv_decept_system

          Change Log:	08-31-2016 DPA	Created.
                    	04-16-2017 DPA	Precertification documentation steps.

Overview:
---------
Optiv Decept System is a Splunk App that monitors for unauthorized and/or malicious activity on your organization’s network.
By placing several honeypots that listen on many ports at strategic locations, we can detect early stage attacks.
The app can provide increased visibility to potentially malicious activity going on in the organization.

This document serves as a guide to both the Optiv_TA_decept app as well as the Optiv Decept.
System app, as they go hand-in-hand.
Optiv Decept System is the app, installed on the search head(s), which visualizes the data collected.
Optiv_TA_decept is the honeypot which is installed on a standalone honeypot server that listens for network traffic.


Features:
--------
*Listen on several common tcp ports and report unauthorized activity to the app.
*Capture keystrokes and network traffic from potentially malicious hosts.
*Search and visualization features.
*Low system requirements and easy install.
*Integration with Splunk Enterprise Security – Intrusion Center
*Integration with Optiv Threat Intel
    https://splunkbase.splunk.com/app/2837/

Prerequisites:
--------------
*Splunk 6.4.x, 6.5.x, or 6.6.x
*Linux or Windows Operating System
*If there is a distributed environment, install the app on the ad hoc search head only.
*For the SanKey visualization dashboard, install the Custom Visualizations app found at:
    https://splunkbase.splunk.com/app/3112/


Install matrix:
--------------

+-----------------+---------------------+
| Splunk role     | App to install      |
+=================+=====================+
| Indexer         | none*               |
+-----------------+---------------------+
| Search head     | optiv_decept_system |
+-----------------+---------------------+
| Heavy forwarder | optiv_TA_decept     |
+-----------------+---------------------+
*create an "optiv" index on each indexer

Install:
--------
*Login to Splunk as an admin.
*Go to Apps->Manage apps
*Click Install app from file.
*Browse to the file folder with the app .tar.gz file.
*Choose the file and click OK.
*After the app is uploaded and installed, restart Splunk.

Upgrade Instructions:
---------------------
*Stop Splunk
*Remove the app from the directory structure on Linux:
rm –rf /opt/splunk/etc/apps/optiv_threat_intel
or on Windows:
c:\Program Files\Splunk\etc\apps\optiv_decept_system
*Start Splunk
*Install using the steps shown in the Install section.
*After the app is uploaded and installed, restart Splunk.

Support:
--------
This is an open source project, no support provided, public repository available.
                        https://github.com/ransomvik/optiv_decept_system

Dependencies:
-------------
This app depends on Optiv_TA_decept being installed on one Splunk server in the environment.
See the Install Matrix section above for details, as well as the included README.pdf
For the SanKey visualization dashboard, install the Custom Visualizations app as described in the Prerequisistes section.

Saved Search Documentation:
---------------------------
N/A - not applicable

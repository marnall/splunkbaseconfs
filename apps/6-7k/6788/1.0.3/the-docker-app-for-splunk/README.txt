Docker App for Splunk
Overview
Welcome to the Docker App for Splunk. The App helps to gain valuable insight of your Docker platform such as information on the containers and their stats, list of images on the server.
This App is dependent on “Docker Add-on for Splunk”.  The “Docker Add-on for Splunk” ingest the required data and this App uses that data to populate the dashboards.

Author	Avotrix
App Version	1.0.0
App Build	1
Vendor Products	Docker
Has Index Time Extraction	False
Creates an Index	False


Release Notes
Version 1.0.0
Initial Release
About This Release
Version 1.0.0 of Docker App for Splunk is compatible with:
Splunk Enterprise versions	8.0,8.1,9.0
Platforms	Splunk Enterprise, Splunk Cloud

Diagnostics Generation
Please include a support diagnostic file when creating a support ticket. Use the following command to generate the file based on which Splunk app or add-on is installed. Send the resulting file to support.
•	$SPLUNK_HOME/bin/splunk diag --collect=app: the-docker-app-for-splunk


Installation:

Software requirements
Splunk Enterprise system requirements
This App runs on Splunk Enterprise, all of the Splunk Enterprise system requirements apply.


Deployment Guide

•	Single Instance 
(Pre-requisite) Docker App For Splunk

•	Distributed deployment 
Search Head – Docker App For Splunk


Configuration:

After installing the app, you can populate it by going to "Advanced Search » Search Macros." From there, search for and edit the macro according to the instructions in the snapshot below. Then, enter the name of the index where the data is being ingested using the "Docker Add-on for Splunk."

Macro name: “docker_index_”

# Binary File Declaration
# Binary File Declaration

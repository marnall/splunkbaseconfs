Copyright (c) 2024 by Proofpoint, Inc.  All Rights Reserved.

Proofpoint, Proofpoint Protection Server and the Proofpoint logos are trademarks or registered trademarks of Proofpoint, Inc.

Proofpoint Protection Server - Technology Add-on for Splunk


Introduction:

Customers interested in integrating Proofpoint Protection Server (PPS) logs with Splunk can utilize this custom-built add-on. This technology add-on focuses on normalizing the filter logs based on the Splunk Common Information Model (CIM) for email.

Splunk CIM Email Data Model

By normalizing filtering data produced by PPS to CIM-compliant Email data model, Splunk users can perform search, report or other operations they have built using the Email data model against PPS filtering data without further customizations, which eliminates the need to understand PPS filtering data format.


Pre-requisites:

1. Splunk Enterprise (tested with version 6.3.x to 6.6.x on Windows and Linux Operating Systems).
2. Proofpoint Protection Server Technology Add-on for Splunk - file or download from the Splunk App Store.


Installation:

The PPS add-on can be installed from the Splunkbase App Store or using an installation package from a local system. Both methods are described below.

1. Installing the PPS add-on from Splunkbase
a. In the Splunk Web Home page, on top left corner, click on the "Manage Apps" gear icon.
b. In the Apps page, click on the "Browse more apps" button.
c. In the Browse More Apps page, search for "Proofpoint Protection Server TA for Splunk", which should appear at the top of the search result. Click on Install button.
d. Upon successful installation, the add-on will be in the listing in the Apps page.

2. Installing the PPS add-on from an installation file:
a. In the Splunk Web Home page, on the top left corner, click on the "Manage Apps" gear icon. 
b. In the Apps page, click on the "Install app from file" button.
c. To install, select the add-on package file (for example, TA_pps.tar.gz).
d. Upon successful installation, the add-on will be in the listing in the Apps page.


Testing the Deployment:

The first step to test the PPS add-on is to upload some filter logs for analysis. Follow these instructions:

a. In the Splunk Web Home page, on the top left corner, click on the "Add Data" icon.
b. In the Add Data page, click on the "Upload" icon.
c. In Select Source, click on "Select file" to find a filter.log file. Then click the Next button.
d. In Set Source Type, search "pps_log" in the "Source type" dropdown list and select it. Then click the Next, Review, and Submit buttons in that order.
e. You will see an acknowledgement page after a successful upload.

Now you can add data, search, create reports, and perform operations against the PPS filtering data in Splunk. 


Configuration:

Add UDP/TCP input to listen on the port for PPS logs and specify "pps_log" as sourcetype. It can be done in two following ways:
1. Rename inputs.conf.example to inputs.conf in $SPLUNK_HOME$/etc/apps/TA-pps/default directory and restart Splunk server. (this will enable UDP 515 port)
2. Using Splunk web UI:
	- Go to "Settings" -> "Data Inputs"
	- Click on "Add new" action for TCP or UDP input
	- Enter port and click on "Next"
	- In "Select sourcetype" search and select "pps_log" sourcetype and click on "Review".
	- Review all configuration and click "Submit"

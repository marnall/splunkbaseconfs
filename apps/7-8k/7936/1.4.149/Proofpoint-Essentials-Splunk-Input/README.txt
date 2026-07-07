Copyright (c) 2010-2025 by Proofpoint, Inc.  All Rights Reserved.

Proofpoint, Proofpoint Protection Server and the Proofpoint logos are trademarks or registered trademarks of Proofpoint, Inc.

Product Name: Proofpoint Essentials Splunk Input
Author: Proofpoint Inc
Version: 1.4.149
Date: 2025-07-17
Splunk requirements: Splunk Enterprise v 6.5+

INTRODUCTION:

The API(mentioned below) allows integration with these solutions by giving administrators the ability to periodically download detailed information about several types of threat events in a SIEM-compatible, vendor-neutral format. Currently, the following event types are exposed:
1. Blocked or permitted clicks to threats recognized by URL Defense
2. Blocked or delivered messages that contain threats recognized by URL Defense or Attachment Defense


PREREQUISITES:

1. Splunk Enterprise (tested with version 6.5.x to 8.x on Windows and Linux Operating Systems).
2. Proofpoint Essentials Splunk Input - file or download from the Splunk App Store.
3. You will need Principal and Secret from your Proofpoint Essentials interface


INSTALLATION:

The Essentials input can be installed from the Splunkbase App Store or using an installation package from a local system. Both methods are described below.

1. Installing the Essentials input from Splunkbase
a. In the Splunk Web Home page, on top left corner, click on the "Manage Apps" gear icon.
b. In the Apps page, click on the "Browse more apps" button.
c. In the Browse More Apps page, search for "Proofpoint Essentials Splunk Input", which should appear at the top of the search result. Click on Install button.
d. Upon successful installation, the add-on will be in the listing in the Apps page.

2. Installing the Essentials input from an installation file:
a. In the Splunk Web Home page, on the top left corner, click on the "Manage Apps" gear icon.
b. In the Apps page, click on the "Install app from file" button.
c. To install, select the add-on package file (for example, proofpoint-essentials-splunk-input_102.tar.gz).
d. Upon successful installation, the add-on will be in the listing in the Apps page.

Add modular input to collect events from Proofpoint Essentials SIEM API. It can be done using following steps:
1. Using Splunk Web UI:
	- Go to "Settings" -> "Data Inputs"
	- Click on “Add New” on Proofpoint Essentials Splunk Input
	- Enter name, Principal and Secret Key and click Next
	- Once modular input created successfully, click on start searching.

In addition, during the third step, under 'More Settings', you can specify an interval in seconds.
The interval determines how frequently your Splunk instance will poll for new events. The recommended(and default) setting is 600 seconds, or 10 minutes. Intervals below 300 seconds are not recommended.

THIRD PARTY COMPONENTS:

This modular input is packaged with the following third-party modules:

splunklib - http://dev.splunk.com/python
dateutil - https://github.com/dateutil/dateutil/
six - https://github.com/benjaminp/six

Table of Contents
Overview
About the Spirion App
Release Notes
Support and Resources
Installation and Configuration
Hardware and software requirements
Installation steps
Deploy to single server instance
Deploy to distributed deployment
Deploy to distributed deployment with Search Head Pooling
Deploy to distributed deployment with Search Head Clustering
Deploy to Splunk Cloud
Configuration


Overview
About the Spirion App for Splunk
Author: Spirion
App Version: 1.0
Has index-time operations: false
Create an index: false
Implements summarization: false

Spirion is the leading provider of sensitive data risk reduction solutions. Spirion's enterprise solution accurately finds all sensitive data, anywhere, anytime and in any format on endpoints, servers, file shares, databases and in the cloud with practically zero false positives. The software eliminates and prevents sensitive data sprawl and the integration with Splunk lets customers understand and manage their risks in the context of all their other information security and business data.

Spirion's integration with Splunk enables customers to share, analyze, and correlate Spirion's sensitive data results with their existing enterprise security systems.  Replacing costly and complex third party development integration and manual data exports, the Spirion integration allows endpoints and locations to be queried by Splunk to show the amount of sensitive data each holds and the amount of data that is currently unprotected. This allows companies to quickly and easily identify where they have data breach exposure.

This product contains the Add-on which integrates Spirion sensitive data events and alerts into Splunk Enterprise. The Add-on is designed for Spirion 10.0 and above. For use with previous versions please contact Spirion.

Release Notes
About this release
Version 1.0 of the Spirion App for Splunk is compatible with:
Splunk Enterprise versions: 6.4
Platforms: Platform independent
Lookup file changes: None

Support and resources
Support
Email: splunkinfo@spirion.com

Installation and Configuration
Hardware and Software Requirements
Hardware Requirements
Spirion App for Splunk supports the following server platforms in the versions support by Splunk Enterprise:
Linux
Windows
Solaris

Software Requirements
To function properly, Spirion App for Splunk requires the following software:
TA for Spirion installed and bringing data into the indexers. To ensure that all dashboard panels are populating and reporting, configure all 2 inputs included in the TA for Spirion. Doing this will on-board the datasets needed to populate the panels.

Splunk Enterprise System Requirements
Because this add-on runs on Splunk Enterprise, all of the Splunk Enterprise system requirements apply.

Installation steps
To install and configure this app on your supported platform, follow these steps:
Download and Deploy the add-on to either a single Splunk Enterprise server or a distributed deployment.

Using the Web Interface:
In splunk Web, click Apps  Manage Apps.
Click Install app from file.
Locate the downloaded file and click Upload.
Verify that the add-on appears in the list of apps and add-ons. You can also find it on the server at $SPLUNK_HOME/etc/apps/spirion

Using the configuration files:
Untar the downloaded app.
Copy or Move the spirion folder to the server and put into $SPLUNK_HOME/etc/apps directory.
Restart Splunk

Standalone Splunk Environemnts and Independent Search Heads
Install the Spirion App for Splunk on the single server using one of the methods described above.

Distributed Environments
In distributed environments, the Spirion App for Splunk Enterprise should be installed on the search heads.

Configuration:
By default, the data gathered by the Spirion Technology Add-On indexes into the main index, and thus the dashboards in the Splunk app for Spirion assumes the same in its searches.  If you plan to use a custom index, simply edit the spirion_index macro to reflect your new index name.  This can be achieved by either creating a local copy of the macros.conf file within the app, or editing the macro through the UI by navigating to Settings>Advanced Search>Search macros.  All that needs to be updated is the index definition for where the Spirion data will be sent.

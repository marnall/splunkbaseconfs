# Cofense-Intelligence Add-on for splunk
## OVERVIEW
* Cofense Intelligence and Splunk partner to alert your Cyber Security Team when network communication is detected between your endpoints and botnet infrastructures.
* Cofense Intelligence provides a high-signal, context-rich source of threat intelligence about the latest phishing and malware attacks hitting businesses, universities, and agencies every day.
* This Add-on collects threat update and details of threat from Cofense Intelligence.
* Author: Cofense, Inc.
* Version: 4.0.0
* Splunk Version: 7.3, 8.0, 8.1
* Browser Support: Chrome, Firefox, Safari.
* Details: [Documentation for this Add-on](https://www.threathq.com/docs/integrations.html#splunk-enterprise)
## END USER LICENSE AGREEMENT
* https://cofense.com/legal/integration-applications/
## RECOMMENDED SYSTEM CONFIGURATION
* As this Add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.
## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This Add-on can be set up in two ways:
    1. For a single-instance deployment on a deployment with a single Search Head, the Add-On(s) should be installed on the Splunk instance.
    2. For a Splunk deployment with an Index Cluster (with or without Enterprise Security), The Add-On(s) should be installed on a Heavy Weight Forwarder AND on the Search Head (if applicable this should be the Enterprise Security Search Head). The installation on the Search Head is to prevent search-time and index-time extraction of Cofense Intelligence JSON data.
## INSTALLATION
* Follow the below-listed steps to install an Add-on from the bundle:
    * Download the Add-on package.
    * In the UI navigate to: Apps->Manage Apps.
    * In the top right corner select Install app from file.
    * Select Choose File and select the Add-on package.
    * Select Upload and follow the prompts.
## CONFIGURATION
* Follow the below steps for configuration.
    * Go to Data Inputs -> Cofense Intelligence. then click on existing input named "cofense" and edit it.
    * Add your API Username and API Password.
    * Add Start Date, from when you want to start collecting data.
    * Add BASE API URL.
    * Add Max Page Size
    * Add Proxy HTTP and Proxy HTTPS URL and credentials of that proxy server (i.e. Proxy User, Proxy Password).
    * Select any no. of checkbox (min. 1 checkbox) of which you want to collect the data from all checkboxes.
    * Click on more settings and configure Interval and Index.
## UNINSTALL ADD-ON
* To uninstall add-on, user can follow below steps:
    * SSH to the Splunk instance -> Go to folder apps($SPLUNK\_HOME/etc/apps) -> Remove the TA-cofenseintelligence folder from apps directory.
    * Restart Splunk.
## SUPPORT
* Support : https://support.cofense.com
* Email :  <support@cofense.com>
## COPYRIGHT
* Copyright 2021 Cofense. All rights reserved.

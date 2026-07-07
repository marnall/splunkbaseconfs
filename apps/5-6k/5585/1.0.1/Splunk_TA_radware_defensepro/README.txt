Radware DefensePro Add-on for Splunk
Copyright (C) 2021 CyberSecThreat Corporation Limited. All Rights Reserved.

================================================
Overview
================================================

This app provides field extraction, cim mapping(Intrusion Detection, authentication, change) for Radware DefensePro in Splunk.

The field extraction accepts both Splunk native tcp/udp connections and rsyslog style syslog.

================================================
Configuring Splunk
================================================
This app need to install on Splunk Search Head and Heavy Forwarder/Indexer.

Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Restart Splunk if a dialog asks you to

Configure the input sourcetype as radware:defensepro

================================================
Known Limitations
================================================

N/A



================================================
Getting Support
================================================

This is an open source project and no active support is provided. If there is any issues, email to info@cybersecthreat.com during weekday business hours (GMT+8).




================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 1.0.0   | Initial release                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0.1   | Fixed issues of props.conf                                                                                       |
|         |                                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
MySQL Community Audit Add-on for Splunk
Copyright (C) 2021 CyberSecThreat Corporation Limited. All Rights Reserved.

================================================
Overview
================================================

This app provides field extraction, cim mapping(authentication) for MySQL Community Audit in Splunk.

The field extraction only accepts local csv file logging from MySQL Community Audit.

================================================
Configuring MySQL Community Audit
================================================

1. Configure audit setting in my.conf:
a. Enable auditing by the setting the edb_audit parameter to csv (edb_audit = 'csv')
b. To audit all connections, set the parameter, edb_audit_connect, to all. (edb_audit_connect = 'all')

Ref: https://www.enterprisedb.com/edb-docs/d/edb-postgres-advanced-server/user-guides/user-guide/10/EDB_Postgres_Advanced_Server_Guide.1.39.html

================================================
Configuring Splunk
================================================
This app need to install on Splunk Search Head and forwarder(MySQL Community DB Server), and optionally installed on Indexer/Heavy Forwarder.

Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Restart Splunk if a dialog asks you to

Configure the input sourcetype as mysql:community:audit.

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
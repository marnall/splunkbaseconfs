About Kaspersky CyberTrace App
===============================

Kaspersky CyberTrace App provides the following functionality:

- Displaying information about URLs, IP addresses, and hashes from events that match Kaspersky data feeds in a dashboard.
- Displaying information about Threat Feed Service status in a dashboard.
- Matching individual URLs, IP addresses, and hashes to Kaspersky data feeds using the lookup script that can be invoked from the Splunk search field within the app.

Additionally, Kaspersky CyberTrace App comes with alert templates that demonstrate the basic trigger conditions.


Software requirements
=====================

Kaspersky CyberTrace App has the following software requirements:

- Splunk 7.2, 7.3, 8.0, 8.1, 8.2
- Python 3.7


About Kaspersky CyberTrace dependency
==============================================

Kaspersky CyberTrace App is intended for use with Kaspersky CyberTrace, and will not work without it. 

Kaspersky CyberTrace analyzes events passed from Splunk and matches URLs, IP addresses, and hashes to Kaspersky data feeds. Indicators of compromise (IOC) from Kaspersky data feeds are not loaded into Splunk, and instead are processed by Kaspersky Threat Feed Service.

To get Kaspersky CyberTrace, please purchase Threat Data Feeds and Kaspersky CyberTrace from Kaspersky. For more information, see http://www.kaspersky.com/enterprise-security/intelligence-services.


Online documentation
====================

For information about installing, configuring, troubleshooting and running Kaspersky CyberTrace App, see online documentation located at https://click.kaspersky.com/?hl=en&link=online_help&pid=KFS&version=1.0&helpid=index.

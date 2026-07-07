About Kaspersky Threat Intelligence Portal for Splunk
=====================================================

Kaspersky Threat Intelligence Portal for Splunk provides the fastest and easiest way to get threat intelligence from Kaspersky Threat Intelligence Portal about indicators in events stored in Splunk.

Software requirements
=====================

Kaspersky Threat Intelligence Portal for Splunk has the following software requirements:

- Splunk 6.5, 6.6

About Kaspersky Lab Threat Intelligence Portal
==============================================

Kaspersky Threat Intelligence Portal for Splunk is intended for use with Kaspersky Threat Intelligence Portal, and will not work without it. 

Access to Kaspersky Threat Intelligence Portal provides reliable, immediate intelligence about cyber-threats, legitimate objects, their inter-connections and indicators, enriched with actionable context to inform your business or clients about the associated risks and implications. Now you can mitigate and respond to threats more effectively, defending against attacks even before they are launched.

Kaspersky Threat Intelligence Portal delivers all the knowledge acquired by Kaspersky Lab about cyber-threats and their relationships, brought together into a single, powerful web service. The goal is to provide your security teams with as much data as possible, preventing cyber-attacks before they impact your organization. The platform retrieves the latest detailed threat intelligence about URLs, domains, IP addresses, file hashes, threat names, statistical/behavior data, WHOIS/DNS data, etc. The result is global visibility of new and emerging threats, helping you secure your organization and boosting incident response.

To get access to Kaspersky Threat Intelligence Portal, please request a certificate for Kaspersky Threat Intelligence Portal by filling the request form at http://www.kaspersky.com/enterprise-security/intelligence-services.

Documentation
=============

You must work with Kaspersky Threat Intelligence Portal for Splunk in a browser. The certificate for Kaspersky Threat Intelligence Portal must be imported in the browser.

How to use Kaspersky Threat Intelligence Portal:

1. In Splunk, install Kaspersky Threat Intelligence Portal App

2. In Splunk, navigate to Kaspersky Threat Intelligence Portal App

3. From the 'Time period' list, select the time period for data that you want to lookup in Kaspersky Threat Intelligence Portal.

4. In the 'Source' field, specify a sourcetype for data that you want to lookup. You can specify a sourcetype in the following ways:
    - Full sourcetype value
    - Partial (substring) sourcetype value
    - * symbol (all sourcetypes)

5. From the 'Field' list, select the field with data that you want to lookup in Kaspersky Threat Intelligence Portal. The list of fields is created automatically based on the specified sourcetype.

6. In the 'Value filter' field, specify a filter for data (if required). The filter works by matching the substrings.

    For example, if you want to lookup IP addresses and specified '192.0.2.', the lookup results will include all IP addresses that have '192.0.2.' substring.

    By default, the 'Value filter' field has a '*' value, and all values for the specified field are included in the lookup.

7. Click the 'Submit' button.

8. In the 'Search results' table, click a value that you want to query using Kaspersky Threat Intelligence Portal. A new browser window with Kaspersky Threat Intelligence Portal webpage will open, showing the lookup results for the query.
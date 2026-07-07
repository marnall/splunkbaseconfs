Cisco ThousandEyes Alerting App for Splunk

Introduction

This app has been developed inconjunction with Cisco by ECS and is part of the Cisco Service Assurance suite.

Overview

The Cisco ThousandEyes Alerting App for Splunk has been written to index and process ThousandEyes global alerts that are sent to Splunk by the cloud based ThousandEyes console using Splunk HTTP Event Collector (HEC).
The app also indexes and processes SNMP trap data. If SNMP trap data is to be included, then an on-premises SNMP trap receiver will have to be configured with a Splunk Universal Forwarder installed and configured to send the data to Splunk.

Lookup Files

The ThousandEyes Splunk app contains four lookup files that are customer specific. These lookup files allow you to group alerts together and apply different weighting to each ThousandEyes test rule in order to identify the root cause of the issue that has triggered the alerts. SNMP traps can also be grouped together and weighting applied to identify the root cause of the issue based on the SNMP trap. Using the same group name for ThousandEyes alerts and SNMP traps allows them to be correlated, and the root cause determined by both the ThousandEyes alerts and SNMP traps.

The app also supports creating ServiceNow incidents and populating them with correlated alerts and SNMP traps, as well as the root cause (that is determined by the entries made to the lookup files). If ServiceNow integration is required, then the Splunk Add-on for ServiceNow must also be installed and configured.

A Python script (available seperately) has also been created that can be used to enrich the alert data with information from the original test report (the origin of the alert). The Python script can be run using a web-hook handler to request the original test result (via an API call) and merge it with the alert to produce an enriched alert. The enriched alert can then be indexed in Splunk.

The ThousandEyes test report contains the original data that is used by ThousandEyes to determine if a rule has been breached, and results in an alert being triggered (and may contain additional information that is not included in the alert).


Introduction
------------
Welcome to the Splunk for Snort app! This app provides field extractions for Snort alert logs (fast and full) as well as dashboards, saved searches, reports, event types, tags and event search interfaces.

This app is maintained by Patrik Nordlen <patrik@nordlen.se>. Suggestions and bug reports are appreciated.


Installation
------------
To install, extract the .spl file in $SPLUNK_HOME/etc/apps

You will need to enable the appropriate inputs, either via inputs.conf, or through the Manager in the Splunk GUI. Splunk for Snort expects full alert logs to have a sourcetype of "snort_alert_full" and fast alert logs to have a sourcetype of "snort_alert_fast". Note that you don't need both types, any one will do - these distinctions are only there to make sure that Splunk parses the logs correctly. Sourcetypes are renamed to "snort" at search time, so if you do have both full and fast logs you won't need to worry about searching separately for each corresponding sourcetype.


Using Splunk for Snort
----------------------
-- Field extractions --

The most basic feature provided by this app is to extract fields from Snort logs. The following fields are extracted for both full and fast:

    * src_ip (Source IP address)
    * dst_ip (Destination IP address)
    * src_port (Source port)
    * dest_port (Destination port)
    * proto (Network protocol)
    * generator_id (ID value of the Snort generator)
    * signature (SID value of the signature)
    * signature_rev (Signature revision)
    * interface (Network interface)
    * name (Signature name)
    * category (Signature category)
    * classification (Signature classification)
    * priority (Signature priority)

The following fields are extracted for full only (as they are not available in fast):

    * ttl (Packet TTL)
    * tos (Type of Service)
    * id (Unique ID for the event)
    * iplen (Packet IP header length)
    * dgmlen (Packet total length)
    * bytes_in (Packet total length)

These field extractions are applied to all logs with sourcetype "snort" (which includes sourcetypes "snort_alert_fast" and "snort_alert_full" as they are renamed to "snort" at search time).


-- Snort event search --

The app includes a custom search interface for Snort events, available under "Snort event search". This interface shows events tables and statistics for issued searches.


-- Dashboards and reports --

A number of dashboards and reports are provided containing the most common information that is usually requested.


-- Map view --

Splunk for Snort provides a dashboard for viewing geographical location of source IPs that have triggered alerts. This map is populated through a scheduled search that runs every hour.
PLEASE NOTE THAT TO VIEW THIS MAP YOU NEED THE MAXMIND APP:
http://www.splunkbase.com/apps/All/4.x/app:Geo+Location+Lookup+Script

Splunk for Postfix
==================

Overview
--------
   * Splunk for Postfix integrates the open source email solution "Postfix" with Splunk
   * Features:
     * Dashboards with charts of Message Size, Messages by Status, Real-Time Message Count, Messages by Host, Top Clients, Top Relays, Top Senders, Top Recipients, Max Connection Count, Max Connection Rate, Max Cache Size, Max Simultaneous Connections, Address Lookups, and Domain Lookups
     * Summary-index-populating searches are scheduled hourly to efficiently report on large volumes of data
     * Quickly and easily view top delivery reasons, errors by host, and common error codes
     * Form Searches including Splunk Transactions by Queue ID
     * Over 20 field extractions, compliant with the Common Information Model

   * This is version 1.1.1 of Splunk for Postfix - any feedback, including requests for enhancement are most welcome. Email: luke@verypowerful.info
   * This app has been created for the specifics of our Postfix environment, so it may or may not suit your specific purposes
   * Copyright (c) 2012 Luke Harris. All Rights Reserved.


Setup Splunk for Postfix
------------------------
Splunk for Postfix should work with the following sourcetypes:
   * syslog
   * syslog_postfix

Ensure that your relevant sourcetype (eg. syslog) is searchable in an index that can be searched by default when no index is specified.

Add an Index to your Splunk Search Head:
   * Create an index called summary_postfix then restart Splunk
      * Note: all of the dashboards use searches based on index = summary_postfix
        which is populated hourly by summary index searches

Wait ~2 hours for the scheduled searches to start populating the summary_postfix index, and then view the included dashboards :)

Splunk includes the fill_summary_index.py script to backfill gaps in summary index collection by running the saved searches that populate
the relevant summary index as they would have been executed at their regularly scheduled times for a given time range. In other words, even
though your new summary_postfix index only started collecting data for the last hour, if necessary you can use fill_summary_index.py to fill
the summary index with data from the past month.

Reference:
http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Managesummaryindexgapsandoverlaps#Use_the_backfill_script_to_add_other_data_or_fill_summary_index_gaps


Disclaimer
----------
   * This app has been created for the specifics of our Postfix environment (Postfix version 2.7.x) and it may or may not suit your specific purposes.

License
-------
   * GNU GENERAL PUBLIC LICENSE Version 3

v1.1.1
------
 - added Delivery dashboard

v1.1
----
 - updated field extractions, added Errors dashboard

v1.0
----
 - initial release (private beta)


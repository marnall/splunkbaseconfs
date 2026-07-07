In order to use the Balabit SCB App for Splunk you need to have the Balabit SCB
Add-On for Splunk installed.

Note that this is the first public release of the app. We welcome your feedback!

Please consider the following when setting up the app:
- Session data is summarized in a summary index, thus you need to enable the
  balabit_scb_summary index. A template can found in default/indexes.conf.
- The app assumes that indexes containing the event data of your SCB are listed
  in "Indexes searched by default". If this is not the case, then please adjust
  the "balabit_scb_all_logs" macro and include the indexes in the search string.
- The Inspect dashboard in the app displays an embedded link to the SCB admin GUI
  to retrieve the audit trail file. To properly set this up, include a mapping
  between the name out of the "host" field in the event data to the DNS FQDN of
  your SCB in lookups/scb_appliance_to_webui.csv.
- To display system statistics, SNMP data collection must be setup, as described in
  the README file of the Balabit SCB Add-On for Splunk.

Known issues:
- The Auditing > Audit Trails dashboard is not yet summarized, thus it takes a bit longer
  to load.

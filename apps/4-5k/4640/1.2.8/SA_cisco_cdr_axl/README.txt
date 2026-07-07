# README for the Supporting AXL Addon for Cisco CDR Reporting and Analytics

Documentation
For all documentation see https://sideviewapps.com/documentation/supporting-axl-for-cisco-cdr-reporting-analytics-installation-and-setup

Requirements
  Splunk Enterprise 8.2 or higher

  SEARCH HEAD(S)
    This app is to be installed on the Search Head,
    alongside the main "Cisco CDR Reporting and Analytics" app.
    You will also need Sideview's "Canary" app installed.

  INDEXER(S)
    This app is NOT to be installed on the indexers.

  FORWARDER(S)
    This app is NOT to be installed on any forwarders.

Splunk Cloud compatibility
  The app is cloud-compatible but we do not actually recommend
  installing it in Splunk Cloud. Consult our docs for more details.

Search Head Cluster Considerations
  There aren't any. Put this on your SHC and it'll be fine.

TA-vmware-vision 1.0.2
VMware Vision ingestion add-on for Splunk heavy forwarders and indexers.

Install on the first full parsing tier for each VMware input path. If an HF
already parses all VMware events, downstream indexers do not need another
copy for parsing. Keep the full vmware_vision app on the search head.

This TA handles event boundaries, timestamps and character encoding only.
VM field extraction remains a search-time function of the main app and its
distributed-search knowledge bundle. The TA has no Python runtime dependency.

No inputs, outputs, indexes, credentials, dashboards or scripts are enabled
or included as active configuration. README/examples contains inactive samples.
Select only the examples needed on each tier and edit them before use.

Read README/TA_CONFIGURATION.md for setup and README/DEPLOYMENT.md for placement.
Verify collection and distributed search in your deployment.
Compatible with VMware Vision for Splunk 1.1.0.

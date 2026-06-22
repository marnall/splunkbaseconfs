# README for the TA_expressway_cdr

Documentation
For all documentation see:
https://sideviewapps.com/

Requirements
  Splunk Enterprise 9.0 or higher

  SEARCH HEAD(S)
    This app is NOT required on the SH tier

  INDEXER(S)
    If you are using the recommended cisco_expressway_syslog sourcetype, then this app must be installed on the Indexers.
    In all cases the index chosen must be created on the indexers by the local Splunk administrator(s)

  UNIVERSAL FORWARDER
    If you are using the other sourcetypes "cisco_expressway_cdr_csv" and "cisco_expressway_cdr_json" (currently less developed), then this app must be installed on the UF.  Note that this is the case even if this TA is *also* installed on the Indexer tier.
    Conversely, if you are NOT using the sourcetype "cisco_expressway_cdr_csv" or "cisco_expressway_cdr_json", then this app is NOT needed on the UF.

  HEAVY FORWARDER
    If you are using a heavy forwarder and the "cooking" of the data happens at HF, with "cooked" data forwarded to the indexer, then then this app must be installed on the HF.

Splunk Cloud compatibility
  Yes. This app passes appInspect and Cloud vetting.


Contact Sideview for any and all questions or comments.  support@sideviewapps.com


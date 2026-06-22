# README for the SA_expressway_cdr

Documentation
For all documentation see:
https://sideviewapps.com/

Requirements
  Splunk Enterprise 9.0 or higher

  SEARCH HEAD(S)
    This app is required on the SH tier.

  INDEXER(S)
    This app is NOT to be installed on the indexers.
    the index chosen must however be created on the indexers by the local Splunk administrator(s).
    (This app is however designed to be always deployed with Sideview's "Supporting Add-on for Expressway CDR" deployed to the Indexing tier.)

  FORWARDER(S)
    This app is not to be installed on the Forwarder tier,  with the exception of cases where you are using a Heavy Forwarder, in which case it is required there.  In the HF case the "cooking" of the Splunk data actually occurs there.


Splunk Cloud compatibility
  Yes. This app passes appInspect and Cloud vetting.

Search Head Cluster Considerations
  There are none.  Deploy this app to your SHC via the SHC Deployer.

Contact Sideview for any and all questions or comments.  support@sideviewapps.com


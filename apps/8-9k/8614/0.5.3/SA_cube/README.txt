# README for the SA_cube app

Documentation
For all documentation see:
https://sideviewapps.com/

Requirements
  Splunk Enterprise 9.0 or higher

  SEARCH HEAD(S)
    This app is required on the SH tier

  INDEXER(S)
    This app is NOT to be installed on the indexers.
    Although the index chosen must be created on the indexers ( by default this index is called "cisco_cdr")

  FORWARDER(S)
    This app is NOT to be installed on any forwarders. See TA_cube and TA_cisco_cdr.


Splunk Cloud compatibility
  The app can be deployed on Splunk Cloud - only on SH

Search Head Cluster Considerations
  There aren't any. Put this on your SHC and it'll be fine.

Contact Sideview for any and all questions or comments.  support@sideviewapps.com


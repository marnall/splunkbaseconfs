# README for the SA_cisco_meeting_server app

Documentation
For all documentation see:
https://sideviewapps.com/

Requirements
  Splunk Enterprise 8.0 or higher

  SEARCH HEAD(S)
    This app is required on the SH tier

  INDEXER(S) AND FORWARDER(S)
    As of this writing, Sideview has not pulled out a separate "TA_cisco_meeting_server" app.
    Instead the index-time configuration is bundled int his app alongside the search-time
    config. We acknowledge that this is less than ideal and over time this will be addressed.

    For now you should install this app on the SH tier, and also install it wherever you are
    running HEC.


Splunk Cloud compatibility
  The app can be deployed on Splunk Cloud

Search Head Cluster Considerations
  There aren't any. Put this on your SHC and it'll be fine.

Contact Sideview for any and all questions or comments.  support@sideviewapps.com


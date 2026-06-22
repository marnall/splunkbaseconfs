# README for the TA_cube app

Documentation
For all documentation see:
https://sideviewapps.com/

Requirements
  Splunk Enterprise 9.0 or higher

  SEARCH HEAD(S)
    This app is NOT to be installed on the SH tier

  INDEXER(S)
    This app should be installed on the indexers if you intend to use the
    "cube_syslog" sourcetype.
    In any event, the index chosen for the data must be created on the
    indexers.

  FORWARDER(S)
    This app should be installed on the forwarders if you intend to use the
    "cube_cdr" or "cube_cdr_compact", sourcetypes, as it contains parsingQueue
    configuration that needs to run out at the forwarders next to the data
    inputs.


Splunk Cloud compatibility
  The app can be deployed on Splunk Cloud.


Contact Sideview for any and all questions or comments at
  support@sideviewapps.com


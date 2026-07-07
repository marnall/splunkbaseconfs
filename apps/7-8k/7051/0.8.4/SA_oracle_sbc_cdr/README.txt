# README for the SA_oracle_sbc_cdr app

Documentation
For all documentation see:
https://sideviewapps.com/

Requirements
  Splunk Enterprise 8.0 or higher

  SEARCH HEAD(S)
    This app is required on the SH tier


  INDEXER(S)
    This app should not be installed on any indexers, UNLESS you are using just one or more standalone indexers, ie where the users are logging into the "indexer" node directly and running searches in its user interface.

  FORWARDER(S)
    This app should not be installed on any forwarders.


Splunk Cloud compatibility
  The app can be deployed on Splunk Cloud - only on SH

Search Head Cluster Considerations
  There aren't any. Put this on your SHC and it'll be fine.

Contact Sideview for any and all questions or comments.  support@sideviewapps.com

On the SBC:
   prevent-duplicate-attrs  should be disabled (which is the default)
   CDR output inclusive   should be DISABLED (set to 0)    IF enabled, this would give 0.0.0.0 instead of nulls, and 1970 timestamps instead of nulls etc, which is silly?
   vsa-id-range   should be blank.  or "set to blank" if possible.

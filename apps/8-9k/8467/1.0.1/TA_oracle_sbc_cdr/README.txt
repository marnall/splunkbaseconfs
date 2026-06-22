# README for the TA_oracle_sbc_cdr app

Documentation
For all documentation see:
https://sideviewapps.com/

Requirements
  Splunk Enterprise 8.0 or higher

  SEARCH HEAD(S)
    This app should not be installed on any search heads.


  INDEXER(S)
    This app contains index-time settings
    This app must be installed on the indexers (OR if you're using a Heavy Forwarder (HF), on the HF node).
    The index must also be created manually by the admins on the indexer nodes.

  FORWARDER(S)
    This app should not be installed on any Universal Forwarders.
    If you are already using a Heavy Forwarder and sending cooked data to your Indexers, this app should then be installed on the HF and in that case is not needed on the indexers.


Splunk Cloud compatibility
  The app can be deployed on Splunk Cloud - only on IDX OR HF


Contact Sideview for any and all questions or comments.  support@sideviewapps.com

On the SBC:
   prevent-duplicate-attrs  should be disabled (which is the default)
   CDR output inclusive   should be DISABLED (set to 0)    IF enabled, this would give 0.0.0.0 instead of nulls, and 1970 timestamps instead of nulls etc, which is silly?
   vsa-id-range   should be blank.  or "set to blank" if possible.

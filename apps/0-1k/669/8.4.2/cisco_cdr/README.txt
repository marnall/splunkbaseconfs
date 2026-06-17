# README for the Cisco CDR Reporting and Analytics app.

Documentation
For all install documentation and user documentation see:
https://sideviewapps.com/documentation/cisco-cdr-reporting-analytics-installation

Requirements
  Splunk Enterprise 8.0 or higher, or Splunk Cloud

  SEARCH HEAD(S)
    This app is to be installed on the Search Head.
    Canary app is required
        https://splunkbase.splunk.com/app/4697/


  INDEXER(S)
    This app is NOT to be installed on the indexers.
    However the index chosen must be created on the indexers ( by default this
    index is called "cisco_cdr")

  FORWARDER(S)
    This app is NOT to be installed on any forwarders, and that goes double for 
    IDM instances.  However TA_cisco_cdr is required on the forwarders and is 
    available on Splunkbase. If you are Cloud Support reading this then the 
    customer and Sideview Support will already have taken care of this part.


Splunk Cloud compatibility
    The app is compatible with Splunk Cloud and can be deployed on Splunk Cloud
    (only on SH, NOT on IDXC or IDM. See above).
    Appinspect:  Although there are often false positives in appinspect and at 
    any given time, the most recent versions of the app are often still making 
    their way through the manual vetting queue, be aware that this app generally 
    does pass Splunk's manual vetting.

Search Head Cluster Considerations
    There aren't any. Put this on your SHC and it'll be fine.
    DO NOT DELETE the inputs.conf file. See comments in inputs.conf. Splunk 
    Cloud folks - this app is already whitelisted as one of the few special apps 
    that are allowed to have inputs on the SH tier.

Contact Sideview for any and all questions or comments.  support@sideviewapps.com

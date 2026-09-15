# README for the TA_cisco_cvp app

Documentation
For all documentation see:
https://sideviewapps.com/

Requirements
  Splunk Enterprise 9.0 or higher

  SEARCH HEAD(S)
    This app should not be installed on any search heads.
    Install the "SA_cisco_ucce" app there instead, which carries all of the
    search-time config for this data.

    On a single-instance deployment, where one Splunk instance is search head,
    indexer and forwarder at once, you do need both this app and SA_cisco_ucce.

  INDEXER(S)
    This app contains index-time settings and should be installed on the
    indexers (OR, if you are using a Heavy Forwarder and for some reason
    sending cooked data to your indexers, on the HF instead).
    The index chosen for the data must also be created on the indexers.

  FORWARDER(S)
    Do not install on UF instances and only install on HF instances
    if for some reason you are doing something custom that necessitates
    cooking the index-time config on the forwarder tier and sending cooked
    data to the indexers.  If you don't know what this means then you don't
    need this app on your HF.


What to monitor
  On a CVP Call Server, the logs live under the CVP install directory, by
  default:

    <CVP>\logs\CVP\CVP.<date>.log          Call Server (SIP, IVR, ICM subsystems)
    <CVP>\VXMLServer\logs\...              VXML Server
    <CVP>\logs\OAMP\...                    Operations Console

  All of them share the header format this app parses, so all of them can go to
  sourcetype "cvp".

  The Call Server log is a mixed file: alongside the product's own
  "%CVP_<version>_<subsystem>-<severity>-<mnemonic>:" lines it carries the
  embedded SIP stack's own logging, which uses a "%_<component>-<severity>-<class>:"
  header instead.  Both are handled, but the second form is handled by the
  search-time config in SA_cisco_ucce, not here.


Splunk Cloud compatibility
  The app can be deployed on Splunk Cloud - only on IDX OR HF.


Contact Sideview for any and all questions or comments at
  support@sideviewapps.com

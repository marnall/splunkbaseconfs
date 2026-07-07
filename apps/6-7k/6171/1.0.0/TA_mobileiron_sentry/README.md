Add-on Homepage: https://apps.splunk.com/apps/id/TA_mobileiron_sentry

Author: Hurricane Labs

Version: 1.0.0

### Description ###
Provides CIM field extractions for MobileIron Sentry syslog.

* Built for Splunk Enterprise 7.x.x or higher
* CIM Compliant (CIM 4.x.x or higher)
* Ready for Enterprise Security

### Constraints / Requirements ###
* Onboard data with sourcetype "mobileiron:sentry" so it can be properly transformed
* Install this TA on your Search Head(s) & the first Splunk Enterprise instance that touches the data
* Documentation for MobileIron Sentry syslog can be found here:
    * https://help.ivanti.com/mi/help/en_us/sntry/9.9.0/gdcl/Content/SentryGuide/Syslog.htm
    * https://help.ivanti.com/mi/help/en_us/sntry/9.9.0/gdcl/Content/SentryGuide/Log_representation_and_f.htm

### INSTALLATION AND CONFIGURATION ###

#### Installation Instructions ####
1. Install this TA on the first Splunk Enterprise instance that touches the data. This is typically a Heavy Forwarder or Indexer. This will put the proper index time settings in place required for this TA to function.
2. Install this TA on your Search Head(s)
3. Onboard your data with the sourcetype "mobileiron:sentry"
4. Validate everything worked by searching for the two new sourcetypes in your environment: `sourcetype=mobileiron:sentry:mi OR sourcetype=mobileiron:sentry:audit`
    * If you see "mobileiron:sentry" as a sourcetype, then you did not install this TA on the first Splunk Enterprise instance that touches the data so the transforming is failing (or your data is formatted differently and you'd need to adjust the transforms.conf).


### New features

### Fixed issues

### Known issues

### Third-party software attributions

### DEV SUPPORT
* Contact: splunk-app@hurricanelabs.com

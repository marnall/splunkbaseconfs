Add-on Homepage: https://apps.splunk.com/apps/id/TA_netmotion_mobility_syslog

Author: Hurricane Labs

Version: 1.0.0

### Description ###
Provides CIM field extractions and other useful field extractions, as well as sourcetype transforming based on the event.

* Currently Supports:
    * NetMotion Mobility Server Event Log (nmservic.exe)
        * https://help.netmotionsoftware.com/support/docs/MobilityXG/1130/help/mobilityhelp.htm#page/Mobility%2520Server%2Fmanage.07.014.html%23
* Built for Splunk Enterprise 7.x or higher
* CIM Compliant (CIM 4.15 or higher)
* Ready for Enterprise Security

### Constraints / Requirements ###
* Requires the use of the Syslog as described here:
    * https://help.netmotionsoftware.com/support/docs/MobilityXG/1130/help/mobilityhelp.htm#page/Mobility%2520Server%2Fmanage.07.016.html%23
* Requires that you onboard data with the sourcetype "netmotion:mobility" for it to be transformed and receive the appropriate fields.

### INSTALLATION AND CONFIGURATION ###

#### Installation Instructions ####
1. This TA should be installed on your Search Heads and the first Splunk Enterprise instance that touches the data (typically Heavy Forwarder(s) or Indexer(s)
2. Ensure Splunk Enterprise has restarted on the parsing instance before ingesting data
3. Data ingestion can be accomplished in many ways. Best practice would be to use a syslog solution that writes out to a file on disk that you monitor with a Splunk file monitor inputs.conf OR use SC4S. You can use the built in Splunk TCP/UDP listener, but this is highly discouraged.
4. Once TA installation and data ingestion have been completed, search your data with `index=X sourcetype=netmotion:mobility:*`
    * You should see many different sourcetypes appear. If you see `netmotion:mobility` as a sourcetype, then the TA was not installed on the parsing tier correctly or your data is formatted differently than expected (and will require a custom fix in local/transforms.conf).

### New features

### Fixed issues

### Known issues

### Third-party software attributions

### DEV SUPPORT
* Contact: splunk-app@hurricanelabs.com

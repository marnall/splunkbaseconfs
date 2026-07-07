Add-on Homepage: https://apps.splunk.com/apps/id/TA-microsoft_nps_radius

Author: Hurricane Labs

Version: 1.1.2s

### Description ###
This add-on ensures that there is proper parsing and CIM compliance for radius logs from Microsoft Network Policy Server (NPS).

* Built for Splunk Enterprise 6.x.x or higher
* +CIM Compliance (CIM 4.0.0 or higher)
* Ready for Enterprise Security

### Constraints / Requirements ###
This app writes to the sourcetype microsoft:nps:radius by default.
It must be installed on a search head to function.

### INSTALLATION AND CONFIGURATION ###

* Search Head: Required
* Heavy Forwarder: Optional
* Indexer: Optional
* Universal Forwarder: Not Supported
* Light Forwarder: Not Supported

#### Installation Instructions ####
* Install the add-on on the Search Head. A Splunk Restart may be required, but you may also attempt a debug refresh.

### New features
Adds additional packet type and reason code translations. 
Fixes issue with improper extractions

### Fixed issues
None
### Known issues
None
### Third-party software attributions
None
### DEV SUPPORT
* Contact: splunk-app@hurricanelabs.com

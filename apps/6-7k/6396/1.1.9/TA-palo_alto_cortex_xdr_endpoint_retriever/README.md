### Description ###
Addon to pull asset information from Palo Alto's Cortex XDR API endpoint.

* Built for Splunk Enterprise 8.0.0 or higher
* Ready for Enterprise Security

### Constraints / Requirements ###
The app can be installed on a forwarder or a search head (in the case of Cloud Victoria Experience).
The default sourcetype for this addon is cortex:xdr:endpoints, which by default will poll the Cortex XDR API once per day.

### INSTALLATION AND CONFIGURATION ###

#### Installation Instructions ####
1. Install the app on a forwarder or search head, depending on your environment configuration.
2. Enter your API credentials, organization name, and authentication settings on the Configuration page.
3. Configure your input under the Inputs tab as needed

### New features
Version 1.1.9 fixes an issue where headers would expire for very large implementations
### Fixed issues
Timeouts
### Known issues
None
### Third-party software attributions

### DEV SUPPORT
The add-on is provided as-is. No additional support is offered.

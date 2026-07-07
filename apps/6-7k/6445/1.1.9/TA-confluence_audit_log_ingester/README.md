### Description ###
Addon to pull audit information from Confluence Cloud's Organization REST API
* Built for Splunk Enterprise 8.0.0 or higher
* Ready for Enterprise Security

### Constraints / Requirements ###
- The app can be installed on a forwarder or a search head (in the case of Cloud Victoria Experience).
- API keys and Org IDs can vary across the type of audit logs, so each input will need to have a separate Org ID and API key entered.
- This is a single script instance modular input. This means that the interval parameter will only be read from the default stanza in inputs.conf, and any intervals configured under user added stanzas will be ignored. See https://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/ModInputsSpec#single_script_instance_mode for more information.

### INSTALLATION AND CONFIGURATION ###

#### Installation Instructions ####
1. Install the app on a forwarder or search head, depending on your environment configuration.
2. Configure your input under the Inputs tab. Org ID and API key's are required for each input

### New features
Version 1.1.9 is the tenth release
### Fixed issues
Version 1.1.9 updates the Splunk Python SDK to version 2.0.2
### Known issues
None
### Third-party software attributions

### DEV SUPPORT
This app is provided as-is. No additional support is offered.
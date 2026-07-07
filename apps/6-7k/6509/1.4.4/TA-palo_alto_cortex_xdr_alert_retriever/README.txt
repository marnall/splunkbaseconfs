### Description ###
Addon to pull alert information from Palo Alto's Cortex XDR Get Alerts API endpoint.

* Built for Splunk Enterprise 8.0.0 or higher
* Ready for Enterprise Security

### Constraints / Requirements ###
The app can be installed on a forwarder or a search head (in the case of Cloud Victoria Experience).
The default sourcetype for this addon is cortex:xdr:alerts, which by default will poll the Cortex XDR API once per minute.

### INSTALLATION AND CONFIGURATION ###

#### Installation Instructions ####
1. Install the app on a forwarder or search head, depending on your environment configuration.
2. Enter your API credentials, organization name, and authentication settings on the Configuration page. Your organization name can be found in your Cortex XDR console.
3. Configure your input under the Inputs tab as needed. By default, the input runs once every 5 minutes.

### New features
Version 1.4.4 is the eighth release.
### Fixed issues
Updates Splunk Python SDK to version 2.0.2
### Known issues
None
### Third-party software attributions

### DEV SUPPORT
This app is provided as-is. No further support is offered.

# Binary File Declaration
bin/ta_palo_alto_cortex_xdr_alert_retriever/aob_py3/setuptools/gui.exe: this file does not require any source code
bin/ta_palo_alto_cortex_xdr_alert_retriever/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
bin/ta_palo_alto_cortex_xdr_alert_retriever/aob_py3/setuptools/gui-64.exe: this file does not require any source code
bin/ta_palo_alto_cortex_xdr_alert_retriever/aob_py3/setuptools/gui-32.exe: this file does not require any source code
bin/ta_palo_alto_cortex_xdr_alert_retriever/aob_py3/setuptools/cli.exe: this file does not require any source code
bin/ta_palo_alto_cortex_xdr_alert_retriever/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
bin/ta_palo_alto_cortex_xdr_alert_retriever/aob_py3/setuptools/cli-64.exe: this file does not require any source code
bin/ta_palo_alto_cortex_xdr_alert_retriever/aob_py3/setuptools/cli-32.exe: this file does not require any source code
bin/ta_palo_alto_cortex_xdr_alert_retriever/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code

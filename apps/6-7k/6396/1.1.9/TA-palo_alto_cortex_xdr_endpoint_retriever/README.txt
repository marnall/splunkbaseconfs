# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/setuptools/gui.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/setuptools/gui-64.exe: this file does not require any source code

### Description ###
Addon to pull asset information from Palo Alto's Cortex XDR API endpoint.

* Built for Splunk Enterprise 8.0.0 or higher
* Ready for Enterprise Security

# Binary File Declaration
/Applications/Splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-palo_alto_cortex_xdr_endpoint_retriever/bin/ta_palo_alto_cortex_xdr_endpoint_retriever/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code

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

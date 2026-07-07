### Version 1.4.1
* Added settings to the conf_replication_include


### Version 1.4.0

* A new configuration option has been added that allows to use a custom prefix in VirusTotal fields, which could prevent collisions between fields.
* Optimized default.meta config
* Updated Splunk SDK to 2.1.1 version

Important breaking changes: "vt_result" output field now will be "result" if not prefix is used


### Version 1.3.4

* Fixed connection issue with url, domain and ip commands


### Version 1.3.3

* Removed library to avoid warning of Splunk Cloud Veting
* Fixed exception


### Version 1.3.2

* Fixed admin user for Splunk Cloud

### Version 1.3.1

* Fixed exception when connection fails

### Version 1.3.0

* Integrated asynchronous HTTP client to reduce time fetching data from VirusTotal
* Enhanced logs creating an app log file to debug errors

### Version 1.2.0

* Added new option to get URL, Domain and IPs reports.
Examples:
... | vt url="https://example.com"
... | vt domain="example.com"
... | vt ip="8.8.8.8"

### Version 1.1.1

* Splunk Cloud App Vetting changes

### Version 1.1.0

* Added the capability to set up a proxy configuration
* Renamed vthash command to vt
* Added CHANGELOG.md and README.md files

### Version: 1.0.0

* First release.
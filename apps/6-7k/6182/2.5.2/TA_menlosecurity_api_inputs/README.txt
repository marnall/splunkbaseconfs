This is an add-on powered by the Splunk Add-on Builder.

2.0.0 Updates
* Add support for API query parameter when calling the Menlo log API
* Change defualt value of the source field from the API URI to the input stannza name
* Fixed bug when backfill is set to "0"
* Add support for fractional days in backfill values
* Add support to limit the maximum timespan in the API request

2.1.0 Updates
* Add Proxy support
* Add support for v2 Menlo API & tokens
* Increase default API timeout from 5-sec to 20-sec
* Add configuration option for API timeout
* Add Splunk & Add-On versions to User-Agent header

2.1.3 Updates
* Correct timespans in API queries to avoid missing events

2.2.0 Updates
* Add configuration option for settling time
* Save checkpoint even when no events are retreived in an interval

2.2.2 Updates
* Update end-time cacluation to use the configuration option for settling time - the option was previously unused

2.3.0 Updates
* Rename the "Threat Intelligence" Log Type "HEAT Alerts"
* Add TRUNCATE=20000 to props.conf for menlo:log:web sourcetype
* Add "Remove NA fields" option to remove fields with the value of "NA" from the events before sending the events for indexing

2.4.7 Updates
* Update to use add-on builder v4.3.0
* Update Splunk Python SDK from 1.6.18 to v2.1.0
* Update splunktalib from 3.0.0 to v3.0.5
* Update splunktaucclib from 6.0.0 to 6.5.3

2.5.0 Updates
* Add support for "Client logs"

2.5.1 Updates
* Fix bug to map "Client logs" to "ms_client_logs" log_type

2.5.2 Updates
* Add props.conf settings for parsing raw ms_client_logs

# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA_menlosecurity_api_inputs/bin/ta_menlosecurity_api_inputs/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA_menlosecurity_api_inputs/bin/ta_menlosecurity_api_inputs/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/Applications/Splunk/var/data/tabuilder/package/TA_menlosecurity_api_inputs/bin/ta_menlosecurity_api_inputs/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA_menlosecurity_api_inputs/bin/ta_menlosecurity_api_inputs/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/Applications/Splunk/var/data/tabuilder/package/TA_menlosecurity_api_inputs/bin/ta_menlosecurity_api_inputs/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA_menlosecurity_api_inputs/bin/ta_menlosecurity_api_inputs/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/Applications/Splunk/var/data/tabuilder/package/TA_menlosecurity_api_inputs/bin/ta_menlosecurity_api_inputs/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA_menlosecurity_api_inputs/bin/ta_menlosecurity_api_inputs/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code

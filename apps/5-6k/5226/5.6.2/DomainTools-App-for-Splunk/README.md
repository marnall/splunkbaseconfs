## DomainTools App for Splunk

The DomainTools App provides direct access to DomainTools’ industry-leading threat intelligence data, predictive risk scoring, and critical tactical attributes to gain situational awareness on malicious domains inside of Splunk.

### App version: 5.6.2

Download on Splunkbase: <https://splunkbase.splunk.com/app/5226/>

#### Key Dependencies

- DomainTools Iris Enrich API access
- DomainTools Iris Investigate API access
- DomainTools Iris Detect API access (optional but recommended)
- DomainTools Whois History API access (optional but recommended)
- DomainTools Python API library (packaged along with the app)

##### Note

The DomainTools Python API library (<https://github.com/DomainTools/python_api>) makes available all API endpoints that DomainTools currently supports. However, within Splunk we leverage only the aforementioned APIs. Not all of the DomainTools API endpoints contained in the DomainTools Python API library are supported within our Splunk App.

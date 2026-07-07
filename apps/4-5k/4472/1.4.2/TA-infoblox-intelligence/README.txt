Splunk Add-on for Infoblox Intelligence allows to get threat intelligence from TIDE (hosts/IPs/URLs - depending on your licenses) and network intelligence from networks in NIOS IPAM. It optionally allows to feed Splunk Entreprise Security (Splunk ES).

Threat Intelligence

Pre-requisite: 
- TIDE api key
- Treemap app - https://splunkbase.splunk.com/app/3118/
- Punchcard - https://splunkbase.splunk.com/app/3129/
- Punycode Address Decoder - https://splunkbase.splunk.com/app/3558

 
Set Configuration / Add-on-settings / TIDE API Key with the key obtained from TIDE / https://platform.activetrust.com

Enable existing inputs or create new input
- to enable input configuration, click on the existing Infoblox threat intelligence domains /  Infoblox threat intelligence IPs /  Infoblox threat intelligence URLs, enable
- to create a new input configuration, click "Create New Input",  Infoblox threat intelligence domains /  Infoblox threat intelligence IPs /  Infoblox threat intelligence URLs
    - Name: Unique name for the input configuration.
    - Interval: The number of seconds between data collections. 3600 second is recommended
    - Profile: IID is the only option currently supported
    - Index: a dedicated index is recommended for best performance e.g: tide. Modify tide_idx eventtype to reflect your index choice

Network Intelligence

Network intelligence is based on the network list exported is in CSV including extensible attributes.
The extensible attributes mapped to Splunk Entreprise Security are Owner, SecurityLevel, latitude, longitude, City, Country plus the comment field.
It is highly recommended to create it on NIOS to have full benefit of this integration.

- To create a new input configuration click "Create New Input" / "Infoblox IPAM Networks"
    - Name: Unique name for the input configuration.
    - Interval: The number of seconds between data collections. 3600 second is recommended
    - API URI Base: The URL provided for the Infoblox NIOS grid master. For example: https://infoblox-grid-master.company.internal
    - API version: v2.5 by default
	- Username / Password: credentials for the account that has read access to all networks over WAPI
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-infoblox-intelligence/bin/ta_infoblox_intelligence/aob_py2/markupsafe/_speedups.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-infoblox-intelligence/bin/ta_infoblox_intelligence/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code

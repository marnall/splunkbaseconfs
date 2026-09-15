macadress.com MAC Address Lookup
=================================

Adds a `macaddresslookup` search command that enriches events with vendor,
device-category, virtualization, and special-use information for a MAC
address field, via the macadress.com API (https://macadress.com).

Setup
-----
1. Get a free API key at https://macadress.com/signup.
2. In Splunk Web, open this app and go to Configuration, then enter the API
   key on the Settings tab. It is stored via Splunk's encrypted
   storage/passwords endpoint, never in a plain-text .conf file.

The configuration page is built with the Universal Configuration Console
(UCC), so it works on Splunk Enterprise, Splunk Cloud Platform, and
Search Head Clustered deployments.

Usage
-----
    ... | macaddresslookup field=<fieldname containing a MAC address>

Example:
    index=network sourcetype=dhcp
    | macaddresslookup field=src_mac
    | stats count by mac_organization, mac_device_category

Fields added
------------
mac_valid, mac_registered, mac_oui, mac_matched_prefix, mac_organization,
mac_vendor_slug, mac_country, mac_block_type, mac_locally_administered,
mac_administration_type, mac_transmission_type, mac_potentially_randomized,
mac_randomization_confidence, mac_device_category, mac_device_confidence,
mac_virtualization_platform, mac_special_use_type, mac_explanation,
mac_lookup_error (set only when a lookup fails).

Requests are batched up to 100 addresses per API call and billed against
your macadress.com plan quota, the same as any other API call.

Changes in 1.1.0
----------------
Replaced the legacy setup.xml configuration screen with a UCC-generated
configuration page. setup.xml is not supported on Splunk Cloud Platform or
with Search Head Clustering; the UCC page is. Existing installs must
re-enter the API key once on the new Configuration page after upgrading.

Support
-------
https://macadress.com/docs
https://github.com/samymassoud/macadress

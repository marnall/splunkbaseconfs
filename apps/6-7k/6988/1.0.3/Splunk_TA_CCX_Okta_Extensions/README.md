**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

CCX Security Operations has taken it upon ourselves to improve the existing Splunk Add-on "Splunk Add-on for Okta Identity Cloud" as to ensure it is as CIM compliant as possible.

This TA does not replace the public Splunk Add-on "Splunk Add-on for Okta Identity Cloud" available in Splunkbase, but works as an additional extension to be deployed on Search Heads (only).

Currently this add-on provides additional field extraction and CIM compliance for sourcetypes:

- OktaIM2:log


Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA includes a saved search that populates user details to a lookup that serves to enrich log verbosity and accuracy match for users involved in Okta events (check configuration/installation details) 
- Log truncation support for all available sourcetypes
   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Okta |
| Service Provider | CyberCX |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads.
- Install Add-on Splunk Add-on for Okta Identity Cloud (https://splunkbase.splunk.com/app/6553) version 4.0.0 or higher.

**Installation:**

- This Add-on is intended to be installed on Splunk Search Heads.
- Install Add-on Splunk Add-on for Okta Identity Cloud (https://splunkbase.splunk.com/app/6553) version 4.0.0 or higher.
- After install this Extensions Add-on:

- 1)update the macro "ccx_okta_extensions_indexes" with your Okta index
- 2)run the saved search "CCX Okta Extensions User Record - Lookup Gen" manually selecting "All Time"
- 3)copy calculated field expression "user" from this Add-on over the calculated field expression "user" on default Add-on

*Do not modify the macro "()" from the default TA "Splunk Add-on for Okta Identity Cloud" version 4.0.0 as we are not supporting the default TA savedsearches.

**Troubleshooting:**

If OktaIM2:group sourcetype requires a support for Event Breaks, apply the following regex to the respective sourcetype on the instance where the inputs are configured

- Regex Option1 (?<=\}\}\})(\, ) 

- Regex Option2  (alternatively you can use this regex) (\},)\{|(\[)\{|(\])\}

In case the issue above persists please use our contact for support.

**Attribution:**

CyberCX acknowledges the excellent (foundation) work done by Splunk Inc. team to provide this TA.
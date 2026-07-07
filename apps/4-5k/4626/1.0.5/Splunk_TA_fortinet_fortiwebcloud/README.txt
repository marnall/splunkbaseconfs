*********************************************
*
* Add-On: Fortinet FortiWebCloud Add-On for Splunk
* Current Version: 1.0.1
* Last Modified: August 2019
* Splunk Version: 7.x
* Author: Fortinet Inc.
*
*********************************************



**** Overview ****

Fortinet FortiWeb Cloud Add-On for Splunk is the technical add-on (TA) developed by Fortinet, Inc.
The Add-on enables Splunk Enterprise to ingest or map security and audit data collected from FortiWeb Cloud.

The key features include:

• Ingesting attack logs of FortiWebCloud.

• Ingesting audit logs of FortiWebCloud.

**** Configuration Steps ****

Please refer to https://splunkbase.splunk.com/app/
for detailed configuration steps

**** sourcetypes and eventtypes ****

	fwbcld_attack
		ftnt_fwbcld_attack
	fwbcld_event
		ftnt_fwbcld_event
	fwbcld_traffic
		ftnt_fwbcld_traffic

**** CIM mappings ****

	Malware
	Attack
	Change
	Endpoint

**** Release Notes ****

v1.0.1: August 2019
    - Remove the duplicated stanza in transforms.conf.

v1.0.0: July 2019
    - Initial release.


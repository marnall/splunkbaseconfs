# Technology Add-on for Vectra Detect (JSON)

**Author:** Vectra AI

**Version:** 1.4.4

**Supported products:**

* Vectra X Series

**Supported CIM Version:**

* &gt;=4.0.0

**Supported CIM Datamodels:**

* Intrusion Detection

**Sourcetypes:**

* `vectra:cognito:audit:json`
* `vectra:cognito:campaigns:json`
* `vectra:cognito:cef:json`
* `vectra:cognito:detect:json`
* `vectra:cognito:accountdetect:json`
* `vectra:cognito:health:json`
* `vectra:cognito:hostscoring:json`
* `vectra:cognito:accountscoring:json`
* `vectra:cognito:accountlockdown:json`
* `vectra:cognito:hostlockdown:json`
* `vectra:cognito:match:json`

**Add-on contains:**

* Search and Parsing-Time configuration

**Input requirements:**

* This release requires Vectra X series to send data in syslog JSON format

## How to map detections to MITRE techniques.
A new Splunk Search processing Language command had been released to add the MITRE techniques to Vectra's detections: **vectramitre**.  

This command, when called in the pipeline, will add a new field named *techniques* by looking at the field named *d_type_vname*.  

This mapping uses our Coverage of MITRE ATT&CK published [on our Knowledge Base](https://support.vectra.ai/s/article/KB-VS-1158).  

When you want to use the latest mapping, you can download the file ending by detection_to_technique.json, rename it to detection_to_technique.json and put it in the json folder of this app. 
Restarting Splunk is not needed.

## Using this Technology Add-on

* The add-on has to be installed on Search Heads
* If data is collected through Intermediate Heavy Forwarders, it has to be installed on Heavy Forwarders, otherwise on indexers
* The add-on expects an initial sourcetype named `vectra:cognito:detect:json`, the sourcetype will be transformed into more specific ones (see sourcetype list)
* A sample `inputs.conf` is provided (`default/inputs.conf.sample`)

## Compatibility

* This new add-on is compatible with the Vectra Detect App >= 1.2.0

## Release Notes

* **1.4.4 / 2025-December-26**
  * Upgraded Splunk SDK to v2.1.1

* **1.4.1 / 2024-January-16**
  * #TM-3373: Map detections to MITRE technique into Splunk

* **1.3.0 / 2023-April-18**

  * #TM-1853: Add support for Vectra's Match


* **1.2.0 / 2022-July-12**

  * #TM-1314: Improved CIM compatibiltiy
  * #TM-1316: Update Vectra's logo

* **1.1.0 / 2021-Apr-28**

  * #TM-233: Update sourcetype names to use different names as the former CEF TA.
  * #TM-333: Update eventtype search query to match new sourcetypes.

* **1.0.0 / 2020-Sep-30**

  * Initial release

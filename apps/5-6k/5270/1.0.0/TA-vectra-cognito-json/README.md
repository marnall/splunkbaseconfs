# Technology Add-on for Vectra Cognito (JSON)

**Author:** Vectra AI

**Version:**

* 1.0.0

**Supported products:**

* Vectra X Series

**Supported CIM Version:**

* &gt;=4.0.0

**Supported CIM Datamodels:**

* Intrusion Detection

**Sourcetypes:**

* `vectra:cognito:audit`
* `vectra:cognito:campaigns`
* `vectra:cognito:cef`
* `vectra:cognito:detect`
* `vectra:cognito:accountdetect`
* `vectra:cognito:health`
* `vectra:cognito:hostscoring`
* `vectra:cognito:accountscoring`
* `vectra:cognito:accountlockdown`
* `vectra:cognito:hostlockdown`

**Add-on contains:**

* Search and Parsing-Time configuration

**Input requirements:**

* This release requires Vectra X series to send data in syslog JSON format

## Using this Technology Add-on

* The add-on has to be installed on Search Heads
* If data is collected through Intermediate Heavy Forwarders, it has to be installed on Heavy Forwarders, otherwise on indexers
* The add-on expects an initial sourcetype named `vectra:cognito:json`, the sourcetype will be transformed into more specific ones (see sourcetype list)
* A sample `inputs.conf` is provided (`default/inputs.conf.sample`)

## Compatibility

* This new add-on is compatible with the current Vectra Cognito App.


## Release Notes

* **1.0.0 / 2020-09-30** mbo

  * Initial release

## Change Log


# Technology Add-on for Vectra Cognito Stream

**Author:** Vectra Networks

**Version:**

* 1.1.1

**Supported products:**

* Vectra Cognito Stream

**Supported CIM Version:**

* &gt;=4.0.0

**Supported CIM Datamodels:**

* Network Traffic (isession metadata)
* Network Resolution (dns metadata)
* Email (smtp metadata)
* dhcp (Network Sessions)
* httpsessioninfo (Web)

**Sourcetypes:**

* `vectra:cognito:stream`
* `bro_conn`
* `bro_dns`

**Add-on contains:**

* Search and Parsing-Time configuration

**Input requirements:**

* This release requires Vectra Stream to send data in syslog format over TCP.

## Using this Technology Add-on

* The add-on has to be installed on Search Heads
* If data is collected through Intermediate Heavy Forwarders, it has to be installed on Heavy Forwarders, otherwise on indexers
* The add-on expects an initial sourcetype named `vectra:cognito:stream`, the sourcetype will be transformed only for isession and dns metadata.
* A sample `inputs.conf` is provided (`default/inputs.conf.sample`)

## Release Notes

* **1.1.1 / 2020-04-27** mbo

  * #TM-364: Global permission
  * #TM-332: Wrong filter in eventtype searches
  * #TM-366: Missing aliases for CIM compatibility

* **1.1.0 / 2020-06-18** mbo

  * Add SMTP parser and mapping to Email Data Model
  * Fix the extraction of SAN attributes of X509 certificates

## Change Log

* **1.1.0 / 2020-06-18** mbo

  * Add SMTP parser and mapping to Email Data Model
  * Fix the extraction of SAN attributes of X509 certificates


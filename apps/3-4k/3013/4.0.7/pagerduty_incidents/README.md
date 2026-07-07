PagerDuty is an agile incident management solution that integrates with IT Ops and DevOps monitoring stacks to improve operational reliability and agility. With 150+ integrations, automated scheduling, advanced reporting and guaranteed reliability, PagerDuty is trusted by 7000+ organizations globally to increase business and employee efficiency.

The PagerDuty App enables Splunk customers to deliver faster response times to service disruptions. Specifically, joint PagerDuty and Splunk customers can:

- Allow PagerDuty to leverage the Splunk Alerts framework with one click, which saves users significant time and energy
- Connect a single Splunk instance to multiple PagerDuty services or accounts, which allows users to tailor their Splunk alerts in PagerDuty to their specific needs and workflow
- Streamline and group incident data within PagerDuty, which reduces alert noise and information overload by allowing users to group incidents in a manner that makes sense to them

## App Description

The purpose of this app is to setup custom alert actions that forward to PagerDuty

## Installation Instructions

* Install via the Splunk Web Admin
* Configure using the full integration url or the integration key supplied after adding the splunk service in the PagerDuty Admin.
* Integration Guide can be found here https://www.pagerduty.com/docs/guides/splunk­integration­guide/

## Dependencies

N/A

## Where to install

The app needs to be installed on the search heads.

## Features

Easily integrates with PagerDuty’s event API to handle oncall alert triggers.

##Support

Website: https://support.pagerduty.com
Email: support@pagerduty.com
Licence: Default Splunkbase license

## Open Source Libraries

No external open-source libraries

## Changelog:

### Version 4.0.7

* Fix: Update the connection logic to dynamically parse the server_uri from the incoming payload
* Splunk Cloud compatibility: resolve AppInspect failure

### Version 4.0.6

* Validated App for Splunk 10
* Upgrade [Splunk SDK](https://github.com/splunk/splunk-sdk-python) to 2.1.1

### Version 4.0.5

* Fixing rakefile
* Upgrade [Splunk SDK](https://github.com/splunk/splunk-sdk-python) to 2.0.2

### Version 4.0.4

* Fixing bug related to token delimiters for search tokens with double quotes
* Upgrade splunklib to 1.7.4 and resolve related warnings

### Version 4.0.1

* Changing storage for integration keys/URLs

### Version 3.0.4

* Application update
* Adding token delimiters for search tokens with double quotes

### Version 3.0.3

* Fixing bug when overriding URL

### Version 3.0.2

* Adding back integration_url parameter.  Which will now take precedence over integration_key if specified.

### Version 3.0.1

* Allowing for global Event Rules integration_keys

### Version 3.0.0

* Updates to the configuration UI.
*  (integration_url) is no longer supported.
*  After setup please set the default Integration Key

### Version 2.0.3

* Python 3 Upgrade

### Version 2.0.0

Allowing Custom Details to be sent by either JSON or Text to PD
Compatible with Python 2/3

### Version 1.1

Changes for certification

### Version 1.0

Initial Release

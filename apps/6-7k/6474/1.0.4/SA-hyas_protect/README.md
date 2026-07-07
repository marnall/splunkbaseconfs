# HYAS Protect for Splunk


## Table of Contents

### OVERVIEW

- About HYAS Protect for Splunk
- Release notes
- Performance benchmarks
- Support and resources

### INSTALLATION

- Hardware and software requirements
- Installation steps

### USER GUIDE

- Key concepts
- Usage (command/lookup documentation)
- Configuration
- Troubleshooting

---
### OVERVIEW

#### About HYAS Protect for Splunk

| Author | HYAS Infosec, Inc. |
| --- | --- |
| App Version | 1.0.0 |
| Vendor Products | HYAS Protect |
| Has index-time operations | false |
| Create an index | false |
| Implements summarization | false |

HYAS Protect is a generational leap forward utilizing authoritative knowledge of attacker
infrastructure including unrivaled domain-based intelligence to proactively protect enterprises from cyberattacks.
HYAS Protect is deployed as a cloud-based DNS security solution or through API integration with existing solutions.
HYAS Protect combines infrastructure expertise and multi-variant communication pattern analysis to deliver reputational 
verdicts for any domain and infrastructure, allowing enterprises to preempt attacks while proactively assessing risk in real-time.
HYAS Protect can enforce security, block command and control (C2) communication used by malware, ransomware, and botnets, block phishing attacks,
and deliver a high-fidelity threat signal that enhances an enterprise’s existing security and IT governance stack.

HYAS Protect for Splunk allows a Splunk® Enterprise administrator to run protect queries from an included dashboard, as well as through search commands.

##### Scripts and binaries

* protect_endpoint.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Protect.
* hyas_api_call.py
  * Internal script which has generalized request function which takes parameters and returns results of various endpoints.
* validation_command.py
  * Python script which has generalized request function which takes parameters and returns result
  whether the provided ioc name and ioc value matches.
* api_key_validation.py
  * Python script which has generalized request function which takes api key as parameter and returns result whether the provided api key is valid or not.
* validation.py
  * Python script which has generalized function which takes ioc and val as parameter and returns result.
* data_parsing.py
  * Python script which has generalized function which takes json result, parses it to remove the nesting of objects, it gives result in json format without nested object and parses data into dictionary.
* proxy_validation.py
  * Python script which has generalized function which takes host and port as parameter and returns result.
* url.py
  * Python script which has URL Regular Expression for validationg url's value.
* constants.py 
 * It contains Regex of various ioc's and constants are defined in this file.

#### Release notes

##### About this release

Version 1.2.0 of HYAS Protect for Splunk is compatible with:

| Splunk Enterprise versions | 8.1, 8.0 |
| --- | --- |
| CIM | N/A |
| Platforms | Platform independent |
| Vendor Products | HYAS Protect |
| Lookup file changes | N/A |

##### Features

Version 1.0.0 Released: 2022-June.
 * Application with search commands and enrichment dashboard, provided with various validations.


#### Performance benchmarks

In general performance impact of this app should be minimal. Individual queries will almost always take less than a second to complete. The following is a few queries listed next to the time spent executing them:

| Command                                                         | Execution Time  |
|-----------------------------------------------------------------| --------------- |
| hyasprotectverdictfordomain value=fishfarm.duckdns.org                 | 145ms         |
| hyasprotectverdictfornameserver value=ns-380.awsdns-47.com             | 145ms         |
| hyasprotectverdictforfqdn value=fishfarm.duckdns.org                   | 145ms         |
| hyasprotectverdictforip value=23.129.64.139                      | 145ms         |


##### Support and resources

Support for this app is provided by HYAS Infosec, Inc. Please send questions to support@hyas.com

* Hours: 9AM-5PM Monday-Frday
* Observed Holidays: Major US Holidays

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

This app has no hardware requirements.

#### Software requirements

HYAS Protect for Splunk can run on either Windows or Linux.

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download HYAS Protect for Splunk from https://splunkbase.splunk.com.

#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1. Download app from Splunkbase
2. Place [app.tar.gz] somewhere on your Search Head
3. Install using splunk command:
_splunk install app /path/to/app.tar.gz_
4. Set API key. This can be done in Splunkweb by clicking "Setup" in the app's navigation bar.



## USER GUIDE

### Usage

Once configured, the easiest way to use this app is through the built-in 
Protect dashboard. Select indicator type and type indicator value and press enter.

HYAS Protect for Splunk also comes with multiple commands and a lookup so that 
you can incorporate Protect queries into your own searches and dashboards. Below is usage documentation for all three of them.

### Adaptive response action

If you use Splunk's Enterprise Security product, this app includes an adaptive response action which can be used from the Incident Review view. Select any notable event you wish to run a Protect query against, select "Run Adaptive Response Actions" and then "Protect Lookup". Select the indicator type from dropdown (ip address, domain, fqdn, nameserver), type of the value of indicator (eg.1.1.1.1) and any other inputs needed. Click "Run", and then refresh the adaptive responses panel of that notable events. Clicking "Protect Lookup" in that panel will send you to a search containing the output of your lookup. 





### hyasprotectverdictfordomain command

Runs this command to get the hyas verdict for domain.


**Examples**

_| hyasprotectverdictfordomain value=fishfarm.duckdns.org_




### hyasprotectverdictforfqdn command

Runs this command to get the hyas verdict for FQDN.


**Examples**

_| hyasprotectverdictforfqdn value=www.fishfarm.duckdns.org_




### hyasprotectverdictfornameserver command

Runs this command to get the hyas verdict for nameserver.


**Examples**

_| hyasprotectverdictfornameserver value=ns2.duckdns.org_




### hyasprotectverdictforip command

Runs this command to get the hyas verdict for IP.


**Examples**

_| hyasprotectverdictforip value=23.129.64.139_




### Configure HYAS Protect for Splunk

The only configuration needed for this app is setting an API key. This can be done in Splunkweb by clicking "Set up" on the "Manage apps" page, or through commandline by editing password.conf.

### Troubleshooting

***Problem***
App returns error "Invalid API Key".".

***Cause***
API Key is missing or incorrect.

***Resolution***
Check that your API key is entered correctly.

***Problem***
App returns error "Query limit reached".

***Cause***
You have reached your query limit. 

***Resolution***
Wait until your limit reset (probably daily at midnight) until making more queries.

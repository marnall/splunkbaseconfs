# HYAS Insight for Splunk


## Table of Contents

### OVERVIEW

- About HYAS Insight for Splunk
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

#### About HYAS Insight for Splunk

| Author                    | HYAS Infosec, Inc. |
| ------------------------- | ------------------ |
| App Version               | 1.0.4              |
| Vendor Products           | HYAS Insight       |
| Has index-time operations | false              |
| Create an index           | false              |
| Implements summarization  | false              |

HYAS Insight is a threat investigation and attribution solution that uses exclusive data sources and non-traditional mechanismsn to improve visibility and productivity for analysts, researchers, and investigators while increasing the accuracy of findings. HYAS Insight connects attack instances and campaigns to billions of indicators of compromise to deliver insights and visibility. With an easy-to-use user interface, transforms, and API access, HYAS Insight combines rich threat data into a powerful research and attribution solution. HYAS Insight is complemented by the HYAS Intelligence team that helps organizations to better understand the nature of the threats they face on a daily basis.

HYAS Insight for Splunk allows a Splunk® Enterprise administrator to run insight queries from an included dashboard, as well as through search commands.

##### Scripts and binaries

* passive.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Insight Passive DNS end point.
* dynamic.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Insight Dynamic DNS end point.
* passivehash.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Insight Passivehash end point.
* device.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Insight Device end point.
* hyas_ssl.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Insight SSL Certificate end point.
* sink.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Insight Sink end point.
* whois.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Insight WhoIs end point.
* whoiscurrent.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Insight WhoIs Current end point.
* whoiscurrent.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Insight WhoIs Current end point.
* cattribution.py
  * This python script takes ioc name and ioc value as input from the user and shows the enriched data from HYAS Insight C2Attribution end point.
* os_indicator.py
  * This python script takes ioc name and ioc value as input from the user 
    and shows the enriched data from HYAS Insight OS Indicator end point.
* sample.py
  * This python script takes ioc name and ioc value as input from the user 
    and shows the enriched data from HYAS Insight Sample end point.
* sample_information.py
  * This python script takes ioc name and ioc value as input from the user 
    and shows the enriched data from HYAS Insight sample/information end point.
* data_parsing.py
  * Internal script used to Validate User Inputs.
* hyas_api_call.py
  * Internal script which has generalized request function which takes parameters and returns results of various endpoints.
* validation_command.py
  * Internal script which has generalized request function which takes parameters and returns result
  whether the provided ioc name and ioc value matches.
* api_key_validation.py
  * Internal script which has generalized request function which takes api key as parameter and returns result whether the provided api key is valid or not.
* validation.py
  * Internal script which has generalized function which takes ioc and val as parameter and returns result.
* data_parsing.py
  * Internal script which has generalized function which takes json result, parses it to remove the nesting of objects and gives result in json format without nested object.


#### Release notes

##### About this release

Version 1.2.0 of HYAS Insight for Splunk is compatible with:

| Splunk Enterprise versions | 9.0, 8.2, 8.1, 8.0   |
| -------------------------- | -------------------- |
| CIM                        | 5.x                  |
| Platforms                  | Platform independent |
| Vendor Products            | HYAS Insight         |
| Lookup file changes        | N/A                  |

##### Features

Version 1.0.0 Released: 2022-June
 * Application with search commands and enrichment dashboard, provided with various validations.


#### Performance benchmarks

In general performance impact of this app should be minimal. Individual queries will almost always take less than a second to complete. The following is a few queries listed next to the time spent executing them:

| Command                                                                                          | Execution Time |
| ------------------------------------------------------------------------------------------------ | -------------- |
| hyasinsightpassivedns type=ip value=1.1.1.1                                                      | 12.904s        |
| hyasinsightdynamicdns type=email value=bitbar@gmail.com                                          | 2.315s         |
| hyasinsightc2attribution sha256 281af32d4b70417c5027c9590f494aa9026c540a5c8af407dc3d464afe0a23ae | 5.138s         |
| hyasinsightwhois type=email value=bitbar@gmail.com                                               | 6.025s         |
| hyasinsightpassivehash type=ip value=4.4.4.4                                                     | 2.522s         |
| hyasinsightsslcertificate type=ip value=4.4.4.4                                                  | 2.459s         |
| hyasinsightdevice type=ip value=4.4.4.4                                                          | 3.722s         |
| hyasinsightmalwareinformation type=hash value=3e1811b957957ff27a15ef46c0a1dcf6                   | 2.362s         |
| hyasinsightmalwarerecord type=hash value=1d0a97c41afe5540edd0a8c1fb9a0f1c                        | 2.172s         |
| hyasinsightdevice type=ip value=4.4.4.4                                                          | 3.722s         |
| hyasinsightwhoiscurrent type=ip value=4.4.4.4                                                    | 1.769s         |





##### Support and resources

Support for this app is provided by HYAS Infosec, Inc. Please send questions to support@hyas.com

* Hours: 9AM-5PM Monday-Frday
* Observed Holidays: Major US Holidays

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

This app has no hardware requirements.

#### Software requirements

HYAS Insight for Splunk can run on either Windows or Linux.

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download HYAS Insight for Splunk  at https://splunkbase.splunk.com/.

#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1. Download app from Splunkbase
2. Place [app.tar.gz] somewhere on your Search Head
3. Install using splunk command:
_splunk install app /path/to/app.tar.gz_
4. Set API key. This can be done in Splunkweb by clicking "Setup" in the app's navigation bar.



## USER GUIDE

### Usage

Once configured, the easiest way to use this app is through the built-in Insight dashboard. Choose a time range, select indicator type and type indicator value and press enter.

HYAS Insight for Splunk also comes with multiple commands and a lookup so that 
you can incorporate Insight queries into your own searches and dashboards. Below is usage documentation for all three of them.

### Adaptive response action

If you use Splunk's Enterprise Security product, this app includes an adaptive response action which can be used from the Incident Review view. Select any notable event you wish to run a Insight query against, select "Run Adaptive Response Actions" and then "Insight Lookup". Select the indicator type from dropdown (ip address, domain, email address, sha256, phone number), type of the value of indicator (eg.1.1.1.1) and any other inputs needed. Click "Run", and then refresh the adaptive responses panel of that notable events. Clicking "Insight Lokup" in that panel will send you to a search containing the output of your lookup. 

### hyasinsightpassivedns command

Runs a HYAS Insight PassiveDNS query against the given Ioc Value and will 
return the latest results.
Supported indicator types are **IPv4, Domain**.

**Syntax**

_hyasinsightpassivedns type=ioc_name value=ioc_value_


**Examples**

_| hyasinsightpassivedns type=ip value=1.1.1.1_

_| hyasinsightpassivedns type=domain value="example.com"_


### hyasinsightdynamicdns command

Runs a HYAS Insight DynamicDNS query against the given Ioc Value and will 
return the latest results.
Supported indicator types are **IPv4, IPv6, Email, Domain**.

**Syntax**

_hyasinsightdynamicdns type=ioc_name value=ioc_value_


**Examples**

_| hyasinsightdynamicdns type=ip value=1.1.1.1_

_| hyasinsightdynamicdns type=email value="a@gmail.com"_


### hyasinsightpassivehash command

Runs a HYAS Insight Passivehash query against the given Ioc Value and will return the latest results.
Supported indicator types are **IPv4, Domain**.

**Syntax**

_hyasinsightpassivehash type=ioc_name value=ioc_value_


**Examples**

_| hyasinsightpassivehash type=ip value=1.1.1.1_

### hyasinsightsslcertificate command

Runs a HYAS Insight SSL certificate query against the given Ioc Value and 
will return the latest results.
Supported indicator types are **IPv4, IPv6, Domain, SHA1**.

**Syntax**

_hyasinsightsslcertificate type=ioc_name value=ioc_value_


**Examples**

_| hyasinsightsslcertificate type=ip value=1.1.1.1_

### hyasinsightwhois command

Runs a HYAS Insight WhoIS query against the given Ioc Value and will return the latest results.
Supported indicator types are **Domain, Phone, Email**.

**Syntax**

_hyasinsightwhois type=ioc_name type=ioc_value_


**Examples**

_| hyasinsightwhois type=phone value=+89876543210_

_| hyasinsightwhois type=email value=a@gmail.com_

_| hyasinsightwhois type=domain value=www.google.com_

### hyasinsightsinkhole command

Runs a HYAS Insight Sink query against the given Ioc Value and will return the latest results.
Supported indicator types are **IPv4**.

**Syntax**

_hyasinsightsinkhole type=ioc_name value=ioc_value_


**Examples**

_| hyasinsightsinkhole type=ip value=1.1.1.1_

### hyasinsightdevice command

Runs a HYAS Insight Device query against the given Ioc Value and will return the latest results.
Supported indicator types are **IPv4, IPv6**.

**Syntax**

_hyasinsightdevice type=ioc_name value=ioc_value_


**Examples**

_| hyasinsightdevice type=ip value=1.1.1.1_

### hyasinsightwhoiscurrent command

Runs a HYAS Insight WhoIS Current query against the given Ioc Value and will return the latest results.
Supported indicator types are **Domain**.

**Syntax**

_hyasinsightwhoiscurrent type=ioc_name value=ioc_value_


**Examples**

_| hyasinsightwhoiscurrent type=domain value=www.google.com_


### hyasinsightc2attribution command

Runs a HYAS Insight C2attribution query against the given Ioc Value and will return the latest results.
Supported indicator types are **Domain, Email, IPv4, IPv6, SHA256**.

**Syntax**

_hyasinsightc2attribution type=ioc_type value=ioc_value_


**Examples**

_| hyasinsightc2attribution type=ip value=1.1.1.1_

_| hyasinsightc2attribution type=email value=a@gmail.com_

_| hyasinsightc2attribution type=domain value=www.google.com_

_| hyasinsightc2attribution type=sha256 value=281af32d4b70417c5027c9590f494aa9026c540a5c8af407dc3d464afe0a23ae_


### hyasinsightmalwareinformation command

Runs a HYAS Insight malware information query against the given Ioc Value and will return the latest results.
Supported indicator types are **sha256, md5, sha1, sha512**.

**Syntax**

_hyasinsightmalwareinformation type=ioc_type value=ioc_value_

**Examples**

_| hyasinsightmalwareinformation type="hash" value="3e1811b957957ff27a15ef46c0a1dcf6"_


### hyasinsightmalwarerecord command

Runs a HYAS Insight malware record query against the given Ioc Value and will return the latest results.
Supported indicator types are **md5, Domain, IPv4**.


**Syntax**

_hyasinsightmalwarerecord type=ioc_type value=ioc_value_


**Examples**

_| hyasinsightmalwarerecord type="hash" value="3e1811b957957ff27a15ef46c0a1dcf6"_


### hyasinsightosindicatorrecord command

Runs a HYAS Insight OS indicator record query against the given Ioc Value and will return the latest results.
Supported indicator types are **md5, SHA256, SHA1, Domain, IPv4, IPv6**.

**Syntax**

_hyasinsightosindicatorrecord type=ioc_type value=ioc_value_


**Examples**

_| hyasinsightosindicatorrecord type="hash" value="3e1811b957957ff27a15ef46c0a1dcf6"_


### Configure HYAS Insight for Splunk

The only configuration needed for this app is setting an API key. This can be done in Splunkweb by clicking "Set up" on the "Manage apps" page, or through commandline by editing password.conf.

### Troubleshooting

***Problem***
App returns error "Authorization failed. Check API key".

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

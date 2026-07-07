# IPQualityScore (IPQS) Threat Risk Scoring


## Table of Contents

### OVERVIEW

- About IPQualityScore (IPQS) Threat Risk Scoring
- Release notes
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

#### About IPQualityScore (IPQS) Threat Risk Scoring

| Author | IPQualityScore |
| --- |-------|
| App Version | 1 |
| Vendor Products | IPQualityScore |
| Has index-time operations | false |
| Create an index | false |
| Implements summarization | false |

The IPQualityScore fraud detection API suite features a variety of different risk analysis APIs designed to Proactively Prevent Fraud™ with industry leading accuracy to identify fraudulent users, suspicious payments, and abusive behavior. From small and medium sized businesses to enterprise companies and the internet's most popular sites, IPQS has the right solutions to solve your challenges with online fraud prevention and user validation.

IPQualityScore (IPQS) Threat Risk Scoring allows a Splunk® Enterprise administrator to run insight queries from an included dashboard, as well as through search commands.


#### Release notes

##### About this release

Version 1.2.1 of IPQualityScore (IPQS) Threat Risk Scoring is compatible with:

| Splunk Enterprise versions |9.3, 9.2, 9.1, 9.0, 8.2, 8.1, 8.0   |
| --- |---------------------|
| CIM | 5.x                 |
| Platforms | Platform independent |
| Vendor Products | IPQualityScore        |
| Lookup file changes | N/A                 |

##### Features

Version 1.2.1 Released: 2024-December

 * Added Dark Web Leak API command.
  
 * Added IPQS Account Management Login History API command.

 * Lookup ipdetection command queries from *.ipqs db files.

##### Support and resources

Support for this app is provided by IPQualityScore. Please send questions to support@ipqualityscore.com

* Hours: 9AM-5PM Monday-Frday
* Observed Holidays: Major US Holidays

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

This app has no hardware requirements.

#### Software requirements

IPQualityScore (IPQS) Threat Risk Scoring can run on either Windows or Linux.

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download IPQualityScore (IPQS) Threat Risk Scoring at https://splunkbase.splunk.com/app/5423.

#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1. Download app from Splunkbase
2. Place [app.tar.gz] somewhere on your Search Head
3. Install using splunk command:
_splunk install app /path/to/app.tar.gz_
4. Set API key. This can be done in Splunkweb by clicking "Setup" in the app's navigation bar.



## USER GUIDE

### Usage

Once configured, the easiest way to use this app is through the built-in dashboard. Choose a time range, select indicator type and type indicator value and press enter.

IPQualityScore (IPQS) Threat Risk Scoring also comes with multiple commands and a lookup so that you can incorporate queries into your own searches and dashboards. Below is usage documentation for all three of them.

### Adaptive response action

If you use Splunk's Enterprise Security product, this app includes an adaptive response action which can be used from the Incident Review view. Select any notable event you wish to run a Insight query against, select "Run Adaptive Response Actions" and then "Insight Lookup". Select the indicator type from dropdown (ip address, domain, email address, url, phone number), type of the value of indicator (eg.1.1.1.1) and any other inputs needed. Click "Run", and then refresh the adaptive responses panel of that notable events. Clicking "Insight Lokup" in that panel will send you to a search containing the output of your lookup. 

### ipdetection command

Runs a IPQualityScore Proxy Detection & Fraud Prevention API against the given Ioc Value and will return the latest results.
Supported indicator types are **IP**.

**Syntax**

_... | ipdetection field=<field_name> [strictness=<int>] [user_agent=<string>] [user_language=<string>] [fast=(true|false)] [mobile=(true|false)] [allow_public_access_points=(true|false)] [lighter_penalties=(true|false)] [transaction_strictness=<int>]_

**Examples**

… | ipdetection field=”src_ip” strictness=2 fast=true


### emailvalidation command

Runs a IPQualityScore Email Validation API against the given Ioc Value and will return the latest results.
Supported indicator types are **Email**.

**Syntax**

_… | emailvalidation field=<field_name> [fast=(true|false)] [timeout=<int>] [suggest_domain=(true|false)] [strictness=<int>] [abuse_strictness=<int>]_


**Examples**

_… | emailvalidation field=”email_address” strictness=2 timeout=30_


### urlchecker command

Runs a IPQualityScore Malicious URL Scanner & Domain Reputation API against the given Ioc Value and will return the latest results.
Supported indicator types are **Domain**.

**Syntax**

_… | urlchecker field=<field_name> [strictness=<int>] [fast=(true|false)] [timeout=<int>]_


**Examples**

_… | urlchecker field=”redirect_url” strictness=2 fast=false timeout=2_

### phonevalidation command

Runs a IPQualityScore Phone Validation & Reputation API against the given Ioc Value and will return the latest results.
Supported indicator types are **Phone**.

**Syntax**

_… | phonevalidation field=<field_name> [strictness=<int>] [country=<string>][enhanced_line_check=(true|false)] [enhanced_name_check=(true|false)]_


**Examples**

_… | phonevalidation field=”phone” strictness=2_


### leakeddata command

Runs a IPQualityScore Dark Web Leak API against the given Ioc Value and will return the leaked data.
Supported indicator types are **Email**, **Password**, **Username**.

**Syntax**

_… | leakeddata field=<field_name> field_type=username|password|email


**Examples**

_… | urlchecker field=”redirect_url” field_type=email


### ipqsipreputation command
Runs a IPQualityScore Proxy Detection & Fraud Prevention API against the given Ioc Value and will return the latest results.
Supported indicator types are **IP**.

**Syntax**

_... | ipdetection value=1.1.1.1 [strictness=<int>] [user_agent=<string>] [user_language=<string>] [fast=(true|false)] [mobile=(true|false)] [allow_public_access_points=(true|false)] [lighter_penalties=(true|false)] [transaction_strictness=<int>]_

**Examples**

… | ipqsipreputation value=1.1.1.1 strictness=2 fast=true


### ipqsemailvalidation command

Runs a IPQualityScore Email Validation API against the given Ioc Value and will return the latest results.
Supported indicator types are **Email**.

**Syntax**

_… | ipqsemailvalidation value=abc@test.com [fast=(true|false)] [timeout=<int>] [suggest_domain=(true|false)] [strictness=<int>] [abuse_strictness=<int>]_


**Examples**

_… | ipqsemailvalidation value=abc@test.com strictness=2 timeout=30_


### ipqsurlscanner command

Runs a IPQualityScore Malicious URL Scanner & Domain Reputation API against the given Ioc Value and will return the latest results.
Supported indicator types are **Domain**.

**Syntax**

_… | ipqsurlscanner value=google.com|https://google.com [strictness=<int>] [fast=(true|false)] [timeout=<int>]_


**Examples**

_… | urlchecker value=google.com strictness=2 fast=false timeout=2_

### ipqsphonevalidation command

Runs a IPQualityScore Phone Validation & Reputation API against the given Ioc Value and will return the latest results.
Supported indicator types are **Phone**.

**Syntax**

_… | ipqsphonevalidation value=91 9999900000 [strictness=<int>] [country=<string>][enhanced_line_check=(true|false)] [enhanced_name_check=(true|false)]_


**Examples**

_… | ipqsphonevalidation value=91 9999900000 strictness=2_


### ipqsleakeddata command

Runs a IPQualityScore Dark Web Leak API against the given Ioc Value and will return the leaked data.
Supported indicator types are **Email**, **Password**, **Username**.

**Syntax**

_… | ipqsleakeddata value=abc@test.com value_type=username|password|email



**Examples**

_… | ipqsleakeddata value=abc@test.com value_type=email

### ipqsloginhistory command

Runs a IPQS Login History API that provides detailed insights into recent and historical login events and authentication attempts on your IPQS account, enabling you to track unauthorized access attempts, detect suspicious activity, and conduct thorough security audits.

**Syntax**

_… | ipqsloginhistory


### Configure IPQualityScore (IPQS) Threat Risk Scoring

The only configuration needed for this app is setting an API key. This can be done in Splunkweb by clicking "Set up" on the "Manage apps" page, or through commandline by editing password.conf.


**For IPQS Reputation Database**

Please provide the URL path for IPQS Local Database search in the 'IPQS IPV4 DB File URL' and 'IPQS IPV6 DB File URL' accordingly.

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

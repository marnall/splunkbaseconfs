# Cybersixgill Darkfeed Enrichment for Splunk


## Table of Contents

### OVERVIEW

- About Cybersixgill Darkfeed Enrichment for Splunk
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

#### About Cybersixgill Darkfeed Enrichment for Splunk

| Author | Cybersixgill |
| --- | --- |
| App Version | 1.0.1

Cybersixgill Darkfeed Enrichment for Splunk allows a Splunk® Enterprise administrator to run queries from an included dashboard, as well as through search commands.

##### Scripts and binaries

* postid_enrich.py
  * This python script takes postId as input from the user and shows the enriched data from Cybersixgill end point.
* actor_enrich.py
  * This python script takes actor as input from the user and shows the enriched data from Cybersixgill end point.
* ip_enrich.py
  * This python script takes IPV4 as input from the user and shows the enriched data from Cybersixgill end point.
* domain_enrich.py
  * This python script takes domain as input from the user and shows the enriched data from Cybersixgill end point.
* hash_enrich.py
  * This python script takes hash as input from the user and shows the enriched data from Cybersixgill end point.
* url_enrich.py
  * This python script takes URL as input from the user and shows the enriched data from Cybersixgill end point.
* credcommand.py
  * Internal script used to authenticate Cybersixgill credentials client_id and client_secret.
* proxy_setup.py
  * Internal script used to take the proxy details and calls the Cybersixgill client package.
* data_parsing.py
  * Internal script which takes the raw data generated from Cybersixgill end point and returns the parsed data.

#### Release notes

##### About this release

Version 1.0.1 of Cybersixgill Darkfeed Enrichment for Splunk is compatible with:

| Splunk Enterprise versions | 8.2, 8.1, 8.0 |
##### Features


##### Cybersixgill Enrich IOC Lookup
This lookup helps you to perfrom lookup action in the fields. You can pass any IOC among (IPV4, Hash, URL, Domain, Postid, Actor) it will redirect you to the dashboard page where you would need to still select the type of Ioc you selected.

##### Support and resources

Support for this app is provided by Cybersixgill. Please send questions to support@cybersixgill.com

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

This app has no hardware requirements.

#### Software requirements

Cybersixgill Darkfeed Enrichment for Splunk can run on either Windows or Linux.

#### Splunk Enterprise system requirements

Because this app runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.


#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1. Download app from Splunkbase
2. Place [app.tar.gz] somewhere on your Search Head
3. Install using splunk command:
_splunk install app /path/to/app.tar.gz_



## USER GUIDE

### Usage

Once the app is installed or downloaded from splunkbase and the app will redirect you to the setup configuration page. Once the Configuration is complete the easiest way to use this app is through dashboard just select the type of IOC you want to enrich and enter the Value and hit the submit button. Only one IOC can be enriched at a time.

Cybersixgill for Splunk also comes with six commands, dashboard and a lookup so that you can incorporate Cybersixgill queries into your own searches and dashboards. Below is usage documentation for all three of them.

### Cyberisxgill Enrich command

Runs a Cybersixgill query on the given target.

**Syntax**

| cybersixgillipenrich 8.8.8.8


**Examples**

| cybersixgillurlenrich http://google.com/
| cybersixgillhashenrich 34nkrb2ku2342n3svsdfdfdsdfsdfsdf

### Configure Cybersixgill for Splunk

The only configuration needed for this app is setting client_id and client_secret. This can be accomplished by setup page in the app settings or if not configured the app will redirect you to the setup page.

### Troubleshooting

***Problem***
App returns error "AuthException('Bad response to URL: https://api.cybersixgill.com/auth/token in POST method [status_code: 400, reason: Bad Request]')"
***Cause***
Client Id, Client Secret is missing or incorrect.
***Resolution***
Check that your Client Id, Client Secret is entered correctly.


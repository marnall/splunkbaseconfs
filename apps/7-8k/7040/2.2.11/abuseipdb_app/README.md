# Splunk App for AbuseIPDB

## Description

This application's goal is to integrate [AbuseIPDB's API](https://docs.abuseipdb.com/) functionality with Splunk. Splunk users can check specific IP addresses against AbuseIPDB's database, report bad IPs, view reports for a given IP, and retrieve a list of known bad IPs. This is accomplished using Python and the [Requests library](https://pypi.org/project/requests/), which is included as a lib, along with urllib3.

## Usage

Install the app and launch it. You'll be directed to a setup page where you must enter your 80-character AbuseIPDB API key to continue. The application provides a link to register a new account, which comes with a key. Remember that users must be given the "list_storage_passwords" capability in order to make API calls with the secret key. Afterwards, you can use the three commands

`abuseipdbcheck`

`abuseipdbreport`

`abuseipdbreports`

to perform the given command against the API. For example:

`|makeresults|abuseipdbcheck ip=127.0.0.1`

checks the loopback address for reports of malicious behavior (this is understood to be a "test input" by the API). See the documentation page for more details.

You can also utilize the AbuseIPDB blacklist API by getting a one-off copy through a search command, or by turning on blacklist auto-update in the options page. Afterwards, you'll be able to access this blacklist with a KV lookup.

## Help

This application was developed by the AbuseIPDB team. If you need support, contact <splunk@abuseipdb.com>.

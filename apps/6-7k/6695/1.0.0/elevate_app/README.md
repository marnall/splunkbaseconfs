# Elevate App For Splunk v1.0.0

## Overview

This is a Splunk App for integrating with the Elevate Security platform.

The integration is bi-directional and comprises of : 

* A custom modular input to poll the Elevate REST API , index the JSON data and generate CSV lookups for watchlists.
* A custom search command and alert action to synchronously and asynchronously stream data from Splunk into Behaviour buckets in Elevate.The data is exported/streamed as NDJSON via HTTP POST.

## Dependencies

* Splunk 8.0+ Enterprise or Cloud
* Elevate Security account

## Enterprise Installation

* Untar the App release to your `$SPLUNK_HOME/etc/apps` directory
* Restart Splunk and Login

## Cloud Installation

* Install the App as per Splunk documentation
* https://docs.splunk.com/Documentation/SplunkCloud/9.0.2208/Admin/SelfServiceAppInstall

## Full Documentation

For full documentation , simple login to Splunk and browse to the Elevate App's landing page
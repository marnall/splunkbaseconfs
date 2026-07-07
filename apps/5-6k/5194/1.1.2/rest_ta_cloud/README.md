# Splunk REST API Modular Input for Cloud v1.1.2

## Overview

This is a Splunk Modular Input for polling data from REST APIs and indexing the responses.

This is a custom version of the standard [REST API Modular Input](https://splunkbase.splunk.com/app/1546) to satisfy any cloud vetting criteria that is over and above "AppInspect Passed" vetting.

Only use this version for deploying into your Splunk Cloud environment.Use the standard [REST API Modular Input](https://splunkbase.splunk.com/app/1546) for your own hosted Splunk environments (on premise / your own cloud environment).

Your Activation Key will work on both REST API Modular Input Apps.

Due to this App being generic to poll any REST/HTTP API and the nature of all the possible fields you can potentially configure in this App , there are countless areas where you could potentially enter a sensitive credential .. in a URL , in part of a URL , in a URL argument , in an HTTP Header property , in a HTTP body payload, in custom auth handler arguments , in custom response handler arguments ,  in a password/token/key field etc..  

Due to the constraints of Splunk Cloud Vetting , it is not feasible to migrate the Modular Input setup user interface (that typically lives under the Data Inputs menu) from the standard [REST API Modular Input App](https://splunkbase.splunk.com/app/1546/) to the Cloud Version.

So this Cloud version of the App has a custom setup page to allow you to copy/paste a REST stanza from `inputs.conf` from the standard  [REST API Modular Input App](https://splunkbase.splunk.com/app/1546/) , and the entire stanza will be encrypted and referenced by a key. At runtime this key is used to retrieve and decrypt the REST stanza from `passwords.conf`.

This design allows for any possible text anywhere in the configuration that a user might enter to be automatically and enforceably encrypted.

Functionally , everything else is exactly the same as the standard  [REST API Modular Input App](https://splunkbase.splunk.com/app/1546/).

If this App requires any customizations for your specific use case for Splunk Cloud or features that would require filesystem access (not permitted in Splunk Cloud) , then we can provide this service to our [Premium Support Plan customers](https://www.baboonbones.com/#support).

We can build a custom release of the App specific to your requirements for submitting to Splunk Cloud.

* custom encryption requirements
* custom setup pages
* custom response handlers
* custom authentication handlers
* custom client certificates
* custom python libraries for any code plugins

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Activation Key

You require an activation key to use this App. Visit [http://www.baboonbones.com/#activation](http://www.baboonbones.com/#activation) to obtain a non-expiring key


## Features

* Perform HTTPS GET/POST/PUT/HEAD requests to REST endpoints and output the responses to Splunk
* Multiple authentication mechanisms
* Add custom HTTPS Header properties
* Add custom URL arguments
* HTTPS Streaming Requests
* HTTPS Proxy support , supports HTTP CONNECT Verb
* Response regex patterns to filter out responses
* Configurable polling interval
* Configurable timeouts
* Configurable indexing of error codes
* Persist and retrieve cookies

## Authentication

The following authentication mechanisms are supported:

* None
* HTTP Basic
* HTTP Digest
* OAuth1
* OAuth2 (with auto refresh of the access token)
* Custom

## Dependencies

* Splunk Cloud or Splunk On-Premise


## Custom Authentication Handlers

You can provide your own custom Authentication Handler. This is a Python class that you should add to the `rest_ta_cloud/bin/authhandlers.py` module.

http://docs.python-requests.org/en/latest/user/advanced/#custom-authentication

You can then declare this class name and any parameters in the REST Input setup page.

## Custom Response Handlers

You can provide your own custom Response Handler. This is a Python class that you should add to the `rest_ta_cloud/bin/responsehandlers.py` module.

You can then declare this class name and any parameters in the REST Input setup page.


## Token substitution in Endpoint URL

There is support for dynamic token substitution in the endpoint URL

ie : /someurl/foo/$sometoken$/goo 

$sometoken$ will get substituted with the output of the 'sometoken' function in bin/tokens.py

So you can add you own tokens simply by adding a function to bin/tokens.py

Currenty there is 1 token implemented , $datetoday$ , which will resolve to today's date in format "2014-02-18"

Token replacement functions in the URL can also return a list of values, that will cause 
multiple URL's to be formed and the requests for these URL's will be executed in parallel in multiple threads. 

## Certificate Verification

By default, certificate verification is disabled.

If you wish to enable certificate verification then you can provide the path to a CA Bundle file when setting up your REST stanza.

More info on the CA Bundle File here , https://requests.readthedocs.io/en/master/user/advanced/#ssl-cert-verification


## Logging

Modular Input logs will get written to `$SPLUNK_HOME/var/log/splunk/restmodinput_app_modularinput.log`

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/restmodinput_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Input logging level can be specified in the input stanza you setup. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.


## Troubleshooting

* Any firewalls blocking outgoing HTTP calls
* Is your REST URL, headers, url arguments correct
* Is your authentication setup correctly

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.

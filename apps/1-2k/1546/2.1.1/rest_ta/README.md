# Splunk REST API Modular Input v2.1.1

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Overview

This is a Splunk modular input add-on for polling REST APIs.

## Activation Key

You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key


## Features

* Perform HTTP(s) GET/POST/PUT/HEAD requests to REST endpoints and output the responses to Splunk
* Multiple authentication mechanisms
* Add custom HTTP(s) Header properties
* Add custom URL arguments
* HTTP(s) Streaming Requests
* HTTP(s) Proxy support , supports HTTP CONNECT Verb
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

* Splunk 5.0+
* Supported on Windows, Linux, MacOS, Solaris, FreeBSD, HP-UX, AIX

## Setup

* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk
* If you are using a Splunk UI Browse to `Settings -> Data Inputs -> REST` to add a new Input stanza via the UI
* If you are not using a Splunk UI (ie: you are running on a Universal Forwarder) , you need to add a stanza to inputs.conf directly as per the specification in `README/inputs.conf.spec`. The `inputs.conf` file should be placed in a `local` directory under an App or User context.

## Custom Authentication Handlers

You can provide your own custom Authentication Handler. This is a Python class that you should add to the rest_ta/bin/authhandlers.py module.

http://docs.python-requests.org/en/latest/user/advanced/#custom-authentication

You can then declare this class name and any parameters in the REST Input setup page.

## Custom Response Handlers

You can provide your own custom Response Handler. This is a Python class that you should add to the rest_ta/bin/responsehandlers.py module.

You can then declare this class name and any parameters in the REST Input setup page.


## Encryption of credentials

If you require an encrypted credential in your configuration , then you can enter it on the `rest_ta` setup page.

Then in your configration stanza refer to it in the format `{encrypted:somekey}`

Where `somekey` is any value you choose to enter on the setup page to refer to your credential.

### EXAMPLES

* `endpoint = http://foo.com/{encrypted:somekey}`
* `http_header_propertys = authkey={encrypted:somekey}`
* `url_args = mysecret={encrypted:somekey}`


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

If you wish to enable certificate verification then you can provide the path to a CA Bundle file when setting up your REST stanza, or use the default bundled "certifi" CA Bundle.

More info on the CA Bundle File here , https://requests.readthedocs.io/en/master/user/advanced/#ssl-cert-verification


## Logging

Modular Input logs will get written to `$SPLUNK_HOME/var/log/splunk/restmodinput_app_modularinput.log`

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/restmodinput_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Input logging level can be specified in the input stanza you setup. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.

## Troubleshooting

* You are using Splunk 5+
* Look for any errors in the logs.
* Any firewalls blocking outgoing HTTP calls
* Is your REST URL, headers, url arguments correct
* Is you authentication setup correctly

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.

# Splunk Pubnub Modular Input v1.5.0

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Overview

This is a Splunk modular input add-on for subscribing to Pubnub channels

## Dependencies

* Splunk 6.3+
* Supported on Windows, Linux, MacOS, Solaris, FreeBSD, HP-UX, AIX
* Pycrypto

## Setup

* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk
* If you are using a Splunk UI Browse to `Settings -> Data Inputs -> Pubnub` to add a new Input stanza via the UI
* If you are not using a Splunk UI (ie: you are running on a Universal Forwarder) , you need to add a stanza to inputs.conf directly as per the specification in `README/inputs.conf.spec`. The `inputs.conf` file should be placed in a `local` directory under an App or User context.

## Activation Key

You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key

## Pycrypto Module

You have to obtain, build and add the pycrypto package yourself :

https://pypi.python.org/pypi/pycrypto

The simplest way is to build pycrypto and drop the "Crypto" directory in $SPLUNK_HOME/etc/apps/pubnub_ta/bin.
I don't recommend installing the pycrypto package to the Splunk Python runtime's site-packages, this could have unforeseen side effects.

### Building and installing PyCrypto

I do not bundle the pycrypto module with the core release , because :

* you need to build it for each separate platform
* US export controls for encrypted software

So , here are a few instructions for building and installing pycrypto yourself :

* Download the pycrypto package from https://pypi.python.org/pypi/pycrypto

* Then run these 3 commands  (note : you will  need to use a System python 2.7 runtime , not the Splunk python runtime)

        python setup.py build
        python setup.py install
        python setup.py test
        
* browse to where the Crypto module was installed to ie: /usr/local/lib/python2.7/dist-packages/Crypto

* Copy the "Crypto" directory to $SPLUNK_HOME/etc/apps/pubnub_ta/bin


## Configuration

You will need a Pubnub account to use this Modular Alert.

You can sign up at pubnub.com

Once your account is setup you will then be able to obtain your Subscribe Key from your profile.

## Encryption of credentials

If you require an encrypted credential in your configuration , then you can enter it on the setup page.

Then in your configration stanza refer to it in the format `{encrypted:somekey}`

Where `somekey` is any value you choose to enter on the setup page to refer to your credential.

## Custom Response Handlers

You can provide your own custom Response Handler. This is a Python class that you should add to the 
rest_ta/bin/responsehandlers.py module.

You can then declare this class name and any parameters in the REST Input setup page.


## Logging

Modular Input logs will get written to `$SPLUNK_HOME/var/log/splunk/pubnubmodinput_app_modularinput.log`

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/pubnubmodinput_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Input logging level can be specified in the input stanza you setup. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.



## Troubleshooting

* You are using Splunk 5+
* Is your channel name correct ?
* Is your subscription key correct ?

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.

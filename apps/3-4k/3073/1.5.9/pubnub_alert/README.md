# Splunk Pubnub Modular Alert v1.5.9

## IMPORTANT

The Python code in this App is dual 2.7/3 compatible.
This version of the App enforces Python 3 for execution of the modular input script when running on Splunk 8+ in order to satisfy Splunkbase AppInspect requirements.
If running this App on Splunk versions prior to 8 , then Python 2.7 will get executed.


## Overview

This is a Splunk Modular Alert for sending messages to a Pubnub channel

## Dependencies

* Splunk 6.3+
* Supported on Windows, Linux, MacOS, Solaris, FreeBSD, HP-UX, AIX
* Pycrypto

## Setup

* Untar the release to your $SPLUNK_HOME/etc/apps directory
* Restart Splunk

## Activation Key

You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key

## Pycrypto Module

You have to obtain, build and add the pycrypto package yourself :

https://pypi.python.org/pypi/pycrypto

The simplest way is to build pycrypto and drop the "Crypto" directory in $SPLUNK_HOME/etc/apps/pubnub_alert/bin.
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
        
3) browse to where the Crypto module was installed to ie: /usr/local/lib/python2.7/dist-packages/Crypto

4) Copy the "Crypto" directory to $SPLUNK_HOME/etc/apps/pubnub_alert/bin


## Configuration

You will need a Pubnub account to use this Modular Alert.

You can sign up at pubnub.com

Once your account is setup you will then be able to obtain your Publish Key from your profile.

## Encryption of credentials

If you require an encrypted credential in your configuration , then you can enter it on the setup page.

Then in your configration stanza refer to it in the format `{encrypted:somekey}`

Where `somekey` is any value you choose to enter on the setup page to refer to your credential.

## Using

Perform a search in Splunk and then navigate to : Save As -> Alert -> Trigger Actions -> Add Actions -> Publish to Pubnub

On this dialogue you can enter your Pubnub  "channel" and "message"

For the message field , token substitution can be used just the same as for email alerts.

http://docs.splunk.com/Documentation/Splunk/latest/Alert/Setupalertactions#Tokens_available_for_email_notifications

## Logging

Modular Alert logs will get written to `$SPLUNK_HOME/var/log/splunk/pubnubalert_app_modularalert.log`

Setup logs will get written to `$SPLUNK_HOME/var/log/splunk/pubnubalert_app_setuphandler.log`

These logs are rotated daily with a backup limit of 5.

The Modular Alert logging level can be specified on the setup page. The default level is `INFO`.

You can search for these log sources in the `_internal` index or browse to the `Logs` menu item on the App's navigation bar.

## Troubleshooting

1) Is your "channel" correct ?
2) Are your alerts actually firing ?
3) Is your publish key correct ?

## Support

[BaboonBones.com](http://www.baboonbones.com#support) offer commercial support for implementing and any questions pertaining to this App.


